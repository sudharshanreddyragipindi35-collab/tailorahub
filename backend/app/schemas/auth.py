from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class LoginIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    identifier: str = Field(min_length=3)
    # Password is the only interactive login method. OTP is reserved for
    # registration verification and password recovery.
    mode: Literal["password"] = "password"
    password: str | None = None
    otp: str | None = Field(default=None, min_length=4, max_length=8)


class ForgotPasswordIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    identifier: str = Field(min_length=3)
    channel: Literal["email", "sms"] | None = None


class ResetPasswordIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    identifier: str = Field(min_length=3)
    otp: str = Field(min_length=4, max_length=8)
    new_password: str = Field(min_length=8)
    confirm_password: str = Field(min_length=8)
    channel: Literal["email", "sms"] | None = None


class TokenPairOut(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"
