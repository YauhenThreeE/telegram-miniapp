from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy import desc, select

from ..db import get_session_maker
from ..i18n import SUPPORTED_LANGUAGES, t
from ..keyboards import main_menu
from ..models import Recipe, User
from ..services.ai_dietitian import AiDietitianService

router = Router()


class RecipeCreate(StatesGroup):
    waiting_title = State()
    waiting_body = State()


class RecipeEdit(StatesGroup):
    waiting_title = State()
    waiting_body = State()


async def _load_user(bot: object, telegram_id: int) -> tuple[User | None, str]:
    session_maker = get_session_maker(bot)
    async with session_maker() as session:
        user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
    lang = user.language if user else "en"
    return user, lang


def _short_title(title: str) -> str:
    return title if len(title) <= 40 else f"{title[:37]}..."


def _recipes_keyboard(recipes: list[Recipe], lang: str) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=_short_title(recipe.title), callback_data=f"recipes_view:{recipe.id}")]
        for recipe in recipes
    ]
    rows.append([InlineKeyboardButton(text=t(lang, "recipes_add_button"), callback_data="recipes_add")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _body_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "recipes_ai_button"), callback_data="recipes_ai_generate")],
            [InlineKeyboardButton(text=t(lang, "recipes_back_button"), callback_data="recipes_back")],
        ]
    )


async def _send_recipes_home(message: Message, bot: object, user: User, lang: str) -> None:
    session_maker = get_session_maker(bot)
    async with session_maker() as session:
        result = await session.scalars(
            select(Recipe)
            .where(Recipe.user_id == user.id)
            .order_by(desc(Recipe.created_at))
            .limit(10)
        )
        recipes = list(result)

    if recipes:
        text = "\n".join(
            [
                t(lang, "recipes_header", count=len(recipes)),
                t(lang, "recipes_hint"),
            ]
        )
    else:
        text = t(lang, "recipes_empty")

    await message.answer(text, reply_markup=_recipes_keyboard(recipes, lang))


@router.message(Command("recipes"))
@router.message(F.text.in_({t(lang, "btn_recipes") for lang in SUPPORTED_LANGUAGES}))
async def recipes_menu(message: Message, state: FSMContext) -> None:
    user, lang = await _load_user(message.bot, message.from_user.id)
    if not user:
        await message.answer(t(lang, "profile_missing"))
        return

    await state.clear()
    await state.update_data(language=lang, user_id=user.id)
    await _send_recipes_home(message, message.bot, user, lang)


@router.callback_query(F.data == "recipes_add")
async def recipes_add(callback: CallbackQuery, state: FSMContext) -> None:
    user, lang = await _load_user(callback.bot, callback.from_user.id)
    if not user:
        await callback.message.answer(t(lang, "profile_missing"))
        await callback.answer()
        return

    await state.set_state(RecipeCreate.waiting_title)
    await state.update_data(language=lang, user_id=user.id)
    await callback.message.answer(t(lang, "recipes_prompt_title"))
    await callback.answer()


@router.callback_query(F.data == "recipes_back")
async def recipes_back(callback: CallbackQuery, state: FSMContext) -> None:
    user, lang = await _load_user(callback.bot, callback.from_user.id)
    if not user:
        await callback.message.answer(t(lang, "profile_missing"))
        await callback.answer()
        return

    await state.clear()
    await state.update_data(language=lang, user_id=user.id)
    await _send_recipes_home(callback.message, callback.bot, user, lang)
    await callback.answer()


@router.callback_query(F.data.startswith("recipes_view:"))
async def recipes_view(callback: CallbackQuery, state: FSMContext) -> None:
    _, recipe_id_str = callback.data.split(":", 1)
    try:
        recipe_id = int(recipe_id_str)
    except ValueError:
        await callback.answer()
        return

    user, lang = await _load_user(callback.bot, callback.from_user.id)
    if not user:
        await callback.message.answer(t(lang, "profile_missing"))
        await callback.answer()
        return

    session_maker = get_session_maker(callback.bot)
    async with session_maker() as session:
        recipe = await session.scalar(
            select(Recipe).where(Recipe.id == recipe_id, Recipe.user_id == user.id)
        )
    if not recipe:
        await callback.answer(t(lang, "recipes_not_found"), show_alert=True)
        return

    await state.update_data(language=lang, user_id=user.id, recipe_id=recipe.id, recipe_title=recipe.title)
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=t(lang, "recipes_edit_title_button"),
                    callback_data=f"recipes_edit_title:{recipe.id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text=t(lang, "recipes_edit_body_button"),
                    callback_data=f"recipes_edit_body:{recipe.id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text=t(lang, "recipes_delete_button"),
                    callback_data=f"recipes_delete:{recipe.id}",
                )
            ],
            [InlineKeyboardButton(text=t(lang, "recipes_back_button"), callback_data="recipes_back")],
        ]
    )
    await callback.message.answer(f"{recipe.title}\n\n{recipe.body}", reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("recipes_delete:"))
