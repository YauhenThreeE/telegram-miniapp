import asyncio
import logging

from aiogram import Bot, Dispatcher

from . import models  # noqa: F401
from .config import load_config
from .db import init_db, setup_database
from .handlers import profile, start

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main() -> None:
    config = load_config()
    setup_database(config.database_url)
    await init_db()

    bot = Bot(token=config.telegram_bot_token, parse_mode="HTML")
    dp = Dispatcher()

    dp.include_router(start.router)
    dp.include_router(profile.router)

    logger.info("Bot started")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
