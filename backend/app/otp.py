"""Purpose-scoped, hashed OTP issue/verify against `otp_verifications`.

Replaces the legacy plaintext single-purpose OTP flow -- see schema.sql's otp_purpose enum for
the valid `purpose` values (registration_phone, registration_email, login,
forgot_password, delivery). Callers own the DB transaction (commit); this
module only executes statements.
"""

import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import text
from sqlalchemy.orm import Session

from .db import fetch_one
from .security import hash_otp, verify_otp_hash

OTP_TTL_MINUTES = 10
MAX_VERIFY_ATTEMPTS = 5
RESEND_COOLDOWN_SECONDS = 30


class OtpError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


def issue(db: Session, target: str, purpose: str) -> tuple[str, datetime]:
    """Store a new hashed OTP for (target, purpose); returns (plaintext_code, expires_at) for the caller to deliver."""
    recent = fetch_one(
        db,
        """SELECT created_at FROM otp_verifications
           WHERE target=:target AND purpose=:purpose AND verified=FALSE
           ORDER BY created_at DESC LIMIT 1""",
        {"target": target, "purpose": purpose},
    )
    now = datetime.now(timezone.utc)
    if recent and recent["created_at"] > now - timedelta(seconds=RESEND_COOLDOWN_SECONDS):
        wait = RESEND_COOLDOWN_SECONDS - int((now - recent["created_at"]).total_seconds())
        raise OtpError("cooldown", f"Please wait {max(wait, 1)}s before requesting another code")

    code = f"{secrets.randbelow(900000) + 100000}"
    expires_at = now + timedelta(minutes=OTP_TTL_MINUTES)
    db.execute(
        text(
            """INSERT INTO otp_verifications (id, target, otp_hash, purpose, expires_at, verified, attempt_count, created_at)
               VALUES (gen_random_uuid(), :target, :otp_hash, :purpose, :expires_at, FALSE, 0, now())"""
        ),
        {"target": target, "otp_hash": hash_otp(code, target, purpose), "purpose": purpose, "expires_at": expires_at},
    )
    return code, expires_at


def verify(db: Session, target: str, purpose: str, code: str) -> bool:
    """Check `code` against the latest pending row for (target, purpose).

    Raises OtpError('expired', ...) if nothing pending, OtpError('locked', ...)
    once MAX_VERIFY_ATTEMPTS wrong guesses have been made against that row.
    Returns True/False for whether `code` matched (False increments the
    attempt counter; caller commits either way).
    """
    row = fetch_one(
        db,
        """SELECT * FROM otp_verifications
           WHERE target=:target AND purpose=:purpose AND verified=FALSE AND expires_at > now()
           ORDER BY created_at DESC LIMIT 1""",
        {"target": target, "purpose": purpose},
    )
    if not row:
        raise OtpError("expired", "Code expired or not requested -- request a new one")
    if row["attempt_count"] >= MAX_VERIFY_ATTEMPTS:
        raise OtpError("locked", "Too many incorrect attempts -- request a new code")

    if not verify_otp_hash(code.strip(), target, purpose, row["otp_hash"]):
        db.execute(text("UPDATE otp_verifications SET attempt_count = attempt_count + 1 WHERE id=:id"), {"id": row["id"]})
        return False

    db.execute(text("UPDATE otp_verifications SET verified=TRUE WHERE id=:id"), {"id": row["id"]})
    return True


def is_recently_verified(db: Session, target: str, purpose: str, within_minutes: int = 30) -> bool:
    """True if (target, purpose) has a verified row within the last `within_minutes` -- used to gate a
    later step (e.g. final registration submit) on an OTP check done earlier in the same flow."""
    row = fetch_one(
        db,
        """SELECT 1 FROM otp_verifications
           WHERE target=:target AND purpose=:purpose AND verified=TRUE
             AND created_at > now() - (CAST(:minutes AS integer) * interval '1 minute')
           ORDER BY created_at DESC LIMIT 1""",
        {"target": target, "purpose": purpose, "minutes": within_minutes},
    )
    return bool(row)
