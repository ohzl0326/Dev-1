import enum
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, Float, DateTime, Enum, Boolean, Integer, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class EventStatus(str, enum.Enum):
    DISCOVERED = "discovered"      # Found, not yet reviewed
    INTERESTED = "interested"      # Want to attend
    REGISTERED = "registered"      # Signed up
    ATTENDED = "attended"          # Went to the event
    MISSED = "missed"              # Couldn't attend
    SKIPPED = "skipped"            # Decided not to attend


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Core identity
    name: Mapped[str] = mapped_column(String(500), index=True)
    organiser: Mapped[Optional[str]] = mapped_column(String(255))
    url: Mapped[str] = mapped_column(String(1000), unique=True, index=True)
    source: Mapped[str] = mapped_column(String(50))  # cfa_singapore, conexus, etc.

    # Classification
    event_type: Mapped[Optional[str]] = mapped_column(
        String(50)
    )  # networking, panel, conference, roundtable
    themes: Mapped[Optional[list]] = mapped_column(JSON)  # ["private markets", "institutional"]
    market_focus: Mapped[Optional[str]] = mapped_column(
        String(100)
    )  # "private markets", "public markets"

    # Logistics
    location: Mapped[Optional[str]] = mapped_column(String(255))
    is_online: Mapped[bool] = mapped_column(Boolean, default=False)
    city: Mapped[Optional[str]] = mapped_column(String(100), index=True)  # Singapore, Sydney
    is_free: Mapped[Optional[bool]] = mapped_column(Boolean)
    cost: Mapped[Optional[str]] = mapped_column(String(100))

    # Description
    description: Mapped[Optional[str]] = mapped_column(Text)
    speakers: Mapped[Optional[list]] = mapped_column(JSON)  # list of speaker names/roles
    agenda: Mapped[Optional[str]] = mapped_column(Text)

    # Scoring
    relevance_score: Mapped[float] = mapped_column(Float, default=0.0)
    networking_value: Mapped[Optional[float]] = mapped_column(Float)  # estimated networking value

    # Workflow
    status: Mapped[EventStatus] = mapped_column(
        Enum(EventStatus), default=EventStatus.DISCOVERED, index=True
    )
    notes: Mapped[Optional[str]] = mapped_column(Text)
    is_starred: Mapped[bool] = mapped_column(Boolean, default=False)

    # Connections made at this event
    connections_made: Mapped[Optional[list]] = mapped_column(JSON)  # list of connection IDs

    # Timestamps
    event_date: Mapped[Optional[datetime]] = mapped_column(DateTime, index=True)
    event_end_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    registration_deadline: Mapped[Optional[datetime]] = mapped_column(DateTime)
    discovered_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self) -> str:
        return f"<Event '{self.name}' [{self.city}] {self.event_date}>"
