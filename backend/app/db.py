from pathlib import Path
import logging
import time

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker

from .settings import settings


logger = logging.getLogger(__name__)


def _engine_options() -> dict:
    options = {"pool_pre_ping": True, "future": True}
    if not settings.database_url.startswith("sqlite"):
        options.update(
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
            pool_timeout=settings.database_pool_timeout_seconds,
            pool_recycle=settings.database_pool_recycle_seconds,
        )
    if settings.database_url.startswith(("postgresql+psycopg://", "postgresql://")):
        options["connect_args"] = {
            "options": f"-c statement_timeout={settings.database_statement_timeout_ms}"
        }
    return options


engine = create_engine(settings.database_url, **_engine_options())
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


@event.listens_for(engine, "before_cursor_execute")
def _query_started(conn, cursor, statement, parameters, context, executemany):
    conn.info.setdefault("query_started_at", []).append(time.perf_counter())


@event.listens_for(engine, "after_cursor_execute")
def _query_finished(conn, cursor, statement, parameters, context, executemany):
    started = conn.info.get("query_started_at", []).pop(-1)
    elapsed_ms = (time.perf_counter() - started) * 1000
    if elapsed_ms >= settings.database_slow_query_ms:
        logger.warning("slow_database_query elapsed_ms=%.1f operation=%s", elapsed_ms, statement.lstrip().split(None, 1)[0].upper())


def run_schema() -> None:
    schema = Path(__file__).with_name("schema.sql").read_text(encoding="utf-8")
    with engine.begin() as conn:
        conn.exec_driver_sql(schema)


def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def row_to_dict(row):
    return dict(row._mapping) if row is not None else None


def fetch_one(db, sql: str, params: dict | None = None):
    return row_to_dict(db.execute(text(sql), params or {}).first())


def fetch_all(db, sql: str, params: dict | None = None):
    return [row_to_dict(r) for r in db.execute(text(sql), params or {}).all()]
