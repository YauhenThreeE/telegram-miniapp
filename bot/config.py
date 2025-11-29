from dataclasses import dataclass
import os

from dotenv import load_dotenv


@dataclass
class Settings:
    telegram_bot_token: str
    database_url: str


def load_config() -> Settings:
    load_dotenv()
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN is not set in the environment")

    database_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///bot.db")

    return Settings(telegram_bot_token=token, database_url=database_url)
