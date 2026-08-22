from __future__ import annotations

import secrets
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[2]


class AppSettings(BaseSettings):
    """Typed settings for the async `/api/v1` scaffold.

    Empty values in `.env` are intentionally allowed; integrations choose
    mock mode when provider keys are not configured.
    """

    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", env_ignore_empty=True, extra="ignore")

    database_url: str = Field(default="postgresql+psycopg://tailorahub@localhost:5432/tailorahub_dev", alias="DATABASE_URL")
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    jwt_secret: str = Field(default_factory=lambda: secrets.token_urlsafe(48), alias="JWT_SECRET")
    jwt_refresh_secret: str = Field(default_factory=lambda: secrets.token_urlsafe(48), alias="JWT_REFRESH_SECRET")
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = Field(default=1440, alias="ACCESS_TOKEN_MINUTES")
    cors_origins: str = Field(default="http://localhost:5173", alias="CORS_ORIGINS")

    sms_provider: str = Field(default="mock", alias="SMS_PROVIDER")
    email_provider: str = Field(default="mock", alias="EMAIL_PROVIDER")
    aadhaar_kyc_provider: str = Field(default="mock", alias="AADHAAR_KYC_PROVIDER")
    payment_provider: str = Field(default="mock", alias="PAYMENT_PROVIDER")
    maps_provider: str = Field(default="mock", alias="MAPS_PROVIDER")

    payment_webhook_secret: str = Field(default="", alias="PAYMENT_WEBHOOK_SECRET")
    admin_whatsapp_number: str = Field(default="918790901281", alias="ADMIN_WHATSAPP_NUMBER")
    admin_payment_upi_id: str = Field(default="", alias="ADMIN_PAYMENT_UPI_ID")
    admin_payment_qr_url: str = Field(default="", alias="ADMIN_PAYMENT_QR_URL")
    manual_payment_expiry_minutes: int = Field(default=5, alias="MANUAL_PAYMENT_EXPIRY_MINUTES")

    @property
    def async_database_url(self) -> str:
        if self.database_url.startswith("postgresql+asyncpg://"):
            return self.database_url
        if self.database_url.startswith("postgresql+psycopg://"):
            return self.database_url.replace("postgresql+psycopg://", "postgresql+asyncpg://", 1)
        if self.database_url.startswith("postgresql://"):
            return self.database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return self.database_url

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> AppSettings:
    return AppSettings()
