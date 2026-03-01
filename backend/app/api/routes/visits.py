import os

from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from datetime import datetime, timezone, timedelta

from app.db.session import get_db
from app.db.models import User, Visit, VisitParticipant, Bath, PointLog
from app.api.deps import get_current_user, get_admin_user
from app.services.visit import set_visit_status, update_participants, set_flag_long, update_visit_bath
from app.services import sheets as sheets_svc
from app.config import settings

router = APIRouter(prefix="/visits", tags=["visits"])


def _creds() -> str:
    if settings.GOOGLE_CREDENTIALS_JSON:
        return settings.GOOGLE_CREDENTIALS_JSON
    here = os.path.dirname(__file__)
    return os.path.join(here, "..", "..", "..", "google_credentials.json")


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
        "created_by": visit.created_by,
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


@router.get("/weekly")
async def weekly_stats(
    week: Optional[int] = None,
    current_user: User = Depends(get_current_user),
):
    """Per-person visit counts for a given week from Google Sheets 'Недельный зачет'."""
    now = datetime.now(timezone.utc)
    if week is None:
        week = now.isocalendar()[1]

    week_start = datetime.fromisocalendar(now.year, week, 1).replace(tzinfo=timezone.utc)
    week_end = week_start + timedelta(days=6)
    date_range = f"{week_start.strftime('%-d %b')} – {week_end.strftime('%-d %b')}"

    try:
        report = await sheets_svc.get_weekly_stats(
            _creds(), settings.GOOGLE_SPREADSHEET_ID, week
        )
    except Exception as e:
        raise HTTPException(500, f"Sheets error: {e}")

    weekly = report["weekly"]
    return {
        "week": week,
        "date_range": date_range,
        "rows": [
            {
                "rank": i + 1,
                "name": row["name"],
                "visit_count": row["visit_count"],
                "total_visits": row.get("total_visits", 0),
            }
            for i, row in enumerate(weekly)
        ],
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
    elif not current_user.is_admin:
        # Non-admins don't see cancelled visits by default
        filters.append(Visit.status != "cancelled")
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
    current_user: User = Depends(get_current_user),
):
    q = await db.execute(select(Visit).where(Visit.id == visit_id))
    visit = q.scalar_one_or_none()
    if not visit:
        raise HTTPException(404, "Visit not found")

    is_admin = current_user.is_admin
    is_creator = visit.created_by == current_user.id

    if not is_admin and not is_creator:
        raise HTTPException(403, "Forbidden")

    if data.status is not None and not is_admin:
        raise HTTPException(403, "Only admins can change status")

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
