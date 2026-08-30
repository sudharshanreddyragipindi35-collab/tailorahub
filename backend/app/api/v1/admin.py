from __future__ import annotations

import csv
from datetime import date
from decimal import Decimal
from io import StringIO
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.core.database import get_db
from app.pagination import PageParams
from app.qr import generate_wallet_qr
from app.schemas.admin import PlatformSettingsIn
from app.services.media_storage import get_media_storage


router = APIRouter()
DISPUTE_STATUSES = {"open", "in_review", "resolved", "rejected"}


class AdminDisputePatchIn(BaseModel):
    status: str
    resolution_notes: str | None = Field(default=None, alias="resolutionNotes")
    refund_amount: Decimal | None = Field(default=None, alias="refundAmount", ge=0)


class PaymentIntentVerifyIn(BaseModel):
    proof_reference: str = Field(alias="proofReference", min_length=2, max_length=160)
    admin_note: str | None = Field(default=None, alias="adminNote", max_length=1000)


class PaymentIntentRejectIn(BaseModel):
    admin_note: str | None = Field(default=None, alias="adminNote", max_length=1000)


class WithdrawalDecisionIn(BaseModel):
    payout_reference: str | None = Field(default=None, alias="payoutReference", max_length=160)
    admin_note: str | None = Field(default=None, alias="adminNote", max_length=1000)


def money_decimal(value) -> Decimal:
    return Decimal(str(value or 0)).quantize(Decimal("0.01"))


