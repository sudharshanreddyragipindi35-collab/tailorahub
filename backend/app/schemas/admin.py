from decimal import Decimal

from pydantic import BaseModel, Field


class PlatformSettingsIn(BaseModel):
    commission_percentage: Decimal = Field(ge=0)
    gst_percentage: Decimal = Field(ge=0)
    platform_fee_percentage: Decimal = Field(ge=0)


class PlatformSettingsOut(PlatformSettingsIn):
    id: int = 1
