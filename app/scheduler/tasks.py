"""
Celery task definitions for scheduled ingestion and recommendation generation.

Schedule (configurable via .env):
  - scrape_jobs:          every 12 hours
  - scrape_events:        every 24 hours
  - generate_suggestions: every 24 hours (after scrapes complete)
  - followup_reminders:   every 24 hours at 08:00 local time
"""
import asyncio
import logging
from datetime import datetime, timedelta

from celery import Celery
from celery.schedules import crontab

from app.config import settings

logger = logging.getLogger(__name__)

celery_app = Celery(
    "career_tracker",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    beat_schedule={
        # Scrape jobs twice daily
        "scrape-jobs-morning": {
            "task": "app.scheduler.tasks.scrape_all_jobs",
            "schedule": crontab(hour="7,19", minute="0"),
        },
        # Scrape events once daily
        "scrape-events-daily": {
            "task": "app.scheduler.tasks.scrape_all_events",
            "schedule": crontab(hour="8", minute="30"),
        },
        # Generate AI suggestions once daily after scrapes
        "generate-suggestions-daily": {
            "task": "app.scheduler.tasks.generate_daily_suggestions",
            "schedule": crontab(hour="9", minute="0"),
        },
        # Send follow-up reminders
        "followup-reminders-daily": {
            "task": "app.scheduler.tasks.send_followup_reminders",
            "schedule": crontab(hour="8", minute="0"),
        },
    },
)


