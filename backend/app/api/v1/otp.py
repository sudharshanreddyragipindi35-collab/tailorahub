from __future__ import annotations

from datetime import datetime, timedelta, timezone
import re
import secrets

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.emailer import send_email
from app.integrations import sms_service
from app.schemas.otp import OtpSendIn, OtpSendOut, OtpVerifyIn, OtpVerifyOut
from app.security import hash_otp, verify_otp_hash


router = APIRouter()

VALID_OTP_PURPOSES = {"registration_phone", "registration_email", "login", "forgot_password", "delivery", "withdrawal", "measurement_arrival"}
PHONE_RE = re.compile(r"^[6-9]\d{9}$")
OTP_TTL_MINUTES = 5
MAX_VERIFY_ATTEMPTS = 5
RESEND_COOLDOWN_SECONDS = 30


class OtpFlowError(Exception):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(message)


def clean_phone(value: str) -> str:
    return re.sub(r"\D", "", value or "")


def normalize_target(target: str, purpose: str) -> tuple[str, bool]:
    value = target.strip()
    is_email = "@" in value
    if purpose == "registration_phone":
        phone = clean_phone(value)
        if not PHONE_RE.fullmatch(phone):
            raise HTTPException(400, "Enter a valid 10-digit mobile number")
        return phone, False
    if purpose == "registration_email":
        if not is_email:
            raise HTTPException(400, "Enter a valid email address")
        return value.lower(), True
    if is_email:
        return value.lower(), True
    phone = clean_phone(value)
    if PHONE_RE.fullmatch(phone):
        return phone, False
    raise HTTPException(400, "Enter a valid email or 10-digit mobile number")


async def fetch_one(db: AsyncSession, sql: str, params: dict | None = None) -> dict | None:
    result = await db.execute(text(sql), params or {})
    row = result.mappings().first()
    return dict(row) if row else None


async def issue_otp(db: AsyncSession, target: str, purpose: str) -> tuple[str, datetime]:
    recent = await fetch_one(
        db,
        """SELECT created_at FROM otp_verifications
           WHERE target=:target AND purpose=:purpose AND verified=FALSE
           ORDER BY created_at DESC LIMIT 1""",
        {"target": target, "purpose": purpose},
    )
    now = datetime.now(timezone.utc)
    if recent:
        created_at = recent["created_at"]
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        elapsed = (now - created_at).total_seconds()
        if elapsed < RESEND_COOLDOWN_SECONDS:
            wait = RESEND_COOLDOWN_SECONDS - int(elapsed)
            raise OtpFlowError(429, f"Please wait {max(wait, 1)}s before requesting another code")

    code = f"{secrets.randbelow(900000) + 100000}"
    expires_at = now + timedelta(minutes=OTP_TTL_MINUTES)
    await db.execute(
        text(
            """INSERT INTO otp_verifications (id, target, otp_hash, purpose, expires_at, verified, attempt_count, created_at)
               VALUES (gen_random_uuid(), :target, :otp_hash, :purpose, :expires_at, FALSE, 0, now())"""
        ),
        {"target": target, "otp_hash": hash_otp(code, target, purpose), "purpose": purpose, "expires_at": expires_at},
    )
    return code, expires_at


async def verify_otp(db: AsyncSession, target: str, purpose: str, code: str) -> bool:
    row = await fetch_one(
        db,
        """SELECT * FROM otp_verifications
           WHERE target=:target AND purpose=:purpose AND verified=FALSE AND expires_at > now()
           ORDER BY created_at DESC LIMIT 1""",
        {"target": target, "purpose": purpose},
    )
    if not row:
        raise OtpFlowError(401, "Code expired or not requested -- request a new one")
    if row["attempt_count"] >= MAX_VERIFY_ATTEMPTS:
        raise OtpFlowError(401, "Too many incorrect attempts -- request a new code")

    if not verify_otp_hash(code.strip(), target, purpose, row["otp_hash"]):
        await db.execute(text("UPDATE otp_verifications SET attempt_count = attempt_count + 1 WHERE id=:id"), {"id": row["id"]})
        return False

    await db.execute(text("UPDATE otp_verifications SET verified=TRUE WHERE id=:id"), {"id": row["id"]})
    return True


async def is_recently_verified(db: AsyncSession, target: str, purpose: str, within_minutes: int = 30) -> bool:
    row = await fetch_one(
        db,
        """SELECT 1 FROM otp_verifications
           WHERE target=:target AND purpose=:purpose AND verified=TRUE
             AND created_at > now() - (CAST(:minutes AS integer) * interval '1 minute')
           ORDER BY created_at DESC LIMIT 1""",
        {"target": target, "purpose": purpose, "minutes": within_minutes},
    )
    return bool(row)


@router.get("/scaffold")
async def otp_scaffold() -> dict:
    return {"module": "otp", "ready": True}


@router.post("/send", response_model=OtpSendOut)
async def send_otp(body: OtpSendIn, db: AsyncSession = Depends(get_db)) -> dict:
    if body.purpose not in VALID_OTP_PURPOSES:
        raise HTTPException(400, "Invalid OTP purpose")
    target, is_email = normalize_target(body.target, body.purpose)
    try:
        code, expires_at = await issue_otp(db, target, body.purpose)
        await db.commit()
    except OtpFlowError as exc:
        await db.rollback()
        raise HTTPException(exc.status_code, exc.message)

    if is_email:
        delivery = send_email(target, "Your TailoraHub verification code", f"Your verification code is {code}. It is valid for {OTP_TTL_MINUTES} minutes.")
        mock_mode = delivery.get("mode") == "mock"
    else:
        delivery = sms_service().send_otp(target, code)
        mock_mode = delivery.get("mode") == "mock"

    return {
        "sent": True,
        "expires_at": expires_at.isoformat(),
        "expires_in_seconds": OTP_TTL_MINUTES * 60,
        "dev_otp": code if mock_mode else None,
    }


@router.post("/verify", response_model=OtpVerifyOut)
async def verify_otp_route(body: OtpVerifyIn, db: AsyncSession = Depends(get_db)) -> dict:
    if body.purpose not in VALID_OTP_PURPOSES:
        raise HTTPException(400, "Invalid OTP purpose")
    target, _ = normalize_target(body.target, body.purpose)
    try:
        matched = await verify_otp(db, target, body.purpose, body.otp)
        await db.commit()
    except OtpFlowError as exc:
        await db.rollback()
        raise HTTPException(exc.status_code, exc.message)
    if not matched:
        raise HTTPException(401, "Incorrect code")
    return {"verified": True, "target": target, "purpose": body.purpose}
