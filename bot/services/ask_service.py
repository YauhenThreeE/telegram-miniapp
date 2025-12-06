from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from ..models import User
from .ai_dietitian import AiDietitianService


async def handle_question(
    session: AsyncSession,
    ai_service: AiDietitianService,
    user: User,
    question: str,
    lang: str,
) -> str:
    await ai_service.save_message(session, user, "user", question)
    recent_messages = await ai_service.get_recent_messages(session, user)
    recent_meals = await ai_service.get_recent_meals(session, user)
    recent_water = await ai_service.get_recent_water(session, user)
    recent_weights = await ai_service.get_recent_weights(session, user)

    reply_text = await ai_service.generate_reply(
        user=user,
        recent_meals=recent_meals,
        recent_water=recent_water,
        recent_weights=recent_weights,
        recent_messages=recent_messages,
        user_message=question,
        language=lang,
    )
    await ai_service.save_message(session, user, "assistant", reply_text)
    return reply_text
