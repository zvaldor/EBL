from aiogram import Router, Bot
from aiogram.types import Message
from aiogram.filters import BaseFilter
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.db.models import User
from app.services.visit import get_or_create_user, create_visit
from app.services.bath import find_best_bath
from app.bot.utils.parser import parse_message
from app.bot.keyboards.inline import visit_card_keyboard, bath_search_keyboard

router = Router()


class BotMentionFilter(BaseFilter):
    async def __call__(self, message: Message, bot: Bot) -> bool:
        me = await bot.get_me()
        text = message.text or message.caption or ""
        return f"@{me.username}" in text


def format_visit_card(
    visit,
    bath_name: str,
    participant_names: list[str],
    points: float = 0,
    uncertain: bool = False,
) -> str:
    status_map = {
        "draft": "📝 Черновик",
        "pending": "⏳ На подтверждении",
        "confirmed": "✅ Подтверждено",
        "disputed": "⚠️ Спорное",
        "cancelled": "❌ Отменено",
    }
    lines = [
        f"🏊 <b>Визит #{visit.id}</b>",
        "",
        f"🏠 Баня: <b>{bath_name}</b>" + (" ❓" if uncertain else ""),
        f"📅 Дата: {visit.visited_at.strftime('%d.%m.%Y')}",
        f"👥 Участники: {', '.join(participant_names) if participant_names else '—'}",
        "",
        f"⭐ Очков начислено: <b>{points:.0f}</b>",
    ]
    if visit.flag_long:
        lines.append("⏱ Долго 150+: ✅")
    lines.append(f"📊 Статус: {status_map.get(visit.status, visit.status)}")
    return "\n".join(lines)


@router.message(BotMentionFilter())
async def handle_mention(message: Message, bot: Bot):
    text = message.text or message.caption or ""
    me = await bot.get_me()

    parsed = parse_message(text, bot_username=me.username)

    async with AsyncSessionLocal() as db:
        creator = await get_or_create_user(db, message.from_user)

        participant_ids = [creator.id]
        participant_names = [
            message.from_user.full_name or f"@{message.from_user.username}" or str(creator.id)
        ]

        for username in parsed.mentioned_usernames:
            if username.lower() == (me.username or "").lower():
                continue
            q = await db.execute(select(User).where(User.username == username))
            user = q.scalar_one_or_none()
            if user and user.id not in participant_ids:
                participant_ids.append(user.id)
                participant_names.append(user.full_name or f"@{username}")

        for uid in parsed.mentioned_user_ids:
            if uid not in participant_ids:
                participant_ids.append(uid)

        bath_id = None
        bath_name = parsed.bath_name or "Баня не указана"
        candidates = []
        uncertain = False

        if parsed.bath_name:
            best_bath, candidates = await find_best_bath(db, parsed.bath_name)
            if best_bath:
                bath_id = best_bath.id
                bath_name = best_bath.name
            elif candidates:
                uncertain = True

        visit = await create_visit(
            db=db,
            bath_id=bath_id,
            created_by=creator.id,
            message_id=message.message_id,
            chat_id=message.chat.id,
            participant_ids=participant_ids,
            flag_long=parsed.flag_long,
        )

        # Calculate total points
        from app.db.models import PointLog
        from sqlalchemy import func
        pts_q = await db.execute(
            select(func.sum(PointLog.points)).where(PointLog.visit_id == visit.id)
        )
        total_points = pts_q.scalar() or 0.0

        card_text = format_visit_card(
            visit, bath_name, participant_names, total_points, uncertain
        )

        if candidates:
            await message.reply(
                card_text + "\n\n<i>Выбери баню из вариантов:</i>",
                reply_markup=bath_search_keyboard(visit.id, candidates),
            )
        elif not bath_id:
            await message.reply(
                card_text + "\n\n<i>Баня не найдена. Создай новую:</i>",
                reply_markup=bath_search_keyboard(visit.id, []),
            )
        else:
            await message.reply(
                card_text,
                reply_markup=visit_card_keyboard(
                    visit_id=visit.id,
                    flag_long=visit.flag_long,
                    bath_id=bath_id,
                ),
            )
