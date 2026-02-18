"""Suggestions API — AI recommendations and manual trigger."""
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.suggestion import Suggestion, SuggestionType

router = APIRouter(prefix="/suggestions", tags=["suggestions"])


class SuggestionResponse(BaseModel):
    id: int
    suggestion_type: SuggestionType
    title: str
    rationale: str
    action_text: Optional[str]
    priority: Optional[str]
    linked_job_id: Optional[int]
    linked_event_id: Optional[int]
    linked_connection_id: Optional[int]
    external_url: Optional[str]
    confidence_score: float
    goal_alignment_score: float
    is_dismissed: bool
    is_acted_on: bool
    model_used: Optional[str]
    generated_at: datetime
    expires_at: Optional[datetime]

    class Config:
        from_attributes = True


class SuggestionFeedback(BaseModel):
    is_dismissed: Optional[bool] = None
    is_acted_on: Optional[bool] = None
    user_feedback: Optional[str] = None


@router.get("", response_model=List[SuggestionResponse])
async def list_suggestions(
    suggestion_type: Optional[SuggestionType] = None,
    priority: Optional[str] = None,
    include_dismissed: bool = False,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    query = select(Suggestion)

    if not include_dismissed:
        query = query.where(Suggestion.is_dismissed == False)
    if suggestion_type:
        query = query.where(Suggestion.suggestion_type == suggestion_type)
    if priority:
        query = query.where(Suggestion.priority == priority)

    # Only show non-expired suggestions
    query = query.where(
        (Suggestion.expires_at == None) | (Suggestion.expires_at >= datetime.utcnow())
    )

    query = query.order_by(
        Suggestion.goal_alignment_score.desc(),
        Suggestion.generated_at.desc(),
    ).limit(limit)

    result = await db.execute(query)
    return result.scalars().all()


@router.patch("/{suggestion_id}/feedback", response_model=SuggestionResponse)
async def submit_feedback(
    suggestion_id: int,
    feedback: SuggestionFeedback,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Suggestion).where(Suggestion.id == suggestion_id))
    suggestion = result.scalar_one_or_none()
    if not suggestion:
        raise HTTPException(status_code=404, detail="Suggestion not found")

    if feedback.is_dismissed is not None:
        suggestion.is_dismissed = feedback.is_dismissed
    if feedback.is_acted_on is not None:
        suggestion.is_acted_on = feedback.is_acted_on
        if feedback.is_acted_on:
            suggestion.acted_on_at = datetime.utcnow()
    if feedback.user_feedback is not None:
        suggestion.user_feedback = feedback.user_feedback

    await db.commit()
    await db.refresh(suggestion)
    return suggestion


@router.post("/generate", status_code=202)
async def trigger_suggestion_generation(background_tasks: BackgroundTasks):
    """Manually trigger suggestion generation (runs in background)."""
    from app.scheduler.tasks import generate_daily_suggestions
    background_tasks.add_task(generate_daily_suggestions.delay)
    return {"message": "Suggestion generation queued"}
