from datetime import datetime, timezone
from sqlalchemy import select, func, delete, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import Visit, VisitParticipant, PointLog, PointConfig, Bath
from app.config import settings


async def get_config(db: AsyncSession) -> dict:
    result = await db.execute(select(PointConfig))
    rows = result.scalars().all()
    cfg = {row.key: row.value for row in rows}
    defaults = {
        "base_points": 1.0,
        "long_bonus": 1.0,
        "region_bonus": 1.0,
        "country_bonus": 1.0,
        "ultraunique_bonus": 1.0,
    }
    return {**defaults, **cfg}


async def recalculate_visit(visit_id: int, db: AsyncSession) -> None:
    """Idempotent: delete old logs for this visit, then recalculate."""
    visit_q = await db.execute(select(Visit).where(Visit.id == visit_id))
    visit = visit_q.scalar_one_or_none()
    if not visit or visit.status in ("cancelled", "disputed"):
        await db.execute(delete(PointLog).where(PointLog.visit_id == visit_id))
        await db.commit()
        return

    cfg = await get_config(db)

    parts_q = await db.execute(
        select(VisitParticipant.user_id).where(VisitParticipant.visit_id == visit_id)
    )
    participant_ids = list(parts_q.scalars().all())
    if not participant_ids:
        return

    await db.execute(delete(PointLog).where(PointLog.visit_id == visit_id))

    new_logs = []
    ultraunique_start = datetime.fromisoformat(settings.ULTRAUNIQUE_START_DATE).replace(tzinfo=timezone.utc)

    bath = None
    if visit.bath_id:
        bath_q = await db.execute(select(Bath).where(Bath.id == visit.bath_id))
        bath = bath_q.scalar_one_or_none()

    # Check ultraunique: no other visits to this bath before current visit since 2023
    is_ultraunique = False
    if bath and cfg.get("ultraunique_bonus", 0) > 0:
        ultra_q = await db.execute(
            select(func.count(Visit.id)).where(
                and_(
                    Visit.bath_id == visit.bath_id,
                    Visit.id != visit_id,
                    Visit.status.in_(["confirmed", "draft", "pending"]),
                    Visit.visited_at >= ultraunique_start,
                    Visit.visited_at < visit.visited_at,
                )
            )
        )
        count = ultra_q.scalar() or 0
        if count == 0:
            # Same-day rule: must be first visit today to this bath
            day_start = visit.visited_at.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = visit.visited_at.replace(hour=23, minute=59, second=59, microsecond=999999)
            earlier_today_q = await db.execute(
                select(func.count(Visit.id)).where(
                    and_(
                        Visit.bath_id == visit.bath_id,
                        Visit.id != visit_id,
                        Visit.status.in_(["confirmed", "draft", "pending"]),
                        Visit.visited_at >= day_start,
                        Visit.visited_at <= day_end,
                        Visit.created_at < visit.created_at,
                    )
                )
            )
            earlier_today = earlier_today_q.scalar() or 0
            is_ultraunique = earlier_today == 0

    for uid in participant_ids:
        # Base points
        new_logs.append(PointLog(
            user_id=uid, visit_id=visit_id,
            points=cfg["base_points"], reason="base",
        ))

        # Long bonus
        if visit.flag_long and cfg.get("long_bonus", 0) > 0:
            new_logs.append(PointLog(
                user_id=uid, visit_id=visit_id,
                points=cfg["long_bonus"], reason="long",
            ))

        # Ultraunique bonus
        if is_ultraunique and cfg.get("ultraunique_bonus", 0) > 0:
            new_logs.append(PointLog(
                user_id=uid, visit_id=visit_id,
                points=cfg["ultraunique_bonus"], reason="ultraunique",
            ))

        # Region bonus: new region for this user in current season year
        if bath and bath.region_id and cfg.get("region_bonus", 0) > 0:
            prev_region_q = await db.execute(
                select(func.count(Visit.id))
                .join(VisitParticipant, VisitParticipant.visit_id == Visit.id)
                .join(Bath, Bath.id == Visit.bath_id)
                .where(
                    and_(
                        VisitParticipant.user_id == uid,
                        Visit.id != visit_id,
                        Bath.region_id == bath.region_id,
                        Visit.status.in_(["confirmed", "draft", "pending"]),
                        func.extract("year", Visit.visited_at) == settings.SEASON_START_YEAR,
                    )
                )
            )
            if (prev_region_q.scalar() or 0) == 0:
                new_logs.append(PointLog(
                    user_id=uid, visit_id=visit_id,
                    points=cfg["region_bonus"], reason="new_region",
                ))

        # Country bonus: new country for this user in current season year
        if bath and bath.country_id and cfg.get("country_bonus", 0) > 0:
            prev_country_q = await db.execute(
                select(func.count(Visit.id))
                .join(VisitParticipant, VisitParticipant.visit_id == Visit.id)
                .join(Bath, Bath.id == Visit.bath_id)
                .where(
                    and_(
                        VisitParticipant.user_id == uid,
                        Visit.id != visit_id,
                        Bath.country_id == bath.country_id,
                        Visit.status.in_(["confirmed", "draft", "pending"]),
                        func.extract("year", Visit.visited_at) == settings.SEASON_START_YEAR,
                    )
                )
            )
            if (prev_country_q.scalar() or 0) == 0:
                new_logs.append(PointLog(
                    user_id=uid, visit_id=visit_id,
                    points=cfg["country_bonus"], reason="new_country",
                ))

    db.add_all(new_logs)
    await db.commit()
