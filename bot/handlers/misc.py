from __future__ import annotations

from aiogram import F, Router
from aiogram.types import Message
from sqlalchemy import select

from ..db import async_session_maker, get_session_maker
from ..i18n import t
from ..models import User

router = Router()


async def _load_user(bot: object, telegram_id: int) -> User | None:
    session_maker = get_session_maker(bot)
    async with session_maker() as session:
        return await session.scalar(select(User).where(User.telegram_id == telegram_id))


@router.message(F.text)
async def unknown_text(message: Message) -> None:
    user = await _load_user(message.bot, message.from_user.id)
    lang = user.language if user else "en"
    await message.answer(t(lang, "unknown_command"))