async def recipes_delete(callback: CallbackQuery, state: FSMContext) -> None:
    _, recipe_id_str = callback.data.split(":", 1)
    try:
        recipe_id = int(recipe_id_str)
    except ValueError:
        await callback.answer()
        return

    user, lang = await _load_user(callback.bot, callback.from_user.id)
    if not user:
        await callback.message.answer(t(lang, "profile_missing"))
        await callback.answer()
        return

    session_maker = get_session_maker(callback.bot)
    async with session_maker() as session:
        await session.execute(
            Recipe.__table__.delete().where(Recipe.id == recipe_id, Recipe.user_id == user.id)
        )
        await session.commit()

    await callback.message.answer(t(lang, "recipes_deleted"))
    await state.update_data(language=lang, user_id=user.id)
    await _send_recipes_home(callback.message, callback.bot, user, lang)
    await callback.answer()


@router.callback_query(F.data.startswith("recipes_edit_title:"))
async def recipes_edit_title(callback: CallbackQuery, state: FSMContext) -> None:
    _, recipe_id_str = callback.data.split(":", 1)
    try:
        recipe_id = int(recipe_id_str)
    except ValueError:
        await callback.answer()
        return

    user, lang = await _load_user(callback.bot, callback.from_user.id)
    if not user:
        await callback.message.answer(t(lang, "profile_missing"))
        await callback.answer()
        return

    await state.set_state(RecipeEdit.waiting_title)
    await state.update_data(language=lang, user_id=user.id, recipe_id=recipe_id)
    await callback.message.answer(t(lang, "recipes_prompt_title"))
    await callback.answer()


@router.callback_query(F.data.startswith("recipes_edit_body:"))
async def recipes_edit_body(callback: CallbackQuery, state: FSMContext) -> None:
    _, recipe_id_str = callback.data.split(":", 1)
    try:
        recipe_id = int(recipe_id_str)
    except ValueError:
        await callback.answer()
        return

    user, lang = await _load_user(callback.bot, callback.from_user.id)
    if not user:
        await callback.message.answer(t(lang, "profile_missing"))
        await callback.answer()
        return

    await state.set_state(RecipeEdit.waiting_body)
    await state.update_data(language=lang, user_id=user.id, recipe_id=recipe_id)
    await callback.message.answer(t(lang, "recipes_prompt_body"), reply_markup=_body_keyboard(lang))
    await callback.answer()


