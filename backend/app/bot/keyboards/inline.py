from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def visit_card_keyboard(
    visit_id: int,
    flag_long: bool,
    bath_id: int | None,
    has_uncertain_bath: bool = False,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if has_uncertain_bath:
        builder.button(text="🏠 Уточнить баню", callback_data=f"visit:bath:{visit_id}")
    builder.button(text="👥 Участники", callback_data=f"visit:participants:{visit_id}")
    long_label = "✅ Долго 150+" if flag_long else "⬜ Долго 150+"
    builder.button(text=long_label, callback_data=f"visit:long:{visit_id}")
    builder.adjust(1)
    return builder.as_markup()


def bath_search_keyboard(
    visit_id: int,
    candidates: list,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for bath, score in candidates:
        builder.button(
            text=f"🏠 {bath.name} ({score}%)",
            callback_data=f"bath:select:{visit_id}:{bath.id}",
        )
    builder.button(text="➕ Создать новую баню", callback_data=f"bath:create:{visit_id}")
    builder.adjust(1)
    return builder.as_markup()


def country_keyboard(countries: list, visit_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for country in countries:
        builder.button(
            text=country.name,
            callback_data=f"wizard:country:{visit_id}:{country.id}",
        )
    builder.adjust(2)
    return builder.as_markup()


def region_keyboard(regions: list, visit_id: int, country_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for region in regions:
        builder.button(
            text=region.name,
            callback_data=f"wizard:region:{visit_id}:{region.id}",
        )
    builder.button(
        text="↩ Другая страна",
        callback_data=f"wizard:back_country:{visit_id}",
    )
    builder.adjust(2)
    return builder.as_markup()


def confirm_keyboard(visit_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Подтвердить", callback_data=f"visit:confirm:{visit_id}")
    builder.button(text="❌ Отменить", callback_data=f"visit:cancel:{visit_id}")
    builder.adjust(2)
    return builder.as_markup()
