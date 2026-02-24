from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.db.session import get_db
from app.db.models import User, PointLog, VisitParticipant, Visit
from app.api.deps import get_current_user, get_admin_user

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me")
async def get_me(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    pts_q = await db.execute(
        select(func.sum(PointLog.points)).where(PointLog.user_id == current_user.id)
    )
    points = pts_q.scalar() or 0.0

    visits_q = await db.execute(
        select(func.count(VisitParticipant.visit_id))
        .join(Visit, Visit.id == VisitParticipant.visit_id)
        .where(
            VisitParticipant.user_id == current_user.id,
            Visit.status.in_(["confirmed", "draft", "pending"]),
        )
    )
    visit_count = visits_q.scalar() or 0

    return {
        "id": current_user.id,
        "username": current_user.username,
        "full_name": current_user.full_name,
        "is_admin": current_user.is_admin,
        "points": float(points),
        "visit_count": visit_count,
    }


@router.get("")
async def list_users(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    result = await db.execute(
        select(User, func.coalesce(func.sum(PointLog.points), 0).label("pts"))
        .outerjoin(PointLog, PointLog.user_id == User.id)
        .group_by(User.id)
        .order_by(User.full_name)
    )
    rows = result.all()
    return [
        {
            "id": u.id,
            "username": u.username,
            "full_name": u.full_name,
            "is_admin": u.is_admin,
            "is_active": u.is_active,
            "points": float(pts or 0),
        }
        for u, pts in rows
    ]


class UserUpdate(BaseModel):
    is_admin: Optional[bool] = None
    is_active: Optional[bool] = None
    full_name: Optional[str] = None


@router.put("/{user_id}")
async def update_user(
    user_id: int,
    data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    q = await db.execute(select(User).where(User.id == user_id))
    user = q.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(user, field, value)
    await db.commit()
    await db.refresh(user)
    return {
        "id": user.id,
        "username": user.username,
        "full_name": user.full_name,
        "is_admin": user.is_admin,
        "is_active": user.is_active,
    }
