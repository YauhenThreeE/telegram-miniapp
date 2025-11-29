from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import select

from ..db import get_session_maker
from ..i18n import t
from ..models import User

router = Router()


def _detect_language(user: User | None) -> str:
    return user.language if user else "en"


async def _load_user(bot: object, telegram_id: int) -> User | None:
    session_maker = get_session_maker(bot)
    async with session_maker() as session:
        return await session.scalar(select(User).where(User.telegram_id == telegram_id))


@router.message(Command("help"))
async def help_command(message: Message) -> None:
    user = await _load_user(message.bot, message.from_user.id)
    lang = _detect_language(user)
    await message.answer(t(lang, "help_text"))
    if not user:
        await message.answer(t(lang, "profile_missing"))
