from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from ..i18n import t
from ..models import User
from ..services.user_service import delete_user_with_data

router = Router()


def _confirm_keyboard(lang: str, telegram_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t(lang, "delete_me_confirm_button_yes"),
                    callback_data=f"delete_me_yes:{telegram_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text=t(lang, "delete_me_confirm_button_no"),
                    callback_data=f"delete_me_no:{telegram_id}",
                )
            ],
        ]
    )


@router.message(Command("delete_me"))
async def delete_me_command(message: Message, user: User | None, lang: str) -> None:
    if not user:
        await message.answer(t(lang, "profile_missing"))
        return

    await message.answer(
        "\n".join([t(lang, "delete_me_intro"), t(lang, "delete_me_confirm_text")]),
        reply_markup=_confirm_keyboard(lang, message.from_user.id),
    )


@router.callback_query(F.data.startswith("delete_me_no:"))
async def delete_me_cancel(callback: CallbackQuery, user: User | None, lang: str) -> None:
    _, telegram_id = callback.data.split(":", 1)
    if str(callback.from_user.id) != telegram_id:
        await callback.answer()
        return
    await callback.message.answer(t(lang, "delete_me_cancelled"))
    await callback.answer()


@router.callback_query(F.data.startswith("delete_me_yes:"))
async def delete_me_confirm(callback: CallbackQuery, user: User | None, lang: str, session_maker) -> None:
    _, telegram_id = callback.data.split(":", 1)
    if str(callback.from_user.id) != telegram_id:
        await callback.answer()
        return
    if not user:
        await callback.message.answer(t(lang, "profile_missing"))
        await callback.answer()
        return

    async with session_maker() as session:
        async with session.begin():
            await delete_user_with_data(session, user.id)

    await callback.message.answer(t(lang, "delete_me_done"))
    await callback.answer()
