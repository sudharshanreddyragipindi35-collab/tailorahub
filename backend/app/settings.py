import os
import secrets
from pathlib import Path
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")
_RUNTIME_JWT_SECRET = secrets.token_urlsafe(48)
_RUNTIME_JWT_REFRESH_SECRET = secrets.token_urlsafe(48)
_RUNTIME_ADMIN_PASSWORD = secrets.token_urlsafe(18)


def env_value(name: str, default: str = "") -> str:
    value = os.getenv(name)
    return default if value is None or value.strip() == "" else value.strip()


def env_bool(name: str, default: bool = False) -> bool:
    value = env_value(name, "true" if default else "false").lower()
    return value in {"1", "true", "yes", "on"}


def env_int(name: str, default: int) -> int:
    try:
        return int(env_value(name, str(default)))
    except ValueError:
        return default


class Settings:
    base_dir = BASE_DIR
    database_url = env_value(
        "DATABASE_URL",
        "postgresql+psycopg://tailorahub@localhost:5432/tailorahub_dev",
    )
    jwt_secret = env_value("JWT_SECRET", _RUNTIME_JWT_SECRET)
    jwt_refresh_secret = env_value("JWT_REFRESH_SECRET", _RUNTIME_JWT_REFRESH_SECRET)
    jwt_algorithm = "HS256"
    access_token_minutes = env_int("ACCESS_TOKEN_MINUTES", 1440)
    session_inactivity_minutes = env_int("SESSION_INACTIVITY_MINUTES", 15)
    cors_origins = [x.strip() for x in env_value("CORS_ORIGINS", "http://localhost:5173,https://tailorahub.com,https://www.tailorahub.com,https://api.tailorahub.com").split(",") if x.strip()]

    auto_migrate = env_bool("AUTO_MIGRATE", True)

    admin_username = env_value("ADMIN_USERNAME", "admin")
    admin_password_configured = bool(os.getenv("ADMIN_PASSWORD") and os.getenv("ADMIN_PASSWORD", "").strip())
    admin_password = env_value("ADMIN_PASSWORD", _RUNTIME_ADMIN_PASSWORD)
    admin_email = env_value("ADMIN_EMAIL", "admin@tailorahub.com")
    admin_phone = env_value("ADMIN_PHONE", "9840099999")

    sms_provider = env_value("SMS_PROVIDER", "mock").lower()
    sms_api_key = env_value("SMS_API_KEY")
    sms_api_secret = env_value("SMS_API_SECRET")
    sms_sender_id = env_value("SMS_SENDER_ID")
    sms_otp_template_id = env_value("SMS_OTP_TEMPLATE_ID")

    email_provider = env_value("EMAIL_PROVIDER", "mock").lower()
    email_api_key = env_value("EMAIL_API_KEY")
    email_from_address = env_value("EMAIL_FROM_ADDRESS", env_value("EMAIL_FROM", "TailoraHub <no-reply@tailorahub.com>"))
    email_from = email_from_address
    smtp_host = env_value("SMTP_HOST")
    smtp_port = env_int("SMTP_PORT", 587)
    smtp_secure = env_bool("SMTP_SECURE", False)
    smtp_starttls = env_bool("SMTP_STARTTLS", True)
    smtp_user = env_value("SMTP_USER")
    smtp_pass = env_value("SMTP_PASS")
    email_outbox = env_value("EMAIL_OUTBOX", str(BASE_DIR / "email-outbox.log"))

    aadhaar_kyc_provider = env_value("AADHAAR_KYC_PROVIDER", "mock").lower()
    aadhaar_kyc_api_key = env_value("AADHAAR_KYC_API_KEY")
    aadhaar_kyc_api_secret = env_value("AADHAAR_KYC_API_SECRET")
    aadhaar_kyc_base_url = env_value("AADHAAR_KYC_BASE_URL")
    aadhaar_encryption_key = env_value("AADHAAR_ENCRYPTION_KEY")

    payment_provider = env_value("PAYMENT_PROVIDER", "mock").lower()
    payment_api_key = env_value("PAYMENT_API_KEY")
    payment_api_secret = env_value("PAYMENT_API_SECRET")
    payment_webhook_secret = env_value("PAYMENT_WEBHOOK_SECRET")
    razorpay_key_id = env_value("RAZORPAY_KEY_ID", payment_api_key)
    razorpay_key_secret = env_value("RAZORPAY_KEY_SECRET", payment_api_secret)
    razorpay_webhook_secret = env_value("RAZORPAY_WEBHOOK_SECRET", payment_webhook_secret)
    payout_api_key = env_value("PAYOUT_API_KEY")
    payout_api_secret = env_value("PAYOUT_API_SECRET")
    admin_payment_upi_id = env_value("ADMIN_PAYMENT_UPI_ID")
    admin_payment_qr_url = env_value("ADMIN_PAYMENT_QR_URL")
    manual_payment_expiry_minutes = env_int("MANUAL_PAYMENT_EXPIRY_MINUTES", 5)

    maps_provider = env_value("MAPS_PROVIDER", "mock").lower()
    maps_api_key = env_value("MAPS_API_KEY")


settings = Settings()
