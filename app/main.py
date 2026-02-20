"""
Career Tracker — FastAPI application entry point.

Endpoints:
  GET  /health              — health check
  GET  /api/dashboard       — summary stats for dashboard
  *    /api/jobs            — job discovery and tracking
  *    /api/events          — event discovery and tracking
  *    /api/connections     — networking CRM
  *    /api/applications    — application pipeline
  *    /api/suggestions     — AI recommendations
  POST /api/scrape/jobs     — manually trigger job scrape
  POST /api/scrape/events   — manually trigger event scrape
"""
import logging
from contextlib import asynccontextmanager
from datetime import date, datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select, func

from app.database import init_db, AsyncSessionLocal
from app.config import GOAL_PROFILE

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Career Tracker API...")
    await init_db()
    logger.info("Database initialised")
    yield
    logger.info("Shutting down Career Tracker API")


app = FastAPI(
    title="Career Tracker",
    description=(
        "Personal job, event and networking tracker for Asset Management "
        "and Banking roles in London. Q3 2026 deadline."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Register routers ---
from app.api.jobs import router as jobs_router
from app.api.events import router as events_router
from app.api.connections import router as connections_router
from app.api.applications import router as applications_router
from app.api.suggestions import router as suggestions_router

app.include_router(jobs_router, prefix="/api")
app.include_router(events_router, prefix="/api")
app.include_router(connections_router, prefix="/api")
app.include_router(applications_router, prefix="/api")
app.include_router(suggestions_router, prefix="/api")


@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


@app.get("/api/dashboard")
async def dashboard_summary():
    """Aggregated stats for the main dashboard view."""
    from app.models.job import Job, JobStatus
    from app.models.event import Event, EventStatus
    from app.models.connection import Connection, OutreachStatus
    from app.models.application import Application, ApplicationStage
    from app.models.suggestion import Suggestion

    deadline = date(2026, 9, 30)
    days_remaining = (deadline - date.today()).days

    async with AsyncSessionLocal() as db:
        # Jobs
        total_jobs = (await db.execute(select(func.count(Job.id)))).scalar() or 0
        new_jobs = (
            await db.execute(
                select(func.count(Job.id)).where(Job.status == JobStatus.NEW)
            )
        ).scalar() or 0
        active_apps = (
            await db.execute(
                select(func.count(Application.id)).where(
                    Application.stage.in_([
                        ApplicationStage.SUBMITTED, ApplicationStage.SCREENING,
                        ApplicationStage.INTERVIEW_1, ApplicationStage.INTERVIEW_2,
                        ApplicationStage.INTERVIEW_3, ApplicationStage.ASSESSMENT,
                    ])
                )
            )
        ).scalar() or 0

        # Events
        upcoming_events = (
            await db.execute(
                select(func.count(Event.id)).where(
                    Event.event_date >= datetime.utcnow()
                )
            )
        ).scalar() or 0
        registered_events = (
            await db.execute(
                select(func.count(Event.id)).where(Event.status == EventStatus.REGISTERED)
            )
        ).scalar() or 0

        # Connections
        total_connections = (
            await db.execute(select(func.count(Connection.id)))
        ).scalar() or 0
        overdue_followups = (
            await db.execute(
                select(func.count(Connection.id)).where(
                    Connection.next_followup_date <= datetime.utcnow()
                )
            )
        ).scalar() or 0

        # Suggestions
        active_suggestions = (
            await db.execute(
                select(func.count(Suggestion.id)).where(
                    Suggestion.is_dismissed == False,
                    Suggestion.is_acted_on == False,
                )
            )
        ).scalar() or 0

    return {
        "goal": {
            "deadline": deadline.isoformat(),
            "days_remaining": days_remaining,
            "target_locations": GOAL_PROFILE["target_locations"],
            "target_roles": ["Institutional Relationship Manager", "Relationship Manager"],
        },
        "jobs": {
            "total_discovered": total_jobs,
            "new_unreviewed": new_jobs,
            "active_applications": active_apps,
        },
        "events": {
            "upcoming": upcoming_events,
            "registered": registered_events,
        },
        "connections": {
            "total": total_connections,
            "overdue_followups": overdue_followups,
        },
        "suggestions": {
            "active": active_suggestions,
        },
    }


@app.post("/api/scrape/jobs", status_code=202)
async def trigger_job_scrape():
    """Manually trigger a job scrape cycle."""
    from app.scheduler.tasks import scrape_all_jobs
    task = scrape_all_jobs.delay()
    return {"message": "Job scrape queued", "task_id": task.id}


@app.post("/api/scrape/events", status_code=202)
async def trigger_event_scrape():
    """Manually trigger an event scrape cycle."""
    from app.scheduler.tasks import scrape_all_events
    task = scrape_all_events.delay()
    return {"message": "Event scrape queued", "task_id": task.id}
