from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from ..i18n import SUPPORTED_LANGUAGES, t
from ..models import User
from ..services.stats_service import fetch_daily_stats, reset_all, reset_today

router = Router()


@router.message(Command("stats"))
@router.message(F.text.in_({t(lang, "menu_stats") for lang in SUPPORTED_LANGUAGES}))
async def daily_stats(message: Message, user: User | None, lang: str, session_maker) -> None:
    if not user:
        await message.answer(t(lang, "profile_missing"))
        return

    try:
        async with session_maker() as session:
            totals, water_total, last_weight = await fetch_daily_stats(session, user.id)
    except Exception:
        await message.answer(t(lang, "stats_error"))
        return

    lines = [t(lang, "stats_today_title")]
    if totals and not all(value is None for value in totals):
        calories, protein, fat, carbs, fiber, sugar = (
            totals[0] or 0,
            totals[1] or 0,
            totals[2] or 0,
            totals[3] or 0,
            totals[4] or 0,
            totals[5] or 0,
        )

        lines.append(
            t(
                lang,
                "stats_today_line",
                calories=_fmt(calories),
                protein=_fmt(protein),
                fat=_fmt(fat),
                carbs=_fmt(carbs),
            )
        )
        if fiber or sugar:
            lines.append(
                t(
                    lang,
                    "stats_today_macros_title",
                )
                + f"\nFiber: {_fmt(fiber)} g, Sugar: {_fmt(sugar)} g"
            )
    else:
        lines.append(t(lang, "stats_today_no_meals"))

    if water_total:
        lines.append(t(lang, "stats_today_water_line", ml=int(water_total)))

    if last_weight:
        lines.append(
            t(
                lang,
                "stats_last_weight_line",
                weight=_fmt(last_weight.weight_kg),
                date=last_weight.datetime.date().isoformat(),
            )
        )

    await message.answer("\n".join(lines))


@router.message(Command("reset_stats"))
async def reset_stats(message: Message, user: User | None, lang: str, session_maker) -> None:
    if not user:
        await message.answer(t(lang, "profile_missing"))
        return

    try:
        async with session_maker() as session:
            await reset_today(session, user.id)
    except Exception:
        await message.answer(t(lang, "stats_reset_error"))
        return

    await message.answer(t(lang, "stats_reset_done"))


@router.message(Command("reset_all"))
async def reset_all_stats(message: Message, user: User | None, lang: str, session_maker) -> None:
    if not user:
        await message.answer(t(lang, "profile_missing"))
        return

    try:
        async with session_maker() as session:
            await reset_all(session, user.id)
    except Exception:
        await message.answer(t(lang, "stats_reset_all_error"))
        return

    await message.answer(t(lang, "stats_reset_all_done"))


def _fmt(value: float | int | None) -> str:
    if value is None:
        return "-"
    return f"{float(value):.1f}"
