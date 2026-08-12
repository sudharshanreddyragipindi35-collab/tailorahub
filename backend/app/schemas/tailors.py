from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from .common import OrmModel


PHONE_PATTERN = r"^[6-9]\d{9}$"


class TailorRegisterIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    full_name: str = Field(min_length=2, max_length=160)
    phone_number: str = Field(pattern=PHONE_PATTERN)
    email: EmailStr
    dob: date
    aadhaar_number: str = Field(min_length=12, max_length=12)
    username: str = Field(min_length=4, max_length=80)
    password: str = Field(min_length=8)
    confirm_password: str | None = Field(default=None, min_length=8)
    experience_years_base: Decimal = Field(default=Decimal("0"), ge=0)
    stitching_since_date: date
    terms_accepted: bool
    referral_code: str | None = Field(default=None, max_length=40)
    shop_name: str | None = Field(default=None, max_length=160)
    zone_id: str | None = Field(default="tnagar", max_length=80)
    address_text: str | None = None
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    bio: str | None = None
    expertise: list[str] = Field(default_factory=list)
    services: list["TailorRegisterServiceIn"] = Field(default_factory=list)


class TailorRegisterServiceIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=2, max_length=160)
    garment_id: str | None = Field(default=None, max_length=80)
    description: str | None = None
    price: int = Field(gt=0)
    days: int = Field(default=5, gt=0)


class TailorAvailabilityCheckIn(BaseModel):
    field: str
    value: str = Field(min_length=1)


class TailorAadhaarVerifyIn(BaseModel):
    full_name: str | None = Field(default=None, max_length=160)
    dob: date | None = None
    aadhaar_number: str = Field(min_length=12, max_length=12)


class TailorLocationIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    address_text: str = Field(min_length=5)
    latitude: Decimal = Field(ge=Decimal("-90"), le=Decimal("90"))
    longitude: Decimal = Field(ge=Decimal("-180"), le=Decimal("180"))
    confirmed: bool = True


class TailorRegisterOut(BaseModel):
    token: str
    access_token: str
    role: str = "tailor"
    tailor_id: UUID
    wallet_id: UUID
    qr_code_url: str | None = None
    tailor_pending: bool = True


class TailorPublic(OrmModel):
    tailor_id: UUID
    full_name: str | None = None
    phone_number: str | None = None
    email: EmailStr | None = None
    bio: str | None = None
    experience_years_base: Decimal | None = None
    stitching_since_date: date | None = None
    experience_display: Decimal | None = None
    referral_code: str | None = None
    is_available: bool | None = None
    status: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class TailorProfileOut(TailorPublic):
    aadhaar_verified: bool = False
