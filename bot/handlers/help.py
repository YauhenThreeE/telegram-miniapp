from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from ..i18n import t
from ..models import User

router = Router()


@router.message(Command("help"))
async def help_command(message: Message, user: User | None, lang: str) -> None:
    await message.answer(t(lang, "help_text"))
    if not user:
        await message.answer(t(lang, "profile_missing"))
