from datetime import datetime, timezone
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import Visit, VisitParticipant, User
from app.services.points import recalculate_visit


async def get_or_create_user(db: AsyncSession, tg_user) -> User:
    q = await db.execute(select(User).where(User.id == tg_user.id))
    user = q.scalar_one_or_none()
    if not user:
        user = User(
            id=tg_user.id,
            username=tg_user.username,
            full_name=tg_user.full_name or str(tg_user.id),
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    else:
        changed = False
        if user.username != tg_user.username:
            user.username = tg_user.username
            changed = True
        if tg_user.full_name and user.full_name != tg_user.full_name:
            user.full_name = tg_user.full_name
            changed = True
        if changed:
            await db.commit()
    return user


async def create_visit(
    db: AsyncSession,
    bath_id: int | None,
    created_by: int,
    message_id: int,
    chat_id: int,
    participant_ids: list[int],
    flag_long: bool = False,
    visited_at: datetime | None = None,
) -> Visit:
    now = datetime.now(timezone.utc)
    visit = Visit(
        bath_id=bath_id,
        created_by=created_by,
        message_id=message_id,
        chat_id=chat_id,
        status="confirmed",
        visited_at=visited_at or now,
        flag_long=flag_long,
    )
    db.add(visit)
    await db.flush()

    for uid in set(participant_ids):
        db.add(VisitParticipant(visit_id=visit.id, user_id=uid))

    await db.commit()
    await db.refresh(visit)

    if bath_id:
        await recalculate_visit(visit.id, db)

    return visit


async def update_visit_bath(db: AsyncSession, visit_id: int, bath_id: int) -> Visit:
    q = await db.execute(select(Visit).where(Visit.id == visit_id))
    visit = q.scalar_one()
    visit.bath_id = bath_id
    visit.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await recalculate_visit(visit_id, db)
    await db.refresh(visit)
    return visit


async def set_flag_long(db: AsyncSession, visit_id: int, value: bool) -> Visit:
    q = await db.execute(select(Visit).where(Visit.id == visit_id))
    visit = q.scalar_one()
    visit.flag_long = value
    visit.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await recalculate_visit(visit_id, db)
    await db.refresh(visit)
    return visit


async def update_participants(db: AsyncSession, visit_id: int, user_ids: list[int]) -> Visit:
    await db.execute(
        delete(VisitParticipant).where(VisitParticipant.visit_id == visit_id)
    )
    for uid in set(user_ids):
        db.add(VisitParticipant(visit_id=visit_id, user_id=uid))
    await db.commit()
    await recalculate_visit(visit_id, db)
    q = await db.execute(select(Visit).where(Visit.id == visit_id))
    return q.scalar_one()


async def set_visit_status(db: AsyncSession, visit_id: int, status: str) -> Visit:
    q = await db.execute(select(Visit).where(Visit.id == visit_id))
    visit = q.scalar_one()
    visit.status = status
    visit.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await recalculate_visit(visit_id, db)
    await db.refresh(visit)
    return visit
