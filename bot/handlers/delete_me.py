from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy import delete, select

from ..db import async_session_maker
from ..i18n import t
from ..models import ConversationMessage, Meal, User, WaterIntake, WeightLog

router = Router()


async def _load_user(telegram_id: int) -> User | None:
    async with async_session_maker() as session:
        return await session.scalar(select(User).where(User.telegram_id == telegram_id))


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
async def delete_me_command(message: Message) -> None:
    user = await _load_user(message.from_user.id)
    lang = user.language if user else "en"
    if not user:
        await message.answer(t(lang, "profile_missing"))
        return

    await message.answer(
        "\n".join([t(lang, "delete_me_intro"), t(lang, "delete_me_confirm_text")]),
        reply_markup=_confirm_keyboard(lang, message.from_user.id),
    )


@router.callback_query(F.data.startswith("delete_me_no:"))
async def delete_me_cancel(callback: CallbackQuery) -> None:
    _, telegram_id = callback.data.split(":", 1)
    if str(callback.from_user.id) != telegram_id:
        await callback.answer()
        return
    user = await _load_user(callback.from_user.id)
    lang = user.language if user else "en"
    await callback.message.answer(t(lang, "delete_me_cancelled"))
    await callback.answer()


@router.callback_query(F.data.startswith("delete_me_yes:"))
async def delete_me_confirm(callback: CallbackQuery) -> None:
    _, telegram_id = callback.data.split(":", 1)
    if str(callback.from_user.id) != telegram_id:
        await callback.answer()
        return
    user = await _load_user(callback.from_user.id)
    lang = user.language if user else "en"
    if not user:
        await callback.message.answer(t(lang, "profile_missing"))
        await callback.answer()
        return

    async with async_session_maker() as session:
        async with session.begin():
            await session.execute(delete(Meal).where(Meal.user_id == user.id))
            await session.execute(delete(WaterIntake).where(WaterIntake.user_id == user.id))
            await session.execute(delete(WeightLog).where(WeightLog.user_id == user.id))
            await session.execute(delete(ConversationMessage).where(ConversationMessage.user_id == user.id))
            await session.execute(delete(User).where(User.id == user.id))

    await callback.message.answer(t(lang, "delete_me_done"))
    await callback.answer()
