import enum
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, DateTime, Enum, Boolean, Integer, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class OutreachStatus(str, enum.Enum):
    NEW = "new"                        # Just added, no contact yet
    PENDING_OUTREACH = "pending"       # Plan to reach out
    OUTREACH_SENT = "outreach_sent"    # First message sent
    RESPONDED = "responded"            # They replied
    CALL_SCHEDULED = "call_scheduled"  # Call/coffee booked
    MET = "met"                        # Had a conversation
    NURTURING = "nurturing"            # Ongoing, periodic contact
    REFERRED = "referred"              # Referred you to a role/contact
    STALE = "stale"                    # Lost touch, need to re-engage
    INACTIVE = "inactive"              # Not pursuing


class Connection(Base):
    __tablename__ = "connections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Identity
    name: Mapped[str] = mapped_column(String(255), index=True)
    current_title: Mapped[Optional[str]] = mapped_column(String(255))
    current_company: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    location: Mapped[Optional[str]] = mapped_column(String(100))  # Singapore, Sydney
    linkedin_url: Mapped[Optional[str]] = mapped_column(String(500))
    email: Mapped[Optional[str]] = mapped_column(String(255))

    # Context
    how_met: Mapped[Optional[str]] = mapped_column(String(500))  # "CFA Singapore networking event"
    met_at_event_id: Mapped[Optional[int]] = mapped_column(Integer, index=True)  # FK to events
    industry: Mapped[Optional[str]] = mapped_column(String(100))  # "Asset Management"
    seniority: Mapped[Optional[str]] = mapped_column(String(50))  # "VP", "Director"
    is_hiring_manager: Mapped[bool] = mapped_column(Boolean, default=False)
    is_recruiter: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationship value
    relevance_notes: Mapped[Optional[str]] = mapped_column(Text)
    warmth: Mapped[Optional[str]] = mapped_column(
        String(20)
    )  # "cold", "warm", "hot"

    # Outreach tracking
    status: Mapped[OutreachStatus] = mapped_column(
        Enum(OutreachStatus), default=OutreachStatus.NEW, index=True
    )
    outreach_history: Mapped[Optional[list]] = mapped_column(
        JSON
    )  # [{date, channel, summary, outcome}]
    last_contact_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    next_followup_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    follow_up_notes: Mapped[Optional[str]] = mapped_column(Text)

    # Outcomes
    referred_jobs: Mapped[Optional[list]] = mapped_column(JSON)  # job IDs referred
    referred_connections: Mapped[Optional[list]] = mapped_column(JSON)  # connection IDs referred
    notes: Mapped[Optional[str]] = mapped_column(Text)
    is_starred: Mapped[bool] = mapped_column(Boolean, default=False)

    # Timestamps
    added_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self) -> str:
        return f"<Connection {self.name} @ {self.current_company} [{self.status}]>"
