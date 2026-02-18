import enum
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, DateTime, Enum, Integer, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class ApplicationStage(str, enum.Enum):
    PREPARING = "preparing"        # Tailoring CV / cover letter
    SUBMITTED = "submitted"        # Application sent
    SCREENING = "screening"        # Phone/recruiter screen
    INTERVIEW_1 = "interview_1"    # First round interview
    INTERVIEW_2 = "interview_2"    # Second round
    INTERVIEW_3 = "interview_3"    # Third round / final panel
    ASSESSMENT = "assessment"      # Case study / technical test
    REFERENCE = "reference"        # Reference check stage
    OFFER = "offer"                # Offer made
    NEGOTIATING = "negotiating"    # Negotiating terms
    ACCEPTED = "accepted"          # Offer accepted
    DECLINED = "declined"          # Declined the offer
    REJECTED = "rejected"          # Rejected by employer
    GHOSTED = "ghosted"            # No response after submission


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Links
    job_id: Mapped[int] = mapped_column(Integer, index=True)  # FK to jobs
    job_title: Mapped[str] = mapped_column(String(255))       # Denormalized for quick display
    company: Mapped[str] = mapped_column(String(255))

    # Stage tracking
    stage: Mapped[ApplicationStage] = mapped_column(
        Enum(ApplicationStage), default=ApplicationStage.PREPARING, index=True
    )
    stage_history: Mapped[Optional[list]] = mapped_column(
        JSON
    )  # [{stage, date, notes}]

    # Key dates
    submitted_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    last_activity_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    next_action_date: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Contacts involved
    recruiter_name: Mapped[Optional[str]] = mapped_column(String(255))
    recruiter_agency: Mapped[Optional[str]] = mapped_column(String(255))
    hiring_manager_name: Mapped[Optional[str]] = mapped_column(String(255))
    contacts_involved: Mapped[Optional[list]] = mapped_column(
        JSON
    )  # list of connection IDs

    # Application materials
    cv_version: Mapped[Optional[str]] = mapped_column(String(100))   # e.g. "v3_singapore_rm"
    cover_letter_used: Mapped[bool] = mapped_column(Boolean, default=False)
    referral_used: Mapped[bool] = mapped_column(Boolean, default=False)
    referral_connection_id: Mapped[Optional[int]] = mapped_column(Integer)

    # Offer details
    offer_salary: Mapped[Optional[int]] = mapped_column(Integer)
    offer_currency: Mapped[Optional[str]] = mapped_column(String(10))
    offer_details: Mapped[Optional[str]] = mapped_column(Text)

    # Notes and learnings
    notes: Mapped[Optional[str]] = mapped_column(Text)
    interview_notes: Mapped[Optional[list]] = mapped_column(
        JSON
    )  # [{round, date, interviewer, questions, outcome}]
    lessons_learned: Mapped[Optional[str]] = mapped_column(Text)
    is_starred: Mapped[bool] = mapped_column(Boolean, default=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self) -> str:
        return f"<Application {self.job_title} @ {self.company} [{self.stage}]>"
