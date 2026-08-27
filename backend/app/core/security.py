from __future__ import annotations

from datetime import datetime, timedelta, timezone
import secrets

import jwt

from app.security import (
    decrypt_aadhaar,
    encrypt_aadhaar,
    hash_aadhaar,
    hash_otp,
    hash_password,
    is_valid_aadhaar_format,
    verify_otp_hash,
    verify_password,
)

from .config import get_settings


def create_access_token(subject: str, roles: list[str] | None = None, session_id: str | None = None) -> str:
    settings = get_settings()
    exp = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_minutes)
    payload = {"sub": subject, "roles": roles or [], "type": "access", "exp": exp}
    if session_id:
        payload["sid"] = session_id
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_refresh_token(subject: str) -> str:
    settings = get_settings()
    exp = datetime.now(timezone.utc) + timedelta(days=30)
    payload = {"sub": subject, "type": "refresh", "jti": secrets.token_urlsafe(24), "exp": exp}
    return jwt.encode(payload, settings.jwt_refresh_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    settings = get_settings()
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


def decode_refresh_token(token: str) -> dict:
    settings = get_settings()
    return jwt.decode(token, settings.jwt_refresh_secret, algorithms=[settings.jwt_algorithm])
