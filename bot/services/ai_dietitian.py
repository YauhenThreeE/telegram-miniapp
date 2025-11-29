from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import ConversationMessage, Meal, User, WaterIntake, WeightLog


class AiDietitianService:
    """Stubbed AI dietitian dialog service.

    Replace the mocked response with a real LLM integration (e.g., OpenAI Chat Completions)
    that uses the provided user context and recent logs to generate tailored guidance.
    """

    def __init__(self, openai_api_key: str | None):
        self.openai_api_key = openai_api_key

    async def get_recent_messages(
        self, session: AsyncSession, user: User, limit: int = 10
    ) -> list[ConversationMessage]:
        stmt = (
            select(ConversationMessage)
            .where(ConversationMessage.user_id == user.id)
            .order_by(desc(ConversationMessage.created_at))
            .limit(limit)
        )
        result = await session.scalars(stmt)
        return list(result)

    async def save_message(
        self, session: AsyncSession, user: User, role: str, content: str
    ) -> ConversationMessage:
        message = ConversationMessage(user_id=user.id, role=role, content=content)
        session.add(message)
        await session.commit()
        await session.refresh(message)
        return message

    async def get_recent_meals(
        self, session: AsyncSession, user: User, limit: int = 10
    ) -> list[Meal]:
        stmt = (
            select(Meal)
            .where(Meal.user_id == user.id)
            .order_by(desc(Meal.created_at))
            .limit(limit)
        )
        result = await session.scalars(stmt)
        return list(result)

    async def get_recent_water(
        self, session: AsyncSession, user: User, days: int = 1
    ) -> list[WaterIntake]:
        now = datetime.now(timezone.utc)
        start = now - timedelta(days=days)
        stmt = (
            select(WaterIntake)
            .where(
                WaterIntake.user_id == user.id,
                WaterIntake.datetime >= start,
                WaterIntake.datetime <= now,
            )
            .order_by(desc(WaterIntake.datetime))
        )
        result = await session.scalars(stmt)
        return list(result)

    async def get_recent_weights(
        self, session: AsyncSession, user: User, limit: int = 3
    ) -> list[WeightLog]:
        stmt = (
            select(WeightLog)
            .where(WeightLog.user_id == user.id)
            .order_by(desc(WeightLog.datetime))
            .limit(limit)
        )
        result = await session.scalars(stmt)
        return list(result)

    async def generate_reply(
        self,
        user: User,
        recent_meals: list[Meal],
        recent_water: list[WaterIntake],
        recent_weights: list[WeightLog],
        recent_messages: list[ConversationMessage],
        user_message: str,
        language: str,
    ) -> str:
        # TODO: build a rich prompt and call a real LLM (e.g., OpenAI Chat Completions)
        # Example structure:
        # system_prompt = (
        #     "You are an AI nutrition coach and dietitian assistant. You know a lot about"
        #     " nutrition and digestion but you are NOT a doctor and do NOT give medical"
        #     " diagnosis. Provide safe, general educational guidance, suggest questions"
        #     " to ask a real doctor in case of serious symptoms, and adapt recommendations"
        #     " to the user's GI conditions and goals."
        # )
        # context = {
        #     "user": {
        #         "sex": user.sex,
        #         "age": _calculate_age(user.date_of_birth),
        #         "height_cm": user.height_cm,
        #         "current_weight_kg": user.current_weight_kg,
        #         "goal_weight_kg": user.goal_weight_kg,
        #         "gi_diagnoses": user.gi_diagnoses,
        #         "allergies": user.allergies_intolerances,
        #         "activity_level": user.activity_level,
        #         "nutrition_goal": user.nutrition_goal,
        #     },
        #     "meals": [meal.raw_text for meal in recent_meals[:5]],
        #     "water_ml_last_day": sum(w.volume_ml for w in recent_water),
        #     "weights": [w.weight_kg for w in recent_weights],
        #     "messages": [m.content for m in recent_messages],
        # }
        # response = openai.ChatCompletion.create(...)
        # return response.choices[0].message["content"]

        if language == "ru":
            return (
                "Это примерный совет на основе ваших данных. Пейте достаточно воды,"
                " добавляйте овощи и белок в каждый приём пищи. Это не медицинская"
                " рекомендация — при серьёзных симптомах обращайтесь к врачу."
            )
        if language == "pl":
            return (
                "To ogólna wskazówka na podstawie twoich danych. Pij odpowiednią ilość"
                " wody i dodawaj warzywa oraz białko do posiłków. To nie jest porada"
                " medyczna — w razie poważnych objawów skonsultuj się z lekarzem."
            )
        return (
            "Here is a general suggestion based on your info. Stay hydrated and include"
            " veggies and protein in your meals. This is not medical advice — please"
            " consult a doctor for serious or persistent symptoms."
        )


def _calculate_age(birth_date: date | None) -> int | None:
    if not birth_date:
        return None
    today = datetime.now().date()
    years = today.year - birth_date.year - (
        (today.month, today.day) < (birth_date.month, birth_date.day)
    )
    return years
