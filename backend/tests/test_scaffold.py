import inspect
from datetime import date, timedelta
from pathlib import Path

import pytest
from fastapi import HTTPException

from app.api.v1 import api_router
from app.api.v1.admin import verify_payment_intent
from app.api.v1.bookings import (
    MEASUREMENT_APPOINTMENT_ERROR,
    MEASUREMENT_APPOINTMENT_REQUIRED_ERROR,
    latest_measurement_appointment_date,
    pay_booking,
    resolve_booking_dates,
    send_delivery_otp,
    verify_delivery_otp,
)
from app.core.config import get_settings
from app.main import app
from app.schema_models import SchemaBase


def test_v1_router_has_health_route():
    paths = {route.path for route in api_router.routes if hasattr(route, "path")}
    for included_router in [route for route in api_router.routes if hasattr(route, "original_router")]:
        prefix = getattr(getattr(included_router, "include_context", None), "prefix", "")
        paths.update(f"{prefix}{route.path}" for route in included_router.original_router.routes)
    assert "/health" in paths
    assert "/otp/send" in paths
    assert "/otp/verify" in paths
    assert "/auth/login" in paths
    assert "/auth/customer-login" in paths
    assert "/auth/refresh" in paths
    assert "/auth/forgot-password" in paths
    assert "/auth/reset-password" in paths
    assert "/auth/customer-forgot-password" in paths
    assert "/auth/customer-reset-password" in paths
    assert "/tailors/register" in paths
    assert "/tailors/check-availability" in paths
    assert "/tailors/me/location" in paths
    assert "/tailors/me/services" in paths
    assert "/tailors/me/services/{service_id}" in paths
    assert "/tailors/{tailor_id}/services" in paths
    assert "/customers/register" in paths
    assert "/customers/check-availability" in paths
    assert "/customers/nearby-tailors" in paths
    assert "/customers/me/wallet" in paths
    assert "/customers/me/referral-code" in paths
    assert "/customers/me/referral-count" in paths
    assert "/bookings" in paths
    assert "/bookings/{booking_id}/status" in paths
    assert "/bookings/{booking_id}/payment-breakdown" in paths
    assert "/bookings/{booking_id}/stage" in paths
    assert "/bookings/{booking_id}/pay" in paths
    assert "/bookings/{booking_id}/send-delivery-otp" in paths
    assert "/bookings/{booking_id}/verify-delivery-otp" in paths
    assert "/bookings/{booking_id}/raise-dispute" in paths
    assert "/bookings/{booking_id}/tailor-confirm" in paths
    assert "/bookings/{booking_id}/measurement-done" in paths
    assert "/tailors/me/waiting-list" in paths
    assert "/wallet/me" in paths
    assert "/wallet/set-upi" in paths
    assert "/wallet/withdraw" in paths
    assert "/wallet/withdraw/send-otp" in paths
    assert "/payments/pay" in paths
    assert "/referrals/my-code" in paths
    assert "/referrals/my-count" in paths
    assert "/admin/referrals/tree/{tailor_id}" in paths
    assert "/admin/customer-referrals/tree/{customer_id}" in paths
    assert "/admin/disputes" in paths
    assert "/admin/disputes/{dispute_id}" in paths
    assert "/admin/finance/settings" in paths
    assert "/admin/finance/wallet" in paths
    assert "/admin/finance/wallet/export" in paths


def test_settings_uses_asyncpg_url():
    assert get_settings().async_database_url.startswith("postgresql+asyncpg://")


def test_large_collection_routes_expose_bounded_pagination():
    schema = app.openapi()
    for path in (
        "/api/customer/bookings",
        "/api/tailor/dashboard",
        "/api/admin/orders",
        "/api/v1/customers/nearby-tailors",
        "/api/v1/admin/payment-intents",
    ):
        parameters = {item["name"]: item for item in schema["paths"][path]["get"]["parameters"]}
        assert parameters["limit"]["schema"]["default"] == 50
        assert parameters["limit"]["schema"]["maximum"] == 100
        assert parameters["offset"]["schema"]["default"] == 0
        assert parameters["offset"]["schema"]["minimum"] == 0


