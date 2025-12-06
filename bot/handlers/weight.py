from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

from ..i18n import SUPPORTED_LANGUAGES, t
from ..keyboards import main_menu
from ..models import User
from ..services.weight_service import log_weight

router = Router()


class WeightStates(StatesGroup):
    waiting_weight = State()


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
async def start_weight_log(message: Message, state: FSMContext, user: User | None, lang: str) -> None:
    if not user:
        return

    await state.set_state(WeightStates.waiting_weight)
    await state.update_data(user_id=user.id, language=lang)
    await message.answer(t(lang, "ask_weight"))


@router.message(WeightStates.waiting_weight)
async def weight_entered(message: Message, state: FSMContext, user: User | None, lang: str, session_maker) -> None:
    if not user:
        await message.answer(t(lang, "profile_missing"))
        await state.clear()
        return

    weight = _parse_weight(message.text or "")
    if weight is None or weight <= 0:
        await message.answer(t(lang, "weight_invalid"))
        return

    async with session_maker() as session:
        new_log, last_log = await log_weight(session, user, weight)

    delta_since_last = weight - last_log.weight_kg if last_log else None
    delta_vs_goal = weight - user.goal_weight_kg if user.goal_weight_kg else None

    lines = [t(lang, "weight_saved")]
    if last_log:
        lines.append(t(lang, "weight_change_since_last", delta=_format_delta(delta_since_last)))
    else:
        lines.append(t(lang, "weight_no_previous"))

    if delta_vs_goal is not None:
        lines.append(t(lang, "weight_change_vs_goal", delta=_format_delta(delta_vs_goal)))

    await message.answer("\n".join(lines), reply_markup=main_menu(lang))
    await state.clear()
