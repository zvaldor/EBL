from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone, timedelta

from app.db.session import AsyncSessionLocal
from app.db.models import User, PointLog, Visit, VisitParticipant, Bath
from app.services.visit import get_or_create_user

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message):
    async with AsyncSessionLocal() as db:
        await get_or_create_user(db, message.from_user)
    await message.answer(
        f"👋 Привет, <b>{message.from_user.full_name}</b>!\n\n"
        "🏊 <b>ЕБЛ — Евразийская Банная Лига</b>\n\n"
        "📸 Отмечай визиты в баню через <code>@ebanakomissiya_bot</code> в чате.\n"
        "📊 /top — лидерборд\n"
        "📅 /week — итоги недели\n"
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


@router.message(Command("week"))
async def cmd_week(message: Message):
    now = datetime.now(timezone.utc)
    # ISO week: Monday = start, Sunday = end
    week_start = (now - timedelta(days=now.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    week_end = week_start + timedelta(days=7)
    week_num = now.isocalendar()[1]
    date_range = f"{week_start.strftime('%-d %b')} – {(week_end - timedelta(days=1)).strftime('%-d %b')}"

    async with AsyncSessionLocal() as db:
        # Load visits for this week with their baths
        visits_q = await db.execute(
            select(Visit)
            .where(
                Visit.visited_at >= week_start,
                Visit.visited_at < week_end,
                Visit.status.in_(["confirmed", "draft", "pending"]),
            )
            .order_by(Visit.visited_at)
        )
        visits = visits_q.scalars().all()

        if not visits:
            await message.answer(
                f"📅 <b>Неделя {week_num}</b> · {date_range}\n\n"
                "Пока нет визитов на этой неделе 🛁"
            )
            return

        # Collect bath ids and build bath map
        bath_ids = {v.bath_id for v in visits if v.bath_id}
        baths_map: dict[int, Bath] = {}
        if bath_ids:
            baths_q = await db.execute(select(Bath).where(Bath.id.in_(bath_ids)))
            for b in baths_q.scalars().all():
                baths_map[b.id] = b

        # Collect per-user stats: points, visit count, bath names
        # user_id -> {full_name, pts, visit_count, bath_names}
        user_stats: dict[int, dict] = {}
        for visit in visits:
            bath = baths_map.get(visit.bath_id) if visit.bath_id else None
            bath_name = bath.name if bath else "—"

            parts_q = await db.execute(
                select(User)
                .join(VisitParticipant, VisitParticipant.user_id == User.id)
                .where(VisitParticipant.visit_id == visit.id)
            )
            participants = parts_q.scalars().all()

            pts_q = await db.execute(
                select(PointLog).where(PointLog.visit_id == visit.id)
            )
            pts_by_user: dict[int, float] = {}
            for lg in pts_q.scalars().all():
                pts_by_user[lg.user_id] = pts_by_user.get(lg.user_id, 0.0) + lg.points

            for u in participants:
                if u.id not in user_stats:
                    user_stats[u.id] = {
                        "name": u.full_name,
                        "pts": 0.0,
                        "visit_count": 0,
                        "baths": [],
                    }
                user_stats[u.id]["pts"] += pts_by_user.get(u.id, 0.0)
                user_stats[u.id]["visit_count"] += 1
                user_stats[u.id]["baths"].append(bath_name)

    # Sort by points desc
    ranked = sorted(user_stats.values(), key=lambda x: -x["pts"])

    lines = [f"📅 <b>Неделя {week_num}</b> · {date_range}\n"]
    medals = ["🥇", "🥈", "🥉"]
    for i, stat in enumerate(ranked):
        medal = medals[i] if i < 3 else f"{i + 1}."
        unique_baths = list(dict.fromkeys(stat["baths"]))  # preserve order, dedupe
        baths_str = ", ".join(unique_baths) if unique_baths else "—"
        lines.append(
            f"{medal} <b>{stat['name']}</b> — {stat['visit_count']} визит(а) — "
            f"<i>{baths_str}</i> — <b>{stat['pts']:.0f} очк.</b>"
        )

    total_visits = len(visits)
    lines.append(f"\n📊 Итого: {total_visits} визит(а), {len(user_stats)} участник(а)")
    await message.answer("\n".join(lines))
