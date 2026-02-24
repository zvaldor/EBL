from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.db.session import get_db
from app.db.models import User
from app.db.models.config import PointConfig, DEFAULT_CONFIG
from app.api.deps import get_admin_user

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("")
async def get_settings(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    result = await db.execute(select(PointConfig))
    rows = result.scalars().all()
    cfg = {row.key: {"value": row.value, "description": row.description} for row in rows}
    for key, (default_val, desc) in DEFAULT_CONFIG.items():
        if key not in cfg:
            cfg[key] = {"value": default_val, "description": desc}
    return cfg


class SettingsUpdate(BaseModel):
    base_points: Optional[float] = None
    long_bonus: Optional[float] = None
    region_bonus: Optional[float] = None
    country_bonus: Optional[float] = None
    ultraunique_bonus: Optional[float] = None


@router.put("")
async def update_settings(
    data: SettingsUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    updates = data.model_dump(exclude_none=True)
    for key, value in updates.items():
        q = await db.execute(select(PointConfig).where(PointConfig.key == key))
        cfg = q.scalar_one_or_none()
        if cfg:
            cfg.value = value
        else:
            _, desc = DEFAULT_CONFIG.get(key, (value, ""))
            db.add(PointConfig(key=key, value=value, description=desc))
    await db.commit()
    return {"status": "ok", "updated": list(updates.keys())}
