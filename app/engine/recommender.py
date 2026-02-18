"""
AI-powered recommendation engine.

Uses OpenAI GPT-4o to generate prioritised, context-aware suggestions:
- Jobs to apply for (with rationale based on profile fit)
- Events to attend (with networking strategy)
- Connections to make or follow up with
- Actions (e.g. "Follow up with Jane — hasn't replied in 14 days")

The engine is given a snapshot of the user's current state (applications,
events attended, connections, goal deadline) and asked to reason about
highest-impact next steps toward the Singapore/Sydney AM RM goal.
"""
import json
import logging
from datetime import datetime, date
from typing import Optional

from app.config import settings, GOAL_PROFILE
from app.models.suggestion import SuggestionType

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """
You are a career strategy advisor specialising in the global Asset Management industry.
Your user is an experienced institutional AM professional with the following profile:

CURRENT ROLE: Institutional Client Onboarding Manager at a mid-size asset manager
EXPERIENCE: ~5 years total — 2 years as an investment analyst advising large institutional
clients on private markets fund investments, then institutional client onboarding & RM.
SKILLS: Sub-fund setup, custodian and counterparty management, multi-stakeholder project
management, investment solution design and implementation, senior client relationship management.

GOAL: Secure a role as an Institutional Relationship Manager (or equivalent) in Singapore
or Sydney, within the Asset Management industry (public or private markets), by end of Q3 2026.

TARGET ROLES: Institutional Relationship Manager, Relationship Manager, Client Relationship
Manager, Institutional Client Services — at asset managers (any AUM size, any market focus).

Your job: analyse the user's current job search state and return a JSON array of
prioritised suggestions. Each suggestion must be specific, actionable, and directly tied
to progressing toward the Q3 2026 goal. Be direct and concrete — not generic.

IMPORTANT: Return ONLY a valid JSON array. No markdown, no explanation outside the array.
"""

USER_PROMPT_TEMPLATE = """
Today's date: {today}
Days remaining to Q3 2026 deadline: {days_remaining}

CURRENT STATE SNAPSHOT:
- Active job applications: {active_applications}
- Jobs shortlisted (not yet applied): {shortlisted_jobs}
- High-relevance new jobs discovered this week: {new_jobs}
- Upcoming events registered: {registered_events}
- Interesting events discovered this week: {new_events}
- Active connections being nurtured: {active_connections}
- Connections awaiting follow-up (overdue): {overdue_followups}
- Events attended (total): {events_attended}
- Applications submitted (total): {total_applied}
- Interviews secured: {total_interviews}

TOP UNREVIEWED JOBS (title | company | location | score):
{top_jobs_list}

TOP UPCOMING EVENTS (name | city | date | score):
{top_events_list}

OVERDUE FOLLOW-UPS (name | company | last contact):
{overdue_list}

Generate 5–8 prioritised suggestions. Return a JSON array where each item has:
{{
  "type": "job" | "event" | "connection" | "action",
  "title": "concise suggestion title (max 80 chars)",
  "rationale": "1–2 sentences explaining WHY this is the right move given current state and deadline",
  "action_text": "specific next step the user should take (1 sentence)",
  "priority": "high" | "medium" | "low",
  "confidence_score": 0.0–1.0,
  "goal_alignment_score": 0.0–1.0,
  "linked_entity_name": "name of the job/event/person if applicable, else null"
}}
"""


