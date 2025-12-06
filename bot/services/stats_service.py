from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.sql import desc
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Meal, WaterIntake, WeightLog


def today_range_utc() -> tuple[datetime, datetime]:
    now = datetime.now(timezone.utc)
    start = datetime(year=now.year, month=now.month, day=now.day, tzinfo=timezone.utc)
    end = start + timedelta(days=1)
    return start, end


async def fetch_daily_stats(session: AsyncSession, user_id: int) -> tuple[tuple, float | None, WeightLog | None]:
    start, end = today_range_utc()

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
            Meal.user_id == user_id,
            Meal.created_at >= start,
            Meal.created_at < end,
        )
    )
    totals = (await session.execute(totals_stmt)).one_or_none()

    water_stmt = (
        select(func.sum(WaterIntake.volume_ml))
        .where(
            WaterIntake.user_id == user_id,
            WaterIntake.datetime >= start,
            WaterIntake.datetime < end,
        )
        .limit(1)
    )
    water_total = await session.scalar(water_stmt)

    last_weight = await session.scalar(
        select(WeightLog)
        .where(WeightLog.user_id == user_id)
        .order_by(desc(WeightLog.datetime))
    )
    return totals, water_total, last_weight


async def reset_today(session: AsyncSession, user_id: int) -> None:
    start, end = today_range_utc()
    await session.execute(
        Meal.__table__.delete().where(
            Meal.user_id == user_id,
            Meal.created_at >= start,
            Meal.created_at < end,
        )
    )
    await session.execute(
        WaterIntake.__table__.delete().where(
            WaterIntake.user_id == user_id,
            WaterIntake.datetime >= start,
            WaterIntake.datetime < end,
        )
    )
    await session.commit()


async def reset_all(session: AsyncSession, user_id: int) -> None:
    await session.execute(Meal.__table__.delete().where(Meal.user_id == user_id))
    await session.execute(WaterIntake.__table__.delete().where(WaterIntake.user_id == user_id))
    await session.execute(WeightLog.__table__.delete().where(WeightLog.user_id == user_id))
    await session.commit()
