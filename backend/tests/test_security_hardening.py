from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.security_hardening import validate_production_settings


def production_settings(**overrides):
    values = {
        "app_env": "production",
        "auto_migrate": False,
        "enable_demo_data": False,
        "write_admin_credential_file": False,
        "jwt_secret": "j" * 48,
        "jwt_secret_configured": True,
        "jwt_refresh_secret": "r" * 48,
        "jwt_refresh_secret_configured": True,
        "admin_password": "Admin-password-unique-2026",
        "admin_password_configured": True,
        "aadhaar_encryption_key": "a" * 48,
        "aadhaar_encryption_key_configured": True,
        "admin_allowed_networks": ["203.0.113.10/32"],
        "database_url": "postgresql+psycopg://app:password@db.internal/tailorahub?sslmode=require",
        "redis_url": "rediss://redis.internal:6379/0",
        "cors_origins": ["https://tailorahub.com", "https://www.tailorahub.com"],
        "task_queue_backend": "sqs",
        "sqs_task_queue_url": "https://sqs.ap-south-1.amazonaws.com/123/tasks",
        "sqs_task_dlq_url": "https://sqs.ap-south-1.amazonaws.com/123/tasks-dlq",
        "media_storage_backend": "s3",
        "cloudfront_media_base_url": "https://media.tailorahub.com",
        "realtime_backplane": "redis",
        "traffic_store_backend": "redis",
        "payment_provider": "razorpay",
        "razorpay_webhook_secret": "w" * 48,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_valid_production_security_settings_pass():
    validate_production_settings(production_settings())


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"enable_demo_data": True}, "ENABLE_DEMO_DATA=false"),
        ({"write_admin_credential_file": True}, "WRITE_ADMIN_CREDENTIAL_FILE=false"),
        ({"jwt_secret_configured": False}, "JWT_SECRET"),
        ({"jwt_refresh_secret": "j" * 48}, "must be different"),
        ({"admin_allowed_networks": []}, "ADMIN_ALLOWED_NETWORKS"),
        ({"database_url": "postgresql+psycopg://app:password@db.internal/tailorahub"}, "sslmode"),
        ({"redis_url": "redis://redis.internal:6379/0"}, "rediss://"),
        ({"cors_origins": ["*"]}, "explicit HTTPS"),
    ],
)
def test_unsafe_production_security_settings_fail_closed(overrides, message):
    with pytest.raises(RuntimeError, match=message):
        validate_production_settings(production_settings(**overrides))


def test_api_responses_include_security_headers():
    with TestClient(app) as client:
        response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert "default-src 'none'" in response.headers["content-security-policy"]
