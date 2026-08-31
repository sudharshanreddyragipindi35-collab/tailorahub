from __future__ import annotations

from urllib.parse import parse_qs, urlparse


_PLACEHOLDER_FRAGMENTS = (
    "change-me",
    "changeme",
    "replace-me",
    "replace_this",
    "generate_",
    "your_",
    "example",
)


def _looks_like_placeholder(value: str) -> bool:
    normalized = value.strip().lower()
    return not normalized or any(fragment in normalized for fragment in _PLACEHOLDER_FRAGMENTS)


def _require_secret(name: str, value: str, configured: bool, minimum_length: int) -> None:
    if not configured or len(value) < minimum_length or _looks_like_placeholder(value):
        raise RuntimeError(f"Production requires an explicitly configured, non-placeholder {name} of at least {minimum_length} characters")


def _database_tls_enabled(database_url: str) -> bool:
    parsed = urlparse(database_url)
    options = parse_qs(parsed.query)
    sslmode = (options.get("sslmode") or [""])[0].lower()
    return sslmode in {"require", "verify-ca", "verify-full"}


def validate_production_settings(settings) -> None:
    """Fail closed when a production task has unsafe or incomplete security settings."""

    if settings.app_env != "production":
        return

    if settings.auto_migrate:
        raise RuntimeError("Production web containers require AUTO_MIGRATE=false; run SERVICE_ROLE=migration once")
    if settings.enable_demo_data:
        raise RuntimeError("Production requires ENABLE_DEMO_DATA=false")
    if settings.write_admin_credential_file:
        raise RuntimeError("Production requires WRITE_ADMIN_CREDENTIAL_FILE=false")

    _require_secret("JWT_SECRET", settings.jwt_secret, settings.jwt_secret_configured, 32)
    _require_secret("JWT_REFRESH_SECRET", settings.jwt_refresh_secret, settings.jwt_refresh_secret_configured, 32)
    _require_secret("ADMIN_PASSWORD", settings.admin_password, settings.admin_password_configured, 16)
    _require_secret(
        "AADHAAR_ENCRYPTION_KEY",
        settings.aadhaar_encryption_key,
        settings.aadhaar_encryption_key_configured,
        32,
    )
    if settings.jwt_secret == settings.jwt_refresh_secret:
        raise RuntimeError("Production JWT_SECRET and JWT_REFRESH_SECRET must be different")

    if not settings.admin_allowed_networks:
        raise RuntimeError("Production requires at least one ADMIN_ALLOWED_NETWORKS CIDR")
    if not settings.database_url.startswith("postgresql") or not _database_tls_enabled(settings.database_url):
        raise RuntimeError("Production DATABASE_URL must be PostgreSQL and include sslmode=require, verify-ca, or verify-full")
    if not settings.redis_url.startswith("rediss://"):
        raise RuntimeError("Production REDIS_URL must use TLS (rediss://)")
    if settings.cloudfront_media_base_url and not settings.cloudfront_media_base_url.startswith("https://"):
        raise RuntimeError("Production CLOUDFRONT_MEDIA_BASE_URL must use HTTPS")
    if not settings.cors_origins or any(origin == "*" or not origin.startswith("https://") for origin in settings.cors_origins):
        raise RuntimeError("Production CORS_ORIGINS must contain only explicit HTTPS origins")

    if settings.task_queue_backend != "sqs" or not settings.sqs_task_queue_url or not settings.sqs_task_dlq_url:
        raise RuntimeError("Production requires the SQS task queue and dead-letter queue configuration")
    if settings.media_storage_backend != "s3":
        raise RuntimeError("Production requires MEDIA_STORAGE_BACKEND=s3")
    if not settings.cloudfront_media_base_url:
        raise RuntimeError("Production requires CLOUDFRONT_MEDIA_BASE_URL")
    if settings.realtime_backplane != "redis":
        raise RuntimeError("Production requires REALTIME_BACKPLANE=redis")
    if settings.traffic_store_backend != "redis":
        raise RuntimeError("Production requires TRAFFIC_STORE_BACKEND=redis for shared caching and rate limits")
    if settings.payment_provider == "razorpay" and not settings.razorpay_webhook_secret:
        raise RuntimeError("Production Razorpay requires RAZORPAY_WEBHOOK_SECRET")


def apply_api_security_headers(response, production: bool) -> None:
    response.headers["Cache-Control"] = "no-store"
    response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
    response.headers["Cross-Origin-Resource-Policy"] = "same-site"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=()"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    if production:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
