from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import create_access_token, create_refresh_token, decode_refresh_token
from app.security import hash_refresh_token


def _expires_at(refresh_token: str) -> datetime:
    payload = decode_refresh_token(refresh_token)
    return datetime.fromtimestamp(payload["exp"], timezone.utc)


async def create_token_pair(db: AsyncSession, user_id: str, roles: list[str] | None = None) -> dict:
    settings = get_settings()
    access_token = create_access_token(user_id, roles or [])
    refresh_token = create_refresh_token(user_id)
    token_hash = hash_refresh_token(refresh_token)
    await db.execute(
        text(
            """
            INSERT INTO refresh_sessions (id,user_id,token_hash,expires_at,created_at)
            VALUES (gen_random_uuid(),:user_id,:token_hash,:expires_at,now())
            """
        ),
        {"user_id": user_id, "token_hash": token_hash, "expires_at": _expires_at(refresh_token)},
    )
    return {
        "token": access_token,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "refreshToken": refresh_token,
        "token_type": "bearer",
        "expires_in_seconds": settings.access_token_minutes * 60,
        "_refresh_token_hash": token_hash,
    }


async def rotate_refresh_session(db: AsyncSession, refresh_token: str) -> dict:
    payload = decode_refresh_token(refresh_token)
    if payload.get("type") != "refresh":
        raise ValueError("Invalid refresh token")
    token_hash = hash_refresh_token(refresh_token)
    result = await db.execute(
        text(
            """
            SELECT rs.*, u.roles
            FROM refresh_sessions rs
            JOIN users u ON u.id=rs.user_id
            WHERE rs.token_hash=:token_hash
              AND rs.revoked_at IS NULL
              AND rs.expires_at > now()
              AND u.status <> 'DELETED'
            FOR UPDATE OF rs
            """
        ),
        {"token_hash": token_hash},
    )
    session = dict(result.mappings().first() or {})
    if not session or session["user_id"] != payload.get("sub"):
        raise ValueError("Refresh token expired or revoked")
    next_tokens = await create_token_pair(db, session["user_id"], session.get("roles") or [])
    await db.execute(
        text("UPDATE refresh_sessions SET revoked_at=now(), replaced_by_token_hash=:next_hash WHERE token_hash=:old_hash"),
        {"next_hash": next_tokens["_refresh_token_hash"], "old_hash": token_hash},
    )
    next_tokens.pop("_refresh_token_hash", None)
    return next_tokens
