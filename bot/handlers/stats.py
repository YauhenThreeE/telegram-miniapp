from __future__ import annotations

from datetime import datetime, timedelta, timezone

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import func, select
from sqlalchemy.sql import desc

from ..db import async_session_maker
from ..i18n import SUPPORTED_LANGUAGES, t
from ..models import Meal, User, WaterIntake, WeightLog

router = Router()


def _today_range_utc() -> tuple[datetime, datetime]:
    now = datetime.now(timezone.utc)
    start = datetime(year=now.year, month=now.month, day=now.day, tzinfo=timezone.utc)
    end = start + timedelta(days=1)
    return start, end


async def _load_user(telegram_id: int) -> User | None:
    async with async_session_maker() as session:
        return await session.scalar(select(User).where(User.telegram_id == telegram_id))


@router.message(Command("stats"))
@router.message(F.text.in_({t(lang, "menu_stats") for lang in SUPPORTED_LANGUAGES}))
async def daily_stats(message: Message) -> None:
    user = await _load_user(message.from_user.id)
    lang = user.language if user else "en"
    if not user:
        await message.answer(t(lang, "profile_missing"))
        return

    start, end = _today_range_utc()

    try:
        async with async_session_maker() as session:
            totals_stmt = (
                select(
                    func.sum(Meal.calories),
                    func.sum(Meal.protein_g),
                    func.sum(Meal.fat_g),
                    func.sum(Meal.carbs_g),
                    func.sum(Meal.fiber_g),
                    func.sum(Meal.sugar_g),
                )
                .where(
                    Meal.user_id == user.id,
                    Meal.created_at >= start,
                    Meal.created_at < end,
                )
            )
            totals = (await session.execute(totals_stmt)).one_or_none()

            water_stmt = (
                select(func.sum(WaterIntake.volume_ml))
                .where(
                    WaterIntake.user_id == user.id,
                    WaterIntake.datetime >= start,
                    WaterIntake.datetime < end,
                )
                .limit(1)
            )
            water_total = await session.scalar(water_stmt)

            last_weight = await session.scalar(
                select(WeightLog)
                    .where(WeightLog.user_id == user.id)
                    .order_by(desc(WeightLog.datetime))
            )
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


def _fmt(value: float | int | None) -> str:
    if value is None:
        return "-"
    return f"{float(value):.1f}"
