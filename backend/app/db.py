from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from .settings import settings


engine = create_engine(settings.database_url, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


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
