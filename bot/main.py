import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.types import BotCommand

from . import models  # noqa: F401
from .config import load_config
from .db import init_db, setup_database
from .handlers import (
    ask,
    delete_me,
    food,
    help as help_handler,
    misc,
    photo_meal,
    profile,
    recipes,
    start,
    stats,
    water,
    weight,
)
from .services import build_ai_dietitian_service, build_ai_nutrition_service, build_document_parser

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    config = load_config()
    setup_database(config.database_url)
    await init_db()

    ai_service = build_ai_nutrition_service(config)
    ai_dietitian_service = build_ai_dietitian_service(config)
    document_parser = build_document_parser(config)

    bot = Bot(
        token=config.telegram_bot_token,
        default=DefaultBotProperties(parse_mode="HTML"),
    )
    # Attach services as attributes for access inside handlers.
    bot.ai_service = ai_service
    bot.ai_dietitian_service = ai_dietitian_service
    bot.document_parser = document_parser
    # Expose session maker so handlers can safely access DB even if the module-level
    # reference is still None in some contexts.
    from .db import async_session_maker  # local import to avoid circular issues

    bot.session_maker = async_session_maker

    dp = Dispatcher()

    dp.include_router(start.router)
    dp.include_router(food.router)
    dp.include_router(photo_meal.router)
    dp.include_router(water.router)
    dp.include_router(weight.router)
    dp.include_router(stats.router)
    dp.include_router(ask.router)
    dp.include_router(recipes.router)
    dp.include_router(profile.router)
    dp.include_router(help_handler.router)
    dp.include_router(delete_me.router)
    dp.include_router(misc.router)

    # Show slash-command suggestions in the Telegram client.
    await bot.set_my_commands(
        [
            BotCommand(command="start", description="Start onboarding"),
            BotCommand(command="profile", description="Show or edit profile"),
            BotCommand(command="stats", description="Today stats"),
            BotCommand(command="water", description="Add water"),
            BotCommand(command="weight", description="Log weight"),
            BotCommand(command="meal", description="Log meal"),
            BotCommand(command="recipes", description="My recipes"),
            BotCommand(command="ask", description="Ask dietitian"),
            BotCommand(command="reset_stats", description="Reset today"),
            BotCommand(command="reset_all", description="Reset all data"),
            BotCommand(command="delete_me", description="Delete account"),
        ]
    )

    logger.info("Bot started")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
