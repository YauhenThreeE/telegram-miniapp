from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from ..i18n import SUPPORTED_LANGUAGES, t
from ..keyboards import main_menu, meal_type_keyboard
from ..models import User
from ..services.meal_service import log_text_meal
from ..services.ai_nutrition import AiNutritionService

router = Router()


class MealLog(StatesGroup):
    choosing_type = State()
    entering_text = State()


@router.message(Command("meal", "food"))
@router.message(F.text.in_({t(lang, "menu_log_meal") for lang in SUPPORTED_LANGUAGES}))
async def start_meal_log(message: Message, state: FSMContext, user: User | None, lang: str) -> None:
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
async def meal_text_received(
    message: Message,
    state: FSMContext,
    user: User | None,
    lang: str,
    session_maker,
) -> None:
    data = await state.get_data()
    meal_type = data.get("meal_type")

    if not user or not meal_type:
        await message.answer(t(lang, "profile_missing"))
        await state.clear()
        return

    raw_text = message.text.strip() if message.text else ""
    if not raw_text:
        await message.answer(t(lang, "ask_meal_text"))
        return

    async with session_maker() as session:
        ai_service: AiNutritionService | None = getattr(message.bot, "ai_service", None)
        _, estimates = await log_text_meal(
            session=session,
            user_id=user.id,
            meal_type=meal_type.replace("mealtype_", ""),
            raw_text=raw_text,
            lang=lang,
            ai_service=ai_service,
        )

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
