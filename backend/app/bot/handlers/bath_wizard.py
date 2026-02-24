from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.services.bath import create_bath, get_all_countries, get_regions_by_country
from app.services.visit import update_visit_bath
from app.bot.keyboards.inline import country_keyboard, region_keyboard, visit_card_keyboard
from app.db.models import Visit

router = Router()


class BathWizard(StatesGroup):
    waiting_name = State()
    waiting_country = State()
    waiting_region = State()
    waiting_city = State()
    waiting_geo = State()


@router.callback_query(F.data.startswith("bath:create:"))
async def start_bath_wizard(callback: CallbackQuery, state: FSMContext):
    visit_id = int(callback.data.split(":")[2])
    await state.update_data(visit_id=visit_id)

    async with AsyncSessionLocal() as db:
        # Pre-fill bath name from visit context if possible
        q = await db.execute(select(Visit).where(Visit.id == visit_id))
        visit = q.scalar_one_or_none()

        countries = await get_all_countries(db)

    await callback.answer()
    await callback.message.answer("✍️ Введи <b>название</b> новой бани:")
    await state.set_state(BathWizard.waiting_name)


@router.message(BathWizard.waiting_name)
async def wizard_got_name(message: Message, state: FSMContext):
    await state.update_data(bath_name=message.text.strip())
    data = await state.get_data()
    visit_id = data["visit_id"]

    async with AsyncSessionLocal() as db:
        countries = await get_all_countries(db)

    if countries:
        await message.answer(
            "🌍 Выбери страну:",
            reply_markup=country_keyboard(countries, visit_id),
        )
        await state.set_state(BathWizard.waiting_country)
    else:
        await message.answer("🏙 Введи город/населённый пункт:")
        await state.set_state(BathWizard.waiting_city)


@router.callback_query(F.data.startswith("wizard:country:"))
async def wizard_select_country(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split(":")
    visit_id = int(parts[2])
    country_id = int(parts[3])
    await state.update_data(country_id=country_id)

    async with AsyncSessionLocal() as db:
        regions = await get_regions_by_country(db, country_id)

    if regions:
        await callback.message.edit_text(
            "📍 Выбери регион:",
            reply_markup=region_keyboard(regions, visit_id, country_id),
        )
        await state.set_state(BathWizard.waiting_region)
    else:
        await callback.message.edit_text("🏙 Введи город/населённый пункт:")
        await state.set_state(BathWizard.waiting_city)
    await callback.answer()


@router.callback_query(F.data.startswith("wizard:region:"))
async def wizard_select_region(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split(":")
    visit_id = int(parts[2])
    region_id = int(parts[3])
    await state.update_data(region_id=region_id)
    await callback.message.edit_text("🏙 Введи город/населённый пункт:")
    await state.set_state(BathWizard.waiting_city)
    await callback.answer()


@router.callback_query(F.data.startswith("wizard:back_country:"))
async def wizard_back_country(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    visit_id = data["visit_id"]
    async with AsyncSessionLocal() as db:
        countries = await get_all_countries(db)
    await callback.message.edit_text(
        "🌍 Выбери страну:",
        reply_markup=country_keyboard(countries, visit_id),
    )
    await state.set_state(BathWizard.waiting_country)
    await callback.answer()


@router.message(BathWizard.waiting_city)
async def wizard_got_city(message: Message, state: FSMContext):
    await state.update_data(city=message.text.strip())
    await message.answer(
        "📌 Отправь геолокацию или введи координаты (широта, долгота).\n"
        "Пример: <code>55.7558, 37.6173</code>\n"
        "Или напиши <code>пропустить</code>."
    )
    await state.set_state(BathWizard.waiting_geo)


@router.message(BathWizard.waiting_geo)
async def wizard_got_geo(message: Message, state: FSMContext):
    data = await state.get_data()
    lat, lng = None, None

    if message.location:
        lat = message.location.latitude
        lng = message.location.longitude
    elif message.text and message.text.lower().strip() not in ("пропустить", "skip", "-"):
        try:
            parts = message.text.replace(" ", "").split(",")
            lat = float(parts[0])
            lng = float(parts[1])
        except (ValueError, IndexError):
            await message.answer(
                "❌ Неверный формат. Введи: <code>широта, долгота</code> "
                "или напиши <code>пропустить</code>."
            )
            return

    bath_name = data.get("bath_name", "Новая баня")
    visit_id = data["visit_id"]

    async with AsyncSessionLocal() as db:
        bath = await create_bath(
            db=db,
            name=bath_name,
            country_id=data.get("country_id"),
            region_id=data.get("region_id"),
            city=data.get("city"),
            lat=lat,
            lng=lng,
        )
        visit = await update_visit_bath(db, visit_id, bath.id)
        q = await db.execute(select(Visit).where(Visit.id == visit_id))
        visit = q.scalar_one()

    await state.clear()

    keyboard = visit_card_keyboard(
        visit_id=visit.id,
        flag_long=visit.flag_long,
        bath_id=visit.bath_id,
    )
    await message.answer(
        f"✅ Баня <b>{bath_name}</b> создана и добавлена к визиту #{visit_id}!",
        reply_markup=keyboard,
    )
