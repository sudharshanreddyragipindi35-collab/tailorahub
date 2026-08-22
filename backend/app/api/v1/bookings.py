from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
import math
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
import re
import uuid
from urllib import error as urllib_error, request as urllib_request

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_customer, get_current_tailor, get_current_user
from app.api.v1.otp import OTP_TTL_MINUTES, OtpFlowError, issue_otp, verify_otp
from app.core.config import get_settings
from app.core.database import get_db
from app.emailer import send_email
from app.qr import generate_wallet_qr
from app.services.tracker_service import tracker_connections


router = APIRouter()

MEASUREMENT_APPOINTMENT_BLOCKED_WINDOW_DAYS = 2
MEASUREMENT_APPOINTMENT_ERROR = "Measurement appointment must be scheduled at least 3 days before the delivery date."
MEASUREMENT_APPOINTMENT_REQUIRED_ERROR = "Choose measurement appointment date."
PAST_DELIVERY_DATE_ERROR = "Expected delivery date cannot be in the past. Choose today or a future date."
PAST_APPOINTMENT_DATE_ERROR = "Measurement appointment cannot be in the past. Choose today or a future date."
TRAVEL_CHARGE_PER_KM = Decimal("5.00")


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
    customer_location_address: str | None = Field(default=None, alias="customerLocationAddress")
    customer_location_lat: float | None = Field(default=None, alias="customerLocationLat", ge=-90, le=90)
    customer_location_lng: float | None = Field(default=None, alias="customerLocationLng", ge=-180, le=180)


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
    return delivery_date - timedelta(days=MEASUREMENT_APPOINTMENT_BLOCKED_WINDOW_DAYS + 1)


