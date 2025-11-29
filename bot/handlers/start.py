from __future__ import annotations

from datetime import datetime

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select

from ..db import async_session_maker, get_session_maker
from ..i18n import SUPPORTED_LANGUAGES, t
from ..keyboards import (
    activity_keyboard,
    language_keyboard,
    main_menu,
    nutrition_goal_keyboard,
    sex_keyboard,
    skip_keyboard,
)
from ..models import User

router = Router()


class Onboarding(StatesGroup):
    sex = State()
    date_of_birth = State()
    height_cm = State()
    current_weight_kg = State()
    goal_weight_kg = State()
    gi_diagnoses = State()
    other_diagnoses = State()
    medications = State()
    allergies_intolerances = State()
    activity_level = State()
    nutrition_goal = State()


def parse_float(value: str) -> float | None:
    try:
        normalized = value.replace(",", ".")
        return float(normalized)
    except ValueError:
        return None


def parse_date(text: str) -> datetime | None:
    for fmt in ("%d.%m.%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


async def get_or_create_user(telegram_id: int, language: str, message: Message) -> User:
    session_maker = get_session_maker(message.bot)
    async with session_maker() as session:
        user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
        if user:
            user.language = language
        else:
            user = User(
                telegram_id=telegram_id,
                username=message.from_user.username if message.from_user else None,
                first_name=message.from_user.first_name if message.from_user else None,
                last_name=message.from_user.last_name if message.from_user else None,
                language=language,
            )
            session.add(user)
        await session.commit()
        await session.refresh(user)
    return user


@router.message(CommandStart())
async def start(message: Message, state: FSMContext) -> None:
    await state.clear()
    session_maker = get_session_maker(message.bot)
    async with session_maker() as session:
        user = await session.scalar(select(User).where(User.telegram_id == message.from_user.id))
    if user:
        lang = user.language
        await message.answer(t(lang, "welcome"), reply_markup=main_menu(lang))
    else:
        await message.answer(t("en", "choose_language"), reply_markup=language_keyboard())


@router.callback_query(F.data.startswith("lang_"))
async def language_selected(callback: CallbackQuery, state: FSMContext) -> None:
    code = callback.data.split("_", 1)[1]
    if code not in SUPPORTED_LANGUAGES:
        await callback.answer()
        return

    user = await get_or_create_user(callback.from_user.id, code, callback.message)

    await callback.message.answer(t(code, "language_selected", language=code))
    await callback.message.answer(t(code, "welcome"))
    await callback.message.answer(t(code, "ask_sex"), reply_markup=sex_keyboard(code))
    await state.update_data(language=code, user_id=user.id)
    await state.set_state(Onboarding.sex)
    await callback.answer()


@router.message(Onboarding.sex)
async def onboarding_sex(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("language", "en")
    mapping = {
        t(lang, "sex_m"): "M",
        t(lang, "sex_f"): "F",
        t(lang, "sex_other"): "other",
    }
    value = mapping.get(message.text)
    if value is None:
        await message.answer(t(lang, "ask_sex"), reply_markup=sex_keyboard(lang))
        return
    await state.update_data(sex=value)
    await state.set_state(Onboarding.date_of_birth)
    await message.answer(t(lang, "ask_date_of_birth"))


@router.message(Onboarding.date_of_birth)
async def onboarding_dob(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("language", "en")
    dob = parse_date(message.text)
    if not dob:
        await message.answer(t(lang, "invalid_date"))
        return
    await state.update_data(date_of_birth=dob.date())
    await state.set_state(Onboarding.height_cm)
    await message.answer(t(lang, "ask_height"))


@router.message(Onboarding.height_cm)
async def onboarding_height(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("language", "en")
    value = parse_float(message.text)
    if value is None:
        await message.answer(t(lang, "invalid_number"))
        return
    await state.update_data(height_cm=value)
    await state.set_state(Onboarding.current_weight_kg)
    await message.answer(t(lang, "ask_weight"))


@router.message(Onboarding.current_weight_kg)
async def onboarding_current_weight(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("language", "en")
    value = parse_float(message.text)
    if value is None:
        await message.answer(t(lang, "invalid_number"))
        return
    await state.update_data(current_weight_kg=value)
    await state.set_state(Onboarding.goal_weight_kg)
    await message.answer(t(lang, "ask_goal_weight"), reply_markup=skip_keyboard(lang))


@router.message(Onboarding.goal_weight_kg)
async def onboarding_goal_weight(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("language", "en")
    if message.text == t(lang, "skip"):
        await state.update_data(goal_weight_kg=None)
    else:
        value = parse_float(message.text)
        if value is None:
            await message.answer(t(lang, "invalid_number"))
            return
        await state.update_data(goal_weight_kg=value)
    await state.set_state(Onboarding.gi_diagnoses)
    await message.answer(t(lang, "ask_gi_diagnoses"))


@router.message(Onboarding.gi_diagnoses)
async def onboarding_gi(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("language", "en")
    await state.update_data(gi_diagnoses=message.text)
    await state.set_state(Onboarding.other_diagnoses)
    await message.answer(t(lang, "ask_other_diagnoses"))


@router.message(Onboarding.other_diagnoses)
async def onboarding_other_diagnoses(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("language", "en")
    await state.update_data(other_diagnoses=message.text)
    await state.set_state(Onboarding.medications)
    await message.answer(t(lang, "ask_medications"))


@router.message(Onboarding.medications)
async def onboarding_medications(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("language", "en")
    await state.update_data(medications=message.text)
    await state.set_state(Onboarding.allergies_intolerances)
    await message.answer(t(lang, "ask_allergies"))


@router.message(Onboarding.allergies_intolerances)
async def onboarding_allergies(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("language", "en")
    await state.update_data(allergies_intolerances=message.text)
    await state.set_state(Onboarding.activity_level)
    await message.answer(t(lang, "ask_activity_level"), reply_markup=activity_keyboard(lang))


@router.message(Onboarding.activity_level)
async def onboarding_activity(message: Message, state: FSMContext) -> None:
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
    await state.update_data(activity_level=value)
    await state.set_state(Onboarding.nutrition_goal)
    await message.answer(t(lang, "ask_nutrition_goal"), reply_markup=nutrition_goal_keyboard(lang))


@router.message(Onboarding.nutrition_goal)
async def onboarding_goal(message: Message, state: FSMContext) -> None:
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
    await state.update_data(nutrition_goal=value)

    await save_onboarding(state, message.from_user.id, message.bot)
    await message.answer(t(lang, "profile_saved"), reply_markup=main_menu(lang))
    await state.clear()


async def save_onboarding(state: FSMContext, telegram_id: int, bot: object | None) -> None:
    data = await state.get_data()
    session_maker = get_session_maker(bot)
    async with session_maker() as session:
        user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
        if not user:
            return
        user.sex = data.get("sex")
        user.date_of_birth = data.get("date_of_birth")
        user.height_cm = data.get("height_cm")
        user.current_weight_kg = data.get("current_weight_kg")
        user.goal_weight_kg = data.get("goal_weight_kg")
        user.gi_diagnoses = data.get("gi_diagnoses")
        user.other_diagnoses = data.get("other_diagnoses")
        user.medications = data.get("medications")
        user.allergies_intolerances = data.get("allergies_intolerances")
        user.activity_level = data.get("activity_level")
        user.nutrition_goal = data.get("nutrition_goal")
        await session.commit()


@router.message(
    F.text.in_(
        {
            t(lang, key)
            for lang in SUPPORTED_LANGUAGES
            for key in [
                "btn_fridge",
                "btn_budget",
            ]
        }
    )
)
async def stub_features(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("language")
    if not lang:
        session_maker = get_session_maker(message.bot)
        async with session_maker() as session:
            user = await session.scalar(select(User).where(User.telegram_id == message.from_user.id))
            lang = user.language if user else "en"
    await message.answer(t(lang, "not_implemented"))