@router.message(RecipeCreate.waiting_title)
async def recipe_title_received(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("language", "en")

    title = (message.text or "").strip()
    if not title:
        await message.answer(t(lang, "recipes_prompt_title"))
        return

    await state.update_data(recipe_title=title[:255])
    await state.set_state(RecipeCreate.waiting_body)
    await message.answer(t(lang, "recipes_prompt_body"), reply_markup=_body_keyboard(lang))


@router.message(RecipeCreate.waiting_body)
async def recipe_body_received(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("language", "en")
    user_id = data.get("user_id")
    title = data.get("recipe_title")

    user, lang_from_user = await _load_user(message.bot, message.from_user.id)
    lang = lang_from_user or lang
    user_id = user_id or (user.id if user else None)

    body = (message.text or "").strip()
    if not body:
        await message.answer(t(lang, "recipes_prompt_body"), reply_markup=_body_keyboard(lang))
        return
    if not user_id or not title:
        await message.answer(t(lang, "profile_missing"))
        await state.clear()
        return

    session_maker = get_session_maker(message.bot)
    async with session_maker() as session:
        session.add(Recipe(user_id=user_id, title=title[:255], body=body))
        await session.commit()

    await message.answer(t(lang, "recipes_saved"), reply_markup=main_menu(lang))
    await state.clear()


@router.message(RecipeEdit.waiting_title)
async def recipe_title_update(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("language", "en")
    recipe_id = data.get("recipe_id")

    title = (message.text or "").strip()
    if not title or not recipe_id:
        await message.answer(t(lang, "recipes_prompt_title"))
        return

    user, lang_from_user = await _load_user(message.bot, message.from_user.id)
    lang = lang_from_user or lang
    if not user:
        await message.answer(t(lang, "profile_missing"))
        await state.clear()
        return

    session_maker = get_session_maker(message.bot)
    async with session_maker() as session:
        await session.execute(
            Recipe.__table__.update()
            .where(Recipe.id == recipe_id, Recipe.user_id == user.id)
            .values(title=title[:255])
        )
        await session.commit()

    await message.answer(t(lang, "recipes_updated"), reply_markup=main_menu(lang))
    await state.clear()


@router.message(RecipeEdit.waiting_body)
async def recipe_body_update(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    lang = data.get("language", "en")
    recipe_id = data.get("recipe_id")

    body = (message.text or "").strip()
    if not body or not recipe_id:
        await message.answer(t(lang, "recipes_prompt_body"), reply_markup=_body_keyboard(lang))
        return

    user, lang_from_user = await _load_user(message.bot, message.from_user.id)
    lang = lang_from_user or lang
    if not user:
        await message.answer(t(lang, "profile_missing"))
        await state.clear()
        return

    session_maker = get_session_maker(message.bot)
    async with session_maker() as session:
        await session.execute(
            Recipe.__table__.update()
            .where(Recipe.id == recipe_id, Recipe.user_id == user.id)
            .values(body=body)
        )
        await session.commit()

    await message.answer(t(lang, "recipes_updated"), reply_markup=main_menu(lang))
    await state.clear()


@router.callback_query(F.data == "recipes_ai_generate")
async def recipes_ai_generate(callback: CallbackQuery, state: FSMContext) -> None:
    current_state = await state.get_state()
    if current_state not in {RecipeCreate.waiting_body.state, RecipeEdit.waiting_body.state}:
        await callback.answer()
        return

    data = await state.get_data()
    lang = data.get("language", "en")
    title = data.get("recipe_title")

    if current_state == RecipeEdit.waiting_body.state and not title:
        recipe_id = data.get("recipe_id")
        user, _ = await _load_user(callback.bot, callback.from_user.id)
        if user and recipe_id:
            session_maker = get_session_maker(callback.bot)
            async with session_maker() as session:
                title = await session.scalar(
                    select(Recipe.title).where(Recipe.id == recipe_id, Recipe.user_id == user.id)
                )

    if not title:
        await callback.answer(t(lang, "recipes_prompt_title"), show_alert=True)
        return

    await callback.message.answer(t(lang, "recipes_ai_working"))
    ai_service: AiDietitianService | None = getattr(callback.bot, "ai_dietitian_service", None)
    recipe_text = None
    if ai_service:
        recipe_text = await ai_service.suggest_recipe(title, lang)

    if not recipe_text:
        await callback.message.answer(t(lang, "recipes_ai_failed"))
        await callback.answer()
        return

    await state.update_data(ai_body=recipe_text)
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "recipes_ai_use_button"), callback_data="recipes_use_ai")],
            [InlineKeyboardButton(text=t(lang, "recipes_back_button"), callback_data="recipes_back")],
        ]
    )
    await callback.message.answer(
        "\n".join([t(lang, "recipes_ai_ready"), "", recipe_text]),
        reply_markup=keyboard,
    )
    await callback.answer()


@router.callback_query(F.data == "recipes_use_ai")
async def recipes_use_ai(callback: CallbackQuery, state: FSMContext) -> None:
    current_state = await state.get_state()
    data = await state.get_data()
    lang = data.get("language", "en")
    ai_body = data.get("ai_body")
    if not ai_body:
        await callback.answer(t(lang, "recipes_ai_failed"), show_alert=True)
        return

    user, lang_from_user = await _load_user(callback.bot, callback.from_user.id)
    lang = lang_from_user or lang
    if not user:
        await callback.message.answer(t(lang, "profile_missing"))
        await state.clear()
        await callback.answer()
        return

    session_maker = get_session_maker(callback.bot)

    if current_state == RecipeCreate.waiting_body.state:
        title = data.get("recipe_title")
        if not title:
            await callback.answer(t(lang, "recipes_prompt_title"), show_alert=True)
            return
        async with session_maker() as session:
            session.add(Recipe(user_id=user.id, title=title[:255], body=ai_body))
            await session.commit()
        await callback.message.answer(t(lang, "recipes_saved"), reply_markup=main_menu(lang))
        await state.clear()
        await callback.answer()
        return

    if current_state == RecipeEdit.waiting_body.state:
        recipe_id = data.get("recipe_id")
        if not recipe_id:
            await callback.answer(t(lang, "recipes_not_found"), show_alert=True)
            return
        async with session_maker() as session:
            await session.execute(
                Recipe.__table__.update()
                .where(Recipe.id == recipe_id, Recipe.user_id == user.id)
                .values(body=ai_body)
            )
            await session.commit()
        await callback.message.answer(t(lang, "recipes_updated"), reply_markup=main_menu(lang))
        await state.clear()
        await callback.answer()
        return

    await callback.answer()
