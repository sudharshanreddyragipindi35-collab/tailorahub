from __future__ import annotations

from decimal import Decimal
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_customer
from app.core.database import get_db
from app.integrations import payment_service
from app.qr import wallet_payment_token
from app.schemas.payments import QrPaymentIn, QrPaymentOut


router = APIRouter()


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


@router.post("/pay", response_model=QrPaymentOut)
async def pay_wallet_qr(
    body: QrPaymentIn,
    customer: dict = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db),
) -> dict:
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
