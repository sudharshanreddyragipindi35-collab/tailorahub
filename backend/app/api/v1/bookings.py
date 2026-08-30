from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
import logging
import math
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
import re
import uuid
from zoneinfo import ZoneInfo
from urllib import error as urllib_error, request as urllib_request
from urllib.parse import quote_plus

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_customer, get_current_tailor, get_current_user
from app.api.v1.otp import OTP_TTL_MINUTES, OtpFlowError, issue_otp, verify_otp
from app.core.config import get_settings
from app.core.security import create_booking_ws_ticket, decode_booking_ws_ticket
from app.core.database import get_db
from app.pagination import PageParams
from app.emailer import send_email
from app.qr import generate_wallet_qr
from app.services.tracker_service import tracker_connections
from app.services.media_storage import MediaStorageError, get_media_storage, validate_file_signature
from app.services.booking_rules import APP_TIMEZONE, BookingRuleError, calculate_booking, zoned_slot


router = APIRouter()
logger = logging.getLogger(__name__)

MEASUREMENT_APPOINTMENT_ERROR = "Measurement appointment must be on or before the delivery date."
MEASUREMENT_APPOINTMENT_REQUIRED_ERROR = "Choose measurement appointment date."
PAST_DELIVERY_DATE_ERROR = "Expected delivery date cannot be in the past. Choose today or a future date."
PAST_APPOINTMENT_DATE_ERROR = "Measurement appointment cannot be in the past. Choose today or a future date."
APPOINTMENT_TIMEZONE = ZoneInfo("Asia/Kolkata")
APPOINTMENT_SLOTS = {
    "08:00-10:00": 480,
    "10:00-12:00": 600,
    "12:00-14:00": 720,
    "14:00-16:00": 840,
    "16:00-18:00": 960,
    "18:00-20:00": 1080,
    "20:00-22:00": 1200,
}
TRAVEL_CHARGE_PER_KM = Decimal("5.00")
DEFAULT_PLATFORM_SETTINGS = {
    "commission_percentage": Decimal("20.00"),
    "gst_percentage": Decimal("18.00"),
    "platform_fee_percentage": Decimal("2.00"),
}
DISPUTE_IMAGE_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
MAX_DISPUTE_IMAGE_BYTES = 8 * 1024 * 1024


class BookingCreateIn(BaseModel):
    tailor_id: str = Field(alias="tailorId", min_length=1)
    service_id: str = Field(alias="serviceId", min_length=1)
    service_name: str | None = Field(default=None, alias="serviceName")
    quantity: int = Field(default=1, ge=1)
    requirements: str | None = None
    preferred_date: date | None = Field(default=None, alias="preferredDate")
    instructions: str | None = None
    measurement_mode: str = Field(default="customer_visits_tailor", alias="measurementMode")
    appointment_date: date | None = Field(default=None, alias="appointmentDate")
    appointment_slot: str | None = Field(default=None, alias="appointmentSlot")
    urgent_days: int | None = Field(default=None, alias="urgentDays")
    customer_location_address: str | None = Field(default=None, alias="customerLocationAddress")
    customer_location_lat: float | None = Field(default=None, alias="customerLocationLat", ge=-90, le=90)
    customer_location_lng: float | None = Field(default=None, alias="customerLocationLng", ge=-180, le=180)
    idempotency_key: str | None = Field(default=None, alias="idempotencyKey", min_length=8, max_length=100)


class StageUpdateIn(BaseModel):
    tracker_stage: str = Field(alias="trackerStage")
    note: str | None = None


class PaymentIn(BaseModel):
    method: str = "razorpay"
    txn_ref: str | None = Field(default=None, alias="txnRef")


class RazorpayVerifyIn(BaseModel):
    razorpay_order_id: str = Field(min_length=1)
    razorpay_payment_id: str = Field(min_length=1)
    razorpay_signature: str = Field(min_length=1)


class DeliveryOtpVerifyIn(BaseModel):
    otp: str = Field(min_length=4, max_length=8)


class MeasurementTripLocationIn(BaseModel):
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    announce: bool = False


class MeasurementOtpVerifyIn(BaseModel):
    otp: str = Field(min_length=4, max_length=8)


class RaiseDisputeIn(BaseModel):
    reason: str = Field(min_length=5, max_length=2000)
    photo_url: str | None = Field(default=None, alias="photoUrl")
    photo_name: str | None = Field(default=None, alias="photoName")
    photo_media_type: str | None = Field(default=None, alias="photoMediaType")


class CustomerOrderUpdateIn(BaseModel):
    instructions: str | None = Field(default=None, max_length=2000)
    preferred_date: date | None = Field(default=None, alias="preferredDate")


