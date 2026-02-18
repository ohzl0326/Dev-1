"""Jobs API — CRUD + filtering + status transitions."""
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.job import Job, JobStatus

router = APIRouter(prefix="/jobs", tags=["jobs"])


class JobResponse(BaseModel):
    id: int
    title: str
    company: str
    location: str
    url: str
    source: str
    description: Optional[str]
    salary_min: Optional[int]
    salary_max: Optional[int]
    salary_currency: Optional[str]
    employment_type: Optional[str]
    seniority_level: Optional[str]
    market_type: Optional[str]
    is_asset_management: bool
    relevance_score: float
    score_breakdown: Optional[dict]
    status: JobStatus
    notes: Optional[str]
    is_starred: bool
    posted_date: Optional[datetime]
    discovered_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class JobUpdate(BaseModel):
    status: Optional[JobStatus] = None
    notes: Optional[str] = None
    is_starred: Optional[bool] = None


class JobsListResponse(BaseModel):
    total: int
    items: List[JobResponse]


@router.get("", response_model=JobsListResponse)
async def list_jobs(
    status: Optional[JobStatus] = None,
    location: Optional[str] = None,
    min_score: float = Query(default=0.0, ge=0.0, le=1.0),
    starred_only: bool = False,
    source: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    sort_by: str = Query(default="relevance_score", pattern="^(relevance_score|discovered_at|posted_date|company)$"),
    sort_dir: str = Query(default="desc", pattern="^(asc|desc)$"),
    db: AsyncSession = Depends(get_db),
):
    query = select(Job)

    if status:
        query = query.where(Job.status == status)
    if location:
        query = query.where(Job.location.ilike(f"%{location}%"))
    if min_score > 0:
        query = query.where(Job.relevance_score >= min_score)
    if starred_only:
        query = query.where(Job.is_starred == True)
    if source:
        query = query.where(Job.source == source)
    if search:
        query = query.where(
            or_(
                Job.title.ilike(f"%{search}%"),
                Job.company.ilike(f"%{search}%"),
                Job.description.ilike(f"%{search}%"),
            )
        )

    # Count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Sort
    sort_col = getattr(Job, sort_by)
    query = query.order_by(sort_col.desc() if sort_dir == "desc" else sort_col.asc())

    # Paginate
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    jobs = result.scalars().all()

    return JobsListResponse(total=total, items=jobs)


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.patch("/{job_id}", response_model=JobResponse)
async def update_job(job_id: int, update: JobUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if update.status is not None:
        job.status = update.status
    if update.notes is not None:
        job.notes = update.notes
    if update.is_starred is not None:
        job.is_starred = update.is_starred
    job.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(job)
    return job


@router.get("/stats/summary")
async def job_stats(db: AsyncSession = Depends(get_db)):
    """Summary counts for the dashboard."""
    results = {}
    for status in JobStatus:
        count_result = await db.execute(
            select(func.count(Job.id)).where(Job.status == status)
        )
        results[status.value] = count_result.scalar() or 0

    total_result = await db.execute(select(func.count(Job.id)))
    results["total"] = total_result.scalar() or 0

    avg_score_result = await db.execute(select(func.avg(Job.relevance_score)))
    results["avg_relevance_score"] = round(avg_score_result.scalar() or 0.0, 3)

    return results
