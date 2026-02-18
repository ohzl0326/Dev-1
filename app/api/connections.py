"""Connections (CRM) API — manage networking contacts and outreach."""
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.connection import Connection, OutreachStatus

router = APIRouter(prefix="/connections", tags=["connections"])


class OutreachEntry(BaseModel):
    date: datetime
    channel: str  # linkedin, email, phone, in-person
    summary: str
    outcome: Optional[str] = None


class ConnectionCreate(BaseModel):
    name: str
    current_title: Optional[str] = None
    current_company: Optional[str] = None
    location: Optional[str] = None
    linkedin_url: Optional[str] = None
    email: Optional[str] = None
    how_met: Optional[str] = None
    met_at_event_id: Optional[int] = None
    industry: Optional[str] = "Asset Management"
    seniority: Optional[str] = None
    is_hiring_manager: bool = False
    is_recruiter: bool = False
    relevance_notes: Optional[str] = None
    warmth: Optional[str] = "cold"
    next_followup_date: Optional[datetime] = None


class ConnectionUpdate(BaseModel):
    current_title: Optional[str] = None
    current_company: Optional[str] = None
    status: Optional[OutreachStatus] = None
    notes: Optional[str] = None
    is_starred: Optional[bool] = None
    warmth: Optional[str] = None
    next_followup_date: Optional[datetime] = None
    follow_up_notes: Optional[str] = None


class AddOutreachRequest(BaseModel):
    entry: OutreachEntry


class ConnectionResponse(BaseModel):
    id: int
    name: str
    current_title: Optional[str]
    current_company: Optional[str]
    location: Optional[str]
    linkedin_url: Optional[str]
    email: Optional[str]
    how_met: Optional[str]
    met_at_event_id: Optional[int]
    industry: Optional[str]
    seniority: Optional[str]
    is_hiring_manager: bool
    is_recruiter: bool
    relevance_notes: Optional[str]
    warmth: Optional[str]
    status: OutreachStatus
    outreach_history: Optional[list]
    last_contact_date: Optional[datetime]
    next_followup_date: Optional[datetime]
    follow_up_notes: Optional[str]
    referred_jobs: Optional[list]
    referred_connections: Optional[list]
    notes: Optional[str]
    is_starred: bool
    added_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ConnectionsListResponse(BaseModel):
    total: int
    items: List[ConnectionResponse]


@router.get("", response_model=ConnectionsListResponse)
async def list_connections(
    status: Optional[OutreachStatus] = None,
    company: Optional[str] = None,
    location: Optional[str] = None,
    starred_only: bool = False,
    overdue_only: bool = False,
    search: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    query = select(Connection)

    if status:
        query = query.where(Connection.status == status)
    if company:
        query = query.where(Connection.current_company.ilike(f"%{company}%"))
    if location:
        query = query.where(Connection.location.ilike(f"%{location}%"))
    if starred_only:
        query = query.where(Connection.is_starred == True)
    if overdue_only:
        query = query.where(Connection.next_followup_date <= datetime.utcnow())
    if search:
        query = query.where(
            or_(
                Connection.name.ilike(f"%{search}%"),
                Connection.current_company.ilike(f"%{search}%"),
                Connection.current_title.ilike(f"%{search}%"),
            )
        )

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(Connection.next_followup_date.asc().nulls_last())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    connections = result.scalars().all()

    return ConnectionsListResponse(total=total, items=connections)


@router.post("", response_model=ConnectionResponse, status_code=201)
async def create_connection(data: ConnectionCreate, db: AsyncSession = Depends(get_db)):
    connection = Connection(**data.model_dump())
    db.add(connection)
    await db.commit()
    await db.refresh(connection)
    return connection


@router.get("/{connection_id}", response_model=ConnectionResponse)
async def get_connection(connection_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Connection).where(Connection.id == connection_id))
    conn = result.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")
    return conn


@router.patch("/{connection_id}", response_model=ConnectionResponse)
async def update_connection(
    connection_id: int, update: ConnectionUpdate, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Connection).where(Connection.id == connection_id))
    conn = result.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")
    for field, value in update.model_dump(exclude_none=True).items():
        setattr(conn, field, value)
    conn.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(conn)
    return conn


@router.post("/{connection_id}/outreach", response_model=ConnectionResponse)
async def log_outreach(
    connection_id: int, request: AddOutreachRequest, db: AsyncSession = Depends(get_db)
):
    """Log a new outreach interaction with this connection."""
    result = await db.execute(select(Connection).where(Connection.id == connection_id))
    conn = result.scalar_one_or_none()
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")

    entry = request.entry.model_dump()
    entry["date"] = entry["date"].isoformat()
    history = conn.outreach_history or []
    history.append(entry)
    conn.outreach_history = history
    conn.last_contact_date = request.entry.date
    conn.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(conn)
    return conn


@router.get("/stats/summary")
async def connection_stats(db: AsyncSession = Depends(get_db)):
    results = {}
    for status in OutreachStatus:
        count_result = await db.execute(
            select(func.count(Connection.id)).where(Connection.status == status)
        )
        results[status.value] = count_result.scalar() or 0

    overdue_result = await db.execute(
        select(func.count(Connection.id)).where(
            Connection.next_followup_date <= datetime.utcnow(),
            Connection.status.in_([
                OutreachStatus.OUTREACH_SENT, OutreachStatus.RESPONDED, OutreachStatus.NURTURING
            ]),
        )
    )
    results["overdue_followups"] = overdue_result.scalar() or 0
    return results
