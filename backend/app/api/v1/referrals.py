from __future__ import annotations

import os
import secrets
import string

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_tailor
from app.core.database import get_db


router = APIRouter()


@router.get("/scaffold")
async def referrals_scaffold() -> dict:
    return {"module": "referrals", "ready": True}


def _share_base_url() -> str:
    return (
        os.getenv("PUBLIC_APP_URL")
        or os.getenv("FRONTEND_URL")
        or os.getenv("APP_PUBLIC_URL")
        or "https://tailorahub.com"
    ).rstrip("/")


async def _unique_referral_code(db: AsyncSession) -> str:
    alphabet = string.ascii_uppercase + string.digits
    for _ in range(10):
        code = "TH" + "".join(secrets.choice(alphabet) for _ in range(8))
        existing = await db.execute(
            text("SELECT 1 FROM tailors WHERE referral_code=:code"),
            {"code": code},
        )
        if not existing.first():
            return code
    return "TH" + secrets.token_hex(6).upper()


@router.get("/my-code")
async def my_referral_code(
    tailor: dict = Depends(get_current_tailor),
    db: AsyncSession = Depends(get_db),
) -> dict:
    referral_code = tailor.get("referral_code")
    if not referral_code:
        referral_code = await _unique_referral_code(db)
        await db.execute(
            text("UPDATE tailors SET referral_code=:code, updated_at=now() WHERE tailor_id=:tailor_id"),
            {"code": referral_code, "tailor_id": tailor["tailor_id"]},
        )
        await db.commit()

    shareable_link = f"{_share_base_url()}/tailor/register?ref={referral_code}"
    return {
        "referral_code": referral_code,
        "referralCode": referral_code,
        "shareable_link": shareable_link,
        "shareableLink": shareable_link,
    }


@router.get("/my-count")
async def my_referral_count(
    tailor: dict = Depends(get_current_tailor),
    db: AsyncSession = Depends(get_db),
) -> dict:
    result = await db.execute(
        text(
            """
            SELECT COUNT(*)::int AS direct_count
            FROM (
              SELECT referred_tailor_id
              FROM referrals
              WHERE referrer_tailor_id=:tailor_id
              UNION
              SELECT tailor_id AS referred_tailor_id
              FROM tailors
              WHERE referred_by_tailor_id=:tailor_id
            ) direct_referrals
            """
        ),
        {"tailor_id": tailor["tailor_id"]},
    )
    direct_count = result.scalar_one() or 0
    return {"direct_count": direct_count, "directCount": direct_count}
