from __future__ import annotations

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Recipe


async def list_recipes(session: AsyncSession, user_id: int, limit: int = 10) -> list[Recipe]:
    result = await session.scalars(
        select(Recipe)
        .where(Recipe.user_id == user_id)
        .order_by(desc(Recipe.created_at))
        .limit(limit)
    )
    return list(result)


async def get_recipe(session: AsyncSession, user_id: int, recipe_id: int) -> Recipe | None:
    return await session.scalar(
        select(Recipe).where(Recipe.id == recipe_id, Recipe.user_id == user_id)
    )


async def create_recipe(session: AsyncSession, user_id: int, title: str, body: str) -> Recipe:
    recipe = Recipe(user_id=user_id, title=title, body=body)
    session.add(recipe)
    await session.commit()
    await session.refresh(recipe)
    return recipe


async def update_recipe_title(session: AsyncSession, user_id: int, recipe_id: int, title: str) -> None:
    await session.execute(
        Recipe.__table__.update()
        .where(Recipe.id == recipe_id, Recipe.user_id == user_id)
        .values(title=title)
    )
    await session.commit()


async def update_recipe_body(session: AsyncSession, user_id: int, recipe_id: int, body: str) -> None:
    await session.execute(
        Recipe.__table__.update()
        .where(Recipe.id == recipe_id, Recipe.user_id == user_id)
        .values(body=body)
    )
    await session.commit()


async def delete_recipe(session: AsyncSession, user_id: int, recipe_id: int) -> None:
    await session.execute(
        Recipe.__table__.delete().where(Recipe.id == recipe_id, Recipe.user_id == user_id)
    )
    await session.commit()