def uid(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


async def _fetch_one(db: AsyncSession, sql: str, params: dict | None = None) -> dict | None:
    result = await db.execute(text(sql), params or {})
    row = result.mappings().first()
    return dict(row) if row else None


@router.get("/scaffold")
async def admin_scaffold(_: dict = Depends(require_admin)) -> dict:
    return {"module": "admin", "ready": True}


@router.get("/finance/settings")
async def finance_settings(
    _: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    settings = await _ensure_platform_settings(db)
    await db.commit()
    return _settings_payload(settings)


@router.patch("/finance/settings")
async def update_finance_settings(
    body: PlatformSettingsIn,
    _: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    result = await db.execute(
        text(
            """
            INSERT INTO platform_settings
              (id,commission_percentage,gst_percentage,platform_fee_percentage,updated_at)
            VALUES
              (1,:commission,:gst,:platform_fee,now())
            ON CONFLICT (id) DO UPDATE SET
              commission_percentage=EXCLUDED.commission_percentage,
              gst_percentage=EXCLUDED.gst_percentage,
              platform_fee_percentage=EXCLUDED.platform_fee_percentage,
              updated_at=now()
            RETURNING *
            """
        ),
        {
            "commission": body.commission_percentage,
            "gst": body.gst_percentage,
            "platform_fee": body.platform_fee_percentage,
        },
    )
    await db.commit()
    return _settings_payload(dict(result.mappings().first()))


@router.get("/finance/wallet")
async def finance_wallet(
    date_from: date | None = Query(default=None, alias="dateFrom"),
    date_to: date | None = Query(default=None, alias="dateTo"),
    page: PageParams = Depends(PageParams),
    _: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    wallet = await _ensure_admin_wallet(db)
    totals, transactions = await _admin_wallet_transactions(db, date_from, date_to, page.limit, page.offset)
    await db.commit()
    return _admin_wallet_payload(wallet, totals, transactions)


@router.get("/finance/wallet/export")
async def finance_wallet_export(
    date_from: date | None = Query(default=None, alias="dateFrom"),
    date_to: date | None = Query(default=None, alias="dateTo"),
    _: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> Response:
    _, transactions = await _admin_wallet_transactions(db, date_from, date_to, 5000, 0)
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "type", "amount", "order_code", "source_booking_id", "tailor", "customer", "created_at"])
    for row in transactions:
        writer.writerow([
            row["id"],
            row["type"],
            row["amount"],
            row.get("orderCode") or row.get("order_code"),
            row.get("sourceBookingId") or row.get("source_booking_id"),
            row.get("shop") or "",
            row.get("customerName") or row.get("customer_name") or "",
            row.get("createdAt") or row.get("created_at") or "",
        ])
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=admin-wallet-transactions.csv"},
    )


@router.get("/payment-intents")
async def payment_intents(
    page: PageParams = Depends(PageParams),
    _: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    await db.execute(text("UPDATE payment_intents SET status='expired', updated_at=now() WHERE status='pending' AND expires_at <= now()"))
    result = await db.execute(
        text(
            """
            SELECT
              pi.*,
              o.code AS order_code,
              o.status AS order_status,
              o.payment_status AS order_payment_status,
              u.name AS customer_name,
              u.phone AS customer_phone,
              t.shop,
              t.owner_name
            FROM payment_intents pi
            JOIN orders o ON o.id=pi.booking_id
            JOIN users u ON u.id=pi.customer_id
            JOIN tailors t ON t.id=pi.tailor_id
            ORDER BY
              CASE pi.status WHEN 'pending' THEN 1 WHEN 'verified' THEN 2 WHEN 'expired' THEN 3 ELSE 4 END,
              pi.created_at DESC
            LIMIT :limit OFFSET :offset
            """
        ),
        page.sql,
    )
    await db.commit()
    return [_payment_intent_admin_payload(dict(row)) for row in result.mappings().all()]


@router.post("/payment-intents/{intent_id}/verify")
async def verify_payment_intent(
    intent_id: str,
    body: PaymentIntentVerifyIn,
    admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    intent = await _payment_intent_for_update(db, intent_id)
    if not intent:
        raise HTTPException(404, "Payment request not found")
    if intent.get("is_expired") and intent.get("status") == "pending":
        await db.execute(text("UPDATE payment_intents SET status='expired', updated_at=now() WHERE id=:id"), {"id": intent_id})
        await db.commit()
        raise HTTPException(409, "This payment request expired. Ask the customer to start a new payment request.")
    if intent.get("status") != "pending":
        raise HTTPException(409, f"This payment request is already {intent.get('status')}.")
    if str(intent.get("method") or "").lower() == "razorpay":
        raise HTTPException(409, "Razorpay payments must be verified by the secure Razorpay signature flow, not manual admin approval.")

    order = await _order_for_update(db, intent["booking_id"])
    if not order:
        raise HTTPException(404, "Order not found")
    if str(order.get("payment_status") or "").lower() == "paid":
        await db.execute(
            text(
                """
                UPDATE payment_intents
                SET status='verified', proof_reference=:proof, admin_note=:note,
                    verified_at=COALESCE(verified_at, now()), verified_by_admin_id=:admin_id, updated_at=now()
                WHERE id=:id
                """
            ),
            {"id": intent_id, "proof": body.proof_reference, "note": body.admin_note, "admin_id": admin["id"]},
        )
        await db.commit()
        return {"ok": True, "message": "Order was already paid. Payment request marked verified."}

    tailor_wallet = await _ensure_tailor_wallet(db, order["tailor_uuid"])
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
    await _credit_admin_wallet(db, "gst_platform_charge", admin_charge, order["id"], source_customer_id=order["customer_id"])
    await _credit_admin_wallet(db, "commission", commission, order["id"], source_tailor_id=order["tailor_uuid"])
    payment = await _fetch_one(db, "SELECT * FROM payments WHERE order_id=:id ORDER BY ts DESC LIMIT 1", {"id": order["id"]})
    if payment:
        await db.execute(
            text("UPDATE payments SET amount=:amount, method='manual_admin', status='paid', txn_ref=:txn, updated=now() WHERE id=:id"),
            {"id": payment["id"], "amount": payable_total, "txn": intent["payment_reference"]},
        )
    else:
        await db.execute(
            text("INSERT INTO payments (id,order_id,amount,method,status,txn_ref) VALUES (:id,:order_id,:amount,'manual_admin','paid',:txn)"),
            {"id": uid("pay"), "order_id": order["id"], "amount": payable_total, "txn": intent["payment_reference"]},
        )
    await db.execute(
        text(
            """
            UPDATE payment_intents
            SET status='verified', proof_reference=:proof, admin_note=:note,
                verified_at=now(), verified_by_admin_id=:admin_id, updated_at=now()
            WHERE id=:id
            """
        ),
        {"id": intent_id, "proof": body.proof_reference, "note": body.admin_note, "admin_id": admin["id"]},
    )
    await _add_history(db, order["id"], "paid", f"Admin verified manual payment {intent['payment_reference']}. Tailor wallet credited net amount {tailor_credit}.", "admin")
    await _notify(db, "user:" + order["customer_id"], "Payment verified", f"Payment for order {order['code']} is verified. Delivery OTP is now enabled.", order["id"])
    await _notify(db, "tailor:" + order["tailor_id"], "Payment verified", f"Payment for order {order['code']} is verified. Net wallet credit: Rs {tailor_credit}.", order["id"])
    await db.commit()
    return {"ok": True, "message": "Payment verified. Tailor wallet credited and delivery OTP unlocked."}


@router.post("/payment-intents/{intent_id}/reject")
async def reject_payment_intent(
    intent_id: str,
    body: PaymentIntentRejectIn,
    admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    intent = await _payment_intent_for_update(db, intent_id)
    if not intent:
        raise HTTPException(404, "Payment request not found")
    if intent.get("status") != "pending":
        raise HTTPException(409, f"This payment request is already {intent.get('status')}.")
    await db.execute(
        text(
            """
            UPDATE payment_intents
            SET status='rejected', admin_note=:note, rejected_at=now(),
                verified_by_admin_id=:admin_id, updated_at=now()
            WHERE id=:id
            """
        ),
        {"id": intent_id, "note": body.admin_note, "admin_id": admin["id"]},
    )
    await db.execute(
        text("UPDATE payments SET status='FAILED', updated=now() WHERE txn_ref=:txn"),
        {"txn": intent["payment_reference"]},
    )
    await _notify(db, "user:" + intent["customer_id"], "Payment request rejected", body.admin_note or "Payment proof was not confirmed. Please create a new payment request.", intent["booking_id"])
    await db.commit()
    return {"ok": True, "message": "Payment request rejected."}


@router.get("/withdrawal-requests")
async def withdrawal_requests(
    page: PageParams = Depends(PageParams),
    _: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    result = await db.execute(
        text(
            """
            SELECT
              wr.*,
              tw.balance AS wallet_balance,
              t.id AS tailor_legacy_id,
              t.shop,
              t.owner_name,
              u.name AS tailor_user_name,
              u.phone AS tailor_phone,
              u.email AS tailor_email
            FROM withdrawal_requests wr
            JOIN tailor_wallets tw ON tw.wallet_id=wr.wallet_id
            JOIN tailors t ON t.tailor_id=wr.tailor_id
            JOIN users u ON u.id=t.user_id
            ORDER BY
              CASE wr.status WHEN 'pending_admin_review' THEN 1 WHEN 'approved' THEN 2 ELSE 3 END,
              wr.requested_at DESC
            LIMIT :limit OFFSET :offset
            """
        ),
        page.sql,
    )
    return [_withdrawal_request_payload(dict(row)) for row in result.mappings().all()]


@router.post("/withdrawal-requests/{request_id}/approve")
async def approve_withdrawal_request(
    request_id: str,
    body: WithdrawalDecisionIn,
    admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    request = await _withdrawal_request_for_update(db, request_id)
    if not request:
        raise HTTPException(404, "Withdrawal request not found")
    if request.get("status") != "pending_admin_review":
        raise HTTPException(409, f"This withdrawal request is already {request.get('status')}.")
    amount = money_decimal(request["amount"])
    if money_decimal(request["wallet_balance"]) < amount:
        raise HTTPException(400, "Tailor wallet balance is lower than the requested withdrawal amount.")
    await db.execute(
        text(
            """
            INSERT INTO wallet_transactions (id,wallet_id,type,amount,status,withdrawal_destination)
            VALUES (gen_random_uuid(),:wallet_id,'debit',:amount,'success',CAST(:destination AS withdrawal_destination_type))
            """
        ),
        {"wallet_id": request["wallet_id"], "amount": amount, "destination": request["destination_type"]},
    )
    await db.execute(
        text("UPDATE tailor_wallets SET balance=balance - :amount, updated_at=now() WHERE wallet_id=:wallet_id"),
        {"amount": amount, "wallet_id": request["wallet_id"]},
    )
    await db.execute(
        text(
            """
            UPDATE withdrawal_requests
            SET status='approved', payout_reference=:payout_reference, admin_note=:admin_note,
                approved_at=now(), approved_by_admin_id=:admin_id, updated_at=now()
            WHERE id=:id
            """
        ),
        {
            "id": request_id,
            "payout_reference": body.payout_reference,
            "admin_note": body.admin_note,
            "admin_id": admin["id"],
        },
    )
    await _notify(db, "tailor:" + request["tailor_legacy_id"], "Withdrawal approved", f"Withdrawal of Rs {amount} was approved. Payout reference: {body.payout_reference or 'manual payout'}.", None)
    await db.commit()
    return {"ok": True, "message": "Withdrawal approved and wallet debited."}


@router.post("/withdrawal-requests/{request_id}/reject")
async def reject_withdrawal_request(
    request_id: str,
    body: WithdrawalDecisionIn,
    admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    request = await _withdrawal_request_for_update(db, request_id)
    if not request:
        raise HTTPException(404, "Withdrawal request not found")
    if request.get("status") != "pending_admin_review":
        raise HTTPException(409, f"This withdrawal request is already {request.get('status')}.")
    await db.execute(
        text(
            """
            UPDATE withdrawal_requests
            SET status='rejected', admin_note=:admin_note, rejected_at=now(),
                approved_by_admin_id=:admin_id, updated_at=now()
            WHERE id=:id
            """
        ),
        {"id": request_id, "admin_note": body.admin_note, "admin_id": admin["id"]},
    )
    await _notify(db, "tailor:" + request["tailor_legacy_id"], "Withdrawal rejected", body.admin_note or "Withdrawal request was rejected by admin.", None)
    await db.commit()
    return {"ok": True, "message": "Withdrawal request rejected."}


def _node_from_row(row: dict) -> dict:
    tailor_uuid = str(row["tailor_id"])
    return {
        "tailor_id": tailor_uuid,
        "tailorId": tailor_uuid,
        "legacy_id": row.get("legacy_id"),
        "legacyId": row.get("legacy_id"),
        "shop": row.get("shop"),
        "owner_name": row.get("owner_name"),
        "ownerName": row.get("owner_name"),
        "full_name": row.get("full_name"),
        "fullName": row.get("full_name"),
        "email": row.get("email"),
        "phone_number": row.get("phone_number"),
        "phoneNumber": row.get("phone_number"),
        "referral_code": row.get("referral_code"),
        "referralCode": row.get("referral_code"),
        "referred_by_tailor_id": str(row["referred_by_tailor_id"]) if row.get("referred_by_tailor_id") else None,
        "referredByTailorId": str(row["referred_by_tailor_id"]) if row.get("referred_by_tailor_id") else None,
        "depth": int(row.get("depth") or 0),
        "joined_at": row.get("joined_at").isoformat() if row.get("joined_at") else None,
        "joinedAt": row.get("joined_at").isoformat() if row.get("joined_at") else None,
        "children": [],
    }


def _customer_node_from_row(row: dict) -> dict:
    customer_uuid = str(row["customer_id"])
    return {
        "customer_id": customer_uuid,
        "customerId": customer_uuid,
        "id": row.get("id"),
        "name": row.get("name"),
        "email": row.get("email"),
        "phone": row.get("phone"),
        "profile_image": row.get("profile_image"),
        "profileImage": row.get("profile_image"),
        "referral_code": row.get("referral_code"),
        "referralCode": row.get("referral_code"),
        "referred_by_customer_id": str(row["referred_by_customer_id"]) if row.get("referred_by_customer_id") else None,
        "referredByCustomerId": str(row["referred_by_customer_id"]) if row.get("referred_by_customer_id") else None,
        "depth": int(row.get("depth") or 0),
        "joined_at": row.get("joined_at").isoformat() if row.get("joined_at") else None,
        "joinedAt": row.get("joined_at").isoformat() if row.get("joined_at") else None,
        "children": [],
    }


def _dispute_payload(row: dict) -> dict:
    dispute_id = str(row["id"])
    photo_url = get_media_storage().download_url(row.get("photo_url"))
    return {
        "id": dispute_id,
        "booking_id": row.get("booking_id"),
        "bookingId": row.get("booking_id"),
        "order_code": row.get("order_code"),
        "orderCode": row.get("order_code"),
        "booking_status": row.get("booking_status"),
        "bookingStatus": row.get("booking_status"),
        "customer_id": row.get("customer_id"),
        "customerId": row.get("customer_id"),
        "customer_name": row.get("customer_name"),
        "customerName": row.get("customer_name"),
        "customer_phone": row.get("customer_phone"),
        "customerPhone": row.get("customer_phone"),
        "customer_email": row.get("customer_email"),
        "customerEmail": row.get("customer_email"),
        "tailor_id": row.get("tailor_id"),
        "tailorId": row.get("tailor_id"),
        "shop": row.get("shop"),
        "owner_name": row.get("owner_name"),
        "ownerName": row.get("owner_name"),
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
        "updated_at": row.get("updated_at"),
        "updatedAt": row.get("updated_at"),
        "resolved_at": row.get("resolved_at"),
        "resolvedAt": row.get("resolved_at"),
    }


def _settings_payload(row: dict) -> dict:
    return {
        "id": row.get("id", 1),
        "commission_percentage": row.get("commission_percentage"),
        "commissionPercentage": row.get("commission_percentage"),
        "gst_percentage": row.get("gst_percentage"),
        "gstPercentage": row.get("gst_percentage"),
        "platform_fee_percentage": row.get("platform_fee_percentage"),
        "platformFeePercentage": row.get("platform_fee_percentage"),
        "updated_at": row.get("updated_at"),
        "updatedAt": row.get("updated_at"),
    }


def _admin_wallet_payload(wallet: dict | None, totals: dict, transactions: list[dict]) -> dict:
    balance = wallet.get("balance") if wallet else 0
    return {
        "wallet_id": str(wallet["wallet_id"]) if wallet else None,
        "walletId": str(wallet["wallet_id"]) if wallet else None,
        "balance": balance or 0,
        "commission_total": totals.get("commission_total") or 0,
        "commissionTotal": totals.get("commission_total") or 0,
        "gst_platform_charge_total": totals.get("gst_platform_charge_total") or 0,
        "gstPlatformChargeTotal": totals.get("gst_platform_charge_total") or 0,
        "transactions": transactions,
    }


def _admin_wallet_tx_payload(row: dict) -> dict:
    return {
        "id": str(row["id"]),
        "type": row.get("type"),
        "amount": row.get("amount"),
        "source_booking_id": row.get("source_booking_id"),
        "sourceBookingId": row.get("source_booking_id"),
        "order_code": row.get("order_code"),
        "orderCode": row.get("order_code"),
        "source_tailor_id": str(row["source_tailor_id"]) if row.get("source_tailor_id") else None,
        "sourceTailorId": str(row["source_tailor_id"]) if row.get("source_tailor_id") else None,
        "source_customer_id": row.get("source_customer_id"),
        "sourceCustomerId": row.get("source_customer_id"),
        "shop": row.get("shop"),
        "customer_name": row.get("customer_name"),
        "customerName": row.get("customer_name"),
        "created_at": row.get("created_at"),
        "createdAt": row.get("created_at"),
    }


async def _ensure_platform_settings(db: AsyncSession) -> dict:
    result = await db.execute(
        text("INSERT INTO platform_settings (id) VALUES (1) ON CONFLICT (id) DO UPDATE SET id=EXCLUDED.id RETURNING *")
    )
    return dict(result.mappings().first())


async def _ensure_admin_wallet(db: AsyncSession) -> dict:
    ledger_balance = await _admin_wallet_ledger_balance(db)
    wallet = await db.execute(text("SELECT * FROM admin_wallet ORDER BY updated_at ASC LIMIT 1"))
    row = wallet.mappings().first()
    if row:
        wallet_row = dict(row)
        if money_decimal(wallet_row.get("balance")) != ledger_balance:
            result = await db.execute(
                text("UPDATE admin_wallet SET balance=:balance, updated_at=now() WHERE wallet_id=:wallet_id RETURNING *"),
                {"balance": ledger_balance, "wallet_id": wallet_row["wallet_id"]},
            )
            return dict(result.mappings().first())
        return wallet_row
    result = await db.execute(
        text("INSERT INTO admin_wallet (wallet_id,balance,updated_at) VALUES (gen_random_uuid(),:balance,now()) RETURNING *"),
        {"balance": ledger_balance},
    )
    return dict(result.mappings().first())


async def _admin_wallet_ledger_balance(db: AsyncSession) -> Decimal:
    result = await db.execute(text("SELECT COALESCE(SUM(amount),0) AS balance FROM admin_wallet_transactions"))
    row = result.mappings().first()
    return money_decimal(row["balance"] if row else 0)


async def _admin_wallet_transactions(db: AsyncSession, date_from: date | None, date_to: date | None, limit: int, offset: int) -> tuple[dict, list[dict]]:
    params = {"date_from": date_from, "date_to": date_to, "limit": limit, "offset": offset}
    totals_result = await db.execute(
        text(
            """
            SELECT
              COALESCE(SUM(CASE WHEN type='commission' THEN amount ELSE 0 END),0) AS commission_total,
              COALESCE(SUM(CASE WHEN type='gst_platform_charge' THEN amount ELSE 0 END),0) AS gst_platform_charge_total
            FROM admin_wallet_transactions
            WHERE (CAST(:date_from AS date) IS NULL OR created_at::date >= CAST(:date_from AS date))
              AND (CAST(:date_to AS date) IS NULL OR created_at::date <= CAST(:date_to AS date))
            """
        ),
        params,
    )
    totals = dict(totals_result.mappings().first() or {})
    rows_result = await db.execute(
        text(
            """
            SELECT
              awt.*,
              o.code AS order_code,
              t.shop,
              u.name AS customer_name
            FROM admin_wallet_transactions awt
            LEFT JOIN orders o ON o.id=awt.source_booking_id
            LEFT JOIN tailors t ON t.tailor_id=awt.source_tailor_id
            LEFT JOIN users u ON u.id=awt.source_customer_id
            WHERE (CAST(:date_from AS date) IS NULL OR awt.created_at::date >= CAST(:date_from AS date))
              AND (CAST(:date_to AS date) IS NULL OR awt.created_at::date <= CAST(:date_to AS date))
            ORDER BY awt.created_at DESC
            LIMIT :limit OFFSET :offset
            """
        ),
        params,
    )
    transactions = [_admin_wallet_tx_payload(dict(row)) for row in rows_result.mappings().all()]
    return totals, transactions


def _payment_intent_admin_payload(row: dict) -> dict:
    return {
        "id": str(row["id"]),
        "booking_id": row.get("booking_id"),
        "bookingId": row.get("booking_id"),
        "order_code": row.get("order_code"),
        "orderCode": row.get("order_code"),
        "customer_id": row.get("customer_id"),
        "customerId": row.get("customer_id"),
        "customer_name": row.get("customer_name"),
        "customerName": row.get("customer_name"),
        "customer_phone": row.get("customer_phone"),
        "customerPhone": row.get("customer_phone"),
        "tailor_id": row.get("tailor_id"),
        "tailorId": row.get("tailor_id"),
        "shop": row.get("shop"),
        "owner_name": row.get("owner_name"),
        "ownerName": row.get("owner_name"),
        "payment_reference": row.get("payment_reference"),
        "paymentReference": row.get("payment_reference"),
        "method": row.get("method"),
        "status": row.get("status"),
        "order_status": row.get("order_status"),
        "orderStatus": row.get("order_status"),
        "order_payment_status": row.get("order_payment_status"),
        "orderPaymentStatus": row.get("order_payment_status"),
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
        "proof_reference": row.get("proof_reference"),
        "proofReference": row.get("proof_reference"),
        "admin_note": row.get("admin_note"),
        "adminNote": row.get("admin_note"),
        "expires_at": row.get("expires_at"),
        "expiresAt": row.get("expires_at"),
        "created_at": row.get("created_at"),
        "createdAt": row.get("created_at"),
        "verified_at": row.get("verified_at"),
        "verifiedAt": row.get("verified_at"),
        "rejected_at": row.get("rejected_at"),
        "rejectedAt": row.get("rejected_at"),
    }


def _withdrawal_request_payload(row: dict) -> dict:
    destination = row.get("destination_upi_id") or row.get("destination_bank_account_number") or "-"
    return {
        "id": str(row["id"]),
        "wallet_id": str(row["wallet_id"]),
        "walletId": str(row["wallet_id"]),
        "tailor_id": str(row["tailor_id"]),
        "tailorId": str(row["tailor_id"]),
        "tailor_legacy_id": row.get("tailor_legacy_id"),
        "tailorLegacyId": row.get("tailor_legacy_id"),
        "shop": row.get("shop"),
        "owner_name": row.get("owner_name"),
        "ownerName": row.get("owner_name"),
        "tailor_user_name": row.get("tailor_user_name"),
        "tailorUserName": row.get("tailor_user_name"),
        "tailor_phone": row.get("tailor_phone"),
        "tailorPhone": row.get("tailor_phone"),
        "tailor_email": row.get("tailor_email"),
        "tailorEmail": row.get("tailor_email"),
        "amount": row.get("amount"),
        "wallet_balance": row.get("wallet_balance"),
        "walletBalance": row.get("wallet_balance"),
        "destination_type": row.get("destination_type"),
        "destinationType": row.get("destination_type"),
        "destination": destination,
        "destination_upi_id": row.get("destination_upi_id"),
        "destinationUpiId": row.get("destination_upi_id"),
        "destination_bank_account_number": row.get("destination_bank_account_number"),
        "destinationBankAccountNumber": row.get("destination_bank_account_number"),
        "destination_bank_ifsc": row.get("destination_bank_ifsc"),
        "destinationBankIfsc": row.get("destination_bank_ifsc"),
        "status": row.get("status"),
        "admin_note": row.get("admin_note"),
        "adminNote": row.get("admin_note"),
        "payout_reference": row.get("payout_reference"),
        "payoutReference": row.get("payout_reference"),
        "requested_at": row.get("requested_at"),
        "requestedAt": row.get("requested_at"),
        "approved_at": row.get("approved_at"),
        "approvedAt": row.get("approved_at"),
        "rejected_at": row.get("rejected_at"),
        "rejectedAt": row.get("rejected_at"),
    }


async def _payment_intent_for_update(db: AsyncSession, intent_id: str) -> dict | None:
    return await _fetch_one(
        db,
        """
        SELECT pi.*, (pi.expires_at <= now()) AS is_expired
        FROM payment_intents pi
        WHERE pi.id=:id
        FOR UPDATE
        """,
        {"id": intent_id},
    )


async def _order_for_update(db: AsyncSession, booking_id: str) -> dict | None:
    return await _fetch_one(
        db,
        """
        SELECT o.*, t.tailor_id AS tailor_uuid
        FROM orders o
        JOIN tailors t ON t.id=o.tailor_id
        WHERE o.id=:id
        FOR UPDATE
        """,
        {"id": booking_id},
    )


async def _ensure_tailor_wallet(db: AsyncSession, tailor_uuid) -> dict:
    row = await _fetch_one(db, "SELECT * FROM tailor_wallets WHERE tailor_id=:tailor_id", {"tailor_id": tailor_uuid})
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


async def _credit_admin_wallet(
    db: AsyncSession,
    txn_type: str,
    amount: Decimal,
    booking_id: str,
    source_tailor_id=None,
    source_customer_id=None,
) -> None:
    if money_decimal(amount) <= 0:
        return
    existing = await _fetch_one(
        db,
        "SELECT 1 FROM admin_wallet_transactions WHERE source_booking_id=:booking_id AND type=CAST(:type AS admin_wallet_transaction_type) LIMIT 1",
        {"booking_id": booking_id, "type": txn_type},
    )
    if existing:
        return
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
            "amount": money_decimal(amount),
            "booking_id": booking_id,
            "tailor_id": source_tailor_id,
            "customer_id": source_customer_id,
        },
    )
    await _ensure_admin_wallet(db)


async def _notify(db: AsyncSession, to_ref: str, title: str, body: str, order_id: str | None = None) -> None:
    await db.execute(
        text("INSERT INTO notifications (id,to_ref,channel,title,body,order_id) VALUES (:id,:to_ref,'in_app',:title,:body,:order_id)"),
        {"id": uid("n"), "to_ref": to_ref, "title": title, "body": body, "order_id": order_id},
    )


async def _add_history(db: AsyncSession, order_id: str, status: str, note: str, by_role: str) -> None:
    await db.execute(
        text("INSERT INTO order_status_history (order_id,status,note,by_role) VALUES (:order_id,:status,:note,:by_role)"),
        {"order_id": order_id, "status": status, "note": note, "by_role": by_role},
    )


async def _withdrawal_request_for_update(db: AsyncSession, request_id: str) -> dict | None:
    return await _fetch_one(
        db,
        """
        SELECT
          wr.*,
          tw.balance AS wallet_balance,
          t.id AS tailor_legacy_id,
          t.shop,
          t.owner_name,
          u.name AS tailor_user_name,
          u.phone AS tailor_phone,
          u.email AS tailor_email
        FROM withdrawal_requests wr
        JOIN tailor_wallets tw ON tw.wallet_id=wr.wallet_id
        JOIN tailors t ON t.tailor_id=wr.tailor_id
        JOIN users u ON u.id=t.user_id
        WHERE wr.id=:id
        FOR UPDATE OF wr, tw
        """,
        {"id": request_id},
    )


@router.get("/referrals/tree/{tailor_id}")
async def referral_tree(
    tailor_id: str,
    max_nodes: int = Query(default=500, alias="maxNodes", ge=1, le=2000),
    _: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    root_result = await db.execute(
        text(
            """
            SELECT tailor_id
            FROM tailors
            WHERE tailor_id::text=:tailor_id OR id=:tailor_id
            LIMIT 1
            """
        ),
        {"tailor_id": tailor_id},
    )
    root_uuid = root_result.scalar_one_or_none()
    if not root_uuid:
        raise HTTPException(status_code=404, detail="Tailor not found")

    result = await db.execute(
        text(
            """
            WITH RECURSIVE referral_tree AS (
              SELECT
                t.tailor_id,
                t.id AS legacy_id,
                t.shop,
                t.owner_name,
                t.full_name,
                t.email,
                t.phone_number,
                t.referral_code,
                t.referred_by_tailor_id,
                NULL::uuid AS parent_tailor_id,
                0::int AS depth,
                ARRAY[t.tailor_id] AS path,
                COALESCE(t.created_at, t.created) AS joined_at
              FROM tailors t
              WHERE t.tailor_id=:root_uuid

              UNION ALL

              SELECT
                child.tailor_id,
                child.id AS legacy_id,
                child.shop,
                child.owner_name,
                child.full_name,
                child.email,
                child.phone_number,
                child.referral_code,
                child.referred_by_tailor_id,
                parent.tailor_id AS parent_tailor_id,
                parent.depth + 1 AS depth,
                parent.path || child.tailor_id AS path,
                COALESCE(child.created_at, child.created) AS joined_at
              FROM tailors child
              JOIN referral_tree parent
                ON (
                  child.referred_by_tailor_id=parent.tailor_id
                  OR EXISTS (
                    SELECT 1
                    FROM referrals r
                    WHERE r.referrer_tailor_id=parent.tailor_id
                      AND r.referred_tailor_id=child.tailor_id
                  )
                )
              WHERE NOT child.tailor_id = ANY(parent.path)
            )
            SELECT
              tailor_id,
              legacy_id,
              shop,
              owner_name,
              full_name,
              email,
              phone_number,
              referral_code,
              referred_by_tailor_id,
              parent_tailor_id,
              depth,
              joined_at
            FROM referral_tree
            ORDER BY depth, shop, owner_name
            LIMIT :max_nodes
            """
        ),
        {"root_uuid": root_uuid, "max_nodes": max_nodes},
    )
    rows = [dict(row) for row in result.mappings().all()]
    nodes: dict[str, dict] = {}
    parent_ids: dict[str, str | None] = {}
    root_key = str(root_uuid)

    for row in rows:
        key = str(row["tailor_id"])
        if key in nodes:
            continue
        nodes[key] = _node_from_row(row)
        parent_ids[key] = str(row["parent_tailor_id"]) if row.get("parent_tailor_id") else None

    for key, node in nodes.items():
        if key == root_key:
            continue
        parent_key = parent_ids.get(key)
        if parent_key and parent_key in nodes:
            nodes[parent_key]["children"].append(node)

    for node in nodes.values():
        node["direct_referrals"] = len(node["children"])
        node["directReferrals"] = len(node["children"])

    return {
        "root_tailor_id": root_key,
        "rootTailorId": root_key,
        "total_tailors": len(nodes),
        "totalTailors": len(nodes),
        "tree": nodes.get(root_key),
    }


@router.get("/customer-referrals/tree/{customer_id}")
async def customer_referral_tree(
    customer_id: str,
    max_nodes: int = Query(default=500, alias="maxNodes", ge=1, le=2000),
    _: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    root_result = await db.execute(
        text(
            """
            SELECT customer_id
            FROM users
            WHERE (customer_id::text=:customer_id OR id=:customer_id)
              AND 'customer'=ANY(roles)
              AND status <> 'DELETED'
            LIMIT 1
            """
        ),
        {"customer_id": customer_id},
    )
    root_uuid = root_result.scalar_one_or_none()
    if not root_uuid:
        raise HTTPException(status_code=404, detail="Customer not found")

    result = await db.execute(
        text(
            """
            WITH RECURSIVE referral_tree AS (
              SELECT
                u.customer_id,
                u.id,
                u.name,
                u.email,
                u.phone,
                u.profile_image,
                u.referral_code,
                u.referred_by_customer_id,
                NULL::uuid AS parent_customer_id,
                0::int AS depth,
                ARRAY[u.customer_id] AS path,
                u.joined AS joined_at
              FROM users u
              WHERE u.customer_id=:root_uuid

              UNION ALL

              SELECT
                child.customer_id,
                child.id,
                child.name,
                child.email,
                child.phone,
                child.profile_image,
                child.referral_code,
                child.referred_by_customer_id,
                parent.customer_id AS parent_customer_id,
                parent.depth + 1 AS depth,
                parent.path || child.customer_id AS path,
                child.joined AS joined_at
              FROM users child
              JOIN referral_tree parent
                ON (
                  child.referred_by_customer_id=parent.customer_id
                  OR EXISTS (
                    SELECT 1
                    FROM customer_referrals cr
                    WHERE cr.referrer_customer_id=parent.customer_id
                      AND cr.referred_customer_id=child.customer_id
                      AND cr.is_valid=TRUE
                  )
                )
              WHERE 'customer'=ANY(child.roles)
                AND child.status <> 'DELETED'
                AND NOT child.customer_id = ANY(parent.path)
            )
            SELECT
              customer_id,
              id,
              name,
              email,
              phone,
              profile_image,
              referral_code,
              referred_by_customer_id,
              parent_customer_id,
              depth,
              joined_at
            FROM referral_tree
            ORDER BY depth, name
            LIMIT :max_nodes
            """
        ),
        {"root_uuid": root_uuid, "max_nodes": max_nodes},
    )
    rows = [dict(row) for row in result.mappings().all()]
    nodes: dict[str, dict] = {}
    parent_ids: dict[str, str | None] = {}
    root_key = str(root_uuid)

    for row in rows:
        key = str(row["customer_id"])
        if key in nodes:
            continue
        nodes[key] = _customer_node_from_row(row)
        parent_ids[key] = str(row["parent_customer_id"]) if row.get("parent_customer_id") else None

    for key, node in nodes.items():
        if key == root_key:
            continue
        parent_key = parent_ids.get(key)
        if parent_key and parent_key in nodes:
            nodes[parent_key]["children"].append(node)

    for node in nodes.values():
        node["valid_referrals"] = len(node["children"])
        node["validReferrals"] = len(node["children"])

    return {
        "root_customer_id": root_key,
        "rootCustomerId": root_key,
        "total_customers": len(nodes),
        "totalCustomers": len(nodes),
        "tree": nodes.get(root_key),
    }


@router.get("/disputes")
async def dispute_queue(
    page: PageParams = Depends(PageParams),
    _: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    result = await db.execute(
        text(
            """
            SELECT
              d.*,
              o.code AS order_code,
              o.status AS booking_status,
              o.tailor_id,
              u.name AS customer_name,
              u.phone AS customer_phone,
              u.email AS customer_email,
              t.shop,
              t.owner_name
            FROM disputes d
            JOIN orders o ON o.id=d.booking_id
            JOIN users u ON u.id=d.customer_id
            LEFT JOIN tailors t ON t.id=o.tailor_id
            ORDER BY
              CASE d.status
                WHEN 'open' THEN 1
                WHEN 'in_review' THEN 2
                WHEN 'resolved' THEN 3
                ELSE 4
              END,
              d.created_at DESC
            LIMIT :limit OFFSET :offset
            """
        ),
        page.sql,
    )
    return [_dispute_payload(dict(row)) for row in result.mappings().all()]


@router.patch("/disputes/{dispute_id}")
async def update_dispute(
    dispute_id: str,
    body: AdminDisputePatchIn,
    _: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    status = body.status.strip().lower()
    if status not in DISPUTE_STATUSES:
        raise HTTPException(400, "Invalid dispute status")
    dispute_result = await db.execute(
        text(
            """
            SELECT d.*, o.code AS order_code, o.status AS booking_status, o.tailor_id,
                   u.customer_id AS customer_uuid, u.name AS customer_name, u.phone AS customer_phone, u.email AS customer_email,
                   t.shop, t.owner_name
            FROM disputes d
            JOIN orders o ON o.id=d.booking_id
            JOIN users u ON u.id=d.customer_id
            LEFT JOIN tailors t ON t.id=o.tailor_id
            WHERE d.id=:id
            FOR UPDATE OF d
            """
        ),
        {"id": dispute_id},
    )
    dispute = dict(dispute_result.mappings().first() or {})
    if not dispute:
        raise HTTPException(404, "Dispute not found")

    existing_refund = Decimal(str(dispute.get("refund_amount") or 0))
    requested_refund = body.refund_amount
    if requested_refund is not None and requested_refund > existing_refund:
        credit_amount = requested_refund - existing_refund
        await db.execute(
            text(
                """
                INSERT INTO customer_wallets (wallet_id,customer_id,balance,created_at,updated_at)
                VALUES (gen_random_uuid(),:customer_id,0,now(),now())
                ON CONFLICT (customer_id) DO NOTHING
                """
            ),
            {"customer_id": dispute["customer_uuid"]},
        )
        await db.execute(
            text("UPDATE customer_wallets SET balance=balance + :amount, updated_at=now() WHERE customer_id=:customer_id"),
            {"amount": credit_amount, "customer_id": dispute["customer_uuid"]},
        )

    await db.execute(
        text(
            """
            UPDATE disputes
            SET status=CAST(:status AS dispute_status_type),
                resolution_notes=COALESCE(:resolution_notes,resolution_notes),
                refund_amount=COALESCE(:refund_amount,refund_amount),
                updated_at=now(),
                resolved_at=CASE WHEN :status IN ('resolved','rejected') THEN now() ELSE NULL END
            WHERE id=:id
            """
        ),
        {
            "id": dispute_id,
            "status": status,
            "resolution_notes": body.resolution_notes,
            "refund_amount": requested_refund,
        },
    )
    if status in {"resolved", "rejected"}:
        await db.execute(
            text(
                """
                UPDATE orders
                SET status=CASE
                  WHEN status='disputed' AND (tracker_stage='Delivered' OR delivered_at IS NOT NULL OR completed_at IS NOT NULL)
                    THEN 'completed'
                  ELSE status
                END
                WHERE id=:booking_id
                """
            ),
            {"booking_id": dispute["booking_id"]},
        )
    await db.commit()
    updated = await db.execute(
        text(
            """
            SELECT
              d.*,
              o.code AS order_code,
              o.status AS booking_status,
              o.tailor_id,
              u.name AS customer_name,
              u.phone AS customer_phone,
              u.email AS customer_email,
              t.shop,
              t.owner_name
            FROM disputes d
            JOIN orders o ON o.id=d.booking_id
            JOIN users u ON u.id=d.customer_id
            LEFT JOIN tailors t ON t.id=o.tailor_id
            WHERE d.id=:id
            """
        ),
        {"id": dispute_id},
    )
    return _dispute_payload(dict(updated.mappings().first()))