class CustomerCancelOrderIn(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


TRACKER_STAGES = [
    "Order Placed",
    "Measurement Scheduled",
    "Measurement Done",
    "Stitching in Progress",
    "Ready for Delivery",
    "Out for Delivery",
    "Delivered",
]

STAGE_TO_STATUS = {
    "Measurement Scheduled": "measurement_pending",
    "Measurement Done": "measurement_done",
    "Stitching in Progress": "in_progress",
    "Ready for Delivery": "ready_for_delivery",
    "Out for Delivery": "out_for_delivery",
}


def is_completed_order(order: dict | None) -> bool:
    if not order:
        return False
    return (
        str(order.get("status") or "").lower() == "completed"
        or bool(order.get("completed_at"))
    )


def is_cancelled_order(order: dict | None) -> bool:
    return str((order or {}).get("status") or "").lower() == "cancelled"


def is_measurement_started(order: dict | None) -> bool:
    if not order:
        return False
    status = str(order.get("status") or "").lower()
    tracker_stage = str(order.get("tracker_stage") or "").lower()
    return (
        bool(order.get("measurement_done_at"))
        or status in {"measurement_done", "in_progress", "ready_for_delivery", "out_for_delivery", "completed", "disputed"}
        or tracker_stage in {"measurement done", "stitching in progress", "ready for delivery", "out for delivery", "delivered"}
    )


def customer_manage_cutoff_error(order: dict | None) -> str | None:
    if not order:
        return "Order not found"
    if is_completed_order(order):
        return "This order is already completed. Manage options are closed after final handover."
    if is_cancelled_order(order):
        return "This order is already cancelled."
    if is_measurement_started(order):
        return "Manage options are available only before measurement starts."
    appointment_date = order.get("appointment_date")
    if isinstance(appointment_date, datetime):
        appointment_date = appointment_date.date()
    if appointment_date and date.today() >= appointment_date:
        return "Manage options are available only before the measurement appointment date."
    return None


def latest_measurement_appointment_date(delivery_date: date) -> date:
    return delivery_date


def resolve_booking_dates(
    preferred_date: date | None,
    appointment_date: date | None,
    service_days: int | None,
) -> tuple[date, date]:
    today = datetime.now(APPOINTMENT_TIMEZONE).date()
    delivery_date = preferred_date or (today + timedelta(days=service_days or 5))
    if delivery_date < today:
        raise HTTPException(400, PAST_DELIVERY_DATE_ERROR)
    if appointment_date is None:
        raise HTTPException(400, MEASUREMENT_APPOINTMENT_REQUIRED_ERROR)
    if appointment_date < today:
        raise HTTPException(400, PAST_APPOINTMENT_DATE_ERROR)
    if appointment_date > delivery_date:
        raise HTTPException(400, MEASUREMENT_APPOINTMENT_ERROR)
    return delivery_date, appointment_date


def validate_appointment_slot(
    appointment_date: date,
    appointment_slot: str | None,
    now: datetime | None = None,
) -> str:
    if appointment_slot not in APPOINTMENT_SLOTS:
        raise HTTPException(400, "Choose a valid appointment time slot.")
    current = now or datetime.now(APPOINTMENT_TIMEZONE)
    if current.tzinfo is None:
        current = current.replace(tzinfo=APPOINTMENT_TIMEZONE)
    current = current.astimezone(APPOINTMENT_TIMEZONE)
    if appointment_date == current.date():
        current_minutes = current.hour * 60 + current.minute
        if APPOINTMENT_SLOTS[appointment_slot] <= current_minutes:
            raise HTTPException(400, "Selected appointment time slot has already expired. Choose a later slot.")
    return appointment_slot


def uid(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def money_decimal(value) -> Decimal:
    return Decimal(str(value or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def percent_amount(amount, percentage) -> Decimal:
    return (money_decimal(amount) * money_decimal(percentage) / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def distance_km_between(lat1, lng1, lat2, lng2) -> Decimal:
    try:
        a_lat, a_lng, b_lat, b_lng = [float(value) for value in (lat1, lng1, lat2, lng2)]
    except (TypeError, ValueError):
        return Decimal("0.00")
    radius_km = 6371.0
    d_lat = math.radians(b_lat - a_lat)
    d_lng = math.radians(b_lng - a_lng)
    start_lat = math.radians(a_lat)
    end_lat = math.radians(b_lat)
    haversine = math.sin(d_lat / 2) ** 2 + math.cos(start_lat) * math.cos(end_lat) * math.sin(d_lng / 2) ** 2
    distance = radius_km * 2 * math.atan2(math.sqrt(haversine), math.sqrt(1 - haversine))
    return Decimal(str(distance)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def travel_charge_for_distance(distance_km: Decimal) -> Decimal:
    return (money_decimal(distance_km) * TRAVEL_CHARGE_PER_KM).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


async def fetch_one(db: AsyncSession, sql: str, params: dict | None = None) -> dict | None:
    result = await db.execute(text(sql), params or {})
    row = result.mappings().first()
    return dict(row) if row else None


async def fetch_all(db: AsyncSession, sql: str, params: dict | None = None) -> list[dict]:
    result = await db.execute(text(sql), params or {})
    return [dict(row) for row in result.mappings().all()]


async def platform_settings(db: AsyncSession) -> dict:
    row = await fetch_one(db, "SELECT * FROM platform_settings WHERE id=1")
    if row:
        return row
    result = await db.execute(
        text("INSERT INTO platform_settings (id) VALUES (1) ON CONFLICT (id) DO UPDATE SET id=EXCLUDED.id RETURNING *")
    )
    return dict(result.mappings().first())


async def ensure_admin_wallet(db: AsyncSession) -> dict:
    ledger_balance = await admin_wallet_ledger_balance(db)
    row = await fetch_one(db, "SELECT * FROM admin_wallet ORDER BY updated_at ASC LIMIT 1")
    if row:
        if money_decimal(row.get("balance")) != ledger_balance:
            result = await db.execute(
                text("UPDATE admin_wallet SET balance=:balance, updated_at=now() WHERE wallet_id=:wallet_id RETURNING *"),
                {"balance": ledger_balance, "wallet_id": row["wallet_id"]},
            )
            return dict(result.mappings().first())
        return row
    result = await db.execute(
        text("INSERT INTO admin_wallet (wallet_id,balance,updated_at) VALUES (gen_random_uuid(),:balance,now()) RETURNING *"),
        {"balance": ledger_balance},
    )
    return dict(result.mappings().first())


async def admin_wallet_ledger_balance(db: AsyncSession) -> Decimal:
    row = await fetch_one(db, "SELECT COALESCE(SUM(amount),0) AS balance FROM admin_wallet_transactions")
    return money_decimal(row["balance"] if row else 0)


async def ensure_tailor_wallet(db: AsyncSession, tailor_uuid) -> dict:
    row = await fetch_one(db, "SELECT * FROM tailor_wallets WHERE tailor_id=:tailor_id", {"tailor_id": tailor_uuid})
    if row:
        return row
    wallet_id = uuid.uuid4()
    qr_url = generate_wallet_qr(str(wallet_id))
    result = await db.execute(
        text(
            """
            INSERT INTO tailor_wallets (wallet_id,tailor_id,qr_code_url,balance,created_at,updated_at)
            VALUES (:wallet_id,:tailor_id,:qr_url,0,now(),now())
            RETURNING *
            """
        ),
        {"wallet_id": wallet_id, "tailor_id": tailor_uuid, "qr_url": qr_url},
    )
    return dict(result.mappings().first())


async def payment_breakdown_for_order(db: AsyncSession, order: dict) -> dict:
    try:
        settings = await platform_settings(db)
    except Exception:
        await db.rollback()
        logger.exception("Platform settings unavailable; using default payment settings")
        settings = DEFAULT_PLATFORM_SETTINGS.copy()
    settings = {**DEFAULT_PLATFORM_SETTINGS, **(settings or {})}
    service_amount = money_decimal(order.get("base_amount") or order.get("base_price") or order.get("total") or 0)
    urgent_charge = money_decimal(order.get("urgent_charge"))
    order_amount = money_decimal(order.get("final_amount") or order.get("total") or service_amount + urgent_charge)
    # Customer pricing is the immutable service snapshot plus the one-time
    # urgent charge. Commission is settled internally and is never added to
    # the amount shown to or paid by the customer.
    travel_charge_amount = Decimal("0.00")
    gst_amount = Decimal("0.00")
    platform_fee_amount = Decimal("0.00")
    charge_amount = Decimal("0.00")
    commission_amount = percent_amount(order_amount, settings.get("commission_percentage"))
    tailor_credit_amount = max(order_amount - commission_amount, Decimal("0.00"))
    grand_total = order_amount
    return {
        "service_amount": service_amount,
        "serviceAmount": service_amount,
        "travel_charge_amount": travel_charge_amount,
        "travelChargeAmount": travel_charge_amount,
        "travel_rate_per_km": TRAVEL_CHARGE_PER_KM,
        "travelRatePerKm": TRAVEL_CHARGE_PER_KM,
        "urgent_charge": urgent_charge,
        "urgentCharge": urgent_charge,
        "order_amount": order_amount,
        "orderAmount": order_amount,
        "commission_percentage": money_decimal(settings.get("commission_percentage")),
        "commissionPercentage": money_decimal(settings.get("commission_percentage")),
        "commission_amount": commission_amount,
        "commissionAmount": commission_amount,
        "tailor_credit_amount": tailor_credit_amount,
        "tailorCreditAmount": tailor_credit_amount,
        "gst_percentage": money_decimal(settings.get("gst_percentage")),
        "gstPercentage": money_decimal(settings.get("gst_percentage")),
        "gst_amount": gst_amount,
        "gstAmount": gst_amount,
        "platform_fee_percentage": money_decimal(settings.get("platform_fee_percentage")),
        "platformFeePercentage": money_decimal(settings.get("platform_fee_percentage")),
        "platform_fee_amount": platform_fee_amount,
        "platformFeeAmount": platform_fee_amount,
        "gst_platform_charge_amount": charge_amount,
        "gstPlatformChargeAmount": charge_amount,
        "payable_total": grand_total,
        "payableTotal": grand_total,
    }


def payment_intent_payload(row: dict | None) -> dict | None:
    if not row:
        return None
    expires_at = row.get("expires_at")
    now = datetime.now(timezone.utc)
    expires_in = 0
    if expires_at:
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        expires_in = max(0, int((expires_at - now).total_seconds()))
    return {
        "id": str(row["id"]),
        "booking_id": row.get("booking_id"),
        "bookingId": row.get("booking_id"),
        "payment_reference": row.get("payment_reference"),
        "paymentReference": row.get("payment_reference"),
        "method": row.get("method"),
        "status": row.get("status"),
        "order_amount": row.get("order_amount"),
        "orderAmount": row.get("order_amount"),
        "gst_platform_charge_amount": row.get("gst_platform_charge_amount"),
        "gstPlatformChargeAmount": row.get("gst_platform_charge_amount"),
        "commission_amount": row.get("commission_amount"),
        "commissionAmount": row.get("commission_amount"),
        "tailor_credit_amount": row.get("tailor_credit_amount"),
        "tailorCreditAmount": row.get("tailor_credit_amount"),
        "payable_total": row.get("payable_total"),
        "payableTotal": row.get("payable_total"),
        "gateway_order_id": row.get("gateway_order_id"),
        "gatewayOrderId": row.get("gateway_order_id"),
        "gateway_payment_id": row.get("gateway_payment_id"),
        "gatewayPaymentId": row.get("gateway_payment_id"),
        "expires_at": row.get("expires_at"),
        "expiresAt": row.get("expires_at"),
        "expires_in_seconds": expires_in,
        "expiresInSeconds": expires_in,
        "created_at": row.get("created_at"),
        "createdAt": row.get("created_at"),
        "verified_at": row.get("verified_at"),
        "verifiedAt": row.get("verified_at"),
        "admin_note": row.get("admin_note"),
        "adminNote": row.get("admin_note"),
        "proof_reference": row.get("proof_reference"),
        "proofReference": row.get("proof_reference"),
    }


async def latest_payment_intent(db: AsyncSession, booking_id: str) -> dict | None:
    await db.execute(
        text(
            """
            UPDATE payment_intents
            SET status='expired', updated_at=now()
            WHERE booking_id=:booking_id
              AND status='pending'
              AND expires_at <= now()
            """
        ),
        {"booking_id": booking_id},
    )
    return await fetch_one(
        db,
        "SELECT * FROM payment_intents WHERE booking_id=:booking_id ORDER BY created_at DESC LIMIT 1",
        {"booking_id": booking_id},
    )


def clean_payment_credential(value: str | None) -> str:
    cleaned = str(value or "").strip().strip('"').strip("'").strip("`")
    return cleaned.replace("\\_", "_").replace(" ", "")


def is_placeholder_credential(value: str) -> bool:
    normalized = value.strip().lower()
    return (
        not normalized
        or normalized.startswith("your_")
        or "paste_" in normalized
        or "change_me" in normalized
        or normalized in {"test_key", "test_secret", "none", "null"}
    )


def razorpay_credentials() -> tuple[str, str]:
    app_settings = get_settings()
    razorpay_key_id = clean_payment_credential(app_settings.razorpay_key_id)
    razorpay_key_secret = clean_payment_credential(app_settings.razorpay_key_secret)
    fallback_key_id = clean_payment_credential(app_settings.payment_api_key)
    fallback_key_secret = clean_payment_credential(app_settings.payment_api_secret)
    key_id = razorpay_key_id if not is_placeholder_credential(razorpay_key_id) else fallback_key_id
    key_secret = razorpay_key_secret if not is_placeholder_credential(razorpay_key_secret) else fallback_key_secret
    if is_placeholder_credential(key_id) or is_placeholder_credential(key_secret):
        return "", ""
    return key_id, key_secret


def require_razorpay_credentials() -> tuple[str, str]:
    key_id, key_secret = razorpay_credentials()
    if not key_id or not key_secret:
        raise HTTPException(
            503,
            "Razorpay keys are not configured. Add RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET in the backend environment, then restart the backend.",
        )
    if not key_id.startswith("rzp_"):
        raise HTTPException(
            503,
            "Razorpay key id is invalid. It must start with rzp_test_ or rzp_live_. Update RAZORPAY_KEY_ID on the backend.",
        )
    if key_secret.startswith("rzp_") or key_secret == key_id:
        raise HTTPException(
            503,
            "Razorpay key secret is invalid. Do not paste the key id into RAZORPAY_KEY_SECRET. Regenerate the secret and restart the backend.",
        )
    return key_id, key_secret


def amount_to_paise(amount: Decimal) -> int:
    return int((money_decimal(amount) * Decimal("100")).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def razorpay_public_checkout_payload(order: dict, intent: dict, breakdown: dict, key_id: str) -> dict:
    payable_total = money_decimal(intent.get("payable_total") or breakdown.get("payable_total"))
    description = f"TailoraHub order {order.get('code') or order.get('id')}"
    return {
        "keyId": key_id,
        "key_id": key_id,
        "razorpayOrderId": intent.get("gateway_order_id"),
        "razorpay_order_id": intent.get("gateway_order_id"),
        "amountPaise": amount_to_paise(payable_total),
        "amount_paise": amount_to_paise(payable_total),
        "amount": amount_to_paise(payable_total),
        "currency": "INR",
        "name": "TailoraHub",
        "description": description,
        "prefill": {
            "name": order.get("customer_name") or "",
            "email": order.get("customer_email") or "",
            "contact": order.get("customer_phone") or "",
        },
        "notes": {
            "booking_id": order.get("id"),
            "order_code": order.get("code"),
            "payment_reference": intent.get("payment_reference"),
        },
        "theme": {"color": "#d4af37"},
    }


def create_razorpay_order_sync(key_id: str, key_secret: str, payload: dict) -> dict:
    auth = base64.b64encode(f"{key_id}:{key_secret}".encode("utf-8")).decode("ascii")
    req = urllib_request.Request(
        "https://api.razorpay.com/v1/orders",
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Basic {auth}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with urllib_request.urlopen(req, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib_error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "ignore")
        message = detail[:300] or "No details returned."
        try:
            parsed = json.loads(detail)
            razorpay_message = parsed.get("error", {}).get("description")
            if razorpay_message:
                message = razorpay_message
        except Exception:
            pass
        if exc.code in {401, 403} or "authentication failed" in message.lower():
            raise HTTPException(
                401,
                "Razorpay authentication failed. The backend is still using an old or mismatched Razorpay key/secret pair. "
                "Update RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET in backend .env or the server container environment, then restart the backend.",
            )
        if exc.code == 400:
            raise HTTPException(400, f"Razorpay rejected the order request. {message}")
        raise HTTPException(500, f"Razorpay order creation failed. {message}")
    except urllib_error.URLError as exc:
        raise HTTPException(500, f"Could not connect to Razorpay: {exc.reason}")


async def create_razorpay_order(key_id: str, key_secret: str, payload: dict) -> dict:
    return await asyncio.to_thread(create_razorpay_order_sync, key_id, key_secret, payload)


def verify_razorpay_signature(order_id: str, payment_id: str, signature: str, key_secret: str) -> bool:
    expected = hmac.new(
        key_secret.encode("utf-8"),
        f"{order_id}|{payment_id}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


async def credit_admin_wallet(db: AsyncSession, txn_type: str, amount: Decimal, booking_id: str, source_tailor_id=None, source_customer_id=None) -> None:
    if amount <= 0:
        return
    existing = await fetch_one(
        db,
        "SELECT 1 FROM admin_wallet_transactions WHERE source_booking_id=:booking_id AND type=CAST(:type AS admin_wallet_transaction_type) LIMIT 1",
        {"booking_id": booking_id, "type": txn_type},
    )
    if existing:
        return
    wallet = await ensure_admin_wallet(db)
    await db.execute(
        text("UPDATE admin_wallet SET balance=balance + :amount, updated_at=now() WHERE wallet_id=:wallet_id"),
        {"amount": amount, "wallet_id": wallet["wallet_id"]},
    )
    await db.execute(
        text(
            """
            INSERT INTO admin_wallet_transactions
              (id,type,amount,source_booking_id,source_tailor_id,source_customer_id,created_at)
            VALUES
              (gen_random_uuid(),CAST(:type AS admin_wallet_transaction_type),:amount,:booking_id,:tailor_id,:customer_id,now())
            """
        ),
        {
            "type": txn_type,
            "amount": amount,
            "booking_id": booking_id,
            "tailor_id": source_tailor_id,
            "customer_id": source_customer_id,
        },
    )


async def apply_completion_commission(db: AsyncSession, order: dict) -> Decimal:
    tailor_uuid = order.get("tailor_uuid")
    if not tailor_uuid:
        tailor_row = await fetch_one(
            db,
            "SELECT t.tailor_id AS tailor_uuid FROM orders o JOIN tailors t ON t.id=o.tailor_id WHERE o.id=:id",
            {"id": order["id"]},
        )
        tailor_uuid = tailor_row["tailor_uuid"] if tailor_row else None
    if not tailor_uuid:
        raise HTTPException(500, "Tailor wallet reference missing for commission")
    if money_decimal(order.get("commission_amount")) > 0:
        return money_decimal(order.get("commission_amount"))
    existing = await fetch_one(
        db,
        "SELECT amount FROM admin_wallet_transactions WHERE source_booking_id=:booking_id AND type='commission' LIMIT 1",
        {"booking_id": order["id"]},
    )
    if existing:
        amount = money_decimal(existing["amount"])
        await db.execute(text("UPDATE orders SET commission_amount=:amount WHERE id=:id"), {"amount": amount, "id": order["id"]})
        return amount
    settings = await platform_settings(db)
    commission = percent_amount(order.get("total") or order.get("base_price") or 0, settings.get("commission_percentage"))
    if commission <= 0:
        await db.execute(text("UPDATE orders SET commission_amount=0 WHERE id=:id"), {"id": order["id"]})
        return Decimal("0.00")
    tailor_wallet = await ensure_tailor_wallet(db, tailor_uuid)
    await db.execute(
        text("UPDATE tailor_wallets SET balance=balance - :amount, updated_at=now() WHERE wallet_id=:wallet_id"),
        {"amount": commission, "wallet_id": tailor_wallet["wallet_id"]},
    )
    await db.execute(
        text(
            """
            INSERT INTO wallet_transactions (id,wallet_id,type,amount,reference_booking_id,status)
            VALUES (gen_random_uuid(),:wallet_id,'debit',:amount,:booking_id,'success')
            """
        ),
        {"wallet_id": tailor_wallet["wallet_id"], "amount": commission, "booking_id": order["id"]},
    )
    await db.execute(text("UPDATE orders SET commission_amount=:amount WHERE id=:id"), {"amount": commission, "id": order["id"]})
    await credit_admin_wallet(db, "commission", commission, order["id"], source_tailor_id=tailor_uuid)
    return commission


def normalize_measurement_mode(value: str) -> str:
    cleaned = re.sub(r"[\s-]+", "_", (value or "").strip().lower())
    aliases = {
        "home": "tailor_visits_customer",
        "tailor_visits_customer": "tailor_visits_customer",
        "customer_home": "tailor_visits_customer",
        "shop": "customer_visits_tailor",
        "tailor_location": "customer_visits_tailor",
        "customer_visits_tailor": "customer_visits_tailor",
    }
    if cleaned not in aliases:
        raise HTTPException(400, "Measurement mode must be tailor_visits_customer or customer_visits_tailor")
    return aliases[cleaned]


async def notify(
    db: AsyncSession,
    to_ref: str,
    title: str,
    body: str,
    order_id: str | None = None,
    *,
    notification_type: str = "BOOKING_UPDATE",
    entity_type: str = "booking",
    entity_id: str | None = None,
    request_group_id: str | None = None,
    payment_id: str | None = None,
    dedupe_key: str | None = None,
) -> None:
    await db.execute(
        text("""INSERT INTO notifications
          (id,to_ref,channel,title,body,order_id,notification_type,entity_type,entity_id,
           request_group_id,booking_request_id,payment_id,dedupe_key)
          VALUES (:id,:to_ref,'in_app',:title,:body,:order_id,:notification_type,:entity_type,
                  :entity_id,:request_group_id,:booking_request_id,:payment_id,:dedupe_key)
          ON CONFLICT (to_ref,dedupe_key) WHERE dedupe_key IS NOT NULL DO NOTHING"""),
        {"id": uid("n"), "to_ref": to_ref, "title": title, "body": body, "order_id": order_id,
         "notification_type": notification_type, "entity_type": entity_type,
         "entity_id": entity_id or order_id, "request_group_id": request_group_id,
         "booking_request_id": order_id, "payment_id": payment_id, "dedupe_key": dedupe_key},
    )


async def add_history(db: AsyncSession, order_id: str, status: str, note: str, by_role: str) -> None:
    await db.execute(
        text("INSERT INTO order_status_history (order_id,status,note,by_role) VALUES (:order_id,:status,:note,:by_role)"),
        {"order_id": order_id, "status": status, "note": note, "by_role": by_role},
    )


async def release_capacity_and_promote(db: AsyncSession, order: dict) -> dict | None:
    """Release one automatic slot and atomically promote its oldest valid waiter."""
    if not order.get("appointment_date") or not order.get("appointment_slot"):
        return None
    released = await fetch_one(db, """UPDATE tailor_slot_capacities
        SET booked_count=GREATEST(booked_count-1,0),updated_at=now()
        WHERE tailor_id=:tailor_id AND slot_date=:slot_date AND slot_value=:slot_value
        RETURNING id,enabled,capacity,booked_count""", {
            "tailor_id": order["tailor_id"], "slot_date": order["appointment_date"], "slot_value": order["appointment_slot"]})
    if not released or not released.get("enabled") or int(released["booked_count"]) >= int(released["capacity"]):
        return None
    candidate = await fetch_one(db, """SELECT o.* FROM orders o
        JOIN booking_request_groups g ON g.id=o.request_group_id
        WHERE o.tailor_id=:tailor_id AND o.appointment_date=:slot_date AND o.appointment_slot=:slot_value
          AND upper(o.status) IN ('WAITLISTED','WAITING_LIST') AND g.assigned_tailor_id IS NULL
          AND o.measurement_cutoff >= now() AND o.measurement_appointment_at > now()
        ORDER BY o.ts ASC FOR UPDATE OF o SKIP LOCKED LIMIT 1""", {
            "tailor_id": order["tailor_id"], "slot_date": order["appointment_date"], "slot_value": order["appointment_slot"]})
    if not candidate:
        return None
    won = await fetch_one(db, """UPDATE booking_request_groups SET status='ASSIGNED',assigned_tailor_id=:tailor_id,
        assigned_order_id=:order_id,assigned_at=now() WHERE id=:group_id AND assigned_tailor_id IS NULL RETURNING id""", {
            "tailor_id": candidate["tailor_id"], "order_id": candidate["id"], "group_id": candidate["request_group_id"]})
    if not won:
        return None
    capacity = await fetch_one(db, """UPDATE tailor_slot_capacities SET booked_count=booked_count+1,updated_at=now()
        WHERE id=:id AND enabled=TRUE AND booked_count < capacity RETURNING id""", {"id": released["id"]})
    if not capacity:
        return None
    await db.execute(text("UPDATE orders SET status='AUTO_APPROVED',status_reason=NULL,assigned_at=now() WHERE id=:id"), {"id": candidate["id"]})
    await add_history(db, candidate["id"], "AUTO_APPROVED", "Promoted from the waiting list after capacity became available", "system")
    await notify(db, "user:" + candidate["customer_id"], "Booking promoted from waiting list",
                 f"Booking {candidate['code']} is now approved.", candidate["id"],
                 notification_type="WAITLIST_PROMOTED", dedupe_key="waitlist-promoted:" + candidate["id"])
    return candidate


async def ensure_measurement_visit_schema(db: AsyncSession) -> None:
    await db.execute(
        text(
            """
            DO $$ BEGIN
              CREATE TYPE otp_purpose AS ENUM (
                'registration_phone',
                'registration_email',
                'login',
                'forgot_password',
                'delivery',
                'withdrawal',
                'measurement_arrival'
              );
            EXCEPTION WHEN duplicate_object THEN NULL;
            END $$;
            """
        )
    )
    await db.execute(text("ALTER TYPE otp_purpose ADD VALUE IF NOT EXISTS 'delivery'"))
    await db.execute(text("ALTER TYPE otp_purpose ADD VALUE IF NOT EXISTS 'withdrawal'"))
    await db.execute(text("ALTER TYPE otp_purpose ADD VALUE IF NOT EXISTS 'measurement_arrival'"))
    await db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS otp_verifications (
              id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
              target VARCHAR(255) NOT NULL,
              otp_hash VARCHAR(255) NOT NULL,
              purpose otp_purpose NOT NULL,
              expires_at TIMESTAMPTZ NOT NULL,
              verified BOOLEAN NOT NULL DEFAULT FALSE,
              attempt_count INTEGER NOT NULL DEFAULT 0,
              created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
    )
    await db.execute(text("ALTER TABLE otp_verifications ADD COLUMN IF NOT EXISTS attempt_count INTEGER NOT NULL DEFAULT 0"))
    await db.execute(text("ALTER TABLE otp_verifications ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT now()"))
    await db.execute(text("CREATE INDEX IF NOT EXISTS otp_verifications_target_idx ON otp_verifications(target, purpose, expires_at DESC)"))
    await db.commit()

    await db.execute(text("ALTER TABLE tailors ADD COLUMN IF NOT EXISTS owner_name TEXT"))
    await db.execute(text("ALTER TABLE tailors ADD COLUMN IF NOT EXISTS shop_address TEXT"))
    await db.execute(text("ALTER TABLE tailors ADD COLUMN IF NOT EXISTS lat NUMERIC(10,7)"))
    await db.execute(text("ALTER TABLE tailors ADD COLUMN IF NOT EXISTS lng NUMERIC(10,7)"))
    await db.execute(text("ALTER TABLE orders ADD COLUMN IF NOT EXISTS measurement_mode TEXT"))
    await db.execute(text("ALTER TABLE orders ADD COLUMN IF NOT EXISTS customer_location_address TEXT"))
    await db.execute(text("ALTER TABLE orders ADD COLUMN IF NOT EXISTS customer_location_lat NUMERIC(10,7)"))
    await db.execute(text("ALTER TABLE orders ADD COLUMN IF NOT EXISTS customer_location_lng NUMERIC(10,7)"))
    await db.execute(text("ALTER TABLE orders ADD COLUMN IF NOT EXISTS customer_location_confirmed_at TIMESTAMPTZ"))
    await db.execute(text("ALTER TABLE orders ADD COLUMN IF NOT EXISTS measurement_trip_status TEXT NOT NULL DEFAULT 'not_started'"))
    await db.execute(text("ALTER TABLE orders ADD COLUMN IF NOT EXISTS tailor_trip_lat NUMERIC(10,7)"))
    await db.execute(text("ALTER TABLE orders ADD COLUMN IF NOT EXISTS tailor_trip_lng NUMERIC(10,7)"))
    await db.execute(text("ALTER TABLE orders ADD COLUMN IF NOT EXISTS tailor_trip_updated_at TIMESTAMPTZ"))
    await db.execute(text("ALTER TABLE orders ADD COLUMN IF NOT EXISTS tailor_started_at TIMESTAMPTZ"))
    await db.execute(text("ALTER TABLE orders ADD COLUMN IF NOT EXISTS tailor_arrived_at TIMESTAMPTZ"))
    await db.execute(text("ALTER TABLE orders ADD COLUMN IF NOT EXISTS measurement_otp_sent_at TIMESTAMPTZ"))
    await db.execute(text("ALTER TABLE orders ADD COLUMN IF NOT EXISTS measurement_otp_verified_at TIMESTAMPTZ"))
    await db.commit()


_uncached_ensure_measurement_visit_schema = ensure_measurement_visit_schema
_measurement_visit_schema_ready = False
_measurement_visit_schema_lock = asyncio.Lock()


async def ensure_measurement_visit_schema(db: AsyncSession) -> None:
    global _measurement_visit_schema_ready
    if _measurement_visit_schema_ready:
        return
    async with _measurement_visit_schema_lock:
        if _measurement_visit_schema_ready:
            return
        try:
            await _uncached_ensure_measurement_visit_schema(db)
            _measurement_visit_schema_ready = True
        except Exception:
            await db.rollback()
            logger.exception("Measurement visit schema setup failed")
            raise


BOOKING_DETAIL_SELECT = """
    SELECT o.*,
           t.shop,
           t.owner_name AS tailor_owner_name,
           t.shop_address AS tailor_location_address,
           t.lat AS tailor_lat,
           t.lng AS tailor_lng,
           t.user_id AS tailor_user_id,
           cu.name AS customer_name,
           cu.phone AS customer_phone,
           cu.email AS customer_email,
           tu.name AS tailor_user_name,
           tu.phone AS tailor_phone,
           tu.email AS tailor_email,
           g.assigned_order_id
    FROM orders o
    JOIN tailors t ON t.id=o.tailor_id
    JOIN users cu ON cu.id=o.customer_id
    LEFT JOIN users tu ON tu.id=t.user_id
    LEFT JOIN booking_request_groups g ON g.id=o.request_group_id
"""


async def fetch_booking_detail(
    db: AsyncSession,
    booking_id: str,
    extra_where: str = "",
    params: dict | None = None,
    for_update: bool = False,
) -> dict | None:
    sql = BOOKING_DETAIL_SELECT + " WHERE o.id=:id " + extra_where
    if for_update:
        sql += " FOR UPDATE OF o"
    return await fetch_one(db, sql, {"id": booking_id, **(params or {})})


def google_maps_search_url(lat, lng, address: str | None = None) -> str | None:
    if lat is not None and lng is not None:
        return "https://www.google.com/maps/search/?api=1&query=" + quote_plus(f"{float(lat):.7f},{float(lng):.7f}")
    if address:
        return "https://www.google.com/maps/search/?api=1&query=" + quote_plus(address)
    return None


def google_maps_directions_url(destination_lat, destination_lng, destination_address: str | None = None, origin_lat=None, origin_lng=None) -> str | None:
    destination = None
    if destination_lat is not None and destination_lng is not None:
        destination = f"{float(destination_lat):.7f},{float(destination_lng):.7f}"
    elif destination_address:
        destination = destination_address
    if not destination:
        return None
    url = "https://www.google.com/maps/dir/?api=1&travelmode=driving&destination=" + quote_plus(destination)
    if origin_lat is not None and origin_lng is not None:
        url += "&origin=" + quote_plus(f"{float(origin_lat):.7f},{float(origin_lng):.7f}")
    return url


def is_home_measurement_visit(order: dict) -> bool:
    try:
        return normalize_measurement_mode(order.get("measurement_mode")) == "tailor_visits_customer"
    except HTTPException:
        return False


def measurement_visit_needs_otp(order: dict) -> bool:
    return is_home_measurement_visit(order) and not bool(order.get("measurement_otp_verified_at"))


def clean_trip_coordinates(body: MeasurementTripLocationIn) -> dict:
    if (body.latitude is None) != (body.longitude is None):
        raise HTTPException(400, "Send both latitude and longitude when sharing live location.")
    return {"lat": body.latitude, "lng": body.longitude}


ACTIVE_CONTACT_STATUSES = {
    "AUTO_APPROVED", "CONFIRMED", "ASSIGNED", "TAILOR_CONFIRMED",
    "MEASUREMENT_PENDING", "MEASUREMENT_DONE", "IN_PROGRESS",
    "READY_FOR_DELIVERY", "OUT_FOR_DELIVERY", "PAYMENT_PENDING", "PAID",
}


def public_booking(row: dict, viewer: dict | None = None) -> dict:
    service_amount = money_decimal(row.get("base_price") or row.get("total") or 0)
    order_amount = money_decimal(row.get("total") or service_amount)
    travel_charge_amount = max(order_amount - service_amount, Decimal("0.00"))
    customer_location_lat = row.get("customer_location_lat")
    customer_location_lng = row.get("customer_location_lng")
    tailor_trip_lat = row.get("tailor_trip_lat")
    tailor_trip_lng = row.get("tailor_trip_lng")
    tailor_lat = row.get("tailor_lat")
    tailor_lng = row.get("tailor_lng")
    route_origin_lat = tailor_trip_lat if tailor_trip_lat is not None else tailor_lat
    route_origin_lng = tailor_trip_lng if tailor_trip_lng is not None else tailor_lng
    roles = set((viewer or {}).get("roles") or [])
    viewer_id = (viewer or {}).get("id")
    status = str(row.get("status") or "").upper()
    assigned = bool(row.get("assigned_at")) or status in ACTIVE_CONTACT_STATUSES
    group_winner = not row.get("request_group_id") or str(row.get("assigned_order_id") or row.get("id")) == str(row.get("id"))
    contact_active = assigned and group_winner and status in ACTIVE_CONTACT_STATUSES
    customer_authorized = contact_active and "customer" in roles and str(viewer_id) == str(row.get("customer_id"))
    tailor_authorized = contact_active and "tailor" in roles and str((viewer or {}).get("tailor_id") or "") == str(row.get("tailor_id"))
    return {
        "id": row["id"],
        "code": row["code"],
        "tailorId": row.get("tailor_id"),
        "tailorName": row.get("shop"),
        "tailorOwnerName": row.get("tailor_owner_name") or row.get("tailor_user_name"),
        "tailorPhone": row.get("tailor_phone") if customer_authorized else None,
        "tailorEmail": row.get("tailor_email") if customer_authorized else None,
        "tailorLocationAddress": row.get("tailor_location_address") if customer_authorized else None,
        "tailorLat": float(tailor_lat) if customer_authorized and tailor_lat is not None else None,
        "tailorLng": float(tailor_lng) if customer_authorized and tailor_lng is not None else None,
        "customerId": row.get("customer_id"),
        "customerName": row.get("customer_name"),
        "customerPhone": row.get("customer_phone") if tailor_authorized else None,
        "customerEmail": row.get("customer_email") if tailor_authorized else None,
        "serviceId": row.get("service_id"),
        "serviceName": row.get("service_name"),
        "quantity": row.get("quantity"),
        "status": row.get("status"),
        "paymentStatus": row.get("payment_status"),
        "payment_status": row.get("payment_status"),
        "trackerStage": row.get("tracker_stage"),
        "tracker_stage": row.get("tracker_stage"),
        "otpVerified": bool(row.get("otp_verified")),
        "otp_verified": bool(row.get("otp_verified")),
        "rated": bool(row.get("rated")),
        "disputeRaised": bool(row.get("dispute_raised")),
        "dispute_raised": bool(row.get("dispute_raised")),
        "deliveredAt": row.get("delivered_at"),
        "completedAt": row.get("completed_at"),
        "measurementMode": row.get("measurement_mode"),
        "customerLocationAddress": row.get("customer_location_address") if tailor_authorized else None,
        "customerLocationLat": float(customer_location_lat) if tailor_authorized and customer_location_lat is not None else None,
        "customerLocationLng": float(customer_location_lng) if tailor_authorized and customer_location_lng is not None else None,
        "customerLocationConfirmedAt": row.get("customer_location_confirmed_at"),
        "measurementTripStatus": row.get("measurement_trip_status") or "not_started",
        "tailorTripLat": float(tailor_trip_lat) if tailor_trip_lat is not None else None,
        "tailorTripLng": float(tailor_trip_lng) if tailor_trip_lng is not None else None,
        "tailorTripUpdatedAt": row.get("tailor_trip_updated_at"),
        "tailorStartedAt": row.get("tailor_started_at"),
        "tailorArrivedAt": row.get("tailor_arrived_at"),
        "measurementOtpSentAt": row.get("measurement_otp_sent_at"),
        "measurementOtpVerifiedAt": row.get("measurement_otp_verified_at"),
        "measurementOtpRequired": measurement_visit_needs_otp(row),
        "customerMapUrl": google_maps_search_url(customer_location_lat, customer_location_lng, row.get("customer_location_address") or row.get("address")) if tailor_authorized else None,
        "customerDirectionsUrl": google_maps_directions_url(customer_location_lat, customer_location_lng, row.get("customer_location_address") or row.get("address"), route_origin_lat, route_origin_lng) if tailor_authorized else None,
        "tailorMapUrl": google_maps_search_url(route_origin_lat, route_origin_lng, row.get("tailor_location_address")) if customer_authorized else None,
        "tailorDirectionsUrl": google_maps_directions_url(route_origin_lat, route_origin_lng, row.get("tailor_location_address")) if customer_authorized else None,
        "address": row.get("address") if tailor_authorized else None,
        "contactSharingActive": contact_active,
        "appointmentDate": row.get("appointment_date"),
        "appointmentSlot": row.get("appointment_slot"),
        "expectedCompletion": row.get("expected_completion"),
        "requestGroupId": row.get("request_group_id"),
        "statusReason": row.get("status_reason"),
        "expiresAt": row.get("expires_at"),
        "urgentDays": row.get("urgent_days"),
        "totalGarmentQuantity": row.get("total_garment_quantity") or row.get("quantity"),
        "urgentCharge": money_decimal(row.get("urgent_charge")),
        "finalAmount": money_decimal(row.get("final_amount") or order_amount),
        "priceSnapshot": row.get("price_snapshot") or {},
        "deliveryDeadline": row.get("delivery_deadline"),
        "measurementCutoff": row.get("measurement_cutoff"),
        "basePrice": service_amount,
        "base_price": service_amount,
        "serviceAmount": service_amount,
        "service_amount": service_amount,
        "travelChargeAmount": travel_charge_amount,
        "travel_charge_amount": travel_charge_amount,
        "travelRatePerKm": TRAVEL_CHARGE_PER_KM,
        "travel_rate_per_km": TRAVEL_CHARGE_PER_KM,
        "total": order_amount,
        "orderAmount": order_amount,
        "commissionAmount": row.get("commission_amount") or 0,
        "commission_amount": row.get("commission_amount") or 0,
        "gstPlatformChargeAmount": row.get("gst_platform_charge_amount") or 0,
        "gst_platform_charge_amount": row.get("gst_platform_charge_amount") or 0,
        "payableTotal": order_amount + money_decimal(row.get("gst_platform_charge_amount")),
        "notes": row.get("notes"),
        "cancelReason": row.get("cancel_reason"),
        "cancel_reason": row.get("cancel_reason"),
        "canCustomerManage": customer_manage_cutoff_error(row) is None,
        "customerManageBlockedReason": customer_manage_cutoff_error(row),
        "ts": row.get("ts"),
    }


async def get_accessible_order(db: AsyncSession, booking_id: str, user: dict) -> dict:
    await ensure_measurement_visit_schema(db)
    roles = user.get("roles") or []
    if "tailor" in roles:
        order = await fetch_booking_detail(
            db,
            booking_id,
            "AND t.user_id=:user_id",
            {"id": booking_id, "user_id": user["id"]},
        )
        if order:
            return order
    if "customer" in roles:
        order = await fetch_booking_detail(
            db,
            booking_id,
            "AND o.customer_id=:user_id",
            {"id": booking_id, "user_id": user["id"]},
        )
        if order:
            return order
    raise HTTPException(404, "Booking not found")


async def tracker_status_payload(db: AsyncSession, order: dict, viewer: dict | None = None) -> dict:
    result = await db.execute(
        text(
            """
            SELECT status, note, by_role, ts
            FROM order_status_history
            WHERE order_id=:order_id
            ORDER BY ts ASC
            LIMIT 500
            """
        ),
        {"order_id": order["id"]},
    )
    history = [dict(row) for row in result.mappings().all()]
    current_stage = order.get("tracker_stage") or "Order Placed"
    if current_stage not in TRACKER_STAGES:
        current_stage = "Order Placed"
    current_index = TRACKER_STAGES.index(current_stage)
    timestamps = {}
    for row in history:
        status = row.get("status")
        if status in TRACKER_STAGES and status not in timestamps:
            timestamps[status] = row.get("ts")
    if "Order Placed" not in timestamps:
        timestamps["Order Placed"] = order.get("ts")
    steps = []
    for index, stage in enumerate(TRACKER_STAGES):
        timestamp = timestamps.get(stage)
        steps.append(
            {
                "stage": stage,
                "completed": index < current_index or (stage == "Delivered" and bool(order.get("delivered_at"))),
                "current": index == current_index and not bool(order.get("delivered_at") and stage == "Delivered"),
                "timestamp": timestamp,
            }
        )
    payment_intent = await latest_payment_intent(db, order["id"])
    return {
        "booking": public_booking(order, viewer),
        "trackerStage": current_stage,
        "tracker_stage": current_stage,
        "steps": steps,
        "history": history,
        "paymentStatus": order.get("payment_status"),
        "otpEnabled": str(order.get("payment_status") or "").lower() == "paid",
        "paymentIntent": payment_intent_payload(payment_intent),
        "payment_intent": payment_intent_payload(payment_intent),
    }


def dispute_payload(row: dict) -> dict:
    dispute_id = str(row["id"])
    photo_url = get_media_storage().download_url(row.get("photo_url"))
    return {
        "id": dispute_id,
        "booking_id": row.get("booking_id"),
        "bookingId": row.get("booking_id"),
        "customer_id": row.get("customer_id"),
        "customerId": row.get("customer_id"),
        "reason": row.get("reason"),
        "photo_url": photo_url,
        "photoUrl": photo_url,
        "photo_name": row.get("photo_name"),
        "photoName": row.get("photo_name"),
        "photo_media_type": row.get("photo_media_type"),
        "photoMediaType": row.get("photo_media_type"),
        "status": row.get("status"),
        "resolution_notes": row.get("resolution_notes"),
        "resolutionNotes": row.get("resolution_notes"),
        "refund_amount": row.get("refund_amount") or 0,
        "refundAmount": row.get("refund_amount") or 0,
        "created_at": row.get("created_at"),
        "createdAt": row.get("created_at"),
        "resolved_at": row.get("resolved_at"),
        "resolvedAt": row.get("resolved_at"),
    }


async def broadcast_status(db: AsyncSession, booking_id: str) -> None:
    order = await fetch_booking_detail(db, booking_id)
    if order:
        await tracker_connections.broadcast(booking_id, jsonable_encoder(await tracker_status_payload(db, order)))


@router.get("/scaffold")
async def bookings_scaffold() -> dict:
    return {"module": "bookings", "ready": True}


@router.get("/availability")
async def booking_slot_availability(
    tailorId: str,
    slotDate: date,
    customer: dict = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db),
) -> dict:
    now = datetime.now(APP_TIMEZONE)
    if slotDate < now.date():
        raise HTTPException(400, PAST_APPOINTMENT_DATE_ERROR)
    tailor = await fetch_one(db, "SELECT id,approval_mode,available_slots,is_available,availability FROM tailors WHERE id=:id AND deleted_at IS NULL", {"id": tailorId})
    if not tailor:
        raise HTTPException(404, "Tailor is not available")
    rows = (await db.execute(text("""SELECT slot_value,enabled,capacity,booked_count
        FROM tailor_slot_capacities WHERE tailor_id=:tailor_id AND slot_date=:slot_date"""),
        {"tailor_id": tailor["id"], "slot_date": slotDate})).mappings().all()
    configured = {row["slot_value"]: dict(row) for row in rows}
    default_capacity = max(int(tailor.get("available_slots") or 1), 1)
    tailor_available = bool(tailor.get("is_available")) and tailor.get("availability") not in {"BUSY", "NOT_AVAILABLE"}
    slots = []
    for value, start_minutes in APPOINTMENT_SLOTS.items():
        row = configured.get(value)
        expired = slotDate == now.date() and start_minutes <= now.hour * 60 + now.minute
        if str(tailor.get("approval_mode") or "AUTOMATIC").upper() == "AUTOMATIC":
            enabled = bool(tailor_available and (not row or (row["enabled"] and int(row["booked_count"]) < int(row["capacity"]))))
        else:
            enabled = bool(row["enabled"]) if row else True
        slots.append({"slot": value, "available": enabled and not expired, "expired": expired,
                      "remaining": max(int(row["capacity"]) - int(row["booked_count"]), 0) if row else default_capacity})
    return {"tailorId": tailor["id"], "slotDate": slotDate, "timezone": "Asia/Kolkata", "slots": slots}


@router.post("/preview")
async def preview_booking(
    body: BookingCreateIn,
    customer: dict = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Validate a booking and return an authoritative, non-mutating summary."""
    measurement_mode = normalize_measurement_mode(body.measurement_mode)
    if measurement_mode == "tailor_visits_customer" and (
        not body.customer_location_address
        or body.customer_location_lat is None
        or body.customer_location_lng is None
    ):
        raise HTTPException(400, "Confirm your home location before booking")

    tailor = await fetch_one(db, """
        SELECT t.*, u.email AS tailor_email
        FROM tailors t JOIN users u ON u.id=t.user_id
        WHERE (t.id=:tailor_id OR t.tailor_id::text=:tailor_id)
          AND t.deleted_at IS NULL AND t.account_status='ACTIVE'
          AND t.status='active' AND t.approval_status='APPROVED' AND t.aadhaar_verified=TRUE
        LIMIT 1
    """, {"tailor_id": body.tailor_id})
    if not tailor:
        raise HTTPException(404, "Tailor is not available for booking")

    service = await fetch_one(db, """
        SELECT * FROM tailor_services
        WHERE tailor_id=:tailor_pk AND (id=:service_id OR service_id::text=:service_id)
          AND COALESCE(is_active, active)=TRUE LIMIT 1
    """, {"tailor_pk": tailor["id"], "service_id": body.service_id})
    if not service:
        raise HTTPException(404, "Selected service is not available")

    expected, appointment_date = resolve_booking_dates(body.preferred_date, body.appointment_date, service.get("days"))
    appointment_slot = validate_appointment_slot(appointment_date, body.appointment_slot)
    try:
        calculation = calculate_booking(
            unit_price=service["price"], service_quantity=body.quantity or 1,
            is_combo=bool(service.get("is_combo")), combo_items=service.get("combo_items"),
            urgent_days=body.urgent_days, delivery_date=expected,
            appointment_date=appointment_date, appointment_slot=appointment_slot,
        )
    except BookingRuleError as exc:
        raise HTTPException(400, str(exc)) from exc

    slot = await fetch_one(db, """SELECT enabled,capacity,booked_count FROM tailor_slot_capacities
        WHERE tailor_id=:tailor_id AND slot_date=:slot_date AND slot_value=:slot_value""",
        {"tailor_id": tailor["id"], "slot_date": appointment_date, "slot_value": appointment_slot})
    if slot and not slot.get("enabled"):
        raise HTTPException(409, "The selected measurement slot is unavailable.")
    approval_mode = str(tailor.get("approval_mode") or "AUTOMATIC").upper()
    available = bool(tailor.get("is_available")) and tailor.get("availability") not in {"BUSY", "NOT_AVAILABLE"}
    slot_available = available and (not slot or int(slot.get("booked_count") or 0) < int(slot.get("capacity") or 0))
    if approval_mode == "MANUAL":
        conflict = await fetch_one(db, """SELECT id FROM orders WHERE tailor_id=:tailor_id
            AND appointment_date=:slot_date AND appointment_slot=:slot_value
            AND upper(status) IN ('AUTO_APPROVED','CONFIRMED','ASSIGNED','MEASUREMENT_PENDING','MEASUREMENT_DONE','IN_PROGRESS') LIMIT 1""",
            {"tailor_id": tailor["id"], "slot_date": appointment_date, "slot_value": appointment_slot})
        if conflict:
            raise HTTPException(409, "The selected measurement slot is already assigned.")
        slot_available = True

    address = body.customer_location_address if measurement_mode == "tailor_visits_customer" else tailor.get("shop_address")
    return {
        "valid": True,
        "tailor": {"id": tailor["id"], "shop": tailor.get("shop"), "ownerName": tailor.get("owner_name"), "phone": tailor.get("phone"), "address": tailor.get("shop_address")},
        "service": {"id": service["id"], "name": service.get("service_name") or service.get("name"), "unitPrice": str(calculation.unit_price), "isCombo": bool(service.get("is_combo")), "comboItems": service.get("combo_items") or []},
        "customer": {"id": customer.get("id"), "name": customer.get("name") or customer.get("full_name"), "email": customer.get("email"), "phone": customer.get("phone")},
        "quantity": body.quantity or 1,
        "requirements": body.requirements,
        "instructions": body.instructions,
        "measurementMode": measurement_mode,
        "appointmentDate": appointment_date,
        "appointmentSlot": appointment_slot,
        "expectedDeliveryDate": expected,
        "address": address,
        "location": {"latitude": body.customer_location_lat, "longitude": body.customer_location_lng} if measurement_mode == "tailor_visits_customer" else None,
        "urgentDays": calculation.urgent_days,
        "price": {"baseAmount": str(calculation.base_amount), "urgentCharge": str(calculation.urgent_charge), "totalGarments": calculation.total_garment_quantity, "finalAmount": str(calculation.final_amount)},
        "slotAvailable": slot_available,
        "expectedStatus": "PENDING_APPROVAL" if approval_mode == "MANUAL" else "AUTO_APPROVED" if slot_available else "WAITLISTED",
        "validatedAt": datetime.now(APP_TIMEZONE).isoformat(),
    }


@router.post("")
async def create_booking(
    body: BookingCreateIn,
    customer: dict = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db),
) -> dict:
    await ensure_measurement_visit_schema(db)
    if body.idempotency_key:
        await db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:key))"), {"key": f"{customer['id']}:{body.idempotency_key}"})
        existing = await fetch_one(db, "SELECT id,code,status FROM orders WHERE customer_id=:customer_id AND client_request_id=:key LIMIT 1", {"customer_id": customer["id"], "key": body.idempotency_key})
        if existing:
            detail = await fetch_booking_detail(db, existing["id"])
            return {"booking": public_booking(detail, {"id": customer["id"], "roles": ["customer"]}), "code": existing["code"], "status": existing["status"], "message": f"Booking {existing['code']} was already submitted.", "duplicate": True}
    measurement_mode = normalize_measurement_mode(body.measurement_mode)
    if measurement_mode == "tailor_visits_customer":
        if not body.customer_location_address or body.customer_location_lat is None or body.customer_location_lng is None:
            raise HTTPException(400, "Confirm your home location before booking")

    tailor = await fetch_one(
        db,
        """
        SELECT t.*, u.email AS tailor_email
        FROM tailors t
        JOIN users u ON u.id=t.user_id
        WHERE (t.id=:tailor_id OR t.tailor_id::text=:tailor_id)
          AND t.deleted_at IS NULL
          AND t.account_status='ACTIVE'
          AND t.status='active'
          AND t.approval_status='APPROVED'
          AND t.aadhaar_verified=TRUE
        LIMIT 1
        """,
        {"tailor_id": body.tailor_id},
    )
    if not tailor:
        raise HTTPException(404, "Tailor is not available for booking")

    service = await fetch_one(
        db,
        """
        SELECT *
        FROM tailor_services
        WHERE tailor_id=:tailor_pk
          AND (id=:service_id OR service_id::text=:service_id)
          AND COALESCE(is_active, active)=TRUE
        LIMIT 1
        """,
        {"tailor_pk": tailor["id"], "service_id": body.service_id},
    )
    if not service:
        raise HTTPException(404, "Selected service is not available")

    approval_mode = str(tailor.get("approval_mode") or "AUTOMATIC").upper()
    available = bool(tailor.get("is_available")) and tailor.get("availability") not in {"BUSY", "NOT_AVAILABLE"}
    order_id = uid("ord")
    request_group_id = uid("grp")
    code_row = await fetch_one(db, "SELECT 'ORD-' || nextval('order_code_seq') AS code")
    code = code_row["code"]
    quantity = body.quantity or 1
    expected, appointment_date = resolve_booking_dates(body.preferred_date, body.appointment_date, service.get("days"))
    appointment_slot = validate_appointment_slot(appointment_date, body.appointment_slot)
    try:
        calculation = calculate_booking(
            unit_price=service["price"],
            service_quantity=quantity,
            is_combo=bool(service.get("is_combo")),
            combo_items=service.get("combo_items"),
            urgent_days=body.urgent_days,
            delivery_date=expected,
            appointment_date=appointment_date,
            appointment_slot=appointment_slot,
        )
    except BookingRuleError as exc:
        raise HTTPException(400, str(exc)) from exc
    base_price = calculation.base_amount
    customer_address = body.customer_location_address if measurement_mode == "tailor_visits_customer" else tailor.get("shop_address")
    travel_distance_km = Decimal("0.00")
    travel_charge = Decimal("0.00")
    if measurement_mode == "tailor_visits_customer":
        travel_distance_km = distance_km_between(
            tailor.get("lat"),
            tailor.get("lng"),
            body.customer_location_lat,
            body.customer_location_lng,
        )
        travel_charge = travel_charge_for_distance(travel_distance_km)
    order_total = calculation.final_amount

    await db.execute(
        text("INSERT INTO booking_request_groups (id,customer_id,status) VALUES (:id,:customer_id,'UNASSIGNED')"),
        {"id": request_group_id, "customer_id": customer["id"]},
    )
    status = "PENDING_APPROVAL"
    status_reason = None
    expires_at = datetime.now(APP_TIMEZONE) + timedelta(hours=1) if approval_mode == "MANUAL" else None
    slot_configuration = await fetch_one(db, """SELECT * FROM tailor_slot_capacities
        WHERE tailor_id=:tailor_id AND slot_date=:slot_date AND slot_value=:slot_value FOR UPDATE""",
        {"tailor_id": tailor["id"], "slot_date": appointment_date, "slot_value": appointment_slot})
    if approval_mode == "AUTOMATIC" and available and not slot_configuration:
        await db.execute(text("""INSERT INTO tailor_slot_capacities
            (tailor_id,slot_date,slot_value,enabled,capacity,booked_count)
            VALUES (:tailor_id,:slot_date,:slot_value,TRUE,:capacity,0)
            ON CONFLICT (tailor_id,slot_date,slot_value) DO NOTHING"""),
            {"tailor_id": tailor["id"], "slot_date": appointment_date, "slot_value": appointment_slot,
             "capacity": max(int(tailor.get("available_slots") or 1), 1)})
        slot_configuration = await fetch_one(db, """SELECT * FROM tailor_slot_capacities
            WHERE tailor_id=:tailor_id AND slot_date=:slot_date AND slot_value=:slot_value FOR UPDATE""",
            {"tailor_id": tailor["id"], "slot_date": appointment_date, "slot_value": appointment_slot})
    if slot_configuration and not slot_configuration.get("enabled"):
        raise HTTPException(409, "The selected measurement slot is unavailable.")
    if approval_mode == "MANUAL":
        conflict = await fetch_one(db, """SELECT id FROM orders WHERE tailor_id=:tailor_id
            AND appointment_date=:slot_date AND appointment_slot=:slot_value
            AND upper(status) IN ('AUTO_APPROVED','CONFIRMED','ASSIGNED','MEASUREMENT_PENDING','MEASUREMENT_DONE','IN_PROGRESS') LIMIT 1""",
            {"tailor_id": tailor["id"], "slot_date": appointment_date, "slot_value": appointment_slot})
        if conflict:
            raise HTTPException(409, "The selected measurement slot is already assigned.")
    if approval_mode == "AUTOMATIC" and available and slot_configuration:
        capacity = await fetch_one(
            db,
            """UPDATE tailor_slot_capacities SET booked_count=booked_count+1,updated_at=now()
               WHERE tailor_id=:tailor_id AND slot_date=:slot_date AND slot_value=:slot_value
                 AND enabled=TRUE AND booked_count < capacity RETURNING id""",
            {"tailor_id": tailor["id"], "slot_date": appointment_date, "slot_value": appointment_slot},
        )
        if capacity:
            status = "AUTO_APPROVED"
            await db.execute(
                text("UPDATE booking_request_groups SET status='ASSIGNED',assigned_tailor_id=:tailor_id,assigned_order_id=:order_id,assigned_at=now() WHERE id=:id AND assigned_tailor_id IS NULL"),
                {"id": request_group_id, "tailor_id": tailor["id"], "order_id": order_id},
            )
        else:
            status, status_reason = "WAITLISTED", "CAPACITY_FULL"
    elif approval_mode == "AUTOMATIC":
        status, status_reason = "WAITLISTED", "CAPACITY_FULL"

    result = await db.execute(
        text(
            """
            INSERT INTO orders
              (id,code,customer_id,tailor_id,service_id,service_name,garment_id,quantity,status,status_reason,request_group_id,expires_at,
               base_price,total,base_amount,urgent_days,urgent_charge,final_amount,total_garment_quantity,price_snapshot,
               delivery_deadline,measurement_cutoff,measurement_appointment_at,assigned_at,
               measurement_mode,appointment_date,appointment_slot,address,expected_completion,notes,
               customer_location_address,customer_location_lat,customer_location_lng,customer_location_confirmed_at,tracker_stage,client_request_id)
            VALUES
              (:id,:code,:customer_id,:tailor_id,:service_id,:service_name,:garment_id,:quantity,:status,:status_reason,:request_group_id,:expires_at,
               :base_price,:total,:base_amount,:urgent_days,:urgent_charge,:final_amount,:total_garment_quantity,CAST(:price_snapshot AS jsonb),
               :delivery_deadline,:measurement_cutoff,:measurement_appointment_at,:assigned_at,
               :measurement_mode,:appointment_date,:appointment_slot,:address,:expected_completion,:notes,
               :customer_location_address,:customer_location_lat,:customer_location_lng,:customer_location_confirmed_at,'Order Placed',:client_request_id)
            RETURNING *
            """
        ),
        {
            "id": order_id,
            "code": code,
            "customer_id": customer["id"],
            "tailor_id": tailor["id"],
            "service_id": service["id"],
            "service_name": body.service_name or service.get("service_name") or service.get("name"),
            "garment_id": service.get("garment_id"),
            "quantity": quantity,
            "status": status,
            "status_reason": status_reason,
            "request_group_id": request_group_id,
            "expires_at": expires_at,
            "base_price": base_price,
            "total": order_total,
            "base_amount": calculation.base_amount,
            "urgent_days": calculation.urgent_days,
            "urgent_charge": calculation.urgent_charge,
            "final_amount": calculation.final_amount,
            "total_garment_quantity": calculation.total_garment_quantity,
            "price_snapshot": json.dumps({
                "serviceId": service["id"], "serviceName": service.get("service_name") or service.get("name"),
                "unitPrice": str(calculation.unit_price), "serviceQuantity": quantity,
                "garmentsPerService": calculation.garments_per_service, "totalGarments": calculation.total_garment_quantity,
                "isCombo": bool(service.get("is_combo")), "comboItems": service.get("combo_items") or [],
                "urgentDays": calculation.urgent_days, "urgentCharge": str(calculation.urgent_charge),
                "finalAmount": str(calculation.final_amount),
            }),
            "delivery_deadline": calculation.delivery_deadline,
            "measurement_cutoff": calculation.measurement_cutoff,
            "measurement_appointment_at": calculation.appointment_start,
            "assigned_at": datetime.now(APP_TIMEZONE) if status == "AUTO_APPROVED" else None,
            "measurement_mode": measurement_mode,
            "appointment_date": appointment_date,
            "appointment_slot": appointment_slot,
            "address": customer_address,
            "expected_completion": expected,
            "notes": body.instructions or body.requirements,
            "customer_location_address": body.customer_location_address if measurement_mode == "tailor_visits_customer" else None,
            "customer_location_lat": body.customer_location_lat if measurement_mode == "tailor_visits_customer" else None,
            "customer_location_lng": body.customer_location_lng if measurement_mode == "tailor_visits_customer" else None,
            "customer_location_confirmed_at": None,
            "client_request_id": body.idempotency_key,
        },
    )
    order = dict(result.mappings().first())
    if measurement_mode == "tailor_visits_customer":
        await db.execute(text("UPDATE orders SET customer_location_confirmed_at=now() WHERE id=:id"), {"id": order_id})
    await db.execute(
        text("INSERT INTO payments (id,order_id,amount,status) VALUES (:id,:order_id,:amount,'PENDING')"),
        {"id": uid("pay"), "order_id": order_id, "amount": order_total},
    )
    await add_history(
        db,
        order_id,
        status,
        "Booking auto-approved within configured capacity" if status == "AUTO_APPROVED" else "Waiting for tailor approval" if status == "PENDING_APPROVAL" else "Slot capacity is full",
        "system",
    )
    await add_history(db, order_id, "Order Placed", "Order placed by customer", "customer")
    await notify(
        db,
        "tailor:" + tailor["id"],
        "New TailoraHub booking" if status == "AUTO_APPROVED" else "Booking approval required" if status == "PENDING_APPROVAL" else "New waiting-list customer",
        f"A customer requested {service.get('service_name') or service.get('name')} ({code}). Open the request to review it.",
        order_id,
    )
    await notify(
        db,
        "user:" + customer["id"],
        "Booking auto-approved" if status == "AUTO_APPROVED" else "Waiting for tailor approval" if status == "PENDING_APPROVAL" else "You are on the waiting list",
        f"Booking {code} was created. Open the booking to see its current status.",
        order_id,
    )
    await db.commit()
    final = await fetch_booking_detail(db, order_id)
    return {
        "booking": public_booking(final, {"id": customer["id"], "roles": ["customer"]}),
        "code": code,
        "status": status,
        "message": "Booking auto-approved." if status == "auto_approved" else "Tailor is currently busy — you're on the waiting list.",
    }


@router.get("/{booking_id}/measurement-trip")
async def get_measurement_trip(
    booking_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    await ensure_measurement_visit_schema(db)
    order = await get_accessible_order(db, booking_id, user)
    viewer = {**user}
    if "tailor" in (user.get("roles") or []):
        viewer["tailor_id"] = order.get("tailor_id")
    return jsonable_encoder({"booking": public_booking(order, viewer)})


async def broadcast_measurement_trip(db: AsyncSession, booking_id: str, order: dict) -> None:
    payload = await tracker_status_payload(db, order)
    payload = {**payload, "type": "measurement_trip", "bookingId": booking_id}
    await tracker_connections.broadcast(booking_id, jsonable_encoder(payload))


@router.post("/{booking_id}/measurement-trip/start")
async def start_measurement_trip(
    booking_id: str,
    body: MeasurementTripLocationIn,
    tailor: dict = Depends(get_current_tailor),
    db: AsyncSession = Depends(get_db),
) -> dict:
    await ensure_measurement_visit_schema(db)
    coords = clean_trip_coordinates(body)
    order = await fetch_booking_detail(db, booking_id, "AND o.tailor_id=:tailor_id", {"tailor_id": tailor["id"]}, True)
    if not order:
        raise HTTPException(404, "Booking not found")
    if is_completed_order(order) or str(order.get("status") or "").lower() == "cancelled":
        raise HTTPException(409, "This order is closed. Visit tracking is unavailable.")
    if not is_home_measurement_visit(order):
        raise HTTPException(409, "Trip tracking is only for bookings where the tailor visits the customer.")
    if order.get("customer_location_lat") is None or order.get("customer_location_lng") is None:
        raise HTTPException(400, "Customer location is not confirmed for this booking.")
    if str(order.get("measurement_trip_status") or "not_started").lower() != "not_started":
        raise HTTPException(409, "This measurement visit is already started. Use live location updates instead.")

    try:
        code, _ = await issue_otp(db, booking_id, "measurement_arrival")
    except OtpFlowError as exc:
        raise HTTPException(exc.status_code, exc.message) from exc
    await db.execute(
        text(
            """
            UPDATE orders
            SET measurement_trip_status='en_route',
                tailor_started_at=COALESCE(tailor_started_at, now()),
                tailor_trip_lat=COALESCE(:lat, tailor_trip_lat),
                tailor_trip_lng=COALESCE(:lng, tailor_trip_lng),
                tailor_trip_updated_at=CASE WHEN :lat IS NULL OR :lng IS NULL THEN tailor_trip_updated_at ELSE now() END,
                measurement_otp_sent_at=now(),
                status=CASE WHEN status IN ('auto_approved','tailor_confirmed') THEN 'measurement_pending' ELSE status END,
                tracker_stage=CASE WHEN tracker_stage='Order Placed' THEN 'Measurement Scheduled' ELSE tracker_stage END
            WHERE id=:id
            """
        ),
        {"id": booking_id, "lat": coords["lat"], "lng": coords["lng"]},
    )
    await add_history(db, booking_id, "Measurement Scheduled", "Tailor started towards customer location", "tailor")
    customer_message = (
        f"TRHB: {tailor['shop']} started for order {order['code']}. "
        f"Share OTP {code} only after the tailor reaches your address. It is valid for {OTP_TTL_MINUTES} minutes."
    )
    await notify(db, "user:" + order["customer_id"], "TRHB measurement arrival OTP", customer_message, booking_id)
    if order.get("customer_email"):
        send_email(order["customer_email"], "TRHB measurement arrival OTP", customer_message)
    await db.commit()
    updated = await fetch_booking_detail(db, booking_id)
    await broadcast_measurement_trip(db, booking_id, updated)
    return jsonable_encoder({"booking": public_booking(updated), "message": "Visit started. Customer arrival OTP was sent."})


@router.post("/{booking_id}/measurement-trip/location")
async def update_measurement_trip_location(
    booking_id: str,
    body: MeasurementTripLocationIn,
    tailor: dict = Depends(get_current_tailor),
    db: AsyncSession = Depends(get_db),
) -> dict:
    await ensure_measurement_visit_schema(db)
    coords = clean_trip_coordinates(body)
    if coords["lat"] is None or coords["lng"] is None:
        raise HTTPException(400, "Share your current latitude and longitude.")
    order = await fetch_booking_detail(db, booking_id, "AND o.tailor_id=:tailor_id", {"tailor_id": tailor["id"]}, True)
    if not order:
        raise HTTPException(404, "Booking not found")
    if is_completed_order(order) or str(order.get("status") or "").lower() == "cancelled":
        raise HTTPException(409, "This order is closed. Location updates are unavailable.")
    if not is_home_measurement_visit(order):
        raise HTTPException(409, "Live location is only for tailor-visits-customer bookings.")
    if (order.get("measurement_trip_status") or "not_started") == "not_started":
        raise HTTPException(409, "Start the visit before sharing live location.")

    await db.execute(
        text(
            """
            UPDATE orders
            SET tailor_trip_lat=:lat,
                tailor_trip_lng=:lng,
                tailor_trip_updated_at=now()
            WHERE id=:id
            """
        ),
        {"id": booking_id, "lat": coords["lat"], "lng": coords["lng"]},
    )
    if body.announce:
        await notify(
            db,
            "user:" + order["customer_id"],
            "TRHB live location update",
            f"TRHB: {tailor['shop']} shared live location for order {order['code']}.",
            booking_id,
        )
    await db.commit()
    updated = await fetch_booking_detail(db, booking_id)
    await broadcast_measurement_trip(db, booking_id, updated)
    return jsonable_encoder({"booking": public_booking(updated), "message": "Live location shared with the customer."})


@router.post("/{booking_id}/measurement-trip/arrive")
async def arrive_measurement_trip(
    booking_id: str,
    body: MeasurementTripLocationIn,
    tailor: dict = Depends(get_current_tailor),
    db: AsyncSession = Depends(get_db),
) -> dict:
    await ensure_measurement_visit_schema(db)
    coords = clean_trip_coordinates(body)
    order = await fetch_booking_detail(db, booking_id, "AND o.tailor_id=:tailor_id", {"tailor_id": tailor["id"]}, True)
    if not order:
        raise HTTPException(404, "Booking not found")
    if is_completed_order(order) or str(order.get("status") or "").lower() == "cancelled":
        raise HTTPException(409, "This order is closed. Arrival updates are unavailable.")
    if not is_home_measurement_visit(order):
        raise HTTPException(409, "Arrival tracking is only for tailor-visits-customer bookings.")
    if (order.get("measurement_trip_status") or "not_started") == "not_started":
        raise HTTPException(409, "Start the visit before marking arrival.")

    await db.execute(
        text(
            """
            UPDATE orders
            SET measurement_trip_status='arrived',
                tailor_arrived_at=COALESCE(tailor_arrived_at, now()),
                tailor_trip_lat=COALESCE(:lat, tailor_trip_lat),
                tailor_trip_lng=COALESCE(:lng, tailor_trip_lng),
                tailor_trip_updated_at=CASE WHEN :lat IS NULL OR :lng IS NULL THEN tailor_trip_updated_at ELSE now() END
            WHERE id=:id
            """
        ),
        {"id": booking_id, "lat": coords["lat"], "lng": coords["lng"]},
    )
    await add_history(db, booking_id, "Tailor Arrived", "Tailor reached the customer address for measurement", "tailor")
    await notify(
        db,
        "user:" + order["customer_id"],
        "TRHB tailor reached your address",
        f"TRHB: {tailor['shop']} reached your address for order {order['code']}. Verify the arrival OTP before measurement.",
        booking_id,
    )
    await db.commit()
    updated = await fetch_booking_detail(db, booking_id)
    await broadcast_measurement_trip(db, booking_id, updated)
    return jsonable_encoder({"booking": public_booking(updated), "message": "Arrival marked. Verify the customer OTP before measurement."})


@router.post("/{booking_id}/measurement-trip/verify-otp")
async def verify_measurement_trip_otp(
    booking_id: str,
    body: MeasurementOtpVerifyIn,
    tailor: dict = Depends(get_current_tailor),
    db: AsyncSession = Depends(get_db),
) -> dict:
    await ensure_measurement_visit_schema(db)
    order = await fetch_booking_detail(db, booking_id, "AND o.tailor_id=:tailor_id", {"tailor_id": tailor["id"]}, True)
    if not order:
        raise HTTPException(404, "Booking not found")
    if is_completed_order(order) or str(order.get("status") or "").lower() == "cancelled":
        raise HTTPException(409, "This order is closed. Measurement OTP verification is unavailable.")
    if not is_home_measurement_visit(order):
        raise HTTPException(409, "Measurement arrival OTP is only for tailor-visits-customer bookings.")
    if (order.get("measurement_trip_status") or "not_started") == "not_started":
        raise HTTPException(409, "Start the visit before verifying the customer OTP.")

    try:
        matched = await verify_otp(db, booking_id, "measurement_arrival", body.otp)
    except OtpFlowError as exc:
        raise HTTPException(exc.status_code, exc.message) from exc
    if not matched:
        raise HTTPException(401, "Invalid or expired measurement arrival OTP.")

    await db.execute(
        text(
            """
            UPDATE orders
            SET measurement_trip_status='otp_verified',
                measurement_otp_verified_at=now()
            WHERE id=:id
            """
        ),
        {"id": booking_id},
    )
    await add_history(db, booking_id, "Measurement OTP Verified", "Customer verified tailor arrival before measurement", "tailor")
    await notify(
        db,
        "user:" + order["customer_id"],
        "TRHB measurement arrival verified",
        f"TRHB: Arrival OTP verified for order {order['code']}. Measurement can now begin.",
        booking_id,
    )
    await notify(
        db,
        "tailor:" + tailor["id"],
        "TRHB measurement OTP verified",
        f"TRHB: Customer verified arrival for order {order['code']}. You can take measurements now.",
        booking_id,
    )
    await db.commit()
    updated = await fetch_booking_detail(db, booking_id)
    await broadcast_measurement_trip(db, booking_id, updated)
    return jsonable_encoder({"booking": public_booking(updated), "message": "Measurement arrival OTP verified. Measurement can begin."})


@router.get("/{booking_id}/status")
async def booking_status(
    booking_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    order = await get_accessible_order(db, booking_id, user)
    viewer = {**user}
    if "tailor" in (user.get("roles") or []):
        viewer["tailor_id"] = order.get("tailor_id")
    return await tracker_status_payload(db, order, viewer)


@router.get("/{booking_id}/payment-breakdown")
async def booking_payment_breakdown(
    booking_id: str,
    customer: dict = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db),
) -> dict:
    order = await fetch_one(
        db,
        "SELECT o.*, t.shop FROM orders o JOIN tailors t ON t.id=o.tailor_id WHERE o.id=:id AND o.customer_id=:customer_id",
        {"id": booking_id, "customer_id": customer["id"]},
    )
    if not order:
        raise HTTPException(404, "Booking not found")
    try:
        return jsonable_encoder(await payment_breakdown_for_order(db, order))
    except Exception as exc:
        await db.rollback()
        logger.exception("Payment breakdown failed for booking %s", booking_id)
        raise HTTPException(500, "Payment details could not be loaded. Please refresh and try again.") from exc


@router.patch("/{booking_id}/customer-update")
async def customer_update_booking(
    booking_id: str,
    body: CustomerOrderUpdateIn,
    customer: dict = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db),
) -> dict:
    order = await fetch_one(
        db,
        """
        SELECT o.*, t.shop
        FROM orders o
        JOIN tailors t ON t.id=o.tailor_id
        WHERE o.id=:id AND o.customer_id=:customer_id
        FOR UPDATE
        """,
        {"id": booking_id, "customer_id": customer["id"]},
    )
    if not order:
        raise HTTPException(404, "Booking not found")
    blocked_reason = customer_manage_cutoff_error(order)
    if blocked_reason:
        raise HTTPException(409, blocked_reason)
    if body.instructions is None and body.preferred_date is None:
        raise HTTPException(400, "Choose instructions or a new delivery date to update.")

    if body.preferred_date is not None:
        if body.preferred_date < datetime.now(APP_TIMEZONE).date():
            raise HTTPException(400, "Delivery date cannot be in the past.")
        appointment_date = order.get("appointment_date")
        if isinstance(appointment_date, datetime):
            appointment_date = appointment_date.date()
        delivery_deadline = datetime.combine(body.preferred_date + timedelta(days=1), datetime.min.time(), APP_TIMEZONE)
        measurement_cutoff = delivery_deadline - timedelta(hours=12 if order.get("urgent_days") in {1, 2, 3} else 48)
        if appointment_date and order.get("appointment_slot"):
            try:
                _, appointment_end = zoned_slot(appointment_date, order["appointment_slot"])
            except BookingRuleError as exc:
                raise HTTPException(400, str(exc)) from exc
            if appointment_end > measurement_cutoff:
                raise HTTPException(400, "Delivery date does not leave the required measurement preparation time.")

    await db.execute(
        text(
            """
            UPDATE orders
            SET notes=COALESCE(:notes, notes),
                expected_completion=COALESCE(:expected_completion, expected_completion),
                delivery_deadline=COALESCE(:delivery_deadline, delivery_deadline),
                measurement_cutoff=COALESCE(:measurement_cutoff, measurement_cutoff)
            WHERE id=:id
            """
        ),
        {
            "id": booking_id,
            "notes": body.instructions,
            "expected_completion": body.preferred_date,
            "delivery_deadline": delivery_deadline if body.preferred_date is not None else None,
            "measurement_cutoff": measurement_cutoff if body.preferred_date is not None else None,
        },
    )
    changed_parts = []
    if body.instructions is not None:
        changed_parts.append("instructions")
    if body.preferred_date is not None:
        changed_parts.append("delivery date")
    await add_history(db, booking_id, "customer_update", f"Customer updated {', '.join(changed_parts)} before measurement.", "customer")
    await notify(
        db,
        "tailor:" + order["tailor_id"],
        "Customer updated order details",
        f"{customer['name']} updated {', '.join(changed_parts)} for order {order['code']}.",
        booking_id,
    )
    await db.commit()
    updated = await fetch_one(
        db,
        "SELECT o.*, t.shop, u.name AS customer_name FROM orders o JOIN tailors t ON t.id=o.tailor_id JOIN users u ON u.id=o.customer_id WHERE o.id=:id",
        {"id": booking_id},
    )
    payload = await tracker_status_payload(db, updated)
    await tracker_connections.broadcast(booking_id, jsonable_encoder(payload))
    return {"ok": True, "booking": public_booking(updated), "message": "Order details updated before measurement."}


@router.post("/{booking_id}/customer-cancel")
async def customer_cancel_booking(
    booking_id: str,
    body: CustomerCancelOrderIn,
    customer: dict = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db),
) -> dict:
    order = await fetch_one(
        db,
        """
        SELECT o.*, t.shop
        FROM orders o
        JOIN tailors t ON t.id=o.tailor_id
        WHERE o.id=:id AND o.customer_id=:customer_id
        FOR UPDATE
        """,
        {"id": booking_id, "customer_id": customer["id"]},
    )
    if not order:
        raise HTTPException(404, "Booking not found")
    blocked_reason = customer_manage_cutoff_error(order)
    if blocked_reason:
        raise HTTPException(409, blocked_reason)
    if str(order.get("payment_status") or "").lower() == "paid":
        raise HTTPException(409, "Paid orders cannot be cancelled here. Raise a support ticket for refund review.")

    reason = (body.reason or "Cancelled by customer before measurement").strip()
    await db.execute(
        text("UPDATE orders SET status='cancelled', cancel_reason=:reason WHERE id=:id"),
        {"id": booking_id, "reason": reason},
    )
    await db.execute(
        text("UPDATE payment_intents SET status='cancelled', updated_at=now() WHERE booking_id=:id AND status='pending'"),
        {"id": booking_id},
    )
    await db.execute(
        text("UPDATE payments SET status='CANCELLED', updated=now() WHERE order_id=:id AND status IN ('PENDING','PROCESSING')"),
        {"id": booking_id},
    )
    await add_history(db, booking_id, "cancelled", reason, "customer")
    await notify(
        db,
        "tailor:" + order["tailor_id"],
        "Order cancelled before measurement",
        f"{customer['name']} cancelled order {order['code']} before the measurement appointment.",
        booking_id,
    )
    await notify(
        db,
        "user:" + customer["id"],
        "Order cancelled",
        f"Your order {order['code']} was cancelled before measurement.",
        booking_id,
    )
    if str(order.get("status") or "").upper() in ACTIVE_CONTACT_STATUSES:
        await release_capacity_and_promote(db, order)
    await db.commit()
    updated = await fetch_one(
        db,
        "SELECT o.*, t.shop, u.name AS customer_name FROM orders o JOIN tailors t ON t.id=o.tailor_id JOIN users u ON u.id=o.customer_id WHERE o.id=:id",
        {"id": booking_id},
    )
    payload = await tracker_status_payload(db, updated)
    await tracker_connections.broadcast(booking_id, jsonable_encoder(payload))
    return {"ok": True, "booking": public_booking(updated), "message": "Order cancelled before measurement."}


@router.patch("/{booking_id}/stage")
async def update_booking_stage(
    booking_id: str,
    body: StageUpdateIn,
    tailor: dict = Depends(get_current_tailor),
    db: AsyncSession = Depends(get_db),
) -> dict:
    await ensure_measurement_visit_schema(db)
    stage = body.tracker_stage.strip()
    if stage not in TRACKER_STAGES:
        raise HTTPException(400, "Invalid tracker stage")
    if stage == "Delivered":
        raise HTTPException(409, "Delivery stage is completed only after payment and handover OTP verification")
    order = await fetch_booking_detail(db, booking_id, "AND o.tailor_id=:tailor_id", {"tailor_id": tailor["id"]}, True)
    if not order:
        raise HTTPException(404, "Booking not found")
    if is_completed_order(order):
        raise HTTPException(409, "This order is already completed. Status updates are disabled after handover OTP verification.")
    if stage == "Measurement Done" and measurement_visit_needs_otp(order):
        raise HTTPException(409, "Verify the customer's measurement arrival OTP before marking measurement done.")
    next_status = STAGE_TO_STATUS.get(stage, order.get("status"))
    update_sql = "UPDATE orders SET tracker_stage=:stage, status=:status WHERE id=:id"
    if stage == "Measurement Done":
        update_sql = "UPDATE orders SET tracker_stage=:stage, status=:status, measurement_done_at=COALESCE(measurement_done_at, now()) WHERE id=:id"
    await db.execute(text(update_sql), {"id": booking_id, "stage": stage, "status": next_status})
    await add_history(db, booking_id, stage, body.note or f"Tracker moved to {stage}", "tailor")
    contact_text = f"Tailor phone: {order.get('tailor_phone') or 'Phone not provided'}. Shop location: {order.get('tailor_location_address') or 'Open the order for the pinned location'}."
    await notify(
        db,
        "user:" + order["customer_id"],
        "TailoraHub order tracker update",
        f"Order {order['code']} status: {stage}. {contact_text}",
        booking_id,
        notification_type="BOOKING_STATUS_UPDATED",
        entity_type="booking",
        entity_id=booking_id,
    )
    await db.commit()
    updated = await fetch_booking_detail(db, booking_id)
    payload = await tracker_status_payload(db, updated)
    await tracker_connections.broadcast(booking_id, jsonable_encoder(payload))
    return payload


async def mark_gateway_payment_paid(
    db: AsyncSession,
    order: dict,
    intent: dict,
    payment_id: str,
    signature: str,
    gateway_response: dict | None = None,
) -> None:
    tailor_wallet = await ensure_tailor_wallet(db, order["tailor_uuid"])
    tailor_credit = money_decimal(intent.get("tailor_credit_amount"))
    admin_charge = money_decimal(intent.get("gst_platform_charge_amount"))
    commission = money_decimal(intent.get("commission_amount"))
    payable_total = money_decimal(intent.get("payable_total"))

    await db.execute(
        text(
            """
            UPDATE orders
            SET payment_status='paid',
                payment_method_selected='qr',
                payment_method_selected_at=now(),
                gst_platform_charge_amount=:admin_charge,
                commission_amount=:commission
            WHERE id=:id
            """
        ),
        {"id": order["id"], "admin_charge": admin_charge, "commission": commission},
    )
    if tailor_credit > 0:
        existing_credit = await fetch_one(
            db,
            """
            SELECT 1
            FROM wallet_transactions
            WHERE wallet_id=:wallet_id
              AND reference_booking_id=:booking_id
              AND type='credit'
              AND status='success'
            LIMIT 1
            """,
            {"wallet_id": tailor_wallet["wallet_id"], "booking_id": order["id"]},
        )
        if not existing_credit:
            await db.execute(
                text(
                    """
                    INSERT INTO wallet_transactions (id,wallet_id,type,amount,reference_booking_id,status)
                    VALUES (gen_random_uuid(),:wallet_id,'credit',:amount,:booking_id,'success')
                    """
                ),
                {"wallet_id": tailor_wallet["wallet_id"], "amount": tailor_credit, "booking_id": order["id"]},
            )
            await db.execute(
                text("UPDATE tailor_wallets SET balance=balance + :amount, updated_at=now() WHERE wallet_id=:wallet_id"),
                {"amount": tailor_credit, "wallet_id": tailor_wallet["wallet_id"]},
            )
    await credit_admin_wallet(db, "gst_platform_charge", admin_charge, order["id"], source_customer_id=order["customer_id"])
    await credit_admin_wallet(db, "commission", commission, order["id"], source_tailor_id=order["tailor_uuid"])
    payment = await fetch_one(db, "SELECT * FROM payments WHERE order_id=:id ORDER BY ts DESC LIMIT 1", {"id": order["id"]})
    if payment:
        await db.execute(
            text("UPDATE payments SET amount=:amount, method='razorpay', status='paid', txn_ref=:txn, updated=now() WHERE id=:id"),
            {"id": payment["id"], "amount": payable_total, "txn": payment_id},
        )
    else:
        await db.execute(
            text("INSERT INTO payments (id,order_id,amount,method,status,txn_ref) VALUES (:id,:order_id,:amount,'razorpay','paid',:txn)"),
            {"id": uid("pay"), "order_id": order["id"], "amount": payable_total, "txn": payment_id},
        )
    await db.execute(
        text(
            """
            UPDATE payment_intents
            SET status='verified',
                gateway_payment_id=:payment_id,
                gateway_signature=:signature,
                gateway_response=COALESCE(CAST(:gateway_response AS jsonb), gateway_response),
                proof_reference=:payment_id,
                admin_note='Razorpay signature verified automatically',
                verified_at=now(),
                updated_at=now()
            WHERE id=:id
            """
        ),
        {
            "id": intent["id"],
            "payment_id": payment_id,
            "signature": signature,
            "gateway_response": json.dumps(gateway_response or {"razorpay_payment_id": payment_id}),
        },
    )
    await add_history(db, order["id"], "paid", f"Razorpay payment {payment_id} verified. Tailor wallet credited net amount {tailor_credit}.", "system")
    await notify(db, "user:" + order["customer_id"], "Payment completed", f"Payment for order {order['code']} is verified. Delivery OTP is now enabled.", order["id"])
    await notify(db, "tailor:" + order["tailor_id"], "Payment completed", f"Payment for order {order['code']} is verified. Net wallet credit: Rs {tailor_credit}.", order["id"])


@router.post("/{booking_id}/pay")
async def pay_booking(
    booking_id: str,
    body: PaymentIn,
    customer: dict = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db),
) -> dict:
    order = await fetch_one(
        db,
        """
        SELECT o.*, t.shop, t.tailor_id AS tailor_uuid,
               u.name AS customer_name, u.email AS customer_email, u.phone AS customer_phone
        FROM orders o
        JOIN tailors t ON t.id=o.tailor_id
        JOIN users u ON u.id=o.customer_id
        WHERE o.id=:id AND o.customer_id=:customer_id
        FOR UPDATE
        """,
        {"id": booking_id, "customer_id": customer["id"]},
    )
    if not order:
        raise HTTPException(404, "Booking not found")
    breakdown = await payment_breakdown_for_order(db, order)
    if str(order.get("payment_status") or "").lower() == "paid":
        return {
            "ok": True,
            "booking": public_booking(order),
            "breakdown": breakdown,
            "message": "Payment was already completed. Delivery OTP is enabled.",
        }
    method = (body.method or "razorpay").strip().lower()
    if method != "razorpay":
        raise HTTPException(400, "Only Razorpay secure checkout is enabled for customer payments.")
    key_id, key_secret = require_razorpay_credentials()

    await latest_payment_intent(db, booking_id)

    app_settings = get_settings()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=max(1, app_settings.manual_payment_expiry_minutes))
    order_amount = money_decimal(breakdown["order_amount"])
    payable_total = money_decimal(breakdown["payable_total"])
    payment_reference = f"THPAY-{str(order.get('code') or booking_id).replace('ORD-', '')}-{uuid.uuid4().hex[:6].upper()}"

    # Test keys can be rotated often. Reusing an old pending Razorpay order after
    # a key change causes checkout authentication failures, so every Pay click
    # creates a fresh gateway order and cancels stale pending intents.
    await db.execute(
        text(
            """
            UPDATE payment_intents
            SET status='cancelled', updated_at=now()
            WHERE booking_id=:booking_id
              AND status='pending'
              AND method='razorpay'
            """
        ),
        {"booking_id": booking_id},
    )
    razorpay_order = await create_razorpay_order(
        key_id,
        key_secret,
        {
            "amount": amount_to_paise(payable_total),
            "currency": "INR",
            "receipt": payment_reference[:40],
            "payment_capture": 1,
            "notes": {
                "booking_id": booking_id,
                "order_code": order.get("code") or "",
                "payment_reference": payment_reference,
            },
        },
    )
    razorpay_order_id = razorpay_order.get("id")
    if not razorpay_order_id:
        raise HTTPException(502, "Razorpay did not return an order id. Please try again.")
    intent_result = await db.execute(
        text(
            """
            INSERT INTO payment_intents
              (booking_id,customer_id,tailor_id,payment_reference,method,order_amount,gst_amount,
               platform_fee_amount,gst_platform_charge_amount,commission_amount,tailor_credit_amount,
               payable_total,status,gateway_order_id,gateway_response,customer_note,expires_at,created_at,updated_at)
            VALUES
              (:booking_id,:customer_id,:tailor_id,:payment_reference,'razorpay',:order_amount,:gst_amount,
               :platform_fee_amount,:gst_platform_charge_amount,:commission_amount,:tailor_credit_amount,
               :payable_total,'pending',:gateway_order_id,CAST(:gateway_response AS jsonb),:customer_note,:expires_at,now(),now())
            RETURNING *
            """
        ),
        {
            "booking_id": booking_id,
            "customer_id": customer["id"],
            "tailor_id": order["tailor_id"],
            "payment_reference": payment_reference,
            "order_amount": order_amount,
            "gst_amount": money_decimal(breakdown["gst_amount"]),
            "platform_fee_amount": money_decimal(breakdown["platform_fee_amount"]),
            "gst_platform_charge_amount": money_decimal(breakdown["gst_platform_charge_amount"]),
            "commission_amount": money_decimal(breakdown["commission_amount"]),
            "tailor_credit_amount": money_decimal(breakdown["tailor_credit_amount"]),
            "payable_total": payable_total,
            "gateway_order_id": razorpay_order_id,
            "gateway_response": json.dumps(razorpay_order),
            "customer_note": body.txn_ref,
            "expires_at": expires_at,
        },
    )
    active_intent = dict(intent_result.mappings().first())
    payment = await fetch_one(db, "SELECT * FROM payments WHERE order_id=:id ORDER BY ts DESC LIMIT 1", {"id": booking_id})
    if payment:
        await db.execute(
            text("UPDATE payments SET amount=:amount, method='razorpay', status='PROCESSING', txn_ref=:txn, updated=now() WHERE id=:id"),
            {"id": payment["id"], "amount": payable_total, "txn": razorpay_order_id},
        )
    else:
        await db.execute(
            text("INSERT INTO payments (id,order_id,amount,method,status,txn_ref) VALUES (:id,:order_id,:amount,'razorpay','PROCESSING',:txn)"),
            {"id": uid("pay"), "order_id": booking_id, "amount": payable_total, "txn": razorpay_order_id},
        )
    await add_history(db, booking_id, "payment_pending", f"Razorpay checkout created for payment reference {payment_reference}.", "customer")
    await notify(db, "user:" + customer["id"], "Razorpay checkout created", f"Payment reference {payment_reference} expires in {app_settings.manual_payment_expiry_minutes} minutes.", booking_id)
    await db.commit()
    updated = await fetch_one(
        db,
        "SELECT o.*, t.shop, u.name AS customer_name FROM orders o JOIN tailors t ON t.id=o.tailor_id JOIN users u ON u.id=o.customer_id WHERE o.id=:id",
        {"id": booking_id},
    )
    payload = await tracker_status_payload(db, updated)
    await tracker_connections.broadcast(booking_id, jsonable_encoder(payload))
    intent = payment_intent_payload(active_intent)
    checkout = razorpay_public_checkout_payload(order, active_intent, breakdown, key_id)
    return {
        "ok": True,
        "provider": "razorpay",
        "booking": public_booking(updated),
        "breakdown": breakdown,
        "paymentIntent": intent,
        "payment_intent": intent,
        "checkout": checkout,
        "razorpayCheckout": checkout,
        "message": "Razorpay checkout created. Delivery OTP unlocks only after secure payment verification.",
    }


@router.post("/{booking_id}/razorpay/verify")
async def verify_razorpay_booking_payment(
    booking_id: str,
    body: RazorpayVerifyIn,
    customer: dict = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db),
) -> dict:
    _, key_secret = require_razorpay_credentials()
    intent = await fetch_one(
        db,
        """
        SELECT *
        FROM payment_intents
        WHERE booking_id=:booking_id
          AND method='razorpay'
          AND gateway_order_id=:gateway_order_id
        ORDER BY created_at DESC
        LIMIT 1
        FOR UPDATE
        """,
        {"booking_id": booking_id, "gateway_order_id": body.razorpay_order_id},
    )
    if not intent:
        raise HTTPException(404, "Razorpay payment request not found for this booking.")
    order = await fetch_one(
        db,
        """
        SELECT o.*, t.shop, t.tailor_id AS tailor_uuid,
               u.name AS customer_name, u.email AS customer_email, u.phone AS customer_phone
        FROM orders o
        JOIN tailors t ON t.id=o.tailor_id
        JOIN users u ON u.id=o.customer_id
        WHERE o.id=:id AND o.customer_id=:customer_id
        FOR UPDATE
        """,
        {"id": booking_id, "customer_id": customer["id"]},
    )
    if not order:
        raise HTTPException(404, "Booking not found")
    if intent.get("customer_id") != customer["id"]:
        raise HTTPException(403, "This payment request belongs to another customer.")
    if str(order.get("payment_status") or "").lower() == "paid" or intent.get("status") == "verified":
        return {
            "ok": True,
            "booking": public_booking(order),
            "paymentIntent": payment_intent_payload(intent),
            "payment_intent": payment_intent_payload(intent),
            "message": "Payment was already verified. Delivery OTP is enabled.",
        }
    if intent.get("status") != "pending":
        raise HTTPException(409, f"This payment request is already {intent.get('status')}.")
    expires_at = intent.get("expires_at")
    if expires_at:
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at <= datetime.now(timezone.utc):
            await db.execute(text("UPDATE payment_intents SET status='expired', updated_at=now() WHERE id=:id"), {"id": intent["id"]})
            await db.commit()
            raise HTTPException(409, "This Razorpay checkout expired. Please start payment again.")
    if not verify_razorpay_signature(body.razorpay_order_id, body.razorpay_payment_id, body.razorpay_signature, key_secret):
        await db.execute(
            text(
                """
                UPDATE payment_intents
                SET admin_note='Razorpay signature verification failed',
                    gateway_payment_id=:payment_id,
                    gateway_signature=:signature,
                    updated_at=now()
                WHERE id=:id
                """
            ),
            {"id": intent["id"], "payment_id": body.razorpay_payment_id, "signature": body.razorpay_signature},
        )
        await db.commit()
        raise HTTPException(400, "Razorpay payment signature is invalid. Payment was not applied.")

    await mark_gateway_payment_paid(
        db,
        order,
        intent,
        body.razorpay_payment_id,
        body.razorpay_signature,
        {
            "razorpay_order_id": body.razorpay_order_id,
            "razorpay_payment_id": body.razorpay_payment_id,
            "verification": "signature_valid",
        },
    )
    await db.commit()
    updated = await fetch_one(
        db,
        "SELECT o.*, t.shop, u.name AS customer_name FROM orders o JOIN tailors t ON t.id=o.tailor_id JOIN users u ON u.id=o.customer_id WHERE o.id=:id",
        {"id": booking_id},
    )
    payload = await tracker_status_payload(db, updated)
    await tracker_connections.broadcast(booking_id, jsonable_encoder(payload))
    return {
        "ok": True,
        "booking": public_booking(updated),
        "paymentIntent": payload.get("paymentIntent"),
        "payment_intent": payload.get("paymentIntent"),
        "message": "Payment completed securely through Razorpay. Delivery OTP is now enabled.",
    }


@router.post("/{booking_id}/send-delivery-otp")
async def send_delivery_otp(
    booking_id: str,
    tailor: dict = Depends(get_current_tailor),
    db: AsyncSession = Depends(get_db),
) -> dict:
    order = await fetch_one(
        db,
        "SELECT o.*, u.email, t.tailor_id AS tailor_uuid FROM orders o JOIN users u ON u.id=o.customer_id JOIN tailors t ON t.id=o.tailor_id WHERE o.id=:id AND o.tailor_id=:tailor_id FOR UPDATE",
        {"id": booking_id, "tailor_id": tailor["id"]},
    )
    if not order:
        raise HTTPException(404, "Booking not found")
    if is_completed_order(order):
        raise HTTPException(409, "This order is already completed. Delivery OTP cannot be sent again.")
    if str(order.get("payment_status") or "").lower() != "paid":
        raise HTTPException(status_code=403, detail="Payment must be completed before delivery OTP can be generated.")
    try:
        code, _ = await issue_otp(db, booking_id, "delivery")
    except OtpFlowError as exc:
        await db.rollback()
        raise HTTPException(exc.status_code, exc.message)
    await db.execute(text("UPDATE orders SET status='out_for_delivery', tracker_stage='Out for Delivery' WHERE id=:id"), {"id": booking_id})
    await add_history(db, booking_id, "Out for Delivery", "Delivery OTP sent to customer", "tailor")
    await notify(db, "user:" + order["customer_id"], "TailoraHub handover OTP", f"Your handover OTP for order {order['code']} is {code}. It is valid for {OTP_TTL_MINUTES} minutes.", booking_id)
    if order.get("email"):
        send_email(order["email"], "TailoraHub handover OTP", f"Your handover OTP for order {order['code']} is {code}. It is valid for {OTP_TTL_MINUTES} minutes.")
    await db.commit()
    updated = await fetch_one(
        db,
        "SELECT o.*, t.shop, u.name AS customer_name FROM orders o JOIN tailors t ON t.id=o.tailor_id JOIN users u ON u.id=o.customer_id WHERE o.id=:id",
        {"id": booking_id},
    )
    payload = await tracker_status_payload(db, updated)
    await tracker_connections.broadcast(booking_id, jsonable_encoder(payload))
    return {"sent": True, "message": "Delivery OTP sent."}


@router.post("/{booking_id}/verify-delivery-otp")
async def verify_delivery_otp(
    booking_id: str,
    body: DeliveryOtpVerifyIn,
    tailor: dict = Depends(get_current_tailor),
    db: AsyncSession = Depends(get_db),
) -> dict:
    order = await fetch_one(
        db,
        """SELECT o.*, u.email, t.tailor_id AS tailor_uuid
           FROM orders o
           JOIN users u ON u.id=o.customer_id
           JOIN tailors t ON t.id=o.tailor_id
           WHERE o.id=:id AND o.tailor_id=:tailor_id
           FOR UPDATE""",
        {"id": booking_id, "tailor_id": tailor["id"]},
    )
    if not order:
        raise HTTPException(404, "Booking not found")
    if is_completed_order(order):
        raise HTTPException(409, "This order is already completed. Handover OTP cannot be verified again.")
    if str(order.get("payment_status") or "").lower() != "paid":
        raise HTTPException(status_code=403, detail="Payment must be completed before delivery OTP can be verified.")
    try:
        matched = await verify_otp(db, booking_id, "delivery", body.otp)
    except OtpFlowError as exc:
        await db.rollback()
        raise HTTPException(exc.status_code, exc.message)
    if not matched:
        raise HTTPException(401, "Incorrect or expired delivery OTP")
    await db.execute(text("UPDATE orders SET otp_verified=TRUE, status='completed', tracker_stage='Delivered', delivered_at=now(), completed_at=now() WHERE id=:id"), {"id": booking_id})
    commission = await apply_completion_commission(db, order)
    await add_history(db, booking_id, "Delivered", "Delivery OTP verified", "tailor")
    await add_history(db, booking_id, "completed", f"Order completed after handover verification. Commission deducted: {commission}.", "tailor")
    await db.execute(text("UPDATE tailors SET completed=(SELECT count(*) FROM orders WHERE tailor_id=:tailor_id AND lower(status)='completed') WHERE id=:tailor_id"), {"tailor_id": tailor["id"]})
    await notify(db, "user:" + order["customer_id"], "Check your stitched item", f"Order {order['code']} is delivered. Please check your stitched item and raise a ticket if there is an issue.", booking_id)
    await db.commit()
    updated = await fetch_one(
        db,
        "SELECT o.*, t.shop, u.name AS customer_name FROM orders o JOIN tailors t ON t.id=o.tailor_id JOIN users u ON u.id=o.customer_id WHERE o.id=:id",
        {"id": booking_id},
    )
    payload = await tracker_status_payload(db, updated)
    await tracker_connections.broadcast(booking_id, jsonable_encoder(payload))
    return {"ok": True, "booking": public_booking(updated), "message": "Delivery OTP verified and order completed."}


@router.post("/{booking_id}/raise-dispute", status_code=201)
async def raise_booking_dispute(
    booking_id: str,
    body: RaiseDisputeIn,
    customer: dict = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db),
) -> dict:
    order = await fetch_one(
        db,
        "SELECT o.*, t.shop FROM orders o JOIN tailors t ON t.id=o.tailor_id WHERE o.id=:id AND o.customer_id=:customer_id FOR UPDATE",
        {"id": booking_id, "customer_id": customer["id"]},
    )
    if not order:
        raise HTTPException(404, "Booking not found")
    existing = await fetch_one(
        db,
        "SELECT * FROM disputes WHERE booking_id=:id AND customer_id=:customer_id AND status IN ('open','in_review') ORDER BY created_at DESC LIMIT 1",
        {"id": booking_id, "customer_id": customer["id"]},
    )
    if existing:
        raise HTTPException(409, "A dispute is already open for this booking")
    photo_reference = None
    if body.photo_url or body.photo_name or body.photo_media_type:
        if not body.photo_url or not body.photo_name or not body.photo_media_type:
            raise HTTPException(400, "Dispute photo requires a file name, media type, and file data")
        media_type = body.photo_media_type.lower()
        extension = DISPUTE_IMAGE_EXTENSIONS.get(media_type)
        if not extension:
            raise HTTPException(400, "Dispute photo must be JPEG, PNG, or WebP")
        prefix = f"data:{media_type};base64,"
        if not body.photo_url.startswith(prefix):
            raise HTTPException(400, "Invalid dispute photo data")
        try:
            raw_photo = base64.b64decode(body.photo_url[len(prefix):], validate=True)
            if not raw_photo or len(raw_photo) > MAX_DISPUTE_IMAGE_BYTES:
                raise ValueError("invalid size")
            validate_file_signature(raw_photo, media_type)
        except (ValueError, MediaStorageError) as exc:
            raise HTTPException(400, "Dispute photo content is invalid or too large") from exc
        object_key = f"private/disputes/{customer['id']}/{uuid.uuid4().hex}{extension}"
        try:
            photo_reference = await asyncio.to_thread(
                get_media_storage().store_private_bytes,
                object_key,
                raw_photo,
                media_type,
            )
        except MediaStorageError as exc:
            raise HTTPException(503, "Dispute attachment storage is temporarily unavailable") from exc
    try:
        result = await db.execute(
            text(
                """
                INSERT INTO disputes
                  (id,booking_id,customer_id,reason,photo_url,photo_name,photo_media_type,status,refund_amount,created_at,updated_at)
                VALUES
                  (gen_random_uuid(),:booking_id,:customer_id,:reason,:photo_url,:photo_name,:photo_media_type,'open',0,now(),now())
                RETURNING *
                """
            ),
            {
                "booking_id": booking_id,
                "customer_id": customer["id"],
                "reason": body.reason.strip(),
                "photo_url": photo_reference,
                "photo_name": body.photo_name,
                "photo_media_type": body.photo_media_type,
            },
        )
    except Exception:
        if photo_reference:
            await asyncio.to_thread(get_media_storage().delete_url, photo_reference)
        raise
    dispute = dict(result.mappings().first())
    await db.execute(text("UPDATE orders SET dispute_raised=TRUE, status='disputed' WHERE id=:id"), {"id": booking_id})
    await add_history(db, booking_id, "disputed", "Customer raised a dispute", "customer")
    await notify(db, "admin", "New customer dispute", f"Order {order['code']} has a new dispute from {customer['name']}.", booking_id)
    await notify(db, "tailor:" + order["tailor_id"], "Order dispute raised", f"Customer raised a dispute for order {order['code']}. Admin will review it.", booking_id)
    await db.commit()
    await broadcast_status(db, booking_id)
    return {
        "dispute": dispute_payload(dispute),
        "message": f"Your dispute has been raised, ticket #{str(dispute['id'])[:8]}. Our team will review it.",
    }


@router.get("/tailors/me/waiting-list")
async def my_waiting_list(
    page: PageParams = Depends(PageParams),
    tailor: dict = Depends(get_current_tailor),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    result = await db.execute(
        text(
            """
            SELECT o.*, u.name AS customer_name, u.phone AS customer_phone, u.email AS customer_email, t.shop
            FROM orders o
            JOIN users u ON u.id=o.customer_id
            JOIN tailors t ON t.id=o.tailor_id
            WHERE o.tailor_id=:tailor_id AND upper(o.status) IN ('WAITING_LIST','WAITLISTED','PENDING_APPROVAL')
            ORDER BY o.ts ASC
            LIMIT :limit OFFSET :offset
            """
        ),
        {"tailor_id": tailor["id"], **page.sql},
    )
    return [public_booking(dict(row)) for row in result.mappings().all()]


@router.post("/{booking_id}/tailor-confirm")
async def tailor_confirm_booking(
    booking_id: str,
    tailor: dict = Depends(get_current_tailor),
    db: AsyncSession = Depends(get_db),
) -> dict:
    order = await fetch_one(
        db,
        "SELECT o.*, u.name AS customer_name FROM orders o JOIN users u ON u.id=o.customer_id WHERE o.id=:id AND o.tailor_id=:tailor_id FOR UPDATE",
        {"id": booking_id, "tailor_id": tailor["id"]},
    )
    if not order:
        raise HTTPException(404, "Booking not found")
    status = str(order["status"] or "").upper()
    if status not in {"WAITING_LIST", "WAITLISTED", "PENDING_APPROVAL"}:
        raise HTTPException(409, "Only active pending or waiting-list bookings can be confirmed")
    if order.get("expires_at") and order["expires_at"] <= datetime.now(timezone.utc):
        await db.execute(text("UPDATE orders SET status='EXPIRED',status_reason='TAILOR_RESPONSE_TIMEOUT' WHERE id=:id"), {"id": booking_id})
        await db.commit()
        raise HTTPException(409, "This request expired because the response time ended")
    conflict = await fetch_one(db, """SELECT id FROM orders WHERE tailor_id=:tailor_id AND appointment_date=:appointment_date
        AND appointment_slot=:appointment_slot AND id<>:id AND upper(status) IN ('AUTO_APPROVED','CONFIRMED','ASSIGNED','MEASUREMENT_PENDING','MEASUREMENT_DONE','IN_PROGRESS') LIMIT 1""",
        {"tailor_id": tailor["id"], "appointment_date": order.get("appointment_date"), "appointment_slot": order.get("appointment_slot"), "id": booking_id})
    if conflict:
        raise HTTPException(409, "This measurement slot is already assigned. Choose another slot.")
    if order.get("request_group_id"):
        assigned = await fetch_one(db, """UPDATE booking_request_groups SET status='ASSIGNED',assigned_tailor_id=:tailor_id,
            assigned_order_id=:order_id,assigned_at=now() WHERE id=:group_id AND assigned_tailor_id IS NULL RETURNING id""",
            {"group_id": order["request_group_id"], "tailor_id": tailor["id"], "order_id": booking_id})
        if not assigned:
            raise HTTPException(409, "Another tailor has already accepted this request")
        await db.execute(text("""UPDATE orders SET status='CANCELLED',status_reason='ANOTHER_TAILOR_ACCEPTED'
            WHERE request_group_id=:group_id AND id<>:id AND upper(status) IN ('PENDING_APPROVAL','WAITLISTED','WAITING_LIST')"""),
            {"group_id": order["request_group_id"], "id": booking_id})

    await db.execute(
        text("UPDATE orders SET status='CONFIRMED',assigned_at=now(),expires_at=NULL,tracker_stage='Measurement Scheduled' WHERE id=:id"),
        {"id": booking_id},
    )
    await add_history(db, booking_id, "CONFIRMED", "Tailor accepted and was atomically assigned", "tailor")
    tailor_contact = order.get("tailor_phone") or "Phone not provided"
    tailor_location = order.get("tailor_location_address") or "Open the order to view the pinned shop location"
    await notify(
        db,
        "user:" + order["customer_id"],
        "Tailor confirmed your booking",
        f"Order {order['code']} is confirmed. Tailor phone: {tailor_contact}. Shop location: {tailor_location}.",
        booking_id,
        notification_type="BOOKING_CONFIRMED",
        entity_type="booking",
        entity_id=booking_id,
        dedupe_key="booking-confirmed:" + booking_id,
    )
    await db.commit()
    updated = await fetch_one(
        db,
        "SELECT o.*, t.shop, u.name AS customer_name FROM orders o JOIN tailors t ON t.id=o.tailor_id JOIN users u ON u.id=o.customer_id WHERE o.id=:id",
        {"id": booking_id},
    )
    await tracker_connections.broadcast(booking_id, jsonable_encoder(await tracker_status_payload(db, updated)))
    return {"booking": public_booking(updated, {"id": tailor.get("user_id"), "tailor_id": tailor["id"], "roles": ["tailor"]}), "message": "Booking confirmed and assigned."}


@router.post("/{booking_id}/tailor-reject")
async def tailor_reject_booking(
    booking_id: str,
    body: CustomerCancelOrderIn,
    tailor: dict = Depends(get_current_tailor),
    db: AsyncSession = Depends(get_db),
) -> dict:
    order = await fetch_one(db, "SELECT * FROM orders WHERE id=:id AND tailor_id=:tailor_id FOR UPDATE",
                            {"id": booking_id, "tailor_id": tailor["id"]})
    if not order:
        raise HTTPException(404, "Booking request not found")
    if str(order.get("status") or "").upper() not in {"PENDING_APPROVAL", "WAITLISTED", "WAITING_LIST"}:
        raise HTTPException(409, "Only an active pending request can be rejected")
    reason = (body.reason or "Tailor is unavailable").strip()
    await db.execute(text("UPDATE orders SET status='REJECTED',status_reason=:reason,expires_at=NULL WHERE id=:id"),
                     {"id": booking_id, "reason": reason})
    if order.get("request_group_id"):
        await db.execute(text("""UPDATE booking_request_groups g SET status='CLOSED',closed_at=now()
            WHERE g.id=:group_id AND g.assigned_tailor_id IS NULL AND NOT EXISTS
              (SELECT 1 FROM orders o WHERE o.request_group_id=g.id AND o.id<>:id
               AND upper(o.status) IN ('PENDING_APPROVAL','WAITLISTED','WAITING_LIST'))"""),
            {"group_id": order["request_group_id"], "id": booking_id})
    await add_history(db, booking_id, "REJECTED", reason, "tailor")
    await notify(db, "user:" + order["customer_id"], "Booking request rejected",
                 f"Booking {order['code']} was not accepted by this tailor. Open the booking for details.", booking_id,
                 notification_type="BOOKING_REJECTED", dedupe_key="booking-rejected:" + booking_id)
    await db.commit()
    return {"ok": True, "message": "Booking request rejected."}


@router.post("/{booking_id}/measurement-done")
async def measurement_done(
    booking_id: str,
    tailor: dict = Depends(get_current_tailor),
    db: AsyncSession = Depends(get_db),
) -> dict:
    await ensure_measurement_visit_schema(db)
    order = await fetch_booking_detail(db, booking_id, "AND o.tailor_id=:tailor_id", {"tailor_id": tailor["id"]}, True)
    if not order:
        raise HTTPException(404, "Booking not found")
    if is_completed_order(order):
        raise HTTPException(409, "This order is already completed. Measurement updates are disabled.")
    if str(order["status"] or "").upper() not in {"AUTO_APPROVED", "CONFIRMED", "ASSIGNED", "TAILOR_CONFIRMED", "MEASUREMENT_PENDING"}:
        raise HTTPException(409, "Measurement can be marked done only after booking approval")
    if measurement_visit_needs_otp(order):
        raise HTTPException(409, "Verify the customer's measurement arrival OTP before marking measurement done.")
    await db.execute(
        text("UPDATE orders SET status='measurement_done', measurement_done_at=now(), tracker_stage='Measurement Done' WHERE id=:id"),
        {"id": booking_id},
    )
    await add_history(db, booking_id, "Measurement Done", "Measurements completed", "tailor")
    await notify(db, "user:" + order["customer_id"], "Measurement completed", f"Measurements for order {order['code']} are completed. Tracker will begin now.", booking_id)
    await db.commit()
    updated = await fetch_booking_detail(db, booking_id)
    await tracker_connections.broadcast(booking_id, jsonable_encoder(await tracker_status_payload(db, updated)))
    return {"booking": public_booking(updated), "message": "Measurement marked done."}


@router.post("/{booking_id}/track-ticket")
async def create_track_ticket(
    booking_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await get_accessible_order(db, booking_id, user)
    settings = get_settings()
    return {
        "ticket": create_booking_ws_ticket(str(user["id"]), booking_id),
        "expiresIn": settings.realtime_ticket_seconds,
    }


@router.websocket("/{booking_id}/track")
async def track_booking(websocket: WebSocket, booking_id: str, ticket: str | None = Query(default=None)) -> None:
    try:
        claims = decode_booking_ws_ticket(ticket or "")
        if str(claims.get("booking_id")) != str(booking_id):
            raise ValueError("Ticket is scoped to a different booking")
    except Exception:
        await websocket.close(code=4401, reason="Valid booking tracker ticket required")
        return
    await tracker_connections.connect(booking_id, websocket)
    try:
        while True:
            message = await websocket.receive_text()
            if message == "ping":
                await websocket.send_json({"type": "pong"})
    except (WebSocketDisconnect, RuntimeError):
        tracker_connections.disconnect(booking_id, websocket)
