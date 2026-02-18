import enum
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, Float, DateTime, Enum, Integer, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class SuggestionType(str, enum.Enum):
    JOB = "job"
    EVENT = "event"
    CONNECTION = "connection"
    ACTION = "action"  # e.g. "Follow up with John Smith", "Update your LinkedIn"


class Suggestion(Base):
    __tablename__ = "suggestions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    suggestion_type: Mapped[SuggestionType] = mapped_column(
        Enum(SuggestionType), index=True
    )

    # Content
    title: Mapped[str] = mapped_column(String(500))
    rationale: Mapped[str] = mapped_column(Text)  # AI-generated explanation
    action_text: Mapped[Optional[str]] = mapped_column(Text)  # What to do
    priority: Mapped[Optional[str]] = mapped_column(String(20))  # high, medium, low

    # Links to entities
    linked_job_id: Mapped[Optional[int]] = mapped_column(Integer)
    linked_event_id: Mapped[Optional[int]] = mapped_column(Integer)
    linked_connection_id: Mapped[Optional[int]] = mapped_column(Integer)
    external_url: Mapped[Optional[str]] = mapped_column(String(1000))

    # Scoring
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    goal_alignment_score: Mapped[float] = mapped_column(Float, default=0.0)

    # User interaction
    is_dismissed: Mapped[bool] = mapped_column(Boolean, default=False)
    is_acted_on: Mapped[bool] = mapped_column(Boolean, default=False)
    user_feedback: Mapped[Optional[str]] = mapped_column(Text)

    # Metadata
    model_used: Mapped[Optional[str]] = mapped_column(String(100))
    context_snapshot: Mapped[Optional[dict]] = mapped_column(JSON)  # state when generated

    # Timestamps
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    acted_on_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    def __repr__(self) -> str:
        return f"<Suggestion [{self.suggestion_type}] '{self.title}' score={self.confidence_score:.2f}>"
