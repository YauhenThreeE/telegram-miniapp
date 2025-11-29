from __future__ import annotations

import json
import logging
from typing import Any

try:
    from openai import AsyncOpenAI
except ImportError:  # pragma: no cover - fallback if dependency не установлена
    AsyncOpenAI = None  # type: ignore

logger = logging.getLogger(__name__)


class AiNutritionService:
    """Stub service that will later call a real LLM or food database."""

    def __init__(self, openai_api_key: str | None) -> None:
        self.openai_api_key = openai_api_key
        self.client = AsyncOpenAI(api_key=openai_api_key) if openai_api_key and AsyncOpenAI else None
        self.model = "gpt-4o-mini"
        self._fallback = {
            "calories": 500.0,
            "protein_g": 20.0,
            "fat_g": 15.0,
            "carbs_g": 60.0,
            "fiber_g": 5.0,
            "sugar_g": 10.0,
            "ai_notes": "Approximate values based on user description.",
        }

    async def estimate_meal_from_text(self, text: str, language: str | None = None) -> dict[str, Any]:
        """
        Estimate macros via OpenAI. Falls back to stub if ключа нет или ответ не удалось распарсить.
        """

        if not self.client:
            return {**self._fallback, "language": language}

        system_prompt = (
            "You are a nutrition analyzer. Given a meal description, estimate calories,"
            " protein_g, fat_g, carbs_g, fiber_g, sugar_g. Respond JSON with keys:"
            ' {"calories": number|null, "protein_g": number|null, "fat_g": number|null,'
            ' "carbs_g": number|null, "fiber_g": number|null, "sugar_g": number|null,'
            ' "ai_notes": string}. Use metric units. Keep ai_notes short.'
        )
        user_prompt = f"Meal description ({language or 'en'}): {text}"

        try:
            resp = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                max_tokens=200,
                temperature=0.2,
            )
            content = resp.choices[0].message.content
            parsed = json.loads(content) if content else {}
            return {
                "calories": parsed.get("calories"),
                "protein_g": parsed.get("protein_g"),
                "fat_g": parsed.get("fat_g"),
                "carbs_g": parsed.get("carbs_g"),
                "fiber_g": parsed.get("fiber_g"),
                "sugar_g": parsed.get("sugar_g"),
                "ai_notes": parsed.get("ai_notes"),
                "language": language,
            }
        except Exception as exc:  # noqa: BLE001
            logger.warning("Nutrition estimation failed, falling back to stub: %s", exc)
            return {**self._fallback, "language": language}

    async def estimate_meal_from_photo(
        self, photo_bytes: bytes | None = None, photo_metadata: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Estimate meal from photo. Если нет байт или vision недоступно — возвращаем оценку из текста метаданных.
        """

        # Если нет ключа или нет фото, падаем на текстовую заглушку.
        if not self.client or not photo_bytes:
            return {**self._fallback, "metadata": photo_metadata}

        try:
            # Используем vision-модель через base64-байты.
            import base64

            b64_image = base64.b64encode(photo_bytes).decode()
            resp = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a nutrition analyzer. Estimate macros from the meal photo."
                            " Reply JSON with keys as in text mode: calories, protein_g, fat_g,"
                            " carbs_g, fiber_g, sugar_g, ai_notes."
                        ),
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Estimate nutrition for this meal photo.",
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{b64_image}",
                                },
                            },
                        ],
                    },
                ],
                response_format={"type": "json_object"},
                max_tokens=200,
                temperature=0.2,
            )
            content = resp.choices[0].message.content
            parsed = json.loads(content) if content else {}
            return {
                "calories": parsed.get("calories"),
                "protein_g": parsed.get("protein_g"),
                "fat_g": parsed.get("fat_g"),
                "carbs_g": parsed.get("carbs_g"),
                "fiber_g": parsed.get("fiber_g"),
                "sugar_g": parsed.get("sugar_g"),
                "ai_notes": parsed.get("ai_notes"),
                "metadata": photo_metadata,
            }
        except Exception as exc:  # noqa: BLE001
            logger.warning("Vision nutrition estimation failed, falling back to stub: %s", exc)
            return {**self._fallback, "metadata": photo_metadata}
