from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select

from ..db import async_session_maker, get_session_maker
from ..i18n import SUPPORTED_LANGUAGES, t
from ..keyboards import main_menu, meal_type_keyboard
from ..models import Meal, User
from ..services.ai_nutrition import AiNutritionService

router = Router()


class MealLog(StatesGroup):
    choosing_type = State()
    entering_text = State()


async def _load_user(bot: object, telegram_id: int) -> User | None:
    session_maker = get_session_maker(bot)
    async with session_maker() as session:
        return await session.scalar(select(User).where(User.telegram_id == telegram_id))


async def _ensure_user(message: Message) -> tuple[User | None, str]:
    user = await _load_user(message.bot, message.from_user.id)
    lang = user.language if user else "en"
    if not user:
        await message.answer(t(lang, "profile_missing"))
    return user, lang


@router.message(Command("meal", "food"))
@router.message(F.text.in_({t(lang, "menu_log_meal") for lang in SUPPORTED_LANGUAGES}))
async def start_meal_log(message: Message, state: FSMContext) -> None:
    user, lang = await _ensure_user(message)
    if not user:
        return

    await state.clear()
    await state.set_state(MealLog.choosing_type)
    await state.update_data(user_id=user.id, language=lang)
    await message.answer(t(lang, "ask_meal_type"), reply_markup=meal_type_keyboard(lang))


@router.callback_query(MealLog.choosing_type, F.data.startswith("mealtype_"))
async def meal_type_selected(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("language", "en")
    user_id = data.get("user_id")
    if not user_id:
        await callback.message.answer(t(lang, "profile_missing"))
        await callback.answer()
        return

    meal_type = callback.data.split("_", 1)[1]
    await state.update_data(meal_type=meal_type)
    await state.set_state(MealLog.entering_text)
    await callback.message.answer(t(lang, "ask_meal_text"))
    await callback.answer()


@router.message(MealLog.entering_text)
async def meal_text_received(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("language", "en")
    user_id = data.get("user_id")
    meal_type = data.get("meal_type")

    if not user_id or not meal_type:
        await message.answer(t(lang, "profile_missing"))
        await state.clear()
        return

    raw_text = message.text.strip() if message.text else ""
    if not raw_text:
        await message.answer(t(lang, "ask_meal_text"))
        return

    ai_service: AiNutritionService | None = getattr(message.bot, "ai_service", None)
    estimates = (
        await ai_service.estimate_meal_from_text(raw_text, language=lang)
        if ai_service
        else {}
    )

    session_maker = get_session_maker(message.bot)
    async with session_maker() as session:
        meal = Meal(
            user_id=user_id,
            meal_type=meal_type.replace("mealtype_", ""),
            raw_text=raw_text,
            language=lang,
            calories=estimates.get("calories"),
            protein_g=estimates.get("protein_g"),
            fat_g=estimates.get("fat_g"),
            carbs_g=estimates.get("carbs_g"),
            fiber_g=estimates.get("fiber_g"),
            sugar_g=estimates.get("sugar_g"),
            ai_notes=estimates.get("ai_notes"),
        )
        session.add(meal)
        await session.commit()

    await message.answer(t(lang, "meal_saved"))
    await message.answer(
        t(
            lang,
            "meal_summary",
            calories=_fmt(estimates.get("calories")),
            protein=_fmt(estimates.get("protein_g")),
            fat=_fmt(estimates.get("fat_g")),
            carbs=_fmt(estimates.get("carbs_g")),
        ),
        reply_markup=main_menu(lang),
    )
    await state.clear()


def _fmt(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value:.1f}"
