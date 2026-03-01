from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from datetime import datetime, timedelta

from app.db.session import get_db
from app.db.models import User, Bath, Country, Region, Visit, VisitParticipant
from app.api.deps import get_current_user, get_admin_user
from app.services.bath import create_bath, merge_baths

router = APIRouter(prefix="/baths", tags=["baths"])


def bath_to_dict(bath: Bath) -> dict:
    return {
        "id": bath.id,
        "name": bath.name,
        "aliases": bath.aliases or [],
        "country_id": bath.country_id,
        "region_id": bath.region_id,
        "city": bath.city,
        "lat": bath.lat,
        "lng": bath.lng,
        "description": bath.description,
        "url": bath.url,
        "is_archived": bath.is_archived,
        "canonical_id": bath.canonical_id,
        "created_at": bath.created_at.isoformat(),
    }


@router.get("")
async def list_baths(
    q: Optional[str] = None,
    include_archived: bool = False,
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(Bath)
    if not include_archived:
        query = query.where(Bath.is_archived == False)
    if q:
        query = query.where(Bath.name.ilike(f"%{q}%"))
    query = query.order_by(Bath.name).limit(limit).offset(offset)
    result = await db.execute(query)
    return [bath_to_dict(b) for b in result.scalars().all()]


@router.get("/countries")
async def list_countries(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Country).order_by(Country.name))
    return [{"id": c.id, "name": c.name, "code": c.code} for c in result.scalars().all()]


@router.get("/regions")
async def list_regions(
    country_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(Region).order_by(Region.name)
    if country_id:
        query = query.where(Region.country_id == country_id)
    result = await db.execute(query)
    return [{"id": r.id, "name": r.name, "country_id": r.country_id} for r in result.scalars().all()]


@router.get("/map")
async def bath_map(
    period: str = Query("all", regex="^(week|year|all)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return baths with per-user visit counts for the TMA bath map."""
    now = datetime.utcnow()
    if period == "week":
        start = (now - timedelta(days=now.weekday())).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
    elif period == "year":
        start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        start = None

    # Query: bath, user, visit_count grouped
    q = (
        select(
            Bath.id.label("bath_id"),
            Bath.name.label("bath_name"),
            Bath.city.label("city"),
            Bath.lat.label("lat"),
            Bath.lng.label("lng"),
            User.id.label("user_id"),
            User.full_name.label("full_name"),
            User.username.label("username"),
            func.count(Visit.id).label("visit_count"),
        )
        .join(Visit, Visit.bath_id == Bath.id)
        .join(VisitParticipant, VisitParticipant.visit_id == Visit.id)
        .join(User, User.id == VisitParticipant.user_id)
        .where(
            Visit.status.in_(["confirmed", "draft", "pending"]),
            Bath.is_archived == False,
        )
        .group_by(Bath.id, Bath.name, Bath.city, Bath.lat, Bath.lng, User.id, User.full_name, User.username)
        .order_by(Bath.name, func.count(Visit.id).desc())
    )
    if start:
        q = q.where(Visit.visited_at >= start)

    result = await db.execute(q)
    rows = result.all()

    # Group by bath
    baths: dict[int, dict] = {}
    for row in rows:
        if row.bath_id not in baths:
            baths[row.bath_id] = {
                "bath_id": row.bath_id,
                "bath_name": row.bath_name,
                "city": row.city,
                "lat": row.lat,
                "lng": row.lng,
                "total_visits": 0,
                "visitors": [],
            }
        baths[row.bath_id]["total_visits"] += row.visit_count
        baths[row.bath_id]["visitors"].append({
            "user_id": row.user_id,
            "full_name": row.full_name,
            "username": row.username,
            "visit_count": row.visit_count,
        })

    return sorted(baths.values(), key=lambda b: -b["total_visits"])


@router.get("/{bath_id}")
async def get_bath(
    bath_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = await db.execute(select(Bath).where(Bath.id == bath_id))
    bath = q.scalar_one_or_none()
    if not bath:
        raise HTTPException(404, "Bath not found")
    return bath_to_dict(bath)


class BathCreate(BaseModel):
    name: str
    country_id: Optional[int] = None
    region_id: Optional[int] = None
    city: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    url: Optional[str] = None
    description: Optional[str] = None


@router.post("")
async def create_bath_route(
    data: BathCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    bath = await create_bath(db, **data.model_dump())
    return bath_to_dict(bath)


class BathUpdate(BaseModel):
    name: Optional[str] = None
    aliases: Optional[list[str]] = None
    country_id: Optional[int] = None
    region_id: Optional[int] = None
    city: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    url: Optional[str] = None
    description: Optional[str] = None
    is_archived: Optional[bool] = None


@router.put("/{bath_id}")
async def update_bath(
    bath_id: int,
    data: BathUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = await db.execute(select(Bath).where(Bath.id == bath_id))
    bath = q.scalar_one_or_none()
    if not bath:
        raise HTTPException(404, "Bath not found")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(bath, field, value)
    await db.commit()
    await db.refresh(bath)
    return bath_to_dict(bath)


@router.delete("/{bath_id}")
async def delete_bath(
    bath_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    q = await db.execute(select(Bath).where(Bath.id == bath_id))
    bath = q.scalar_one_or_none()
    if not bath:
        raise HTTPException(404, "Bath not found")
    await db.delete(bath)
    await db.commit()
    return {"ok": True}


class MergeRequest(BaseModel):
    target_id: int


@router.post("/{bath_id}/merge")
async def merge_bath(
    bath_id: int,
    data: MergeRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    bath = await merge_baths(db, source_id=bath_id, target_id=data.target_id)
    return bath_to_dict(bath)
