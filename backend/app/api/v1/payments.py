from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
import logging
import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_customer
from app.core.database import get_db
from app.integrations import payment_service
from app.qr import wallet_payment_token
from app.schemas.payments import QrPaymentIn, QrPaymentOut
from app.services.tracker_service import tracker_connections
from app.services.webhook_service import verify_payment_webhook_signature
from app.settings import settings
from app.observability import emit_metric


router = APIRouter()
logger = logging.getLogger(__name__)


def uid(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


async def fetch_one(db: AsyncSession, sql: str, params: dict | None = None) -> dict | None:
    result = await db.execute(text(sql), params or {})
    row = result.mappings().first()
    return dict(row) if row else None


def wallet_id_from_token(token: str) -> str:
    value = token.strip()
    prefix = "tailorahub:wallet:"
    if value.startswith(prefix):
        value = value[len(prefix):]
    try:
        uuid.UUID(value)
        return value
    except ValueError:
        raise HTTPException(400, "Invalid wallet payment token")


@router.get("/scaffold")
async def payments_scaffold() -> dict:
    return {"module": "payments", "ready": True}


def _razorpay_entities(payload: dict) -> tuple[str, str | None, str | None]:
    event_type = str(payload.get("event") or "unknown")
    entities = payload.get("payload") if isinstance(payload.get("payload"), dict) else {}
    payment = entities.get("payment", {}).get("entity", {}) if isinstance(entities.get("payment"), dict) else {}
    order = entities.get("order", {}).get("entity", {}) if isinstance(entities.get("order"), dict) else {}
    payment_id = str(payment.get("id")) if payment.get("id") else None
    order_id = payment.get("order_id") or order.get("id")
    return event_type, str(order_id) if order_id else None, payment_id


@router.post("/webhooks/razorpay")
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: str | None = Header(default=None, alias="X-Razorpay-Signature"),
    x_razorpay_event_id: str | None = Header(default=None, alias="X-Razorpay-Event-Id"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    raw_payload = await request.body()
    if not settings.razorpay_webhook_secret and not settings.payment_webhook_secret:
        emit_metric("PaymentWebhookFailure", 1, Category="not_configured")
        raise HTTPException(503, "Payment webhook verification is not configured.")
    if not x_razorpay_signature or not verify_payment_webhook_signature(raw_payload, x_razorpay_signature):
        logger.warning("razorpay_webhook_rejected category=invalid_signature")
        emit_metric("PaymentWebhookFailure", 1, Category="invalid_signature")
        raise HTTPException(401, "Invalid Razorpay webhook signature.")
    try:
        payload = json.loads(raw_payload)
    except json.JSONDecodeError:
        raise HTTPException(400, "Invalid webhook payload.")
    if not isinstance(payload, dict):
        raise HTTPException(400, "Invalid webhook payload.")

    payload_hash = hashlib.sha256(raw_payload).hexdigest()
    event_type, gateway_order_id, gateway_payment_id = _razorpay_entities(payload)
    event_id = (x_razorpay_event_id or f"{event_type}:{gateway_payment_id or gateway_order_id or payload_hash[:24]}")[:240]
    inserted = await db.execute(
        text(
            """
            INSERT INTO payment_webhook_events
              (provider,event_id,event_type,payload_sha256,status,gateway_order_id,gateway_payment_id)
            VALUES ('razorpay',:event_id,:event_type,:payload_hash,'processing',:order_id,:payment_id)
            ON CONFLICT (provider,event_id) DO NOTHING
            RETURNING event_id
            """
        ),
        {
            "event_id": event_id,
            "event_type": event_type,
            "payload_hash": payload_hash,
            "order_id": gateway_order_id,
            "payment_id": gateway_payment_id,
        },
    )
    claimed = inserted.mappings().first()
    if not claimed:
        existing = await fetch_one(
            db,
            "SELECT status,payload_sha256,updated_at FROM payment_webhook_events WHERE provider='razorpay' AND event_id=:event_id",
            {"event_id": event_id},
        )
        if existing and existing["payload_sha256"] != payload_hash:
            raise HTTPException(409, "Webhook event identifier was reused with different content.")
        processing_is_fresh = (
            existing
            and existing["status"] == "processing"
            and existing.get("updated_at")
            and (
                datetime.now(timezone.utc)
                - (
                    existing["updated_at"]
                    if existing["updated_at"].tzinfo
                    else existing["updated_at"].replace(tzinfo=timezone.utc)
                )
            ).total_seconds() < 300
        )
        if existing and (existing["status"] in {"completed", "ignored"} or processing_is_fresh):
            return {"ok": True, "duplicate": True, "status": existing["status"]}
        await db.execute(
            text("UPDATE payment_webhook_events SET status='processing',last_error=NULL,updated_at=now() WHERE provider='razorpay' AND event_id=:event_id"),
            {"event_id": event_id},
        )
    await db.commit()

    supported = event_type in {"payment.captured", "order.paid"}
    if not supported or not gateway_order_id or not gateway_payment_id:
        await db.execute(
            text("UPDATE payment_webhook_events SET status='ignored',processed_at=now(),updated_at=now() WHERE provider='razorpay' AND event_id=:event_id"),
            {"event_id": event_id},
        )
        await db.commit()
        return {"ok": True, "status": "ignored"}

    try:
        intent = await fetch_one(
            db,
            "SELECT * FROM payment_intents WHERE method='razorpay' AND gateway_order_id=:order_id ORDER BY created_at DESC LIMIT 1 FOR UPDATE",
            {"order_id": gateway_order_id},
        )
        if not intent:
            await db.execute(
                text("UPDATE payment_webhook_events SET status='ignored',processed_at=now(),updated_at=now() WHERE provider='razorpay' AND event_id=:event_id"),
                {"event_id": event_id},
            )
            await db.commit()
            return {"ok": True, "status": "ignored"}
        order = await fetch_one(
            db,
            """
            SELECT o.*,t.shop,t.tailor_id AS tailor_uuid,u.name AS customer_name,u.email AS customer_email,u.phone AS customer_phone
            FROM orders o JOIN tailors t ON t.id=o.tailor_id JOIN users u ON u.id=o.customer_id
            WHERE o.id=:booking_id FOR UPDATE
            """,
            {"booking_id": intent["booking_id"]},
        )
        if not order:
            raise RuntimeError("Webhook booking record was not found")
        if str(order.get("payment_status") or "").lower() != "paid" and intent.get("status") != "verified":
            from app.api.v1.bookings import mark_gateway_payment_paid, tracker_status_payload

            await mark_gateway_payment_paid(
                db,
                order,
                intent,
                gateway_payment_id,
                "webhook_signature_verified",
                {
                    "event": event_type,
                    "razorpay_order_id": gateway_order_id,
                    "razorpay_payment_id": gateway_payment_id,
                    "verification": "webhook_signature_valid",
                },
            )
        await db.execute(
            text(
                "UPDATE payment_webhook_events SET status='completed',booking_id=:booking_id,processed_at=now(),updated_at=now() "
                "WHERE provider='razorpay' AND event_id=:event_id"
            ),
            {"booking_id": order["id"], "event_id": event_id},
        )
        await db.commit()
        from app.api.v1.bookings import tracker_status_payload

        updated = await fetch_one(
            db,
            "SELECT o.*,t.shop,u.name AS customer_name FROM orders o JOIN tailors t ON t.id=o.tailor_id JOIN users u ON u.id=o.customer_id WHERE o.id=:id",
            {"id": order["id"]},
        )
        tracker_payload = await tracker_status_payload(db, updated)
        await tracker_connections.broadcast(order["id"], jsonable_encoder(tracker_payload))
        return {"ok": True, "status": "completed"}
    except Exception as exc:
        await db.rollback()
        await db.execute(
            text("UPDATE payment_webhook_events SET status='failed',last_error=:error,updated_at=now() WHERE provider='razorpay' AND event_id=:event_id"),
            {"error": type(exc).__name__, "event_id": event_id},
        )
        await db.commit()
        logger.exception("razorpay_webhook_processing_failed event_id=%s category=%s", event_id, type(exc).__name__)
        emit_metric("PaymentWebhookFailure", 1, Category="processing_failed")
        raise HTTPException(500, "Webhook processing failed and may be retried.")


@router.post("/pay", response_model=QrPaymentOut)
async def pay_wallet_qr(
    body: QrPaymentIn,
    customer: dict = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if settings.payment_provider != "mock":
        raise HTTPException(409, "Direct wallet QR credit is disabled for live payments. Use verified Razorpay booking checkout.")
    wallet_id = wallet_id_from_token(body.payment_token)
    wallet = await fetch_one(
        db,
        """SELECT w.wallet_id, w.balance, t.id AS tailor_pk
           FROM tailor_wallets w
           JOIN tailors t ON t.tailor_id=w.tailor_id
           WHERE w.wallet_id=:wallet_id""",
        {"wallet_id": wallet_id},
    )
    if not wallet:
        raise HTTPException(404, "Wallet payment token was not found")

    order = None
    if body.booking_id:
        order = await fetch_one(
            db,
            """SELECT * FROM orders
               WHERE id=:booking_id AND customer_id=:customer_id""",
            {"booking_id": body.booking_id, "customer_id": customer["id"]},
        )
        if not order:
            raise HTTPException(404, "Booking was not found for this customer")
        if order["tailor_id"] != wallet["tailor_pk"]:
            raise HTTPException(400, "This QR does not belong to the booking tailor")

    amount = Decimal(body.amount)
    payment_ref = body.gateway_reference or body.booking_id or wallet_payment_token(wallet_id)
    payment = payment_service().capture(int(amount), payment_ref, body.method or "qr")
    ok = bool(payment.get("ok")) and payment.get("status") != "failed"
    status = "success" if ok else "failed"
    txn_ref = payment.get("txnRef")

    try:
        await db.execute(
            text(
                """INSERT INTO wallet_transactions (id,wallet_id,type,amount,reference_booking_id,status)
                   VALUES (gen_random_uuid(),:wallet_id,'credit',:amount,:booking_id,CAST(:status AS wallet_transaction_status))"""
            ),
            {"wallet_id": wallet_id, "amount": amount, "booking_id": body.booking_id, "status": status},
        )
        if ok:
            await db.execute(
                text("UPDATE tailor_wallets SET balance=balance + :amount, updated_at=now() WHERE wallet_id=:wallet_id"),
                {"wallet_id": wallet_id, "amount": amount},
            )
            if order:
                existing_payment = await fetch_one(db, "SELECT id FROM payments WHERE order_id=:order_id ORDER BY ts DESC LIMIT 1", {"order_id": order["id"]})
                await db.execute(
                    text("UPDATE orders SET payment_status='PAID', status=CASE WHEN status='PAYMENT_PENDING' THEN 'PAYMENT_COMPLETED' ELSE status END WHERE id=:id"),
                    {"id": order["id"]},
                )
                if existing_payment:
                    await db.execute(
                        text("UPDATE payments SET amount=:amount, method='qr', status='PAID', txn_ref=:txn_ref, updated=now() WHERE id=:id"),
                        {"id": existing_payment["id"], "amount": amount, "txn_ref": txn_ref},
                    )
                else:
                    await db.execute(
                        text("INSERT INTO payments (id,order_id,amount,method,status,txn_ref) VALUES (:id,:order_id,:amount,'qr','PAID',:txn_ref)"),
                        {"id": uid("pay"), "order_id": order["id"], "amount": amount, "txn_ref": txn_ref},
                    )
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    return {
        "ok": ok,
        "provider": payment.get("provider", "mock"),
        "status": status,
        "txn_ref": txn_ref,
        "wallet_id": wallet_id,
        "amount": amount,
    }
