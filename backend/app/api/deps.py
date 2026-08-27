from __future__ import annotations

from typing import Annotated

from datetime import datetime, timezone

from fastapi import Depends, Header, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_access_token
from app.core.config import get_settings


bearer = HTTPBearer(auto_error=False)
DbSession = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    db: DbSession,
    activity_at: Annotated[str | None, Header(alias="X-TailoraHub-Activity-At")] = None,
) -> dict:
    if not credentials:
        raise HTTPException(status_code=401, detail="Sign in required")
    try:
        payload = decode_access_token(credentials.credentials)
    except Exception:
        raise HTTPException(status_code=401, detail="Session expired")
    session_id = payload.get("sid")
    if session_id:
        result = await db.execute(
            text("SELECT last_activity_at, revoked_at, expires_at FROM refresh_sessions WHERE token_hash=:sid"),
            {"sid": session_id},
        )
        auth_session = result.mappings().first()
        if not auth_session or auth_session["revoked_at"] or auth_session["expires_at"] <= datetime.now(timezone.utc):
            raise HTTPException(status_code=401, detail="Session expired")
        client_activity = None
        try:
            client_activity = datetime.fromtimestamp(int(activity_at or "0") / 1000, timezone.utc)
        except (TypeError, ValueError, OSError):
            pass
        now = datetime.now(timezone.utc)
        effective_activity = max(auth_session["last_activity_at"], client_activity) if client_activity else auth_session["last_activity_at"]
        if (now - effective_activity).total_seconds() >= get_settings().session_inactivity_minutes * 60:
            await db.execute(text("UPDATE refresh_sessions SET revoked_at=now() WHERE token_hash=:sid"), {"sid": session_id})
            await db.commit()
            raise HTTPException(status_code=401, detail="Session expired due to inactivity")
        if client_activity and client_activity > auth_session["last_activity_at"] and client_activity <= now:
            await db.execute(text("UPDATE refresh_sessions SET last_activity_at=:activity WHERE token_hash=:sid"), {"activity": client_activity, "sid": session_id})
            await db.commit()
    result = await db.execute(text("SELECT * FROM users WHERE id=:id"), {"id": payload.get("sub")})
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=401, detail="Account not found")
    user = dict(row)
    if user.get("status") == "DELETED":
        raise HTTPException(status_code=403, detail="This account has been removed")
    return user


async def get_current_customer(user: Annotated[dict, Depends(get_current_user)]) -> dict:
    if "customer" not in (user.get("roles") or []):
        raise HTTPException(status_code=403, detail="Customer access required")
    return user


async def get_current_tailor(
    user: Annotated[dict, Depends(get_current_user)],
    db: DbSession,
) -> dict:
    if "tailor" not in (user.get("roles") or []):
        raise HTTPException(status_code=403, detail="Tailor access required")
    result = await db.execute(
        text("SELECT * FROM tailors WHERE user_id=:uid AND deleted_at IS NULL"),
        {"uid": user["id"]},
    )
    tailor = result.mappings().first()
    if not tailor:
        raise HTTPException(status_code=404, detail="Tailor profile not found")
    return dict(tailor)


async def require_admin(user: Annotated[dict, Depends(get_current_user)]) -> dict:
    if "admin" not in (user.get("roles") or []):
        raise HTTPException(status_code=403, detail="Admin access required")
    return user
