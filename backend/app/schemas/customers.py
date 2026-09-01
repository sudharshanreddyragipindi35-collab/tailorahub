from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from .common import OrmModel
from .tailors import PHONE_PATTERN


class CustomerRegisterIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    full_name: str = Field(min_length=2, max_length=160)
    phone_number: str = Field(pattern=PHONE_PATTERN)
    email: EmailStr
    password: str = Field(min_length=8)
    confirm_password: str | None = Field(default=None, min_length=8)
    referral_code: str | None = Field(default=None, max_length=40)
    terms_accepted: bool


class CustomerAvailabilityCheckIn(BaseModel):
    field: str
    value: str = Field(min_length=1)


class CustomerPublic(OrmModel):
    customer_id: UUID
    full_name: str
    phone_number: str
    email: EmailStr | None = None
    referral_code: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
