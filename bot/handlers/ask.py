from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from sqlalchemy import select

from ..db import async_session_maker, get_session_maker
from ..i18n import SUPPORTED_LANGUAGES, t
from ..models import User
from ..services.ai_dietitian import AiDietitianService

router = Router()


class AskDialog(StatesGroup):
    awaiting_question = State()


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


@router.message(Command("ask"))
@router.message(F.text.in_({t(lang, "menu_ask_dietitian") for lang in SUPPORTED_LANGUAGES}))
async def start_ask(message: Message, state: FSMContext) -> None:
    user, lang = await _ensure_user(message)
    if not user:
        return

    await state.set_state(AskDialog.awaiting_question)
    await state.update_data(user_id=user.id, language=lang)
    await message.answer(t(lang, "ask_dietitian_intro"))
    await message.answer(t(lang, "ask_dietitian_disclaimer"))
    await message.answer(t(lang, "ask_dietitian_prompt"))


@router.message(AskDialog.awaiting_question)
async def receive_question(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("language", "en")
    user_id = data.get("user_id")

    if not user_id:
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
        session_maker = get_session_maker(message.bot)
        async with session_maker() as session:
            user = await session.get(User, user_id)
            if not user:
                await message.answer(t(lang, "profile_missing"))
                await state.clear()
                return

            await ai_service.save_message(session, user, "user", question)
            recent_messages = await ai_service.get_recent_messages(session, user)
            recent_meals = await ai_service.get_recent_meals(session, user)
            recent_water = await ai_service.get_recent_water(session, user)
            recent_weights = await ai_service.get_recent_weights(session, user)

            reply_text = await ai_service.generate_reply(
                user=user,
                recent_meals=recent_meals,
                recent_water=recent_water,
                recent_weights=recent_weights,
                recent_messages=recent_messages,
                user_message=question,
                language=lang,
            )
            await ai_service.save_message(session, user, "assistant", reply_text)
    except Exception:
        await message.answer(t(lang, "ask_dietitian_error"))
        return

    await message.answer(reply_text)
