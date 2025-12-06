from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from ..i18n import SUPPORTED_LANGUAGES, t
from ..keyboards import main_menu, water_presets_keyboard
from ..models import User
from ..services.water_service import add_water_and_total

router = Router()


class WaterStates(StatesGroup):
    waiting_amount = State()


def _parse_amount(text: str) -> float | None:
    try:
        return float(text.replace(",", "."))
    except (TypeError, ValueError):
        return None


@router.message(Command("water"))
@router.message(F.text.in_({t(lang, "menu_water") for lang in SUPPORTED_LANGUAGES}))
async def start_water_log(
    message: Message,
    state: FSMContext,
    user: User | None,
    lang: str,
    session_maker,
) -> None:
    if not user:
        return

    await state.set_state(WaterStates.waiting_amount)
    await state.update_data(user_id=user.id, language=lang)
    await message.answer(t(lang, "ask_water_amount"), reply_markup=water_presets_keyboard(lang))


@router.callback_query(WaterStates.waiting_amount, F.data.startswith("water_ml_"))
async def water_preset_selected(callback: CallbackQuery, state: FSMContext, session_maker) -> None:
    data = await state.get_data()
    lang = data.get("language", "en")
    user_id = data.get("user_id")
    if not user_id:
        await callback.message.answer(t(lang, "profile_missing"))
        await callback.answer()
        return

    volume_str = callback.data.split("_", 2)[2]
    volume = _parse_amount(volume_str)
    if volume is None or volume <= 0:
        await callback.message.answer(t(lang, "water_invalid_amount"))
        await callback.answer()
        return

    async with session_maker() as session:
        total_ml = await add_water_and_total(session, user_id, volume)
    await callback.message.answer(
        "\n".join(
            [
                t(lang, "water_saved"),
                t(lang, "water_today_total", ml=int(total_ml)),
            ]
        ),
        reply_markup=main_menu(lang),
    )
    await callback.answer()
    await state.clear()


@router.callback_query(WaterStates.waiting_amount, F.data == "water_other")
async def water_other_amount(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("language", "en")
    await callback.message.answer(t(lang, "ask_water_amount"))
    await callback.answer()


@router.message(WaterStates.waiting_amount)
async def water_amount_entered(message: Message, state: FSMContext, session_maker) -> None:
    data = await state.get_data()
    lang = data.get("language", "en")
    user_id = data.get("user_id")
    if not user_id:
        await message.answer(t(lang, "profile_missing"))
        await state.clear()
        return

    amount = _parse_amount(message.text or "")
    if amount is None or amount <= 0:
        await message.answer(t(lang, "water_invalid_amount"))
        return

    async with session_maker() as session:
        total_ml = await add_water_and_total(session, user_id, amount)
    await message.answer(
        "\n".join(
            [t(lang, "water_saved"), t(lang, "water_today_total", ml=int(total_ml))]
        ),
        reply_markup=main_menu(lang),
    )
    await state.clear()
