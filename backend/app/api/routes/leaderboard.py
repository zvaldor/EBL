from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta

from app.db.session import get_db
from app.db.models import User, PointLog, Visit, VisitParticipant, Bath
from app.api.deps import get_current_user

router = APIRouter(prefix="/leaderboard", tags=["leaderboard"])


@router.get("")
async def get_leaderboard(
    period: str = Query("year", regex="^(year|month|week|all)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    now = datetime.utcnow()
    if period == "week":
        start = (now - timedelta(days=now.weekday())).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
    elif period == "month":
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    elif period == "year":
        start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        start = None

    q = (
        select(
            User.id,
            User.full_name,
            User.username,
            func.coalesce(func.sum(PointLog.points), 0).label("total_points"),
            func.count(func.distinct(VisitParticipant.visit_id)).label("visit_count"),
            func.count(func.distinct(Bath.id)).label("bath_count"),
        )
        .join(PointLog, PointLog.user_id == User.id)
        .join(VisitParticipant, VisitParticipant.user_id == User.id)
        .join(Visit, Visit.id == VisitParticipant.visit_id)
        .outerjoin(Bath, Bath.id == Visit.bath_id)
        .where(
            User.is_active == True,
            Visit.status.in_(["confirmed", "draft", "pending"]),
        )
        .group_by(User.id, User.full_name, User.username)
        .order_by(func.coalesce(func.sum(PointLog.points), 0).desc())
    )
    if start:
        q = q.where(Visit.visited_at >= start)

    result = await db.execute(q)
    rows = result.all()

    return [
        {
            "rank": i + 1,
            "user_id": row.id,
            "full_name": row.full_name,
            "username": row.username,
            "points": float(row.total_points or 0),
            "visit_count": row.visit_count or 0,
            "bath_count": row.bath_count or 0,
        }
        for i, row in enumerate(rows)
    ]
