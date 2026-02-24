from aiogram import Router, F
from aiogram.types import CallbackQuery
from sqlalchemy import select, func

from app.db.session import AsyncSessionLocal
from app.db.models import Visit, VisitParticipant, Bath, User, PointLog
from app.services.visit import set_flag_long, update_visit_bath, set_visit_status
from app.bot.keyboards.inline import visit_card_keyboard, bath_search_keyboard

router = Router()


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


@router.callback_query(F.data.startswith("visit:participants:"))
async def cb_show_participants(callback: CallbackQuery):
    visit_id = int(callback.data.split(":")[2])
    async with AsyncSessionLocal() as db:
        parts_q = await db.execute(
            select(User)
            .join(VisitParticipant, VisitParticipant.user_id == User.id)
            .where(VisitParticipant.visit_id == visit_id)
        )
        participants = parts_q.scalars().all()
    if participants:
        names = [u.full_name or f"@{u.username}" or str(u.id) for u in participants]
        text = "👥 Участники:\n" + "\n".join(f"• {n}" for n in names)
    else:
        text = "👥 Участников пока нет"
    await callback.answer(text, show_alert=True)


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
    await callback.message.edit_text(card_text, reply_markup=keyboard)
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
    await callback.message.edit_text(card_text, reply_markup=keyboard)
    await callback.answer("🏠 Баня обновлена")


@router.callback_query(F.data.startswith("visit:confirm:"))
async def cb_confirm_visit(callback: CallbackQuery):
    visit_id = int(callback.data.split(":")[2])
    async with AsyncSessionLocal() as db:
        visit = await set_visit_status(db, visit_id, "confirmed")
        card_text = await build_card_text(visit, db)
    await callback.message.edit_text(card_text)
    await callback.answer("✅ Визит подтверждён")


@router.callback_query(F.data.startswith("visit:cancel:"))
async def cb_cancel_visit(callback: CallbackQuery):
    visit_id = int(callback.data.split(":")[2])
    async with AsyncSessionLocal() as db:
        visit = await set_visit_status(db, visit_id, "cancelled")
        card_text = await build_card_text(visit, db)
    await callback.message.edit_text(card_text)
    await callback.answer("❌ Визит отменён")
