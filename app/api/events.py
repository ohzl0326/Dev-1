"""Events API — CRUD + filtering + status transitions."""
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.event import Event, EventStatus

router = APIRouter(prefix="/events", tags=["events"])


class EventResponse(BaseModel):
    id: int
    name: str
    organiser: Optional[str]
    url: str
    source: str
    event_type: Optional[str]
    themes: Optional[list]
    location: Optional[str]
    is_online: bool
    city: Optional[str]
    is_free: Optional[bool]
    cost: Optional[str]
    description: Optional[str]
    speakers: Optional[list]
    relevance_score: float
    networking_value: Optional[float]
    status: EventStatus
    notes: Optional[str]
    is_starred: bool
    event_date: Optional[datetime]
    event_end_date: Optional[datetime]
    registration_deadline: Optional[datetime]
    discovered_at: datetime

    class Config:
        from_attributes = True


class EventUpdate(BaseModel):
    status: Optional[EventStatus] = None
    notes: Optional[str] = None
    is_starred: Optional[bool] = None


class EventsListResponse(BaseModel):
    total: int
    items: List[EventResponse]


@router.get("", response_model=EventsListResponse)
async def list_events(
    status: Optional[EventStatus] = None,
    city: Optional[str] = None,
    event_type: Optional[str] = None,
    min_score: float = Query(default=0.0, ge=0.0, le=1.0),
    starred_only: bool = False,
    upcoming_only: bool = True,
    search: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    query = select(Event)

    if status:
        query = query.where(Event.status == status)
    if city:
        query = query.where(Event.city.ilike(f"%{city}%"))
    if event_type:
        query = query.where(Event.event_type == event_type)
    if min_score > 0:
        query = query.where(Event.relevance_score >= min_score)
    if starred_only:
        query = query.where(Event.is_starred == True)
    if upcoming_only:
        query = query.where(
            or_(Event.event_date >= datetime.utcnow(), Event.event_date == None)
        )
    if search:
        query = query.where(
            or_(
                Event.name.ilike(f"%{search}%"),
                Event.organiser.ilike(f"%{search}%"),
                Event.description.ilike(f"%{search}%"),
            )
        )

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(Event.event_date.asc().nulls_last(), Event.relevance_score.desc())
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    events = result.scalars().all()

    return EventsListResponse(total=total, items=events)


@router.get("/{event_id}", response_model=EventResponse)
async def get_event(event_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Event).where(Event.id == event_id))
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@router.patch("/{event_id}", response_model=EventResponse)
async def update_event(event_id: int, update: EventUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Event).where(Event.id == event_id))
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if update.status is not None:
        event.status = update.status
    if update.notes is not None:
        event.notes = update.notes
    if update.is_starred is not None:
        event.is_starred = update.is_starred
    event.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(event)
    return event


@router.get("/stats/summary")
async def event_stats(db: AsyncSession = Depends(get_db)):
    results = {}
    for status in EventStatus:
        count_result = await db.execute(
            select(func.count(Event.id)).where(Event.status == status)
        )
        results[status.value] = count_result.scalar() or 0

    upcoming_result = await db.execute(
        select(func.count(Event.id)).where(Event.event_date >= datetime.utcnow())
    )
    results["upcoming"] = upcoming_result.scalar() or 0
    return results
