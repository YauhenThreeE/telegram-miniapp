from __future__ import annotations

from ..config import Settings
from .ai_nutrition import AiNutritionService


def build_ai_nutrition_service(settings: Settings) -> AiNutritionService:
    """Factory for the AI nutrition estimator service."""

    return AiNutritionService(openai_api_key=getattr(settings, "openai_api_key", None))
