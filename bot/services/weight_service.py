from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import User, WeightLog


async def log_weight(session: AsyncSession, user: User, weight: float) -> tuple[WeightLog, WeightLog | None]:
    last_log = await session.scalar(
        select(WeightLog)
        .where(WeightLog.user_id == user.id)
        .order_by(WeightLog.datetime.desc())
    )

    new_log = WeightLog(user_id=user.id, weight_kg=weight)
    session.add(new_log)
    user.current_weight_kg = weight

    await session.commit()
    await session.refresh(new_log)
    return new_log, last_log
