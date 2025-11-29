# Bot commands and features

- `/start` — onboarding or reset profile
- `/profile` — show/edit profile
- `/stats` — today’s stats (meals, water, last weight)
- `/water` — add water intake
- `/weight` — log weight
- `/ask` — ask the AI dietitian
- `/reset_stats` — clear today’s meals and water
- `/reset_all` — delete all meals, water, and weight logs
- `/delete_me` — delete all data (profile, logs, chat history)

Notes:
- AI features use OpenAI (model `gpt-4o-mini` by default); set `OPENAI_API_KEY` in `.env`.
- Run the bot from project root: `python -m bot.main` (with venv activated).
