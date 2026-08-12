from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class OrmModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class MessageOut(BaseModel):
    ok: bool = True
    message: str


class TimestampedOut(OrmModel):
    created_at: datetime | None = None
    updated_at: datetime | None = None
