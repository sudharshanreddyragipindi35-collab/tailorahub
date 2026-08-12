import base64
import hashlib
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from cryptography.fernet import Fernet, InvalidToken

from .settings import settings


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str | None) -> bool:
    if not hashed:
        return False
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


def create_token(user: dict) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_minutes)
    payload = {"sub": user["id"], "roles": user.get("roles", []), "exp": exp}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


# --- Aadhaar: Verhoeff checksum + encryption-at-rest -----------------------
#
# Aadhaar numbers use the Verhoeff algorithm as their check-digit scheme.
# This lets us reject a mistyped number client- and server-side without
# ever calling an external verification API.

_VERHOEFF_D = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
    [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
    [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
    [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
    [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
    [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
    [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
    [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
    [9, 8, 7, 6, 5, 4, 3, 2, 1, 0],
]
_VERHOEFF_P = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
    [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
    [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
    [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
    [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
    [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
    [7, 0, 4, 6, 9, 1, 3, 2, 5, 8],
]


def verhoeff_is_valid(number: str) -> bool:
    """True if `number` (digits only) passes the Verhoeff checksum."""
    if not number.isdigit():
        return False
    checksum = 0
    for i, digit in enumerate(reversed(number)):
        checksum = _VERHOEFF_D[checksum][_VERHOEFF_P[i % 8][int(digit)]]
    return checksum == 0


def is_valid_aadhaar_format(aadhaar_number: str) -> bool:
    digits = (aadhaar_number or "").strip()
    return len(digits) == 12 and verhoeff_is_valid(digits)


def hash_aadhaar(aadhaar_number: str) -> str:
    """SHA-256 hash used only for uniqueness lookups -- never reversed."""
    return hashlib.sha256(aadhaar_number.strip().encode("utf-8")).hexdigest()


def _aadhaar_fernet() -> Fernet:
    # AADHAAR_ENCRYPTION_KEY is blank by default (see .env.example) so the
    # app still runs in dev without it configured; derive a valid 32-byte
    # Fernet key from whatever secret material is available either way,
    # same "works out of the box, upgrade via env in prod" pattern as the
    # rest of settings.py.
    key_material = settings.aadhaar_encryption_key or f"dev-aadhaar-key::{settings.jwt_secret}"
    derived = hashlib.sha256(key_material.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(derived))


def encrypt_aadhaar(aadhaar_number: str) -> str:
    return _aadhaar_fernet().encrypt(aadhaar_number.strip().encode("utf-8")).decode("utf-8")


def decrypt_aadhaar(token: str) -> str | None:
    try:
        return _aadhaar_fernet().decrypt(token.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        return None


# --- OTP hashing -------------------------------------------------------
#
# OTPs are short-lived, rate-limited, numeric codes -- hashing here is
# defense-in-depth against a DB dump exposing live codes, not brute-force
# resistance (that comes from expiry + attempt lockout), so a fast salted
# SHA-256 is appropriate rather than bcrypt.

def hash_otp(code: str, target: str, purpose: str) -> str:
    return hashlib.sha256(f"{purpose}:{target}:{code}".encode("utf-8")).hexdigest()


def verify_otp_hash(code: str, target: str, purpose: str, hashed: str) -> bool:
    return hash_otp(code, target, purpose) == hashed


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
