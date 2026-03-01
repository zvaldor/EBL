from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone, timedelta
import os

from app.db.session import AsyncSessionLocal
from app.db.models import User, PointLog, Visit, VisitParticipant, Bath
from app.services.visit import get_or_create_user
from app.services import sheets as sheets_svc
from app.config import settings

router = Router()


def _creds() -> str:
    """Return JSON string from env var, or fall back to local file path."""
    if settings.GOOGLE_CREDENTIALS_JSON:
        return settings.GOOGLE_CREDENTIALS_JSON
    here = os.path.dirname(__file__)
    return os.path.join(here, "..", "..", "..", "google_credentials.json")


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


def _bath_word(n: int) -> str:
    if n % 10 == 1 and n % 100 != 11:
        return "баня"
    if 2 <= n % 10 <= 4 and not (12 <= n % 100 <= 14):
        return "бани"
    return "бань"


def _pts_str(pts: float) -> str:
    return f"{pts:.0f}" if pts == int(pts) else f"{pts:.2f}".rstrip("0")


@router.message(Command("week"))
async def cmd_week(message: Message):
    now = datetime.now(timezone.utc)
    week_start = (now - timedelta(days=now.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    week_num = now.isocalendar()[1]
    date_range = (
        f"{week_start.strftime('%-d %b')} – "
        f"{(week_start + timedelta(days=6)).strftime('%-d %b')}"
    )

    creds = _creds()
    try:
        report = await sheets_svc.get_weekly_stats(
            creds, settings.GOOGLE_SPREADSHEET_ID, week_num
        )
    except Exception as e:
        await message.answer(f"⚠️ Не удалось прочитать таблицу: {e}")
        return

    weekly = report["weekly"]
    year_top = report["year_top"]

    if not weekly:
        await message.answer(
            f"📅 <b>Неделя {week_num}</b> · {date_range}\n\n"
            "Пока нет данных за эту неделю 🛁"
        )
        return

    medals = ["🥇", "🥈", "🥉"]
    lines = [f"📅 <b>Неделя {week_num}</b> · {date_range}\n"]

    total_visits = 0
    total_pts = 0.0
    for i, row in enumerate(weekly):
        medal = medals[i] if i < 3 else f"{i + 1}."
        v = row["visit_count"]
        pts = row["points"]
        total_visits += v
        total_pts += pts
        baths = f"{v} {_bath_word(v)}" if v else ""
        pts_part = f"{_pts_str(pts)} очк." if pts else ""
        detail = " · ".join(filter(None, [baths, pts_part]))
        lines.append(f"{medal} <b>{row['name']}</b> — {detail}")

    lines.append(f"\n📊 Итого за неделю: {total_visits} визитов, {_pts_str(total_pts)} очков")

    if year_top:
        lines.append(f"\n🏆 <b>Топ-3 за {now.year} год:</b>")
        for i, row in enumerate(year_top):
            v = row["visit_count"]
            lines.append(
                f"{medals[i]} {row['name']} — {_pts_str(row['points'])} очк. · {v} {_bath_word(v)}"
            )

    await message.answer("\n".join(lines), parse_mode="HTML")
