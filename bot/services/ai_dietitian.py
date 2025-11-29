from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone

try:
    from openai import AsyncOpenAI
except ImportError:  # pragma: no cover - fallback if dependency не установлена
    AsyncOpenAI = None  # type: ignore

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import ConversationMessage, Meal, User, WaterIntake, WeightLog

logger = logging.getLogger(__name__)


class AiDietitianService:
    """Stubbed AI dietitian dialog service.

    Replace the mocked response with a real LLM integration (e.g., OpenAI Chat Completions)
    that uses the provided user context and recent logs to generate tailored guidance.
    """

    def __init__(self, openai_api_key: str | None):
        self.openai_api_key = openai_api_key
        self.client = AsyncOpenAI(api_key=openai_api_key) if openai_api_key and AsyncOpenAI else None
        self.model = "gpt-4o-mini"

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
        # Без ключа работаем по старой заглушке.
        if not self.client:
            return _fallback(language)

        age = _calculate_age(user.date_of_birth)
        messages = [
            {
                "role": "system",
                "content": (
                    "You are an AI nutrition coach and dietitian assistant. You are NOT a doctor."
                    " Provide safe, general educational guidance. Do not give medical diagnoses."
                    " Be concise (4-6 sentences). If symptoms are serious, suggest talking to a doctor."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"User profile: sex={user.sex}, age={age}, height_cm={user.height_cm}, "
                    f"current_weight_kg={user.current_weight_kg}, goal_weight_kg={user.goal_weight_kg}, "
                    f"GI diagnoses={user.gi_diagnoses}, other diagnoses={user.other_diagnoses}, "
                    f"medications={user.medications}, allergies={user.allergies_intolerances}, "
                    f"activity_level={user.activity_level}, nutrition_goal={user.nutrition_goal}. "
                    f"Recent meals: {[m.raw_text for m in recent_meals[:5]]}. "
                    f"Water last {len(recent_water)} entries (ml): {[w.volume_ml for w in recent_water]}. "
                    f"Recent weights: {[w.weight_kg for w in recent_weights]}. "
                    f"Recent dialog: {[m.content for m in recent_messages]}. "
                    f"User says: {user_message}. Language: {language}."
                ),
            },
        ]

        try:
            resp = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=350,
                temperature=0.4,
            )
            return resp.choices[0].message.content
        except Exception as exc:  # noqa: BLE001
            logger.warning("Dietitian reply failed, falling back to stub: %s", exc)
            return _fallback(language)

    async def suggest_recipe(self, title: str, language: str) -> str:
        """
        Generate a short home-cooking recipe draft with ingredients and steps.
        Falls back to a local stub if no OpenAI client is configured.
        """

        if not self.client:
            return _recipe_fallback(language, title)

        system = (
            "You help home cooks. Given a recipe title, return a concise recipe with "
            "ingredients list and 4-6 numbered steps. Keep it simple and practical. "
            "Return plain text; avoid markdown formatting."
        )
        user_prompt = f"Title: {title}. Language: {language}."
        try:
            resp = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=400,
                temperature=0.5,
            )
            return resp.choices[0].message.content
        except Exception as exc:  # noqa: BLE001
            logger.warning("Recipe suggestion failed, falling back to stub: %s", exc)
            return _recipe_fallback(language, title)


def _calculate_age(birth_date: date | None) -> int | None:
    if not birth_date:
        return None
    today = datetime.now().date()
    years = today.year - birth_date.year - (
        (today.month, today.day) < (birth_date.month, birth_date.day)
    )
    return years


def _fallback(language: str) -> str:
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


def _recipe_fallback(language: str, title: str) -> str:
    base = (
        f"{title}\n\n"
        "Ingredients:\n"
        "- Protein of choice (chicken/tofu) — 200 g\n"
        "- Vegetables mix — 300 g\n"
        "- Olive oil — 1 tbsp\n"
        "- Salt, pepper, herbs to taste\n\n"
        "Steps:\n"
        "1) Cut protein and vegetables into bite-size pieces.\n"
        "2) Heat oil in a pan, add protein, cook until golden.\n"
        "3) Add vegetables, salt, pepper, herbs; sauté 6–8 minutes.\n"
        "4) Adjust seasoning and serve warm."
    )
    if language == "ru":
        return (
            f"{title}\n\n"
            "Ингредиенты:\n"
            "- Белок (курица/тофу) — 200 г\n"
            "- Овощная смесь — 300 г\n"
            "- Оливковое масло — 1 ст. л.\n"
            "- Соль, перец, травы по вкусу\n\n"
            "Шаги:\n"
            "1) Нарежьте белок и овощи небольшими кусочками.\n"
            "2) Разогрейте масло, обжарьте белок до золотистого цвета.\n"
            "3) Добавьте овощи, соль, перец, травы; тушите 6–8 минут.\n"
            "4) Подкорректируйте вкус и подавайте тёплым."
        )
    if language == "pl":
        return (
            f"{title}\n\n"
            "Składniki:\n"
            "- Białko (kurczak/tofu) — 200 g\n"
            "- Mieszanka warzyw — 300 g\n"
            "- Oliwa — 1 łyżka\n"
            "- Sól, pieprz, zioła do smaku\n\n"
            "Kroki:\n"
            "1) Pokrój białko i warzywa na małe kawałki.\n"
            "2) Rozgrzej oliwę, podsmaż białko na złoto.\n"
            "3) Dodaj warzywa, sól, pieprz, zioła; duś 6–8 minut.\n"
            "4) Dopraw do smaku i podawaj na ciepło."
        )
    return base
