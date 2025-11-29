from __future__ import annotations

from datetime import datetime, timedelta, timezone

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy import func, select

from ..db import async_session_maker
from ..i18n import SUPPORTED_LANGUAGES, t
from ..keyboards import main_menu, water_presets_keyboard
from ..models import User, WaterIntake

router = Router()


class WaterStates(StatesGroup):
    waiting_amount = State()


async def _today_range_utc() -> tuple[datetime, datetime]:
    now = datetime.now(timezone.utc)
    start = datetime(year=now.year, month=now.month, day=now.day, tzinfo=timezone.utc)
    end = start + timedelta(days=1)
    return start, end


async def _load_user(telegram_id: int) -> User | None:
    async with async_session_maker() as session:
        return await session.scalar(select(User).where(User.telegram_id == telegram_id))


async def _ensure_user(message: Message) -> tuple[User | None, str]:
    user = await _load_user(message.from_user.id)
    lang = user.language if user else "en"
    if not user:
        await message.answer(t(lang, "profile_missing"))
    return user, lang


async def _save_water_and_total(user_id: int, volume_ml: float) -> float:
    start, end = await _today_range_utc()
    async with async_session_maker() as session:
        intake = WaterIntake(user_id=user_id, volume_ml=volume_ml)
        session.add(intake)
        await session.commit()

        total_stmt = (
            select(func.sum(WaterIntake.volume_ml))
            .where(
                WaterIntake.user_id == user_id,
                WaterIntake.datetime >= start,
                WaterIntake.datetime < end,
            )
            .limit(1)
        )
        total_ml = await session.scalar(total_stmt)
        return float(total_ml or 0)


def _parse_amount(text: str) -> float | None:
    try:
        return float(text.replace(",", "."))
    except (TypeError, ValueError):
        return None


@router.message(Command("water"))
@router.message(F.text.in_({t(lang, "menu_water") for lang in SUPPORTED_LANGUAGES}))
async def start_water_log(message: Message, state: FSMContext) -> None:
    user, lang = await _ensure_user(message)
    if not user:
        return

    await state.set_state(WaterStates.waiting_amount)
    await state.update_data(user_id=user.id, language=lang)
    await message.answer(t(lang, "ask_water_amount"), reply_markup=water_presets_keyboard(lang))


@router.callback_query(WaterStates.waiting_amount, F.data.startswith("water_ml_"))
async def water_preset_selected(callback: CallbackQuery, state: FSMContext) -> None:
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

    total_ml = await _save_water_and_total(user_id, volume)
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
async def water_amount_entered(message: Message, state: FSMContext) -> None:
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

    total_ml = await _save_water_and_total(user_id, amount)
    await message.answer(
        "\n".join(
            [t(lang, "water_saved"), t(lang, "water_today_total", ml=int(total_ml))]
        ),
        reply_markup=main_menu(lang),
    )
    await state.clear()
