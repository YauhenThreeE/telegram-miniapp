from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select

from ..i18n import t
from ..keyboards import activity_keyboard, main_menu, nutrition_goal_keyboard, profile_edit_keyboard
from ..models import User

router = Router()


class EditProfile(StatesGroup):
    waiting_weight = State()
    waiting_height = State()
    waiting_activity = State()
    waiting_goal = State()


def format_profile(user: User, lang: str) -> str:
    def display(value: str | float | None) -> str:
        return str(value) if value is not None else "-"

    lines = [
        t(lang, "profile_title"),
        f"{t(lang, 'profile_field_sex')}: {display(user.sex)}",
        f"{t(lang, 'profile_field_dob')}: {display(user.date_of_birth)}",
        f"{t(lang, 'profile_field_height')}: {display(user.height_cm)}",
        f"{t(lang, 'profile_field_weight')}: {display(user.current_weight_kg)}",
        f"{t(lang, 'profile_field_goal_weight')}: {display(user.goal_weight_kg)}",
        f"{t(lang, 'profile_field_gi_diagnoses')}: {display(user.gi_diagnoses)}",
        f"{t(lang, 'profile_field_other_diagnoses')}: {display(user.other_diagnoses)}",
        f"{t(lang, 'profile_field_medications')}: {display(user.medications)}",
        f"{t(lang, 'profile_field_allergies')}: {display(user.allergies_intolerances)}",
        f"{t(lang, 'profile_field_activity_level')}: {display(user.activity_level)}",
        f"{t(lang, 'profile_field_nutrition_goal')}: {display(user.nutrition_goal)}",
    ]
    return "\n".join(lines)


@router.message(Command("profile"))
async def view_profile(message: Message, state: FSMContext, user: User | None, lang: str) -> None:
    await state.clear()
    if not user:
        await message.answer(t("en", "profile_missing"))
        return
    await message.answer(format_profile(user, lang), reply_markup=profile_edit_keyboard(lang))


@router.callback_query(F.data == "edit_weight")
async def edit_weight(callback: CallbackQuery, state: FSMContext, user: User | None, lang: str) -> None:
    await set_edit_state(callback, state, EditProfile.waiting_weight, user, lang)


@router.callback_query(F.data == "edit_height")
async def edit_height(callback: CallbackQuery, state: FSMContext, user: User | None, lang: str) -> None:
    await set_edit_state(callback, state, EditProfile.waiting_height, user, lang)


@router.callback_query(F.data == "edit_activity")
async def edit_activity(callback: CallbackQuery, state: FSMContext, user: User | None, lang: str) -> None:
    await set_edit_state(callback, state, EditProfile.waiting_activity, user, lang, keyboard=activity_keyboard)


@router.callback_query(F.data == "edit_goal")
async def edit_goal(callback: CallbackQuery, state: FSMContext, user: User | None, lang: str) -> None:
    await set_edit_state(callback, state, EditProfile.waiting_goal, user, lang, keyboard=nutrition_goal_keyboard)


async def set_edit_state(
    callback: CallbackQuery,
    state: FSMContext,
    new_state: State,
    user: User | None,
    lang: str,
    keyboard=None,
) -> None:
    if not user:
        await callback.message.answer(t("en", "profile_missing"))
        await callback.answer()
        return
    await state.set_state(new_state)
    await state.update_data(language=lang)
    reply_markup = keyboard(lang) if keyboard else None
    await callback.message.answer(t(lang, "profile_edit_prompt"), reply_markup=reply_markup)
    await callback.answer()


@router.message(EditProfile.waiting_weight)
async def update_weight(message: Message, state: FSMContext, session_maker) -> None:
    await update_numeric_field(message, state, "current_weight_kg", session_maker)


@router.message(EditProfile.waiting_height)
async def update_height(message: Message, state: FSMContext, session_maker) -> None:
    await update_numeric_field(message, state, "height_cm", session_maker)


@router.message(EditProfile.waiting_activity)
async def update_activity(message: Message, state: FSMContext, session_maker) -> None:
    data = await state.get_data()
    lang = data.get("language", "en")
    mapping = {
        t(lang, "activity_low"): "low",
        t(lang, "activity_medium"): "medium",
        t(lang, "activity_high"): "high",
    }
    value = mapping.get(message.text)
    if value is None:
        await message.answer(t(lang, "ask_activity_level"), reply_markup=activity_keyboard(lang))
        return
    await save_field(session_maker, message.from_user.id, "activity_level", value)
    await finish_edit(message, state, lang)


@router.message(EditProfile.waiting_goal)
async def update_goal(message: Message, state: FSMContext, session_maker) -> None:
    data = await state.get_data()
    lang = data.get("language", "en")
    mapping = {
        t(lang, "goal_weight_loss"): "weight_loss",
        t(lang, "goal_maintenance"): "maintenance",
        t(lang, "goal_weight_gain"): "weight_gain",
        t(lang, "goal_symptom_control"): "symptom_control",
    }
    value = mapping.get(message.text)
    if value is None:
        await message.answer(t(lang, "ask_nutrition_goal"), reply_markup=nutrition_goal_keyboard(lang))
        return
    await save_field(session_maker, message.from_user.id, "nutrition_goal", value)
    await finish_edit(message, state, lang)


def parse_float(value: str) -> float | None:
    try:
        normalized = value.replace(",", ".")
        return float(normalized)
    except ValueError:
        return None


async def update_numeric_field(message: Message, state: FSMContext, field_name: str, session_maker) -> None:
    data = await state.get_data()
    lang = data.get("language", "en")
    value = parse_float(message.text)
    if value is None:
        await message.answer(t(lang, "invalid_number"))
        return
    await save_field(session_maker, message.from_user.id, field_name, value)
    await finish_edit(message, state, lang)


async def save_field(session_maker, telegram_id: int, field_name: str, value) -> None:
    async with session_maker() as session:
        user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
        if not user:
            return
        setattr(user, field_name, value)
        await session.commit()


async def finish_edit(message: Message, state: FSMContext, lang: str) -> None:
    await state.clear()
    await message.answer(t(lang, "updated"), reply_markup=main_menu(lang))
