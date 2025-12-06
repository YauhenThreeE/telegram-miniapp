from __future__ import annotations

from aiogram import F, Router
from aiogram.types import Message

from ..i18n import t
from ..models import User

router = Router()


@router.message(F.text)
async def unknown_text(message: Message, user: User | None, lang: str) -> None:
    await message.answer(t(lang, "unknown_command"))
