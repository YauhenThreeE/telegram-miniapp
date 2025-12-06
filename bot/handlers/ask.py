from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from ..i18n import SUPPORTED_LANGUAGES, t
from ..models import User
from ..services.ai_dietitian import AiDietitianService
from ..services.ask_service import handle_question

router = Router()


class AskDialog(StatesGroup):
    awaiting_question = State()


@router.message(Command("ask"))
@router.message(F.text.in_({t(lang, "menu_ask_dietitian") for lang in SUPPORTED_LANGUAGES}))
async def start_ask(message: Message, state: FSMContext, user: User | None, lang: str) -> None:
    if not user:
        return

    await state.set_state(AskDialog.awaiting_question)
    await state.update_data(user_id=user.id, language=lang)
    await message.answer(t(lang, "ask_dietitian_intro"))
    await message.answer(t(lang, "ask_dietitian_disclaimer"))
    await message.answer(t(lang, "ask_dietitian_prompt"))


@router.message(AskDialog.awaiting_question)
async def receive_question(
    message: Message,
    state: FSMContext,
    user: User | None,
    lang: str,
    session_maker,
) -> None:
    data = await state.get_data()

    if not user:
        await message.answer(t(lang, "profile_missing"))
        await state.clear()
        return

    question = message.text.strip() if message.text else ""
    if not question:
        await message.answer(t(lang, "ask_dietitian_prompt"))
        return

    ai_service: AiDietitianService | None = getattr(message.bot, "ai_dietitian_service", None)
    if not ai_service:
        await message.answer(t(lang, "ask_dietitian_error"))
        return

    try:
        async with session_maker() as session:
            reply_text = await handle_question(
                session=session,
                ai_service=ai_service,
                user=user,
                question=question,
                lang=lang,
            )
    except Exception:
        await message.answer(t(lang, "ask_dietitian_error"))
        return

    await message.answer(reply_text)
