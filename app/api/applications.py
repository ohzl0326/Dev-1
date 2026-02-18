"""Applications API — track job application pipeline with stage history."""
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.application import Application, ApplicationStage

router = APIRouter(prefix="/applications", tags=["applications"])


class InterviewNote(BaseModel):
    round: str
    date: datetime
    interviewer: Optional[str] = None
    format: Optional[str] = None  # "video", "in-person", "phone"
    questions: Optional[str] = None
    outcome: Optional[str] = None
    notes: Optional[str] = None


class ApplicationCreate(BaseModel):
    job_id: int
    job_title: str
    company: str
    stage: ApplicationStage = ApplicationStage.PREPARING
    cv_version: Optional[str] = None
    cover_letter_used: bool = False
    referral_used: bool = False
    referral_connection_id: Optional[int] = None
    recruiter_name: Optional[str] = None
    recruiter_agency: Optional[str] = None
    notes: Optional[str] = None


class ApplicationUpdate(BaseModel):
    stage: Optional[ApplicationStage] = None
    recruiter_name: Optional[str] = None
    recruiter_agency: Optional[str] = None
    hiring_manager_name: Optional[str] = None
    notes: Optional[str] = None
    lessons_learned: Optional[str] = None
    next_action_date: Optional[datetime] = None
    offer_salary: Optional[int] = None
    offer_currency: Optional[str] = None
    offer_details: Optional[str] = None
    is_starred: Optional[bool] = None


class ApplicationResponse(BaseModel):
    id: int
    job_id: int
    job_title: str
    company: str
    stage: ApplicationStage
    stage_history: Optional[list]
    submitted_date: Optional[datetime]
    last_activity_date: Optional[datetime]
    next_action_date: Optional[datetime]
    recruiter_name: Optional[str]
    recruiter_agency: Optional[str]
    hiring_manager_name: Optional[str]
    contacts_involved: Optional[list]
    cv_version: Optional[str]
    cover_letter_used: bool
    referral_used: bool
    referral_connection_id: Optional[int]
    offer_salary: Optional[int]
    offer_currency: Optional[str]
    offer_details: Optional[str]
    notes: Optional[str]
    interview_notes: Optional[list]
    lessons_learned: Optional[str]
    is_starred: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ApplicationsListResponse(BaseModel):
    total: int
    items: List[ApplicationResponse]


@router.get("", response_model=ApplicationsListResponse)
async def list_applications(
    stage: Optional[ApplicationStage] = None,
    company: Optional[str] = None,
    active_only: bool = False,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    query = select(Application)

    if stage:
        query = query.where(Application.stage == stage)
    if company:
        query = query.where(Application.company.ilike(f"%{company}%"))
    if active_only:
        active_stages = [
            ApplicationStage.PREPARING, ApplicationStage.SUBMITTED,
            ApplicationStage.SCREENING, ApplicationStage.INTERVIEW_1,
            ApplicationStage.INTERVIEW_2, ApplicationStage.INTERVIEW_3,
            ApplicationStage.ASSESSMENT, ApplicationStage.REFERENCE,
            ApplicationStage.OFFER, ApplicationStage.NEGOTIATING,
        ]
        query = query.where(Application.stage.in_(active_stages))

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(Application.updated_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    apps = result.scalars().all()

    return ApplicationsListResponse(total=total, items=apps)


@router.post("", response_model=ApplicationResponse, status_code=201)
async def create_application(data: ApplicationCreate, db: AsyncSession = Depends(get_db)):
    app = Application(**data.model_dump())
    app.stage_history = [{"stage": data.stage.value, "date": datetime.utcnow().isoformat()}]
    if data.stage == ApplicationStage.SUBMITTED:
        app.submitted_date = datetime.utcnow()
    db.add(app)
    await db.commit()
    await db.refresh(app)
    return app


@router.get("/{app_id}", response_model=ApplicationResponse)
async def get_application(app_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Application).where(Application.id == app_id))
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    return app


@router.patch("/{app_id}", response_model=ApplicationResponse)
async def update_application(
    app_id: int, update: ApplicationUpdate, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Application).where(Application.id == app_id))
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    if update.stage is not None and update.stage != app.stage:
        history = app.stage_history or []
        history.append({"stage": update.stage.value, "date": datetime.utcnow().isoformat()})
        app.stage_history = history
        app.last_activity_date = datetime.utcnow()
        if update.stage == ApplicationStage.SUBMITTED and not app.submitted_date:
            app.submitted_date = datetime.utcnow()

    for field, value in update.model_dump(exclude_none=True, exclude={"stage"}).items():
        setattr(app, field, value)

    if update.stage is not None:
        app.stage = update.stage

    app.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(app)
    return app


@router.post("/{app_id}/interview-notes", response_model=ApplicationResponse)
async def add_interview_note(
    app_id: int, note: InterviewNote, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Application).where(Application.id == app_id))
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    notes = app.interview_notes or []
    entry = note.model_dump()
    entry["date"] = entry["date"].isoformat()
    notes.append(entry)
    app.interview_notes = notes
    app.last_activity_date = datetime.utcnow()
    app.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(app)
    return app


@router.get("/stats/pipeline")
async def pipeline_stats(db: AsyncSession = Depends(get_db)):
    """Funnel stats for the application pipeline."""
    results = {}
    for stage in ApplicationStage:
        count_result = await db.execute(
            select(func.count(Application.id)).where(Application.stage == stage)
        )
        results[stage.value] = count_result.scalar() or 0
    return results
