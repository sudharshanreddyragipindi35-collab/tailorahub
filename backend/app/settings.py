import os
import secrets
import json
from pathlib import Path
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _load_runtime_secret() -> None:
    """Load application settings from Secrets Manager when explicitly enabled.

    The EC2 instance role supplies temporary credentials. Values are placed in
    the process environment before Settings is evaluated; they are never
    written to disk or printed.
    """
    secret_id = os.getenv("AWS_SECRETS_MANAGER_SECRET_ID", "").strip()
    if not secret_id:
        return
    try:
        import boto3

        region = os.getenv("AWS_SECRETS_MANAGER_REGION") or os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION")
        client = boto3.client("secretsmanager", region_name=region) if region else boto3.client("secretsmanager")
        response = client.get_secret_value(SecretId=secret_id)
        payload = json.loads(response.get("SecretString") or "{}")
        if not isinstance(payload, dict):
            raise ValueError("secret must contain a JSON object")
        for key, value in payload.items():
            if isinstance(key, str) and value is not None:
                os.environ[key] = str(value)
    except Exception as exc:
        raise RuntimeError("AWS_SECRETS_MANAGER_SECRET_ID is configured but the application secret could not be loaded") from exc


_load_runtime_secret()
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
    app_env = env_value("APP_ENV", "development").lower()
    log_level = env_value("LOG_LEVEL", "INFO").upper()
    cloudwatch_emf_enabled = env_bool("CLOUDWATCH_EMF_ENABLED", app_env == "production")
    database_url = env_value(
        "DATABASE_URL",
        "postgresql+psycopg://tailorahub@localhost:5432/tailorahub_dev",
    )
    database_pool_size = env_int("DATABASE_POOL_SIZE", 10)
    database_max_overflow = env_int("DATABASE_MAX_OVERFLOW", 10)
    database_pool_timeout_seconds = env_int("DATABASE_POOL_TIMEOUT_SECONDS", 30)
    database_pool_recycle_seconds = env_int("DATABASE_POOL_RECYCLE_SECONDS", 1800)
    database_statement_timeout_ms = env_int("DATABASE_STATEMENT_TIMEOUT_MS", 5000)
    database_slow_query_ms = env_int("DATABASE_SLOW_QUERY_MS", 500)
    jwt_secret = env_value("JWT_SECRET", _RUNTIME_JWT_SECRET)
    jwt_secret_configured = bool(os.getenv("JWT_SECRET") and os.getenv("JWT_SECRET", "").strip())
    jwt_refresh_secret = env_value("JWT_REFRESH_SECRET", _RUNTIME_JWT_REFRESH_SECRET)
    jwt_refresh_secret_configured = bool(os.getenv("JWT_REFRESH_SECRET") and os.getenv("JWT_REFRESH_SECRET", "").strip())
    jwt_algorithm = "HS256"
    access_token_minutes = env_int("ACCESS_TOKEN_MINUTES", 1440)
    session_inactivity_minutes = env_int("SESSION_INACTIVITY_MINUTES", 15)
    cors_origins = [x.strip() for x in env_value("CORS_ORIGINS", "http://localhost:5173,https://tailorahub.com,https://www.tailorahub.com,https://api.tailorahub.com").split(",") if x.strip()]

    auto_migrate = env_bool("AUTO_MIGRATE", True)
    enable_demo_data = env_bool("ENABLE_DEMO_DATA", app_env != "production")
    write_admin_credential_file = env_bool("WRITE_ADMIN_CREDENTIAL_FILE", app_env != "production")

    admin_username = env_value("ADMIN_USERNAME", "admin")
    admin_password_configured = bool(os.getenv("ADMIN_PASSWORD") and os.getenv("ADMIN_PASSWORD", "").strip())
    admin_password = env_value("ADMIN_PASSWORD", _RUNTIME_ADMIN_PASSWORD)
    admin_email = env_value("ADMIN_EMAIL", "admin@tailorahub.com")
    admin_phone = env_value("ADMIN_PHONE", "9840099999")
    admin_allowed_networks = [
        value.strip()
        for value in env_value("ADMIN_ALLOWED_NETWORKS").split(",")
        if value.strip()
    ]
    admin_trusted_proxy_networks = [
        value.strip()
        for value in env_value("ADMIN_TRUSTED_PROXY_NETWORKS", "127.0.0.1/32,::1/128").split(",")
        if value.strip()
    ]

    sms_provider = env_value("SMS_PROVIDER", "mock").lower()
    sms_api_key = env_value("SMS_API_KEY")
    sms_api_secret = env_value("SMS_API_SECRET")
    sms_sender_id = env_value("SMS_SENDER_ID")
    sms_otp_template_id = env_value("SMS_OTP_TEMPLATE_ID")
    sms_api_base_url = env_value("SMS_API_BASE_URL")

    email_provider = env_value("EMAIL_PROVIDER", "mock").lower()
    email_api_key = env_value("EMAIL_API_KEY")
    # Keep the transport account and visible sender addresses separate.  A
    # provider may require each alias to be verified before it can be used.
    email_from_address = env_value("EMAIL_FROM_ADDRESS", env_value("EMAIL_FROM", "TailoraHub <noreply@tailorahub.com>"))
    email_from = email_from_address
    email_reply_to = env_value("EMAIL_REPLY_TO")
    email_from_default = env_value("EMAIL_FROM_DEFAULT", email_from_address)
    email_from_verify = env_value("EMAIL_FROM_VERIFY", "TailoraHub Verify <verify@tailorahub.com>")
    email_from_bookings = env_value("EMAIL_FROM_BOOKINGS", "TailoraHub Bookings <bookings@tailorahub.com>")
    email_from_support = env_value("EMAIL_FROM_SUPPORT", "TailoraHub Support <support@tailorahub.com>")
    email_from_payments = env_value("EMAIL_FROM_PAYMENTS", "TailoraHub Payments <payments@tailorahub.com>")
    email_from_admin = env_value("EMAIL_FROM_ADMIN", "TailoraHub Admin <admin@tailorahub.com>")
    smtp_host = env_value("SMTP_HOST")
    smtp_port = env_int("SMTP_PORT", 587)
    smtp_secure = env_bool("SMTP_SECURE", False)
    smtp_starttls = env_bool("SMTP_STARTTLS", True)
    smtp_user = env_value("SMTP_USER")
    smtp_pass = env_value("SMTP_PASS")
    email_outbox = env_value("EMAIL_OUTBOX", str(BASE_DIR / "email-outbox.log"))
    aws_ses_region = env_value("AWS_SES_REGION", "ap-south-1")

    aadhaar_kyc_provider = env_value("AADHAAR_KYC_PROVIDER", "mock").lower()
    aadhaar_kyc_api_key = env_value("AADHAAR_KYC_API_KEY")
    aadhaar_kyc_api_secret = env_value("AADHAAR_KYC_API_SECRET")
    aadhaar_kyc_base_url = env_value("AADHAAR_KYC_BASE_URL")
    aadhaar_encryption_key = env_value("AADHAAR_ENCRYPTION_KEY")
    aadhaar_encryption_key_configured = bool(
        os.getenv("AADHAAR_ENCRYPTION_KEY") and os.getenv("AADHAAR_ENCRYPTION_KEY", "").strip()
    )

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

    media_storage_backend = env_value("MEDIA_STORAGE_BACKEND", "local").lower()
    s3_media_bucket = env_value("S3_MEDIA_BUCKET")
    s3_media_region = env_value("S3_MEDIA_REGION", "ap-south-1")
    s3_media_endpoint_url = env_value("S3_MEDIA_ENDPOINT_URL")
    s3_media_key_prefix = env_value("S3_MEDIA_KEY_PREFIX", "media").strip("/")
    cloudfront_media_base_url = env_value("CLOUDFRONT_MEDIA_BASE_URL").rstrip("/")
    s3_presign_ttl_seconds = env_int("S3_PRESIGN_TTL_SECONDS", 300)

    realtime_backplane = env_value("REALTIME_BACKPLANE", "local").lower()
    realtime_channel_prefix = env_value("REALTIME_CHANNEL_PREFIX", "tailorahub:booking")
    realtime_ticket_seconds = env_int("REALTIME_TICKET_SECONDS", 120)
    redis_url = env_value("REDIS_URL", "redis://localhost:6379/0")

    traffic_store_backend = env_value("TRAFFIC_STORE_BACKEND", "memory").lower()
    public_cache_ttl_seconds = env_int("PUBLIC_CACHE_TTL_SECONDS", 60)
    rate_limit_enabled = env_bool("RATE_LIMIT_ENABLED", True)
    rate_limit_general_per_minute = env_int("RATE_LIMIT_GENERAL_PER_MINUTE", 300)
    rate_limit_auth_per_minute = env_int("RATE_LIMIT_AUTH_PER_MINUTE", 10)
    rate_limit_otp_per_minute = env_int("RATE_LIMIT_OTP_PER_MINUTE", 5)
    rate_limit_payment_per_minute = env_int("RATE_LIMIT_PAYMENT_PER_MINUTE", 10)
    rate_limit_upload_per_minute = env_int("RATE_LIMIT_UPLOAD_PER_MINUTE", 20)
    rate_limit_webhook_per_minute = env_int("RATE_LIMIT_WEBHOOK_PER_MINUTE", 1000)
    max_request_body_bytes = env_int("MAX_REQUEST_BODY_BYTES", 2 * 1024 * 1024)
    max_upload_request_bytes = env_int("MAX_UPLOAD_REQUEST_BYTES", 25 * 1024 * 1024)
    client_ip_trusted_proxy_networks = [
        value.strip()
        for value in env_value("CLIENT_IP_TRUSTED_PROXY_NETWORKS", "127.0.0.1/32,::1/128").split(",")
        if value.strip()
    ]

    service_role = env_value("SERVICE_ROLE", "web").lower()
    task_queue_backend = env_value("TASK_QUEUE_BACKEND", "inline").lower()
    sqs_task_queue_url = env_value("SQS_TASK_QUEUE_URL")
    sqs_task_dlq_url = env_value("SQS_TASK_DLQ_URL")
    sqs_region = env_value("SQS_REGION", "ap-south-1")
    sqs_endpoint_url = env_value("SQS_ENDPOINT_URL")
    task_max_attempts = env_int("TASK_MAX_ATTEMPTS", 5)
    task_visibility_timeout_seconds = env_int("TASK_VISIBILITY_TIMEOUT_SECONDS", 60)
    task_long_poll_seconds = env_int("TASK_LONG_POLL_SECONDS", 20)

    external_connect_timeout_seconds = env_int("EXTERNAL_CONNECT_TIMEOUT_SECONDS", 5)
    external_response_timeout_seconds = env_int("EXTERNAL_RESPONSE_TIMEOUT_SECONDS", 15)
    external_safe_retry_attempts = env_int("EXTERNAL_SAFE_RETRY_ATTEMPTS", 3)
    external_retry_base_ms = env_int("EXTERNAL_RETRY_BASE_MS", 250)
    external_circuit_failure_threshold = env_int("EXTERNAL_CIRCUIT_FAILURE_THRESHOLD", 5)
    external_circuit_reset_seconds = env_int("EXTERNAL_CIRCUIT_RESET_SECONDS", 30)


settings = Settings()
