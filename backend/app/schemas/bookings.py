from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel

from .common import OrmModel


class BookingCreateIn(BaseModel):
    tailor_id: UUID | None = None
    measurement_mode: str
    customer_location_address: str | None = None
    customer_location_lat: Decimal | None = None
    customer_location_lng: Decimal | None = None


class BookingTrackerOut(OrmModel):
    booking_id: UUID
    status: str
    tracker_stage: str
    payment_status: str
    delivery_otp_verified: bool = False
    updated_at: datetime | None = None
