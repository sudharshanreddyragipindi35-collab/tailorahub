import asyncio
import inspect
from datetime import date, datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path

import pytest
from fastapi import HTTPException, WebSocketDisconnect

from app.api.v1 import api_router
from app.api.v1.admin import verify_payment_intent
from app.api.v1.bookings import (
    MEASUREMENT_APPOINTMENT_ERROR,
    MEASUREMENT_APPOINTMENT_REQUIRED_ERROR,
    latest_measurement_appointment_date,
    pay_booking,
    resolve_booking_dates,
    send_delivery_otp,
    track_booking,
    verify_delivery_otp,
)
from app.api.v1 import bookings as bookings_module
from app.core.config import get_settings
from app.core.security import create_booking_ws_ticket, decode_booking_ws_ticket
from app.main import app
from app.schema_models import SchemaBase
from app.services.media_storage import MediaStorage, MediaStorageError, validate_file_signature
from app.services.tracker_service import TrackerConnectionManager


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
    assert "/bookings/{booking_id}/track-ticket" in paths
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


def test_booking_tracker_websocket_replies_to_heartbeat(monkeypatch):
    class FakeTrackerConnections:
        def __init__(self):
            self.disconnected = False

        async def connect(self, booking_id, websocket):
            self.booking_id = booking_id

        def disconnect(self, booking_id, websocket):
            self.disconnected = True

    class FakeWebSocket:
        def __init__(self):
            self.messages = iter(("ping",))
            self.sent = []

        async def receive_text(self):
            try:
                return next(self.messages)
            except StopIteration as exc:
                raise WebSocketDisconnect() from exc

        async def send_json(self, payload):
            self.sent.append(payload)

    connections = FakeTrackerConnections()
    websocket = FakeWebSocket()
    monkeypatch.setattr(bookings_module, "tracker_connections", connections)

    ticket = create_booking_ws_ticket("phase2-test-user", "ORD-PHASE2")
    asyncio.run(track_booking(websocket, "ORD-PHASE2", ticket))

    assert websocket.sent == [{"type": "pong"}]
    assert connections.booking_id == "ORD-PHASE2"
    assert connections.disconnected is True


def test_booking_tracker_ticket_is_short_lived_and_booking_scoped():
    ticket = create_booking_ws_ticket("user-1", "booking-1")
    payload = decode_booking_ws_ticket(ticket)

    assert payload["sub"] == "user-1"
    assert payload["booking_id"] == "booking-1"
    assert payload["type"] == "booking_ws"
    remaining = payload["exp"] - int(datetime.now(timezone.utc).timestamp())
    assert 0 < remaining <= 600


def test_booking_tracker_rejects_missing_ticket():
    class FakeWebSocket:
        def __init__(self):
            self.closed = None

        async def close(self, **kwargs):
            self.closed = kwargs

    websocket = FakeWebSocket()
    asyncio.run(track_booking(websocket, "booking-1", None))

    assert websocket.closed["code"] == 4401


def test_tracker_backplane_delivers_remote_events_and_ignores_its_own():
    class FakeWebSocket:
        def __init__(self):
            self.sent = []

        async def send_json(self, payload):
            self.sent.append(payload)

    async def exercise():
        manager = TrackerConnectionManager(backplane="local")
        websocket = FakeWebSocket()
        manager._rooms["booking-1"].add(websocket)
        await manager._handle_backplane_message('{"source":"other","bookingId":"booking-1","payload":{"status":"ready"}}')
        await manager._handle_backplane_message(
            '{"source":"' + manager.instance_id + '","bookingId":"booking-1","payload":{"status":"duplicate"}}'
        )
        return websocket.sent

    assert asyncio.run(exercise()) == [{"status": "ready"}]


def test_local_media_storage_uses_bounded_keys_and_deletes(monkeypatch, tmp_path):
    from app import settings as settings_module

    monkeypatch.setattr(settings_module.settings, "base_dir", tmp_path)
    monkeypatch.setattr(settings_module.settings, "media_storage_backend", "local")
    storage = MediaStorage()

    url = storage.store_bytes("tailors/t-1/profile/photo.webp", b"image-bytes", "image/webp")
    assert url == "/uploads/tailors/t-1/profile/photo.webp"
    assert (tmp_path / "uploads" / "tailors" / "t-1" / "profile" / "photo.webp").read_bytes() == b"image-bytes"
    storage.delete_url(url)
    assert not (tmp_path / "uploads" / "tailors" / "t-1" / "profile" / "photo.webp").exists()

    with pytest.raises(MediaStorageError):
        storage.store_bytes("../escape.webp", b"bad", "image/webp")


def test_s3_presign_enforces_type_size_and_validates_file_signature(monkeypatch, tmp_path):
    from app import settings as settings_module

    class FakeS3:
        def __init__(self):
            self.deleted = []

        def generate_presigned_post(self, **kwargs):
            self.presign = kwargs
            return {"url": "https://upload.example.test", "fields": {"key": kwargs["Key"]}}

        def head_object(self, **kwargs):
            return {"ContentLength": 12, "ContentType": "image/webp"}

        def get_object(self, **kwargs):
            return {"Body": BytesIO(b"RIFF\x04\x00\x00\x00WEBP")}

        def delete_object(self, **kwargs):
            self.deleted.append(kwargs)

    monkeypatch.setattr(settings_module.settings, "base_dir", tmp_path)
    monkeypatch.setattr(settings_module.settings, "media_storage_backend", "local")
    storage = MediaStorage()
    fake = FakeS3()
    storage.backend = "s3"
    storage.bucket = "tailorahub-media"
    storage.region = "ap-south-1"
    storage.key_prefix = "media"
    storage.public_base_url = "https://media.tailorahub.com"
    storage._client = fake

    plan = storage.create_presigned_upload("tailors/t-1/portfolio/photo.webp", "image/webp", 1024)
    assert plan["mode"] == "direct"
    assert ["content-length-range", 1, 1024] in fake.presign["Conditions"]
    assert {"Content-Type": "image/webp"} in fake.presign["Conditions"]
    assert storage.validate_uploaded_object("tailors/t-1/portfolio/photo.webp", "image/webp", 1024) == (
        "https://media.tailorahub.com/media/tailors/t-1/portfolio/photo.webp"
    )
    validate_file_signature(b"\x89PNG\r\n\x1a\nmore", "image/png")
    with pytest.raises(MediaStorageError):
        validate_file_signature(b"not-an-image", "image/png")


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
