# AI Dietitian Telegram Bot (Skeleton)

This is a minimal, production-ready skeleton for an AI dietitian Telegram bot built with Python 3.11+, Aiogram v3, and SQLite via SQLAlchemy.

## Features in this step
- Environment configuration via `.env` using `python-dotenv`.
- Async SQLite database with SQLAlchemy and `User` / `Meal` models.
- Basic internationalization (English, Russian, Polish).
- Onboarding questionnaire to collect a health profile.
- `/profile` command to view and edit key profile fields.
- Meal logging with a stubbed AI nutrition estimator and daily `/stats` summary.
- Long polling runner (no webhooks yet).

## Setup
1. Create and activate a Python 3.11+ virtual environment.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and set `TELEGRAM_BOT_TOKEN` (and optionally `DATABASE_URL` and `OPENAI_API_KEY`).

## Running the bot
```bash
python -m bot.main
```

The bot uses long polling. Ensure the bot token is valid and reachable from your environment.

## Project structure
- `bot/main.py` — entry point, dispatcher, polling.
- `bot/config.py` — loads `.env` configuration.
- `bot/db.py` — async engine, session, and DB initialization.
- `bot/models.py` — SQLAlchemy models (`User`, `Meal`).
- `bot/i18n.py` — translations and helper `t()`.
- `bot/keyboards.py` — inline/reply keyboards.
- `bot/handlers/start.py` — `/start`, language selection, onboarding.
- `bot/handlers/profile.py` — `/profile` view and edits.
- `bot/handlers/food.py` — meal logging flow.
- `bot/handlers/stats.py` — daily statistics summary.
- `bot/services/ai_nutrition.py` — stubbed nutrition estimator service.

## Notes
- Unimplemented menu buttons reply with a stub message.
- Database defaults to `sqlite+aiosqlite:///bot.db` if `DATABASE_URL` is not set.
