from __future__ import annotations

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from sqlalchemy import select

from .db import get_session_maker
from .models import User


class UserContextMiddleware(BaseMiddleware):
    """
    Resolves user, language, and session_maker into handler context.
    Handlers can accept parameters: user, lang, session_maker.
    """

    async def __call__(self, handler, event: TelegramObject, data: dict):
        bot = data.get("bot")
        session_maker = get_session_maker(bot)
        data["session_maker"] = session_maker

        user = None
        lang = "en"

        # Not every update has from_user (e.g., channel posts), guard accordingly.
        from_user = getattr(event, "from_user", None)
        if from_user:
            async with session_maker() as session:
                user = await session.scalar(select(User).where(User.telegram_id == from_user.id))
            if user:
                lang = user.language

        data["user"] = user
        data["lang"] = lang
        return await handler(event, data)
