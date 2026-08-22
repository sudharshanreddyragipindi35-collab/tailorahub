from __future__ import annotations

from decimal import Decimal
import re
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_tailor
from app.api.v1.otp import OTP_TTL_MINUTES, OtpFlowError, issue_otp, verify_otp
from app.core.database import get_db
from app.integrations import sms_service
from app.emailer import send_email
from app.qr import generate_wallet_qr
from app.schemas.wallet import SetUpiIn, WithdrawIn, WalletOut


router = APIRouter()
PHONE_RE = re.compile(r"^[6-9]\d{9}$")
UPI_RE = re.compile(r"^[A-Za-z0-9.\-_]{2,}@[A-Za-z][A-Za-z0-9.\-_]{2,}$")
MONEY_QUANT = Decimal("0.01")


async def fetch_one(db: AsyncSession, sql: str, params: dict | None = None) -> dict | None:
    result = await db.execute(text(sql), params or {})
    row = result.mappings().first()
    return dict(row) if row else None


def clean_phone(value: str) -> str:
    return re.sub(r"\D", "", value or "")


def mask_target(target: str) -> str:
    if "@" in target:
        name, domain = target.split("@", 1)
        return f"{name[:2]}***@{domain}" if len(name) > 2 else f"{name[:1]}***@{domain}"
    return f"******{target[-4:]}"


def money_decimal(value) -> Decimal:
    return Decimal(str(value or 0)).quantize(MONEY_QUANT)


async def pending_withdrawal_amount(db: AsyncSession, wallet_id) -> Decimal:
    row = await fetch_one(
        db,
        """
        SELECT COALESCE(SUM(amount), 0) AS pending_amount
        FROM withdrawal_requests
        WHERE wallet_id=:wallet_id
          AND status='pending_admin_review'
        """,
        {"wallet_id": wallet_id},
    )
    return money_decimal(row["pending_amount"] if row else 0)


async def wallet_balance_snapshot(db: AsyncSession, row: dict) -> tuple[Decimal, Decimal, Decimal]:
    ledger_balance = money_decimal(row.get("balance"))
    pending_amount = await pending_withdrawal_amount(db, row["wallet_id"])
    available_balance = ledger_balance - pending_amount
    if available_balance < 0:
        available_balance = Decimal("0.00")
    return ledger_balance, pending_amount, available_balance


async def wallet_payload(db: AsyncSession, row: dict) -> dict:
    ledger_balance, pending_amount, available_balance = await wallet_balance_snapshot(db, row)
    return {
        "wallet_id": row["wallet_id"],
        "balance": available_balance,
        "ledger_balance": ledger_balance,
        "available_balance": available_balance,
        "pending_withdrawal_amount": pending_amount,
        "upi_id": row.get("upi_id"),
        "qr_code_url": row.get("qr_code_url"),
        "bank_account_configured": bool(row.get("bank_account_number") and row.get("bank_ifsc")),
    }


async def ensure_wallet(db: AsyncSession, tailor: dict) -> dict:
    row = await fetch_one(db, "SELECT * FROM tailor_wallets WHERE tailor_id=:tailor_id", {"tailor_id": tailor["tailor_id"]})
    if row:
        if not row.get("qr_code_url"):
            qr_url = generate_wallet_qr(str(row["wallet_id"]))
            await db.execute(text("UPDATE tailor_wallets SET qr_code_url=:qr, updated_at=now() WHERE wallet_id=:wallet_id"), {"qr": qr_url, "wallet_id": row["wallet_id"]})
            row["qr_code_url"] = qr_url
        return row
    wallet_id = uuid.uuid4()
    qr_url = generate_wallet_qr(str(wallet_id))
    result = await db.execute(
        text(
            """INSERT INTO tailor_wallets (wallet_id, tailor_id, qr_code_url, balance)
               VALUES (:wallet_id, :tailor_id, :qr_code_url, 0)
               RETURNING *"""
        ),
        {"wallet_id": wallet_id, "tailor_id": tailor["tailor_id"], "qr_code_url": qr_url},
    )
    return dict(result.mappings().first())


async def tailor_contact(db: AsyncSession, tailor: dict) -> tuple[str, bool]:
    row = await fetch_one(
        db,
        """SELECT COALESCE(t.phone_number, u.phone) AS phone, COALESCE(t.email, u.email) AS email
           FROM tailors t JOIN users u ON u.id=t.user_id
           WHERE t.id=:id""",
        {"id": tailor["id"]},
    )
    phone = clean_phone(row.get("phone") if row else "")
    if PHONE_RE.fullmatch(phone):
        return phone, False
    email = (row.get("email") if row else "") or ""
    if email:
        return email.lower(), True
    raise HTTPException(400, "Add a verified mobile number or email before withdrawing")


async def send_withdrawal_otp(db: AsyncSession, tailor: dict) -> dict:
    target, is_email = await tailor_contact(db, tailor)
    try:
        code, _ = await issue_otp(db, target, "withdrawal")
        await db.commit()
    except OtpFlowError as exc:
        await db.rollback()
        raise HTTPException(exc.status_code, exc.message)
    if is_email:
        delivery = send_email(target, "Your TailoraHub withdrawal OTP", f"Your withdrawal OTP is {code}. It is valid for {OTP_TTL_MINUTES} minutes.")
        mock_mode = delivery.get("mode") == "mock"
    else:
        delivery = sms_service().send_otp(target, code)
        mock_mode = delivery.get("mode") == "mock"
    return {
        "sent": True,
        "target": mask_target(target),
        "channel": "email" if is_email else "sms",
        "expires_in_seconds": OTP_TTL_MINUTES * 60,
        "dev_otp": code if mock_mode else None,
    }


