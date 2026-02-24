from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from datetime import datetime

from app.db.session import get_db
from app.db.models import User, Visit, VisitParticipant, Bath, PointLog
from app.api.deps import get_current_user, get_admin_user
from app.services.visit import set_visit_status, update_participants, set_flag_long, update_visit_bath

router = APIRouter(prefix="/visits", tags=["visits"])


async def visit_to_dict(visit: Visit, db: AsyncSession) -> dict:
    bath = None
    if visit.bath_id:
        bath_q = await db.execute(select(Bath).where(Bath.id == visit.bath_id))
        bath = bath_q.scalar_one_or_none()

    parts_q = await db.execute(
        select(User)
        .join(VisitParticipant, VisitParticipant.user_id == User.id)
        .where(VisitParticipant.visit_id == visit.id)
    )
    participants = parts_q.scalars().all()

    logs_q = await db.execute(
        select(PointLog).where(PointLog.visit_id == visit.id)
    )
    logs = logs_q.scalars().all()

    return {
        "id": visit.id,
        "status": visit.status,
        "visited_at": visit.visited_at.isoformat(),
        "created_at": visit.created_at.isoformat(),
        "flag_long": visit.flag_long,
        "flag_ultraunique": visit.flag_ultraunique,
        "bath": {
            "id": bath.id,
            "name": bath.name,
            "city": bath.city,
            "country_id": bath.country_id,
            "region_id": bath.region_id,
        } if bath else None,
        "participants": [
            {"id": u.id, "full_name": u.full_name, "username": u.username}
            for u in participants
        ],
        "point_logs": [
            {"user_id": lg.user_id, "points": lg.points, "reason": lg.reason}
            for lg in logs
        ],
        "total_points": sum(lg.points for lg in logs),
    }


@router.get("")
async def list_visits(
    status: Optional[str] = None,
    bath_id: Optional[int] = None,
    user_id: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = select(Visit).order_by(Visit.visited_at.desc()).limit(limit).offset(offset)
    filters = []
    if status:
        filters.append(Visit.status == status)
    if bath_id:
        filters.append(Visit.bath_id == bath_id)
    if user_id:
        q = q.join(VisitParticipant, VisitParticipant.visit_id == Visit.id)
        filters.append(VisitParticipant.user_id == user_id)
    if date_from:
        filters.append(Visit.visited_at >= datetime.fromisoformat(date_from))
    if date_to:
        filters.append(Visit.visited_at <= datetime.fromisoformat(date_to))
    if filters:
        q = q.where(and_(*filters))

    result = await db.execute(q)
    visits = result.scalars().all()
    return [await visit_to_dict(v, db) for v in visits]


@router.get("/me")
async def my_visits(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = await db.execute(
        select(Visit)
        .join(VisitParticipant, VisitParticipant.visit_id == Visit.id)
        .where(VisitParticipant.user_id == current_user.id)
        .order_by(Visit.visited_at.desc())
    )
    visits = q.scalars().all()
    return [await visit_to_dict(v, db) for v in visits]


@router.get("/{visit_id}")
async def get_visit(
    visit_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = await db.execute(select(Visit).where(Visit.id == visit_id))
    visit = q.scalar_one_or_none()
    if not visit:
        raise HTTPException(404, "Visit not found")
    return await visit_to_dict(visit, db)


class VisitUpdate(BaseModel):
    status: Optional[str] = None
    flag_long: Optional[bool] = None
    bath_id: Optional[int] = None
    participant_ids: Optional[list[int]] = None


@router.put("/{visit_id}")
async def update_visit(
    visit_id: int,
    data: VisitUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    q = await db.execute(select(Visit).where(Visit.id == visit_id))
    visit = q.scalar_one_or_none()
    if not visit:
        raise HTTPException(404, "Visit not found")

    if data.status:
        visit = await set_visit_status(db, visit_id, data.status)
    if data.flag_long is not None:
        visit = await set_flag_long(db, visit_id, data.flag_long)
    if data.bath_id is not None:
        visit = await update_visit_bath(db, visit_id, data.bath_id)
    if data.participant_ids is not None:
        visit = await update_participants(db, visit_id, data.participant_ids)

    return await visit_to_dict(visit, db)


@router.post("/{visit_id}/approve")
async def approve_visit(
    visit_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    visit = await set_visit_status(db, visit_id, "confirmed")
    return await visit_to_dict(visit, db)


@router.post("/{visit_id}/cancel")
async def cancel_visit(
    visit_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    visit = await set_visit_status(db, visit_id, "cancelled")
    return await visit_to_dict(visit, db)


@router.post("/{visit_id}/dispute")
async def dispute_visit(
    visit_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    visit = await set_visit_status(db, visit_id, "disputed")
    return await visit_to_dict(visit, db)