def test_schema_models_registered():
    assert "tailors" in SchemaBase.metadata.tables
    assert "users" in SchemaBase.metadata.tables
    assert "orders" in SchemaBase.metadata.tables
    assert "customer_wallets" in SchemaBase.metadata.tables
    assert "customer_referrals" in SchemaBase.metadata.tables
    assert "disputes" in SchemaBase.metadata.tables
    assert "platform_settings" in SchemaBase.metadata.tables
    assert "admin_wallet" in SchemaBase.metadata.tables
    assert "admin_wallet_transactions" in SchemaBase.metadata.tables
    assert "refresh_sessions" in SchemaBase.metadata.tables
    order_columns = SchemaBase.metadata.tables["orders"].columns
    assert "commission_amount" in order_columns
    assert "gst_platform_charge_amount" in order_columns
    dispute_columns = SchemaBase.metadata.tables["disputes"].columns
    assert "resolution_notes" in dispute_columns
    assert "refund_amount" in dispute_columns


def test_delivery_otp_is_server_gated_by_paid_payment():
    source = inspect.getsource(send_delivery_otp) + inspect.getsource(verify_delivery_otp)
    assert "payment_status" in source
    assert "status_code=403" in source
    assert "Payment must be completed before delivery OTP can be generated." in source
    assert "issue_otp" in source
    assert "verify_otp" in source
    assert "delivery_otps" not in source
    assert "otp_codes" not in source


def test_finance_engine_hooks_payment_and_completion():
    payment_source = inspect.getsource(pay_booking)
    admin_verification_source = inspect.getsource(verify_payment_intent)
    completion_source = inspect.getsource(verify_delivery_otp)
    assert "gst_platform_charge" in payment_source
    assert "payment_intents" in payment_source
    assert "_credit_admin_wallet" in admin_verification_source
    assert "_ensure_tailor_wallet" in admin_verification_source
    assert "apply_completion_commission" in completion_source


def test_security_schema_uses_hashed_otp_and_refresh_sessions():
    schema = (Path(__file__).resolve().parents[1] / "app" / "schema.sql").read_text(encoding="utf-8")
    assert "CREATE TABLE IF NOT EXISTS otp_verifications" in schema
    assert "otp_hash" in schema
    assert "attempt_count" in schema
    assert "CREATE TABLE IF NOT EXISTS refresh_sessions" in schema
    assert "CREATE TABLE IF NOT EXISTS otp_codes" not in schema
    assert "delivery_otps" not in schema


def test_access_tokens_support_full_work_sessions():
    settings = get_settings()
    assert settings.access_token_minutes >= 60
    assert settings.jwt_secret
    assert settings.jwt_refresh_secret
    assert settings.jwt_secret != settings.jwt_refresh_secret


def test_booking_dates_no_longer_apply_old_fixed_three_day_rule():
    delivery_date = date.today() + timedelta(days=2)
    appointment_date = date.today() + timedelta(days=1)

    assert resolve_booking_dates(delivery_date, appointment_date, 5) == (delivery_date, appointment_date)


def test_measurement_appointment_rejects_missing_or_past_dates():
    delivery_date = date.today() + timedelta(days=5)
    with pytest.raises(HTTPException) as missing_exc:
        resolve_booking_dates(delivery_date, None, 5)

    assert missing_exc.value.status_code == 400
    assert missing_exc.value.detail == MEASUREMENT_APPOINTMENT_REQUIRED_ERROR

    with pytest.raises(HTTPException) as exc_info:
        resolve_booking_dates(delivery_date, date.today() - timedelta(days=1), 5)
    assert exc_info.value.status_code == 400