def _run_async(coro):
    """Run an async coroutine from a sync Celery task."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(bind=True, name="app.scheduler.tasks.scrape_all_jobs", max_retries=2)
def scrape_all_jobs(self):
    """Run all job scrapers and persist new/updated jobs to the database."""
    logger.info("[tasks] Starting job scrape cycle")
    try:
        return _run_async(_scrape_jobs_async())
    except Exception as exc:
        logger.error(f"[tasks] Job scrape failed: {exc}")
        raise self.retry(exc=exc, countdown=300)


async def _scrape_jobs_async():
    from app.ingestion.jobs.efinancialcareers import EFinancialCareersScraper
    from app.ingestion.jobs.seek import SeekScraper
    from app.ingestion.jobs.jobsdb import JobsDBScraper
    from app.ingestion.jobs.linkedin import LinkedInScraper
    from app.engine.matcher import score_job
    from app.config import JOB_CRITERIA
    from app.database import AsyncSessionLocal
    from app.models.job import Job, JobStatus
    from sqlalchemy import select

    scrapers = [
        EFinancialCareersScraper(),
        SeekScraper(),
        JobsDBScraper(),
        LinkedInScraper(),
    ]

    all_jobs = []
    for Scraper in scrapers:
        try:
            async with Scraper as s:
                jobs = await s.scrape()
                all_jobs.extend(jobs)
                logger.info(f"[tasks] {s.source_name}: {len(jobs)} jobs scraped")
        except Exception as e:
            logger.error(f"[tasks] Scraper {Scraper.__class__.__name__} failed: {e}")

    # Score and persist
    new_count = 0
    async with AsyncSessionLocal() as session:
        for scraped in all_jobs:
            score, breakdown = score_job(scraped)
            if score < JOB_CRITERIA["min_score_threshold"]:
                continue  # Below threshold — skip

            # Deduplicate by URL
            existing = await session.execute(
                select(Job).where(Job.url == scraped.url)
            )
            existing_job = existing.scalar_one_or_none()

            if existing_job:
                # Update score and description if changed
                existing_job.relevance_score = score
                existing_job.score_breakdown = breakdown
                if scraped.description and len(scraped.description) > len(existing_job.description or ""):
                    existing_job.description = scraped.description
                existing_job.updated_at = datetime.utcnow()
            else:
                from app.engine.matcher import job_scorer
                job = Job(
                    title=scraped.title,
                    company=scraped.company,
                    location=scraped.location,
                    url=scraped.url,
                    source=scraped.source,
                    description=scraped.description,
                    requirements=scraped.requirements,
                    salary_min=scraped.salary_min,
                    salary_max=scraped.salary_max,
                    salary_currency=scraped.salary_currency,
                    employment_type=scraped.employment_type,
                    seniority_level=scraped.seniority_level,
                    posted_date=scraped.posted_date,
                    relevance_score=score,
                    score_breakdown=breakdown,
                    is_asset_management=breakdown.get("industry", 0) >= 0.5,
                    market_type=job_scorer.infer_market_type(scraped),
                    status=JobStatus.NEW,
                )
                session.add(job)
                new_count += 1

        await session.commit()

    logger.info(f"[tasks] Job scrape complete: {new_count} new jobs added")
    return {"new_jobs": new_count, "total_scraped": len(all_jobs)}


@celery_app.task(bind=True, name="app.scheduler.tasks.scrape_all_events", max_retries=2)
def scrape_all_events(self):
    """Run all event scrapers and persist new events to the database."""
    logger.info("[tasks] Starting event scrape cycle")
    try:
        return _run_async(_scrape_events_async())
    except Exception as exc:
        logger.error(f"[tasks] Event scrape failed: {exc}")
        raise self.retry(exc=exc, countdown=300)


async def _scrape_events_async():
    from app.ingestion.events.cfa import CFASingaporeScraper, CFASydneyScraper
    from app.ingestion.events.industry import (
        ConexusScraper, AsianInvestorScraper, AIMAEventScraper,
        CAIAScraper, FiduciaryInvestorsScraper, InvestmentMagazineScraper,
    )
    from app.ingestion.events.eventbrite import EventbriteScraper
    from app.engine.matcher import score_event
    from app.config import EVENT_CRITERIA
    from app.database import AsyncSessionLocal
    from app.models.event import Event, EventStatus
    from sqlalchemy import select

    scrapers = [
        CFASingaporeScraper(),
        CFASydneyScraper(),
        ConexusScraper(),
        AsianInvestorScraper(),
        AIMAEventScraper(),
        CAIAScraper(),
        FiduciaryInvestorsScraper(),
        InvestmentMagazineScraper(),
        EventbriteScraper(),
    ]

    all_events = []
    for Scraper in scrapers:
        try:
            async with Scraper as s:
                events = await s.scrape()
                all_events.extend(events)
                logger.info(f"[tasks] {s.source_name}: {len(events)} events scraped")
        except Exception as e:
            logger.error(f"[tasks] Event scraper {Scraper.__class__.__name__} failed: {e}")

    new_count = 0
    async with AsyncSessionLocal() as session:
        for scraped in all_events:
            score, networking_value = score_event(scraped)
            if score < EVENT_CRITERIA["min_score_threshold"]:
                continue

            existing = await session.execute(
                select(Event).where(Event.url == scraped.url)
            )
            existing_event = existing.scalar_one_or_none()

            if existing_event:
                existing_event.relevance_score = score
                existing_event.networking_value = networking_value
                if scraped.event_date:
                    existing_event.event_date = scraped.event_date
                existing_event.updated_at = datetime.utcnow()
            else:
                # Filter out past events
                if scraped.event_date and scraped.event_date < datetime.utcnow():
                    continue
                event = Event(
                    name=scraped.name,
                    organiser=scraped.organiser,
                    url=scraped.url,
                    source=scraped.source,
                    event_type=scraped.event_type,
                    themes=scraped.themes,
                    location=scraped.location,
                    is_online=scraped.is_online,
                    city=scraped.city,
                    description=scraped.description,
                    speakers=scraped.speakers,
                    is_free=scraped.is_free,
                    cost=scraped.cost,
                    event_date=scraped.event_date,
                    event_end_date=scraped.event_end_date,
                    registration_deadline=scraped.registration_deadline,
                    relevance_score=score,
                    networking_value=networking_value,
                    status=EventStatus.DISCOVERED,
                )
                session.add(event)
                new_count += 1

        await session.commit()

    logger.info(f"[tasks] Event scrape complete: {new_count} new events added")
    return {"new_events": new_count, "total_scraped": len(all_events)}


@celery_app.task(name="app.scheduler.tasks.generate_daily_suggestions")
def generate_daily_suggestions():
    """Generate AI-powered suggestions based on current state."""
    logger.info("[tasks] Generating daily suggestions")
    return _run_async(_generate_suggestions_async())


async def _generate_suggestions_async():
    from app.database import AsyncSessionLocal
    from app.models.job import Job, JobStatus
    from app.models.event import Event, EventStatus
    from app.models.connection import Connection, OutreachStatus
    from app.models.application import Application, ApplicationStage
    from app.models.suggestion import Suggestion, SuggestionType
    from app.engine.recommender import recommendation_engine
    from sqlalchemy import select, func

    async with AsyncSessionLocal() as session:
        # Build context snapshot
        one_week_ago = datetime.utcnow() - timedelta(days=7)
        fourteen_days_ago = datetime.utcnow() - timedelta(days=14)

        new_jobs_result = await session.execute(
            select(Job).where(
                Job.discovered_at >= one_week_ago,
                Job.status == JobStatus.NEW,
            ).order_by(Job.relevance_score.desc()).limit(10)
        )
        new_jobs = new_jobs_result.scalars().all()

        new_events_result = await session.execute(
            select(Event).where(
                Event.discovered_at >= one_week_ago,
                Event.status == EventStatus.DISCOVERED,
            ).order_by(Event.relevance_score.desc()).limit(10)
        )
        new_events = new_events_result.scalars().all()

        active_apps_result = await session.execute(
            select(func.count(Application.id)).where(
                Application.stage.in_([
                    ApplicationStage.SUBMITTED, ApplicationStage.SCREENING,
                    ApplicationStage.INTERVIEW_1, ApplicationStage.INTERVIEW_2,
                    ApplicationStage.INTERVIEW_3, ApplicationStage.ASSESSMENT,
                ])
            )
        )
        active_apps_count = active_apps_result.scalar() or 0

        shortlisted_result = await session.execute(
            select(func.count(Job.id)).where(Job.status == JobStatus.SHORTLISTED)
        )
        shortlisted_count = shortlisted_result.scalar() or 0

        overdue_result = await session.execute(
            select(Connection).where(
                Connection.next_followup_date <= datetime.utcnow(),
                Connection.status.in_([
                    OutreachStatus.OUTREACH_SENT, OutreachStatus.RESPONDED,
                    OutreachStatus.NURTURING,
                ])
            ).limit(10)
        )
        overdue = overdue_result.scalars().all()

        registered_events_result = await session.execute(
            select(func.count(Event.id)).where(Event.status == EventStatus.REGISTERED)
        )
        registered_count = registered_events_result.scalar() or 0

        attended_result = await session.execute(
            select(func.count(Event.id)).where(Event.status == EventStatus.ATTENDED)
        )
        attended_count = attended_result.scalar() or 0

        total_applied_result = await session.execute(
            select(func.count(Application.id))
        )
        total_applied = total_applied_result.scalar() or 0

        total_interviews_result = await session.execute(
            select(func.count(Application.id)).where(
                Application.stage.in_([
                    ApplicationStage.INTERVIEW_1, ApplicationStage.INTERVIEW_2,
                    ApplicationStage.INTERVIEW_3,
                ])
            )
        )
        total_interviews = total_interviews_result.scalar() or 0

        active_connections_result = await session.execute(
            select(func.count(Connection.id)).where(
                Connection.status.in_([
                    OutreachStatus.RESPONDED, OutreachStatus.NURTURING,
                    OutreachStatus.CALL_SCHEDULED, OutreachStatus.MET,
                ])
            )
        )
        active_connections = active_connections_result.scalar() or 0

        context = {
            "active_applications": active_apps_count,
            "shortlisted_jobs": shortlisted_count,
            "new_jobs": [
                {
                    "title": j.title,
                    "company": j.company,
                    "location": j.location,
                    "relevance_score": j.relevance_score,
                }
                for j in new_jobs
            ],
            "registered_events": registered_count,
            "new_events": [
                {
                    "name": e.name,
                    "city": e.city,
                    "event_date": e.event_date.isoformat() if e.event_date else None,
                    "relevance_score": e.relevance_score,
                }
                for e in new_events
            ],
            "active_connections": active_connections,
            "overdue_followups": [
                {
                    "name": c.name,
                    "company": c.current_company,
                    "last_contact_date": (
                        c.last_contact_date.isoformat() if c.last_contact_date else "unknown"
                    ),
                }
                for c in overdue
            ],
            "events_attended": attended_count,
            "total_applied": total_applied,
            "total_interviews": total_interviews,
        }

        suggestions_data = await recommendation_engine.generate_suggestions(context)

        for s_data in suggestions_data:
            type_map = {
                "job": SuggestionType.JOB,
                "event": SuggestionType.EVENT,
                "connection": SuggestionType.CONNECTION,
                "action": SuggestionType.ACTION,
            }
            suggestion = Suggestion(
                suggestion_type=type_map.get(s_data.get("type", "action"), SuggestionType.ACTION),
                title=s_data.get("title", "")[:500],
                rationale=s_data.get("rationale", ""),
                action_text=s_data.get("action_text"),
                priority=s_data.get("priority", "medium"),
                confidence_score=float(s_data.get("confidence_score", 0.5)),
                goal_alignment_score=float(s_data.get("goal_alignment_score", 0.5)),
                model_used=settings.openai_model,
                context_snapshot=context,
                expires_at=datetime.utcnow() + timedelta(days=7),
            )
            session.add(suggestion)

        await session.commit()
        logger.info(f"[tasks] {len(suggestions_data)} suggestions saved")
        return {"suggestions_generated": len(suggestions_data)}


@celery_app.task(name="app.scheduler.tasks.send_followup_reminders")
def send_followup_reminders():
    """Send reminders for overdue connection follow-ups."""
    logger.info("[tasks] Checking follow-up reminders")
    return _run_async(_reminders_async())


async def _reminders_async():
    from app.database import AsyncSessionLocal
    from app.models.connection import Connection, OutreachStatus
    from app.notifications.notifier import send_notification
    from sqlalchemy import select

    async with AsyncSessionLocal() as session:
        overdue = await session.execute(
            select(Connection).where(
                Connection.next_followup_date <= datetime.utcnow(),
                Connection.status.in_([
                    OutreachStatus.OUTREACH_SENT, OutreachStatus.RESPONDED,
                    OutreachStatus.NURTURING, OutreachStatus.CALL_SCHEDULED,
                ]),
            ).limit(20)
        )
        contacts = overdue.scalars().all()

        if contacts:
            names = ", ".join(c.name for c in contacts[:5])
            more = f" (+{len(contacts) - 5} more)" if len(contacts) > 5 else ""
            message = (
                f"📋 Follow-up reminder: {len(contacts)} connections need attention\n"
                f"{names}{more}\n"
                f"Open the tracker to see details."
            )
            await send_notification(message)

    return {"reminders_sent": len(contacts)}
