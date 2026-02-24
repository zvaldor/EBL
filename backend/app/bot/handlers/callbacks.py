from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select, func

from app.db.session import AsyncSessionLocal
from app.db.models import Visit, VisitParticipant, Bath, User, PointLog
from app.services.visit import (
    set_flag_long, update_visit_bath, set_visit_status,
    update_participants, get_or_create_user,
)
from app.bot.keyboards.inline import visit_card_keyboard, bath_search_keyboard, participants_keyboard

router = Router()


class ParticipantEdit(StatesGroup):
    waiting_mentions = State()


# ── helpers ──────────────────────────────────────────────────────────────────

async def build_card_text(visit: Visit, db) -> str:
    bath_name = "Неизвестная баня"
    if visit.bath_id:
        bath_q = await db.execute(select(Bath).where(Bath.id == visit.bath_id))
        bath = bath_q.scalar_one_or_none()
        if bath:
            bath_name = bath.name

    parts_q = await db.execute(
        select(User)
        .join(VisitParticipant, VisitParticipant.user_id == User.id)
        .where(VisitParticipant.visit_id == visit.id)
    )
    participants = parts_q.scalars().all()
    names = [u.full_name or f"@{u.username}" or str(u.id) for u in participants]

    pts_q = await db.execute(
        select(func.sum(PointLog.points)).where(PointLog.visit_id == visit.id)
    )
    total_pts = pts_q.scalar() or 0.0

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
        f"🏠 Баня: <b>{bath_name}</b>",
        f"📅 Дата: {visit.visited_at.strftime('%d.%m.%Y')}",
        f"👥 Участники: {', '.join(names) if names else '—'}",
        "",
        f"⭐ Очков: <b>{total_pts:.0f}</b>",
    ]
    if visit.flag_long:
        lines.append("⏱ Долго 150+: ✅")
    lines.append(f"📊 Статус: {status_map.get(visit.status, visit.status)}")
    return "\n".join(lines)


async def load_participants(db, visit_id: int) -> list[User]:
    q = await db.execute(
        select(User)
        .join(VisitParticipant, VisitParticipant.user_id == User.id)
        .where(VisitParticipant.visit_id == visit_id)
    )
    return list(q.scalars().all())


def build_participants_text(visit_id: int, participants: list[User]) -> str:
    if not participants:
        return f"👥 В визите #{visit_id} пока нет участников\n\nНажми ➕ чтобы добавить."
    names = [u.full_name or f"@{u.username}" or str(u.id) for u in participants]
    return (
        f"👥 <b>Участники визита #{visit_id}:</b>\n"
        + "\n".join(f"• {n}" for n in names)
        + "\n\nНажми на участника чтобы удалить, или ➕ чтобы добавить."
    )


# ── participants screen ───────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("visit:participants:"))
async def cb_show_participants(callback: CallbackQuery):
    visit_id = int(callback.data.split(":")[2])
    async with AsyncSessionLocal() as db:
        participants = await load_participants(db, visit_id)
    text = build_participants_text(visit_id, participants)
    part_list = [(u.id, u.full_name or f"@{u.username}" or str(u.id)) for u in participants]
    await callback.message.edit_text(
        text, parse_mode="HTML", reply_markup=participants_keyboard(visit_id, part_list)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("participant:remove:"))
async def cb_remove_participant(callback: CallbackQuery):
    parts = callback.data.split(":")
    visit_id = int(parts[2])
    remove_id = int(parts[3])
    async with AsyncSessionLocal() as db:
        q = await db.execute(
            select(VisitParticipant.user_id).where(VisitParticipant.visit_id == visit_id)
        )
        current_ids = [row[0] for row in q.all()]
        new_ids = [uid for uid in current_ids if uid != remove_id]
        await update_participants(db, visit_id, new_ids)
        participants = await load_participants(db, visit_id)
    text = build_participants_text(visit_id, participants)
    part_list = [(u.id, u.full_name or f"@{u.username}" or str(u.id)) for u in participants]
    await callback.message.edit_text(
        text, parse_mode="HTML", reply_markup=participants_keyboard(visit_id, part_list)
    )
    await callback.answer("✅ Участник удалён")


