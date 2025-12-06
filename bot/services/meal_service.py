from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Meal
from ..services.ai_nutrition import AiNutritionService


async def log_text_meal(
    session: AsyncSession,
    user_id: int,
    meal_type: str,
    raw_text: str,
    lang: str,
    ai_service: AiNutritionService | None,
) -> tuple[Meal, dict]:
    estimates = (
        await ai_service.estimate_meal_from_text(raw_text, language=lang)
        if ai_service
        else {}
    )
    meal = Meal(
        user_id=user_id,
        meal_type=meal_type,
        raw_text=raw_text,
        language=lang,
        calories=estimates.get("calories"),
        protein_g=estimates.get("protein_g"),
        fat_g=estimates.get("fat_g"),
        carbs_g=estimates.get("carbs_g"),
        fiber_g=estimates.get("fiber_g"),
        sugar_g=estimates.get("sugar_g"),
        ai_notes=estimates.get("ai_notes"),
    )
    session.add(meal)
    await session.commit()
    await session.refresh(meal)
    return meal, estimates


async def log_photo_meal(
    session: AsyncSession,
    user_id: int,
    meal_type: str,
    lang: str,
    caption: str | None,
    photo_file_id: str,
    ai_service: AiNutritionService | None,
    photo_bytes: bytes | None,
    photo_metadata: dict | None = None,
) -> tuple[Meal, dict]:
    estimates = (
        await ai_service.estimate_meal_from_photo(photo_bytes=photo_bytes, photo_metadata=photo_metadata)
        if ai_service
        else {}
    )
    meal = Meal(
        user_id=user_id,
        meal_type=meal_type,
        is_from_photo=True,
        photo_file_id=photo_file_id,
        raw_text=caption,
        language=lang,
        calories=estimates.get("calories"),
        protein_g=estimates.get("protein_g"),
        fat_g=estimates.get("fat_g"),
        carbs_g=estimates.get("carbs_g"),
        fiber_g=estimates.get("fiber_g"),
        sugar_g=estimates.get("sugar_g"),
        ai_notes=estimates.get("ai_notes"),
    )
    session.add(meal)
    await session.commit()
    await session.refresh(meal)
    return meal, estimates
