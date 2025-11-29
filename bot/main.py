import asyncio
import logging

from aiogram import Bot, Dispatcher

from . import models  # noqa: F401
from .config import load_config
from .db import init_db, setup_database
from .handlers import ask, food, photo_meal, profile, start, stats, water, weight
from .services import build_ai_dietitian_service, build_ai_nutrition_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main() -> None:
    config = load_config()
    setup_database(config.database_url)
    await init_db()

    ai_service = build_ai_nutrition_service(config)
    ai_dietitian_service = build_ai_dietitian_service(config)

    bot = Bot(token=config.telegram_bot_token, parse_mode="HTML")
    bot["ai_service"] = ai_service
    bot["ai_dietitian_service"] = ai_dietitian_service
    dp = Dispatcher()

    dp.include_router(start.router)
    dp.include_router(food.router)
    dp.include_router(photo_meal.router)
    dp.include_router(water.router)
    dp.include_router(weight.router)
    dp.include_router(stats.router)
    dp.include_router(ask.router)
    dp.include_router(profile.router)

    logger.info("Bot started")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
