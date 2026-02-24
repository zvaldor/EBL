from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.db.models import User, PointLog, Visit, VisitParticipant
from app.services.visit import get_or_create_user

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message):
    async with AsyncSessionLocal() as db:
        await get_or_create_user(db, message.from_user)
    await message.answer(
        f"👋 Привет, <b>{message.from_user.full_name}</b>!\n\n"
        "🏊 <b>ЕБЛ — Единая Банная Лига</b>\n\n"
        "📸 Отмечай визиты в баню через <code>@ebanakomissiya_bot</code> в чате.\n"
        "📊 /top — лидерборд\n"
        "🙋 /me — мои очки"
    )


@router.message(Command("me"))
async def cmd_me(message: Message):
    async with AsyncSessionLocal() as db:
        user = await get_or_create_user(db, message.from_user)

        pts_q = await db.execute(
            select(func.sum(PointLog.points)).where(PointLog.user_id == user.id)
        )
        points = pts_q.scalar() or 0.0

        visits_q = await db.execute(
            select(func.count(VisitParticipant.visit_id))
            .join(Visit, Visit.id == VisitParticipant.visit_id)
            .where(
                VisitParticipant.user_id == user.id,
                Visit.status.in_(["confirmed", "draft", "pending"]),
            )
        )
        visit_count = visits_q.scalar() or 0

    await message.answer(
        f"🙋 <b>{message.from_user.full_name}</b>\n\n"
        f"⭐ Очков: <b>{points:.0f}</b>\n"
        f"🏊 Визитов: <b>{visit_count}</b>"
    )


@router.message(Command("top"))
async def cmd_top(message: Message):
    async with AsyncSessionLocal() as db:
        q = await db.execute(
            select(
                User.full_name,
                User.username,
                func.sum(PointLog.points).label("pts"),
            )
            .join(PointLog, PointLog.user_id == User.id)
            .where(User.is_active == True)
            .group_by(User.id, User.full_name, User.username)
            .order_by(func.sum(PointLog.points).desc())
            .limit(10)
        )
        rows = q.all()

    if not rows:
        await message.answer("📊 Пока нет данных для лидерборда.")
        return

    lines = ["🏆 <b>Лидерборд ЕБЛ</b>\n"]
    medals = ["🥇", "🥈", "🥉"]
    for i, (name, username, pts) in enumerate(rows):
        medal = medals[i] if i < 3 else f"{i + 1}."
        display = f"@{username}" if username else name
        lines.append(f"{medal} {display} — <b>{pts:.0f}</b> очк.")

    await message.answer("\n".join(lines))