@router.callback_query(F.data.startswith("participant:add:"))
async def cb_add_participant_start(callback: CallbackQuery, state: FSMContext):
    visit_id = int(callback.data.split(":")[2])
    await state.update_data(visit_id=visit_id)
    await state.set_state(ParticipantEdit.waiting_mentions)
    await callback.message.answer(
        "👤 Упомяни участников через @username.\n"
        "Например: <code>@user1 @user2</code>",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(ParticipantEdit.waiting_mentions)
async def handle_participant_mentions(message: Message, state: FSMContext):
    data = await state.get_data()
    visit_id = data["visit_id"]
    await state.clear()

    added = []
    not_found = []

    async with AsyncSessionLocal() as db:
        # Current participant IDs
        q = await db.execute(
            select(VisitParticipant.user_id).where(VisitParticipant.visit_id == visit_id)
        )
        current_ids = list(set(row[0] for row in q.all()))
        new_ids = list(current_ids)

        if message.entities:
            for entity in message.entities:
                if entity.type == "text_mention" and entity.user:
                    # Telegram gave us the full user object
                    user = await get_or_create_user(db, entity.user)
                    if user.id not in new_ids:
                        new_ids.append(user.id)
                        added.append(user.full_name or f"@{entity.user.username}")
                elif entity.type == "mention":
                    username = message.text[entity.offset + 1: entity.offset + entity.length]
                    q2 = await db.execute(select(User).where(User.username == username))
                    user = q2.scalar_one_or_none()
                    if user:
                        if user.id not in new_ids:
                            new_ids.append(user.id)
                            added.append(user.full_name or f"@{username}")
                    else:
                        not_found.append(f"@{username}")

        await update_participants(db, visit_id, new_ids)
        participants = await load_participants(db, visit_id)

    text = build_participants_text(visit_id, participants)
    if not_found:
        text += f"\n\n⚠️ Не найдены (ещё не регистрировались): {', '.join(not_found)}"

    part_list = [(u.id, u.full_name or f"@{u.username}" or str(u.id)) for u in participants]
    await message.answer(
        text, parse_mode="HTML", reply_markup=participants_keyboard(visit_id, part_list)
    )


# ── back to visit card ────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("visit:back:"))
async def cb_back_to_visit(callback: CallbackQuery, state: FSMContext):
    visit_id = int(callback.data.split(":")[2])
    await state.clear()  # cancel any pending FSM state
    async with AsyncSessionLocal() as db:
        q = await db.execute(select(Visit).where(Visit.id == visit_id))
        visit = q.scalar_one_or_none()
        if not visit:
            await callback.answer("Визит не найден")
            return
        card_text = await build_card_text(visit, db)
        keyboard = visit_card_keyboard(
            visit_id=visit.id, flag_long=visit.flag_long, bath_id=visit.bath_id
        )
    await callback.message.edit_text(card_text, parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()


# ── visit card buttons ────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("visit:long:"))
async def cb_toggle_long(callback: CallbackQuery):
    visit_id = int(callback.data.split(":")[2])
    async with AsyncSessionLocal() as db:
        q = await db.execute(select(Visit).where(Visit.id == visit_id))
        visit = q.scalar_one_or_none()
        if not visit:
            await callback.answer("Визит не найден")
            return
        visit = await set_flag_long(db, visit_id, not visit.flag_long)
        card_text = await build_card_text(visit, db)
        keyboard = visit_card_keyboard(
            visit_id=visit.id, flag_long=visit.flag_long, bath_id=visit.bath_id
        )
    await callback.message.edit_text(card_text, parse_mode="HTML", reply_markup=keyboard)
    await callback.answer("✅ Флаг обновлён")


@router.callback_query(F.data.startswith("bath:select:"))
async def cb_bath_select(callback: CallbackQuery):
    parts = callback.data.split(":")
    visit_id = int(parts[2])
    bath_id = int(parts[3])
    async with AsyncSessionLocal() as db:
        visit = await update_visit_bath(db, visit_id, bath_id)
        card_text = await build_card_text(visit, db)
        keyboard = visit_card_keyboard(
            visit_id=visit.id, flag_long=visit.flag_long, bath_id=visit.bath_id
        )
    await callback.message.edit_text(card_text, parse_mode="HTML", reply_markup=keyboard)
    await callback.answer("🏠 Баня обновлена")


@router.callback_query(F.data.startswith("visit:confirm:"))
async def cb_confirm_visit(callback: CallbackQuery):
    visit_id = int(callback.data.split(":")[2])
    async with AsyncSessionLocal() as db:
        visit = await set_visit_status(db, visit_id, "confirmed")
        card_text = await build_card_text(visit, db)
    await callback.message.edit_text(card_text, parse_mode="HTML")
    await callback.answer("✅ Визит подтверждён")


@router.callback_query(F.data.startswith("visit:cancel:"))
async def cb_cancel_visit(callback: CallbackQuery):
    visit_id = int(callback.data.split(":")[2])
    async with AsyncSessionLocal() as db:
        visit = await set_visit_status(db, visit_id, "cancelled")
        card_text = await build_card_text(visit, db)
    await callback.message.edit_text(card_text, parse_mode="HTML")
    await callback.answer("❌ Визит отменён")
