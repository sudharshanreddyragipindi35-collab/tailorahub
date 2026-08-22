from __future__ import annotations

from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from .common import OrmModel


class WalletOut(OrmModel):
    wallet_id: UUID
    balance: Decimal
    ledger_balance: Decimal | None = None
    available_balance: Decimal | None = None
    pending_withdrawal_amount: Decimal | None = None
    upi_id: str | None = None
    qr_code_url: str | None = None
    bank_account_configured: bool = False


class SetUpiIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    upi_id: str = Field(min_length=3, max_length=160)


class WithdrawOtpOut(BaseModel):
    sent: bool
    target: str
    channel: str
    expires_in_seconds: int
    dev_otp: str | None = None


class WithdrawIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    amount: Decimal = Field(gt=0)
    destination_type: Literal["bank_account", "upi_id"]
    otp: str = Field(min_length=4, max_length=8)
    bank_account_number: str | None = Field(default=None, min_length=6, max_length=32)
    bank_ifsc: str | None = Field(default=None, min_length=5, max_length=20)


class WithdrawOut(BaseModel):
    ok: bool
    status: str
    txn_ref: str | None = None
    balance: Decimal
    ledger_balance: Decimal | None = None
    available_balance: Decimal | None = None
    pending_withdrawal_amount: Decimal | None = None
