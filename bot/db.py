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