def resolve_booking_dates(
    preferred_date: date | None,
    appointment_date: date | None,
    service_days: int | None,
) -> tuple[date, date]:
    today = date.today()
    delivery_date = preferred_date or (today + timedelta(days=service_days or 5))
    if delivery_date < today:
        raise HTTPException(400, PAST_DELIVERY_DATE_ERROR)
    if appointment_date is None:
        raise HTTPException(400, MEASUREMENT_APPOINTMENT_REQUIRED_ERROR)
    if appointment_date < today:
        raise HTTPException(400, PAST_APPOINTMENT_DATE_ERROR)
    latest_appointment_date = latest_measurement_appointment_date(delivery_date)
    if appointment_date > latest_appointment_date:
        raise HTTPException(400, MEASUREMENT_APPOINTMENT_ERROR)
    return delivery_date, appointment_date


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
    settings = await platform_settings(db)
    service_amount = money_decimal(order.get("base_price") or order.get("total") or 0)
    order_amount = money_decimal(order.get("total") or service_amount)
    travel_charge_amount = max(order_amount - service_amount, Decimal("0.00"))
    gst_amount = percent_amount(order_amount, settings.get("gst_percentage"))
    platform_fee_amount = percent_amount(order_amount, settings.get("platform_fee_percentage"))
    charge_amount = gst_amount + platform_fee_amount
    commission_amount = percent_amount(order_amount, settings.get("commission_percentage"))
    tailor_credit_amount = max(order_amount - commission_amount, Decimal("0.00"))
    grand_total = order_amount + charge_amount
    return {
        "service_amount": service_amount,
        "serviceAmount": service_amount,
        "travel_charge_amount": travel_charge_amount,
        "travelChargeAmount": travel_charge_amount,
        "travel_rate_per_km": TRAVEL_CHARGE_PER_KM,
        "travelRatePerKm": TRAVEL_CHARGE_PER_KM,
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


def razorpay_credentials() -> tuple[str, str]:
    app_settings = get_settings()
    key_id = (app_settings.razorpay_key_id or app_settings.payment_api_key or "").strip()
    key_secret = (app_settings.razorpay_key_secret or app_settings.payment_api_secret or "").strip()
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
        raise HTTPException(502, f"Razorpay order creation failed. {detail[:300]}")
    except urllib_error.URLError as exc:
        raise HTTPException(502, f"Could not connect to Razorpay: {exc.reason}")


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


async def notify(db: AsyncSession, to_ref: str, title: str, body: str, order_id: str | None = None) -> None:
    await db.execute(
        text("INSERT INTO notifications (id,to_ref,channel,title,body,order_id) VALUES (:id,:to_ref,'in_app',:title,:body,:order_id)"),
        {"id": uid("n"), "to_ref": to_ref, "title": title, "body": body, "order_id": order_id},
    )


async def add_history(db: AsyncSession, order_id: str, status: str, note: str, by_role: str) -> None:
    await db.execute(
        text("INSERT INTO order_status_history (order_id,status,note,by_role) VALUES (:order_id,:status,:note,:by_role)"),
        {"order_id": order_id, "status": status, "note": note, "by_role": by_role},
    )


def public_booking(row: dict) -> dict:
    service_amount = money_decimal(row.get("base_price") or row.get("total") or 0)
    order_amount = money_decimal(row.get("total") or service_amount)
    travel_charge_amount = max(order_amount - service_amount, Decimal("0.00"))
    return {
        "id": row["id"],
        "code": row["code"],
        "tailorId": row.get("tailor_id"),
        "tailorName": row.get("shop"),
        "customerId": row.get("customer_id"),
        "customerName": row.get("customer_name"),
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
        "customerLocationAddress": row.get("customer_location_address"),
        "customerLocationLat": float(row["customer_location_lat"]) if row.get("customer_location_lat") is not None else None,
        "customerLocationLng": float(row["customer_location_lng"]) if row.get("customer_location_lng") is not None else None,
        "customerLocationConfirmedAt": row.get("customer_location_confirmed_at"),
        "address": row.get("address"),
        "appointmentDate": row.get("appointment_date"),
        "appointmentSlot": row.get("appointment_slot"),
        "expectedCompletion": row.get("expected_completion"),
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
    roles = user.get("roles") or []
    if "tailor" in roles:
        order = await fetch_one(
            db,
            """
            SELECT o.*, t.shop, u.name AS customer_name
            FROM orders o
            JOIN tailors t ON t.id=o.tailor_id
            JOIN users u ON u.id=o.customer_id
            WHERE o.id=:id AND t.user_id=:user_id
            """,
            {"id": booking_id, "user_id": user["id"]},
        )
        if order:
            return order
    if "customer" in roles:
        order = await fetch_one(
            db,
            """
            SELECT o.*, t.shop, u.name AS customer_name
            FROM orders o
            JOIN tailors t ON t.id=o.tailor_id
            JOIN users u ON u.id=o.customer_id
            WHERE o.id=:id AND o.customer_id=:user_id
            """,
            {"id": booking_id, "user_id": user["id"]},
        )
        if order:
            return order
    raise HTTPException(404, "Booking not found")


async def tracker_status_payload(db: AsyncSession, order: dict) -> dict:
    result = await db.execute(
        text(
            """
            SELECT status, note, by_role, ts
            FROM order_status_history
            WHERE order_id=:order_id
            ORDER BY ts ASC
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
        "booking": public_booking(order),
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
    return {
        "id": dispute_id,
        "booking_id": row.get("booking_id"),
        "bookingId": row.get("booking_id"),
        "customer_id": row.get("customer_id"),
        "customerId": row.get("customer_id"),
        "reason": row.get("reason"),
        "photo_url": row.get("photo_url"),
        "photoUrl": row.get("photo_url"),
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
    order = await fetch_one(
        db,
        "SELECT o.*, t.shop, u.name AS customer_name FROM orders o JOIN tailors t ON t.id=o.tailor_id JOIN users u ON u.id=o.customer_id WHERE o.id=:id",
        {"id": booking_id},
    )
    if order:
        await tracker_connections.broadcast(booking_id, jsonable_encoder(await tracker_status_payload(db, order)))


@router.get("/scaffold")
async def bookings_scaffold() -> dict:
    return {"module": "bookings", "ready": True}


@router.post("")
async def create_booking(
    body: BookingCreateIn,
    customer: dict = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db),
) -> dict:
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

    available = bool(tailor.get("is_available")) and tailor.get("availability") not in {"BUSY", "NOT_AVAILABLE"}
    status = "auto_approved" if available else "waiting_list"
    order_id = uid("ord")
    code_row = await fetch_one(db, "SELECT 'ORD-' || nextval('order_code_seq') AS code")
    code = code_row["code"]
    quantity = body.quantity or 1
    base_price = int(service["price"]) * quantity
    expected, appointment_date = resolve_booking_dates(body.preferred_date, body.appointment_date, service.get("days"))
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
    order_total = int((money_decimal(base_price) + travel_charge).quantize(Decimal("1"), rounding=ROUND_HALF_UP))

    result = await db.execute(
        text(
            """
            INSERT INTO orders
              (id,code,customer_id,tailor_id,service_id,service_name,garment_id,quantity,status,base_price,total,
               measurement_mode,appointment_date,appointment_slot,address,expected_completion,notes,
               customer_location_address,customer_location_lat,customer_location_lng,customer_location_confirmed_at,tracker_stage)
            VALUES
              (:id,:code,:customer_id,:tailor_id,:service_id,:service_name,:garment_id,:quantity,:status,:base_price,:total,
               :measurement_mode,:appointment_date,:appointment_slot,:address,:expected_completion,:notes,
               :customer_location_address,:customer_location_lat,:customer_location_lng,:customer_location_confirmed_at,'Order Placed')
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
            "base_price": base_price,
            "total": order_total,
            "measurement_mode": measurement_mode,
            "appointment_date": appointment_date,
            "appointment_slot": body.appointment_slot,
            "address": customer_address,
            "expected_completion": expected,
            "notes": body.instructions or body.requirements,
            "customer_location_address": body.customer_location_address if measurement_mode == "tailor_visits_customer" else None,
            "customer_location_lat": body.customer_location_lat if measurement_mode == "tailor_visits_customer" else None,
            "customer_location_lng": body.customer_location_lng if measurement_mode == "tailor_visits_customer" else None,
            "customer_location_confirmed_at": None,
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
        "Booking auto-approved because tailor is available" if status == "auto_approved" else "Tailor is busy; customer added to waiting list",
        "system",
    )
    await add_history(db, order_id, "Order Placed", "Order placed by customer", "customer")
    await notify(
        db,
        "tailor:" + tailor["id"],
        "New TailoraHub booking" if status == "auto_approved" else "New waiting-list customer",
        f"{customer['name']} booked {service.get('service_name') or service.get('name')} ({code}).",
        order_id,
    )
    await notify(
        db,
        "user:" + customer["id"],
        "Booking auto-approved" if status == "auto_approved" else "You are on the waiting list",
        f"{tailor['shop']} {'received your booking.' if status == 'auto_approved' else 'is currently busy. You are on the waiting list.'}",
        order_id,
    )
    await db.commit()
    final = await fetch_one(
        db,
        "SELECT o.*, t.shop, u.name AS customer_name FROM orders o JOIN tailors t ON t.id=o.tailor_id JOIN users u ON u.id=o.customer_id WHERE o.id=:id",
        {"id": order_id},
    )
    return {
        "booking": public_booking(final),
        "code": code,
        "status": status,
        "message": "Booking auto-approved." if status == "auto_approved" else "Tailor is currently busy — you're on the waiting list.",
    }


@router.get("/{booking_id}/status")
async def booking_status(
    booking_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    order = await get_accessible_order(db, booking_id, user)
    return await tracker_status_payload(db, order)


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
    return await payment_breakdown_for_order(db, order)


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
        if body.preferred_date < date.today():
            raise HTTPException(400, "Delivery date cannot be in the past.")
        appointment_date = order.get("appointment_date")
        if isinstance(appointment_date, datetime):
            appointment_date = appointment_date.date()
        if appointment_date and appointment_date > latest_measurement_appointment_date(body.preferred_date):
            raise HTTPException(400, "Delivery date must stay at least 3 days after the measurement appointment.")

    await db.execute(
        text(
            """
            UPDATE orders
            SET notes=COALESCE(:notes, notes),
                expected_completion=COALESCE(:expected_completion, expected_completion)
            WHERE id=:id
            """
        ),
        {
            "id": booking_id,
            "notes": body.instructions,
            "expected_completion": body.preferred_date,
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
    stage = body.tracker_stage.strip()
    if stage not in TRACKER_STAGES:
        raise HTTPException(400, "Invalid tracker stage")
    if stage == "Delivered":
        raise HTTPException(409, "Delivery stage is completed only after payment and handover OTP verification")
    order = await fetch_one(
        db,
        "SELECT * FROM orders WHERE id=:id AND tailor_id=:tailor_id FOR UPDATE",
        {"id": booking_id, "tailor_id": tailor["id"]},
    )
    if not order:
        raise HTTPException(404, "Booking not found")
    if is_completed_order(order):
        raise HTTPException(409, "This order is already completed. Status updates are disabled after handover OTP verification.")
    next_status = STAGE_TO_STATUS.get(stage, order.get("status"))
    update_sql = "UPDATE orders SET tracker_stage=:stage, status=:status WHERE id=:id"
    if stage == "Measurement Done":
        update_sql = "UPDATE orders SET tracker_stage=:stage, status=:status, measurement_done_at=COALESCE(measurement_done_at, now()) WHERE id=:id"
    await db.execute(text(update_sql), {"id": booking_id, "stage": stage, "status": next_status})
    await add_history(db, booking_id, stage, body.note or f"Tracker moved to {stage}", "tailor")
    await notify(db, "user:" + order["customer_id"], "TailoraHub order tracker update", f"Order {order['code']} status: {stage}.", booking_id)
    await db.commit()
    updated = await fetch_one(
        db,
        "SELECT o.*, t.shop, u.name AS customer_name FROM orders o JOIN tailors t ON t.id=o.tailor_id JOIN users u ON u.id=o.customer_id WHERE o.id=:id",
        {"id": booking_id},
    )
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
    key_id, key_secret = razorpay_credentials()
    if not key_id or not key_secret:
        raise HTTPException(503, "Razorpay keys are not configured. Add RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET in the backend environment.")

    await latest_payment_intent(db, booking_id)
    active_intent = await fetch_one(
        db,
        """
        SELECT *
        FROM payment_intents
        WHERE booking_id=:booking_id
          AND status='pending'
          AND expires_at > now()
          AND method='razorpay'
          AND gateway_order_id IS NOT NULL
        ORDER BY created_at DESC
        LIMIT 1
        """,
        {"booking_id": booking_id},
    )
    if active_intent:
        intent = payment_intent_payload(active_intent)
        checkout = razorpay_public_checkout_payload(order, active_intent, breakdown, key_id)
        return {
            "ok": True,
            "provider": "razorpay",
            "booking": public_booking(order),
            "breakdown": breakdown,
            "paymentIntent": intent,
            "payment_intent": intent,
            "checkout": checkout,
            "razorpayCheckout": checkout,
            "message": "Razorpay checkout is ready. Complete payment before the order expires.",
        }

    app_settings = get_settings()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=max(1, app_settings.manual_payment_expiry_minutes))
    order_amount = money_decimal(breakdown["order_amount"])
    payable_total = money_decimal(breakdown["payable_total"])
    payment_reference = f"THPAY-{str(order.get('code') or booking_id).replace('ORD-', '')}-{uuid.uuid4().hex[:6].upper()}"

    await db.execute(
        text("UPDATE payment_intents SET status='cancelled', updated_at=now() WHERE booking_id=:booking_id AND status='pending'"),
        {"booking_id": booking_id},
    )
    razorpay_order = await create_razorpay_order(
        key_id,
        key_secret,
        {
            "amount": amount_to_paise(payable_total),
            "currency": "INR",
            "receipt": payment_reference[:40],
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
    _, key_secret = razorpay_credentials()
    if not key_secret:
        raise HTTPException(503, "Razorpay keys are not configured on the backend.")
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
            "photo_url": body.photo_url,
            "photo_name": body.photo_name,
            "photo_media_type": body.photo_media_type,
        },
    )
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
            WHERE o.tailor_id=:tailor_id AND o.status='waiting_list'
            ORDER BY o.ts ASC
            """
        ),
        {"tailor_id": tailor["id"]},
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
    if order["status"] != "waiting_list":
        raise HTTPException(409, "Only waiting-list bookings can be confirmed from this queue")

    await db.execute(
        text("UPDATE orders SET status='measurement_pending', tracker_stage='Measurement Scheduled' WHERE id=:id"),
        {"id": booking_id},
    )
    await add_history(db, booking_id, "Measurement Scheduled", "Tailor confirmed this waiting-list booking", "tailor")
    await notify(db, "user:" + order["customer_id"], "Tailor confirmed your booking", f"{tailor['shop']} confirmed order {order['code']}. Measurement is pending.", booking_id)
    await db.commit()
    updated = await fetch_one(
        db,
        "SELECT o.*, t.shop, u.name AS customer_name FROM orders o JOIN tailors t ON t.id=o.tailor_id JOIN users u ON u.id=o.customer_id WHERE o.id=:id",
        {"id": booking_id},
    )
    await tracker_connections.broadcast(booking_id, jsonable_encoder(await tracker_status_payload(db, updated)))
    return {"booking": public_booking(updated), "message": "Booking moved to measurement pending."}


@router.post("/{booking_id}/measurement-done")
async def measurement_done(
    booking_id: str,
    tailor: dict = Depends(get_current_tailor),
    db: AsyncSession = Depends(get_db),
) -> dict:
    order = await fetch_one(
        db,
        "SELECT * FROM orders WHERE id=:id AND tailor_id=:tailor_id FOR UPDATE",
        {"id": booking_id, "tailor_id": tailor["id"]},
    )
    if not order:
        raise HTTPException(404, "Booking not found")
    if is_completed_order(order):
        raise HTTPException(409, "This order is already completed. Measurement updates are disabled.")
    if order["status"] not in {"auto_approved", "tailor_confirmed", "measurement_pending"}:
        raise HTTPException(409, "Measurement can be marked done only after booking approval")
    await db.execute(
        text("UPDATE orders SET status='measurement_done', measurement_done_at=now(), tracker_stage='Measurement Done' WHERE id=:id"),
        {"id": booking_id},
    )
    await add_history(db, booking_id, "Measurement Done", "Measurements completed", "tailor")
    await notify(db, "user:" + order["customer_id"], "Measurement completed", f"Measurements for order {order['code']} are completed. Tracker will begin now.", booking_id)
    await db.commit()
    updated = await fetch_one(
        db,
        "SELECT o.*, t.shop, u.name AS customer_name FROM orders o JOIN tailors t ON t.id=o.tailor_id JOIN users u ON u.id=o.customer_id WHERE o.id=:id",
        {"id": booking_id},
    )
    await tracker_connections.broadcast(booking_id, jsonable_encoder(await tracker_status_payload(db, updated)))
    return {"booking": public_booking(updated), "message": "Measurement marked done."}


@router.websocket("/{booking_id}/track")
async def track_booking(websocket: WebSocket, booking_id: str) -> None:
    await tracker_connections.connect(booking_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        tracker_connections.disconnect(booking_id, websocket)
