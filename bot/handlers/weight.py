from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from sqlalchemy import select

from ..db import get_session_maker
from ..i18n import SUPPORTED_LANGUAGES, t
from ..keyboards import main_menu
from ..models import User, WeightLog

router = Router()


class WeightStates(StatesGroup):
    waiting_weight = State()


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


def _format_delta(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value:+.1f}"


def _parse_weight(text: str) -> float | None:
    try:
        return float(text.replace(",", "."))
    except (TypeError, ValueError):
        return None


@router.message(Command("weight"))
@router.message(F.text.in_({t(lang, "menu_weight") for lang in SUPPORTED_LANGUAGES}))
async def start_weight_log(message: Message, state: FSMContext) -> None:
    user, lang = await _ensure_user(message)
    if not user:
        return

    await state.set_state(WeightStates.waiting_weight)
    await state.update_data(user_id=user.id, language=lang)
    await message.answer(t(lang, "ask_weight"))


@router.message(WeightStates.waiting_weight)
async def weight_entered(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("language", "en")
    user_id = data.get("user_id")

    if not user_id:
        await message.answer(t(lang, "profile_missing"))
        await state.clear()
        return

    weight = _parse_weight(message.text or "")
    if weight is None or weight <= 0:
        await message.answer(t(lang, "weight_invalid"))
        return

    session_maker = get_session_maker(message.bot)
    async with session_maker() as session:
        user = await session.get(User, user_id)
        last_log = await session.scalar(
            select(WeightLog)
            .where(WeightLog.user_id == user_id)
            .order_by(WeightLog.datetime.desc())
        )

        new_log = WeightLog(user_id=user_id, weight_kg=weight)
        session.add(new_log)

        if user:
            user.current_weight_kg = weight

        await session.commit()

    delta_since_last = weight - last_log.weight_kg if last_log else None
    delta_vs_goal = weight - user.goal_weight_kg if user and user.goal_weight_kg else None

    lines = [t(lang, "weight_saved")]
    if last_log:
        lines.append(t(lang, "weight_change_since_last", delta=_format_delta(delta_since_last)))
    else:
        lines.append(t(lang, "weight_no_previous"))

    if delta_vs_goal is not None:
        lines.append(t(lang, "weight_change_vs_goal", delta=_format_delta(delta_vs_goal)))

    await message.answer("\n".join(lines), reply_markup=main_menu(lang))
    await state.clear()
