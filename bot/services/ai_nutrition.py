from __future__ import annotations

from typing import Any


class AiNutritionService:
    """Stub service that will later call a real LLM or food database."""

    def __init__(self, openai_api_key: str | None) -> None:
        self.openai_api_key = openai_api_key

    async def estimate_meal_from_text(self, text: str, language: str | None = None) -> dict[str, Any]:
        """
        Return mocked nutrition estimates for the provided text.

        TODO: Replace this stub with a real integration to an LLM or food database API
        (e.g., OpenAI, Azure, or a dedicated nutrition API). Use self.openai_api_key
        for authentication when wiring the real service.
        """

        return {
            "calories": 500.0,
            "protein_g": 20.0,
            "fat_g": 15.0,
            "carbs_g": 60.0,
            "fiber_g": 5.0,
            "sugar_g": 10.0,
            "ai_notes": "Approximate values based on user description.",
            "language": language,
        }
