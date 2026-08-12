from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class PaymentIntentIn(BaseModel):
    booking_id: str
    method: str = Field(default="wallet")


class PaymentOut(BaseModel):
    ok: bool
    provider: str
    status: str
    txn_ref: str | None = None


class QrPaymentIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    payment_token: str = Field(min_length=10)
    amount: Decimal = Field(gt=0)
    booking_id: str | None = None
    gateway_reference: str | None = None
    method: str = "qr"


class QrPaymentOut(BaseModel):
    ok: bool
    provider: str
    status: str
    txn_ref: str | None = None
    wallet_id: str
    amount: Decimal
