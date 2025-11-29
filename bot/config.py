from dataclasses import dataclass
import os

from dotenv import load_dotenv


@dataclass
class Settings:
    telegram_bot_token: str
    database_url: str
    openai_api_key: str | None = None


def load_config() -> Settings:
    load_dotenv()
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN is not set in the environment")

    database_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///bot.db")
    openai_api_key = os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY")

    return Settings(
        telegram_bot_token=token,
        database_url=database_url,
        openai_api_key=openai_api_key,
    )