async def verify_withdrawal_otp(db: AsyncSession, tailor: dict, otp: str) -> None:
    target, _ = await tailor_contact(db, tailor)
    try:
        matched = await verify_otp(db, target, "withdrawal", otp)
        await db.commit()
    except OtpFlowError as exc:
        await db.rollback()
        raise HTTPException(exc.status_code, exc.message)
    if not matched:
        raise HTTPException(401, "Incorrect withdrawal OTP")


@router.get("/scaffold")
async def wallet_scaffold() -> dict:
    return {"module": "wallet", "ready": True}


@router.get("/me", response_model=WalletOut)
async def my_wallet(tailor: dict = Depends(get_current_tailor), db: AsyncSession = Depends(get_db)) -> dict:
    wallet = await ensure_wallet(db, tailor)
    await db.commit()
    return await wallet_payload(db, wallet)


@router.post("/set-upi", response_model=WalletOut)
async def set_upi(body: SetUpiIn, tailor: dict = Depends(get_current_tailor), db: AsyncSession = Depends(get_db)) -> dict:
    upi_id = body.upi_id.strip()
    if not UPI_RE.fullmatch(upi_id):
        raise HTTPException(400, "Enter a valid UPI ID")
    wallet = await ensure_wallet(db, tailor)
    result = await db.execute(
        text("UPDATE tailor_wallets SET upi_id=:upi_id, updated_at=now() WHERE wallet_id=:wallet_id RETURNING *"),
        {"upi_id": upi_id, "wallet_id": wallet["wallet_id"]},
    )
    await db.commit()
    return await wallet_payload(db, dict(result.mappings().first()))


@router.post("/withdraw/send-otp")
async def send_withdraw_otp(tailor: dict = Depends(get_current_tailor), db: AsyncSession = Depends(get_db)) -> dict:
    await ensure_wallet(db, tailor)
    return await send_withdrawal_otp(db, tailor)


@router.post("/withdraw")
async def withdraw(body: WithdrawIn, tailor: dict = Depends(get_current_tailor), db: AsyncSession = Depends(get_db)) -> dict:
    wallet = await ensure_wallet(db, tailor)
    amount = money_decimal(body.amount)
    if amount <= 0:
        raise HTTPException(400, "Withdrawal amount must be greater than zero")
    ledger_balance, pending_amount, available_balance = await wallet_balance_snapshot(db, wallet)
    if available_balance < amount:
        raise HTTPException(
            400,
            f"Insufficient available wallet balance. Available: Rs {available_balance}; pending admin approval: Rs {pending_amount}.",
        )
    destination_upi_id = None
    destination_bank_account = None
    destination_bank_ifsc = None
    if body.destination_type == "upi_id":
        destination_upi_id = (wallet.get("upi_id") or "").strip()
        if not destination_upi_id:
            raise HTTPException(400, "Set your UPI ID before withdrawing to UPI")
    if body.destination_type == "bank_account":
        account = (body.bank_account_number or wallet.get("bank_account_number") or "").strip()
        ifsc = (body.bank_ifsc or wallet.get("bank_ifsc") or "").strip().upper()
        if not account or not ifsc:
            raise HTTPException(400, "Bank account number and IFSC are required for bank withdrawal")
        destination_bank_account = account
        destination_bank_ifsc = ifsc
        await db.execute(
            text("UPDATE tailor_wallets SET bank_account_number=:account, bank_ifsc=:ifsc, updated_at=now() WHERE wallet_id=:wallet_id"),
            {"account": account, "ifsc": ifsc, "wallet_id": wallet["wallet_id"]},
        )

    await verify_withdrawal_otp(db, tailor, body.otp)
    try:
        wallet = await fetch_one(db, "SELECT * FROM tailor_wallets WHERE wallet_id=:wallet_id FOR UPDATE", {"wallet_id": wallet["wallet_id"]}) or wallet
        ledger_balance, pending_amount, available_balance = await wallet_balance_snapshot(db, wallet)
        if available_balance < amount:
            raise HTTPException(
                400,
                f"Insufficient available wallet balance. Available: Rs {available_balance}; pending admin approval: Rs {pending_amount}.",
            )
        result = await db.execute(
            text(
                """
                INSERT INTO withdrawal_requests
                  (wallet_id,tailor_id,amount,destination_type,destination_upi_id,
                   destination_bank_account_number,destination_bank_ifsc,status,otp_verified_at,requested_at,updated_at)
                VALUES
                  (:wallet_id,:tailor_id,:amount,CAST(:destination AS withdrawal_destination_type),:upi_id,
                   :bank_account,:bank_ifsc,'pending_admin_review',now(),now(),now())
                RETURNING *
                """
            ),
            {
                "wallet_id": wallet["wallet_id"],
                "tailor_id": tailor["tailor_id"],
                "amount": amount,
                "destination": body.destination_type,
                "upi_id": destination_upi_id,
                "bank_account": destination_bank_account,
                "bank_ifsc": destination_bank_ifsc,
            },
        )
        request_row = dict(result.mappings().first())
        await db.commit()
        updated_wallet = await fetch_one(db, "SELECT * FROM tailor_wallets WHERE wallet_id=:wallet_id", {"wallet_id": wallet["wallet_id"]}) or wallet
        wallet_view = await wallet_payload(db, updated_wallet)
    except Exception:
        await db.rollback()
        raise
    return {
        "ok": True,
        "status": request_row["status"],
        "txn_ref": str(request_row["id"]),
        "balance": wallet_view["balance"],
        "ledger_balance": wallet_view["ledger_balance"],
        "available_balance": wallet_view["available_balance"],
        "pending_withdrawal_amount": wallet_view["pending_withdrawal_amount"],
        "message": "Withdrawal request sent to admin. Manual payout will be reviewed within 24 hours.",
    }
