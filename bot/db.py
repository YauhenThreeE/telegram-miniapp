from collections.abc import AsyncIterator
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


engine: Optional[AsyncEngine] = None
async_session_maker: Optional[async_sessionmaker[AsyncSession]] = None


def setup_database(database_url: str) -> None:
    global engine, async_session_maker
    engine = create_async_engine(database_url, echo=False, future=True)
    async_session_maker = async_sessionmaker(engine, expire_on_commit=False)


async def init_db() -> None:
    if engine is None:
        raise RuntimeError("Database engine is not initialized. Call setup_database first.")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncIterator[AsyncSession]:
    if async_session_maker is None:
        raise RuntimeError("Session maker is not initialized. Call setup_database first.")

    async with async_session_maker() as session:
        yield session


def get_session_maker(bot: object | None = None) -> async_sessionmaker[AsyncSession]:
    """
    Return an initialized sessionmaker. Prefer a value attached to the bot instance
    to avoid cases where the module-level async_session_maker is still None.
    """

    if bot is not None and hasattr(bot, "session_maker"):
        sm = getattr(bot, "session_maker", None)
        if sm:
            return sm

    if async_session_maker is None:
        raise RuntimeError("Session maker is not initialized. Call setup_database first.")

    return async_session_maker
