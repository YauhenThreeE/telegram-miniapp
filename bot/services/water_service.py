from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import WaterIntake


def _today_range_utc() -> tuple[datetime, datetime]:
    now = datetime.now(timezone.utc)
    start = datetime(year=now.year, month=now.month, day=now.day, tzinfo=timezone.utc)
    end = start + timedelta(days=1)
    return start, end


async def add_water_and_total(session: AsyncSession, user_id: int, volume_ml: float) -> float:
    start, end = _today_range_utc()
    intake = WaterIntake(user_id=user_id, volume_ml=volume_ml)
    session.add(intake)
    await session.commit()

    total_stmt = (
        select(func.sum(WaterIntake.volume_ml))
        .where(
            WaterIntake.user_id == user_id,
            WaterIntake.datetime >= start,
            WaterIntake.datetime < end,
        )
        .limit(1)
    )
    total_ml = await session.scalar(total_stmt)
    return float(total_ml or 0)
