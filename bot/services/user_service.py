from __future__ import annotations

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import ConversationMessage, Meal, Recipe, User, WaterIntake, WeightLog


async def delete_user_with_data(session: AsyncSession, user_id: int) -> None:
    await session.execute(delete(Meal).where(Meal.user_id == user_id))
    await session.execute(delete(WaterIntake).where(WaterIntake.user_id == user_id))
    await session.execute(delete(WeightLog).where(WeightLog.user_id == user_id))
    await session.execute(delete(ConversationMessage).where(ConversationMessage.user_id == user_id))
    await session.execute(delete(Recipe).where(Recipe.user_id == user_id))
    await session.execute(delete(User).where(User.id == user_id))
