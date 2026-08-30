from __future__ import annotations

from collections.abc import AsyncGenerator
import logging
import time

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from .config import get_settings


settings = get_settings()
logger = logging.getLogger(__name__)


def _engine_options() -> dict:
    options = {"pool_pre_ping": True}
    if not settings.async_database_url.startswith("sqlite"):
        options.update(
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
            pool_timeout=settings.database_pool_timeout_seconds,
            pool_recycle=settings.database_pool_recycle_seconds,
        )
    if settings.async_database_url.startswith("postgresql+asyncpg://"):
        options["connect_args"] = {
            "server_settings": {"statement_timeout": str(settings.database_statement_timeout_ms)}
        }
    return options


async_engine = create_async_engine(settings.async_database_url, **_engine_options())
AsyncSessionLocal = async_sessionmaker(async_engine, expire_on_commit=False, autoflush=False)


@event.listens_for(async_engine.sync_engine, "before_cursor_execute")
def _query_started(conn, cursor, statement, parameters, context, executemany):
    conn.info.setdefault("query_started_at", []).append(time.perf_counter())


@event.listens_for(async_engine.sync_engine, "after_cursor_execute")
def _query_finished(conn, cursor, statement, parameters, context, executemany):
    started = conn.info.get("query_started_at", []).pop(-1)
    elapsed_ms = (time.perf_counter() - started) * 1000
    if elapsed_ms >= settings.database_slow_query_ms:
        logger.warning("slow_database_query elapsed_ms=%.1f operation=%s", elapsed_ms, statement.lstrip().split(None, 1)[0].upper())


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


async def dispose_engine() -> None:
    await async_engine.dispose()
