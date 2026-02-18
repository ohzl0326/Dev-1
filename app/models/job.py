import enum
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    String, Text, Float, DateTime, Enum, Boolean, Integer, JSON
)
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class JobStatus(str, enum.Enum):
    NEW = "new"                    # Just discovered, not yet reviewed
    REVIEWING = "reviewing"        # Currently evaluating fit
    SHORTLISTED = "shortlisted"    # Decided to apply
    APPLIED = "applied"            # Application submitted
    INTERVIEWING = "interviewing"  # In interview process
    OFFER = "offer"                # Offer received
    ACCEPTED = "accepted"          # Offer accepted
    REJECTED = "rejected"          # Rejected (by them or you)
    WITHDRAWN = "withdrawn"        # Withdrew application
    CLOSED = "closed"              # Role no longer open


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Core identity
    title: Mapped[str] = mapped_column(String(255), index=True)
    company: Mapped[str] = mapped_column(String(255), index=True)
    location: Mapped[str] = mapped_column(String(100), index=True)
    url: Mapped[str] = mapped_column(String(1000), unique=True, index=True)
    source: Mapped[str] = mapped_column(String(50))  # seek, efinancialcareers, etc.

    # Description and details
    description: Mapped[Optional[str]] = mapped_column(Text)
    requirements: Mapped[Optional[str]] = mapped_column(Text)
    salary_min: Mapped[Optional[int]] = mapped_column(Integer)
    salary_max: Mapped[Optional[int]] = mapped_column(Integer)
    salary_currency: Mapped[Optional[str]] = mapped_column(String(10))
    employment_type: Mapped[Optional[str]] = mapped_column(String(50))  # full-time, contract
    seniority_level: Mapped[Optional[str]] = mapped_column(String(50))

    # Market classification
    market_type: Mapped[Optional[str]] = mapped_column(String(50))  # public, private, multi-asset
    is_asset_management: Mapped[bool] = mapped_column(Boolean, default=False)

    # Scoring
    relevance_score: Mapped[float] = mapped_column(Float, default=0.0)
    score_breakdown: Mapped[Optional[dict]] = mapped_column(JSON)

    # Workflow status
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus), default=JobStatus.NEW, index=True
    )
    notes: Mapped[Optional[str]] = mapped_column(Text)
    is_starred: Mapped[bool] = mapped_column(Boolean, default=False)

    # Contacts at this company
    internal_contacts: Mapped[Optional[list]] = mapped_column(JSON)  # list of connection IDs

    # Timestamps
    posted_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    discovered_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    closes_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    def __repr__(self) -> str:
        return f"<Job {self.title} @ {self.company} [{self.location}] score={self.relevance_score:.2f}>"
