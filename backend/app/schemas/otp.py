from pydantic import BaseModel, Field


class OtpSendIn(BaseModel):
    target: str = Field(min_length=3)
    purpose: str


class OtpVerifyIn(BaseModel):
    target: str = Field(min_length=3)
    purpose: str
    otp: str = Field(min_length=4, max_length=8)


class OtpSendOut(BaseModel):
    sent: bool
    expires_at: str | None = None
    dev_otp: str | None = None
    expires_in_seconds: int | None = None


class OtpVerifyOut(BaseModel):
    verified: bool
    target: str
    purpose: str