class RecommendationEngine:
    def __init__(self):
        self._client = None

    def _get_client(self):
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY not configured — AI recommendations disabled")
        if self._client is None:
            try:
                from openai import AsyncOpenAI
                self._client = AsyncOpenAI(api_key=settings.openai_api_key)
            except ImportError:
                raise RuntimeError("openai package not installed")
        return self._client

    async def generate_suggestions(self, context: dict) -> list[dict]:
        """
        Generate suggestions given a context snapshot.

        context keys (all optional, will default to 0/"none"):
          - active_applications: int
          - shortlisted_jobs: int
          - new_jobs: list[dict] with title, company, location, score
          - registered_events: int
          - new_events: list[dict] with name, city, event_date, relevance_score
          - active_connections: int
          - overdue_followups: list[dict] with name, company, last_contact_date
          - events_attended: int
          - total_applied: int
          - total_interviews: int
        """
        client = self._get_client()

        today = date.today()
        deadline = date(2026, 9, 30)
        days_remaining = (deadline - today).days

        # Format lists for the prompt
        top_jobs = context.get("new_jobs", [])[:5]
        jobs_list = "\n".join(
            f"- {j.get('title')} | {j.get('company')} | {j.get('location')} | "
            f"score={j.get('relevance_score', 0):.2f}"
            for j in top_jobs
        ) or "  (none)"

        top_events = context.get("new_events", [])[:5]
        events_list = "\n".join(
            f"- {e.get('name')} | {e.get('city')} | {e.get('event_date', 'TBD')} | "
            f"score={e.get('relevance_score', 0):.2f}"
            for e in top_events
        ) or "  (none)"

        overdue = context.get("overdue_followups", [])[:5]
        overdue_list = "\n".join(
            f"- {o.get('name')} @ {o.get('company')} | last contact: {o.get('last_contact_date', 'unknown')}"
            for o in overdue
        ) or "  (none)"

        user_prompt = USER_PROMPT_TEMPLATE.format(
            today=today.isoformat(),
            days_remaining=days_remaining,
            active_applications=context.get("active_applications", 0),
            shortlisted_jobs=context.get("shortlisted_jobs", 0),
            new_jobs=len(top_jobs),
            registered_events=context.get("registered_events", 0),
            new_events=len(top_events),
            active_connections=context.get("active_connections", 0),
            overdue_followups=len(overdue),
            events_attended=context.get("events_attended", 0),
            total_applied=context.get("total_applied", 0),
            total_interviews=context.get("total_interviews", 0),
            top_jobs_list=jobs_list,
            top_events_list=events_list,
            overdue_list=overdue_list,
        )

        try:
            response = await client.chat.completions.create(
                model=settings.openai_model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.4,
                max_tokens=2000,
                response_format={"type": "json_object"},
            )
            raw = response.choices[0].message.content
            # The model may return {"suggestions": [...]} or just [...]
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                suggestions = parsed
            elif isinstance(parsed, dict):
                suggestions = parsed.get("suggestions", [parsed])
            else:
                suggestions = []

            logger.info(f"[recommender] Generated {len(suggestions)} suggestions")
            return suggestions

        except Exception as e:
            logger.error(f"[recommender] OpenAI call failed: {e}")
            return self._fallback_suggestions(context, days_remaining)

    def _fallback_suggestions(self, context: dict, days_remaining: int) -> list[dict]:
        """Rule-based fallback suggestions when AI is unavailable."""
        suggestions = []

        if context.get("overdue_followups"):
            suggestions.append({
                "type": "action",
                "title": "Follow up with overdue connections",
                "rationale": (
                    f"You have {len(context['overdue_followups'])} connections "
                    "who haven't heard from you recently. Consistent nurturing is "
                    "critical in relationship-driven AM hiring."
                ),
                "action_text": "Send a brief, personalised follow-up message to each overdue contact.",
                "priority": "high",
                "confidence_score": 0.9,
                "goal_alignment_score": 0.85,
                "linked_entity_name": None,
            })

        if context.get("new_jobs"):
            top = context["new_jobs"][0]
            suggestions.append({
                "type": "job",
                "title": f"Review new high-match role: {top.get('title')} at {top.get('company')}",
                "rationale": (
                    f"This role scored {top.get('relevance_score', 0):.0%} against your profile "
                    f"and is in your target location ({top.get('location')}). With "
                    f"{days_remaining} days to deadline, each application counts."
                ),
                "action_text": "Read the full JD, check for internal connections at this firm, then apply or shortlist.",
                "priority": "high",
                "confidence_score": 0.85,
                "goal_alignment_score": 0.9,
                "linked_entity_name": top.get("title"),
            })

        if context.get("new_events"):
            top_event = context["new_events"][0]
            suggestions.append({
                "type": "event",
                "title": f"Register for: {top_event.get('name')}",
                "rationale": (
                    "This event is directly relevant to your target industry and location. "
                    "In-person events are the fastest way to build relationships in Singapore/Sydney AM."
                ),
                "action_text": "Register and prepare 2–3 conversation starters about current market themes.",
                "priority": "medium",
                "confidence_score": 0.8,
                "goal_alignment_score": 0.75,
                "linked_entity_name": top_event.get("name"),
            })

        if context.get("active_applications", 0) == 0 and days_remaining < 200:
            suggestions.append({
                "type": "action",
                "title": "Increase application velocity — no active applications",
                "rationale": (
                    f"With {days_remaining} days to your Q3 2026 deadline and zero active "
                    "applications, you need to increase outreach urgency."
                ),
                "action_text": (
                    "Set a target of 3–5 applications per week. "
                    "Prioritise eFinancialCareers and LinkedIn for SG/AU AM roles."
                ),
                "priority": "high",
                "confidence_score": 0.95,
                "goal_alignment_score": 1.0,
                "linked_entity_name": None,
            })

        return suggestions


recommendation_engine = RecommendationEngine()
