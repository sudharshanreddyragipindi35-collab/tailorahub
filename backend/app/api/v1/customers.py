from __future__ import annotations

import re
import secrets
import string
import uuid
import os

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_customer
from app.api.v1.otp import is_recently_verified, normalize_target
from app.api.v1.session_tokens import create_token_pair
from app.core.database import get_db
from app.schemas.customers import CustomerAvailabilityCheckIn, CustomerRegisterIn
from app.security import hash_password


router = APIRouter()
PHONE_RE = re.compile(r"^[6-9]\d{9}$")
CUSTOMER_REFERRER_BONUS = 100
CUSTOMER_REFERRED_BONUS = 50


@router.get("/scaffold")
async def customers_scaffold() -> dict:
    return {"module": "customers", "ready": True}


def uid(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def clean_phone(value: str) -> str:
    return re.sub(r"\D", "", value or "")


def password_is_strong(value: str) -> bool:
    return len(value or "") >= 8 and bool(re.search(r"[A-Za-z]", value)) and bool(re.search(r"\d", value))


def share_base_url() -> str:
    return (
        os.getenv("PUBLIC_APP_URL")
        or os.getenv("FRONTEND_URL")
        or os.getenv("APP_PUBLIC_URL")
        or "https://tailorahub.com"
    ).rstrip("/")


async def fetch_one(db: AsyncSession, sql: str, params: dict | None = None) -> dict | None:
    result = await db.execute(text(sql), params or {})
    row = result.mappings().first()
    return dict(row) if row else None


async def generate_customer_referral_code(db: AsyncSession) -> str:
    alphabet = string.ascii_uppercase + string.digits
    for _ in range(10):
        code = "CH" + "".join(secrets.choice(alphabet) for _ in range(8))
        if not await fetch_one(db, "SELECT 1 FROM users WHERE referral_code=:code", {"code": code}):
            return code
    return "CH" + secrets.token_hex(6).upper()


def public_customer(row: dict, wallet_id=None) -> dict:
    customer_id = str(row["customer_id"])
    return {
        "id": row["id"],
        "customer_id": customer_id,
        "customerId": customer_id,
        "name": row["name"],
        "fullName": row["name"],
        "phone": row.get("phone"),
        "phoneNumber": row.get("phone"),
        "email": row.get("email"),
        "roles": row.get("roles") or ["customer"],
        "status": row.get("status"),
        "referral_code": row.get("referral_code"),
        "referralCode": row.get("referral_code"),
        "wallet_id": str(wallet_id) if wallet_id else None,
        "walletId": str(wallet_id) if wallet_id else None,
        "joined": row.get("joined"),
    }


def customer_wallet_payload(row: dict) -> dict:
    return {
        "wallet_id": str(row["wallet_id"]),
        "walletId": str(row["wallet_id"]),
        "customer_id": str(row["customer_id"]),
        "customerId": str(row["customer_id"]),
        "balance": row.get("balance") or 0,
        "updated_at": row.get("updated_at"),
        "updatedAt": row.get("updated_at"),
    }


def public_nearby_tailor(row: dict) -> dict:
    distance = float(row.get("distance_km") or 0)
    experience = row.get("computed_experience_display")
    if experience is None:
        experience = row.get("experience_display")
    if experience is None:
        experience = row.get("experience_years_base") or row.get("years") or 0
    return {
        "id": row["id"],
        "tailorId": str(row["tailor_id"]),
        "shop": row["shop"],
        "ownerName": row["owner_name"],
        "zoneId": row["zone_id"],
        "shopAddress": row.get("address_text") or row.get("shop_address"),
        "latitude": float(row["latitude"]) if row.get("latitude") is not None else None,
        "longitude": float(row["longitude"]) if row.get("longitude") is not None else None,
        "distanceKm": round(distance, 2),
        "distance_km": round(distance, 2),
        "experienceDisplay": float(experience or 0),
        "experience_display": float(experience or 0),
        "rating": float(row.get("rating") or 0),
        "ratingCount": row.get("rating_count") or 0,
        "completed": row.get("completed") or 0,
        "verified": bool(row.get("verified")),
        "aadhaarVerified": bool(row.get("aadhaar_verified")),
        "isAvailable": bool(row.get("is_available")),
        "availability": row.get("availability"),
        "acceptingRequests": bool(row.get("accepting_requests", True)),
        "startingPrice": int(row.get("starting_price") or 0),
        "profileImage": row.get("profile_image"),
        "portfolio": row.get("portfolio") or [],
        "expertise": row.get("expertise") or [],
    }


async def duplicate_message(db: AsyncSession, field: str, value: str) -> str | None:
    cleaned = value.strip()
    if field == "phone":
        phone = clean_phone(cleaned)
        if not PHONE_RE.fullmatch(phone):
            return "Enter a valid 10-digit mobile number"
        taken = await fetch_one(
            db,
            "SELECT 1 FROM users WHERE phone=:phone AND 'customer'=ANY(roles) AND status <> 'DELETED' LIMIT 1",
            {"phone": phone},
        )
        return "This mobile number is already registered." if taken else None
    if field == "email":
        if not cleaned:
            return None
        taken = await fetch_one(
            db,
            "SELECT 1 FROM users WHERE lower(email)=:email AND 'customer'=ANY(roles) AND status <> 'DELETED' LIMIT 1",
            {"email": cleaned.lower()},
        )
        return "This email is already registered." if taken else None
    raise HTTPException(400, "Unsupported field")


async def ensure_customer_wallet(db: AsyncSession, customer: dict) -> dict:
    row = await fetch_one(db, "SELECT * FROM customer_wallets WHERE customer_id=:customer_id", {"customer_id": customer["customer_id"]})
    if row:
        return row
    result = await db.execute(
        text(
            """
            INSERT INTO customer_wallets (wallet_id,customer_id,balance,created_at,updated_at)
            VALUES (gen_random_uuid(),:customer_id,0,now(),now())
            RETURNING *
            """
        ),
        {"customer_id": customer["customer_id"]},
    )
    return dict(result.mappings().first())


async def ensure_customer_wallet_by_customer_id(db: AsyncSession, customer_id) -> None:
    await db.execute(
        text(
            """
            INSERT INTO customer_wallets (wallet_id,customer_id,balance,created_at,updated_at)
            SELECT gen_random_uuid(),:customer_id,0,now(),now()
            WHERE NOT EXISTS (
              SELECT 1 FROM customer_wallets WHERE customer_id=:customer_id
            )
            """
        ),
        {"customer_id": customer_id},
    )


async def customer_referrer_for_code(db: AsyncSession, referral_code: str | None) -> dict | None:
    code = (referral_code or "").strip().upper()
    if not code:
        return None
    return await fetch_one(
        db,
        "SELECT id, customer_id, referral_code FROM users WHERE referral_code=:code AND 'customer'=ANY(roles) AND status <> 'DELETED'",
        {"code": code},
    )


async def record_invalid_customer_referral_attempt(db: AsyncSession, referrer_customer_id, phone: str) -> None:
    await db.execute(
        text(
            """
            INSERT INTO customer_referrals
              (id,referrer_customer_id,referred_customer_id,referred_phone_number,is_valid,bonus_amount,created_at)
            VALUES
              (gen_random_uuid(),:referrer,NULL,:phone,FALSE,NULL,now())
            """
        ),
        {"referrer": referrer_customer_id, "phone": phone},
    )


@router.post("/check-availability")
async def check_customer_availability(body: CustomerAvailabilityCheckIn, db: AsyncSession = Depends(get_db)) -> dict:
    message = await duplicate_message(db, body.field.strip().lower(), body.value)
    return {"available": message is None, "message": message}


@router.get("/nearby-tailors")
async def nearby_tailors(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    radius_km: float = Query(50, ge=1, le=100),
    customer: dict = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    radius = min(radius_km or 50, 100)
    result = await db.execute(
        text(
            """
            WITH located_tailors AS (
              SELECT
                t.*,
                loc.address_text,
                loc.latitude,
                loc.longitude,
                COALESCE(min(s.price), 0)::int AS starting_price,
                COALESCE(
                  t.experience_display,
                  t.experience_years_base
                    + CASE
                        WHEN t.stitching_since_date IS NULL THEN 0
                        ELSE GREATEST(EXTRACT(year FROM age(CURRENT_DATE, t.stitching_since_date)), 0)
                      END
                ) AS computed_experience_display,
                (
                  6371 * 2 * asin(
                    sqrt(
                      power(sin(radians((loc.latitude::float - :latitude) / 2)), 2)
                      + cos(radians(:latitude)) * cos(radians(loc.latitude::float))
                      * power(sin(radians((loc.longitude::float - :longitude) / 2)), 2)
                    )
                  )
                ) AS distance_km
              FROM tailor_locations loc
              JOIN tailors t ON t.tailor_id=loc.tailor_id
              LEFT JOIN tailor_services s ON s.tailor_id=t.id AND COALESCE(s.is_active, s.active)=TRUE
              WHERE loc.is_fixed=TRUE
                AND t.deleted_at IS NULL
                AND t.account_status='ACTIVE'
                AND t.status='active'
                AND t.approval_status='APPROVED'
                AND t.aadhaar_verified=TRUE
              GROUP BY t.id, loc.address_text, loc.latitude, loc.longitude
            )
            SELECT *
            FROM located_tailors
            WHERE distance_km <= :radius
            ORDER BY distance_km ASC, rating DESC, computed_experience_display DESC
            """
        ),
        {"latitude": latitude, "longitude": longitude, "radius": radius},
    )
    return [public_nearby_tailor(dict(row)) for row in result.mappings().all()]


@router.get("/me/wallet")
async def my_customer_wallet(
    customer: dict = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db),
) -> dict:
    wallet = await ensure_customer_wallet(db, customer)
    await db.commit()
    return customer_wallet_payload(wallet)


@router.get("/me/referral-code")
async def my_customer_referral_code(
    customer: dict = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db),
) -> dict:
    referral_code = customer.get("referral_code")
    if not referral_code:
        referral_code = await generate_customer_referral_code(db)
        await db.execute(
            text("UPDATE users SET referral_code=:code WHERE id=:id"),
            {"code": referral_code, "id": customer["id"]},
        )
        await db.commit()
    shareable_link = f"{share_base_url()}/customer/register?ref={referral_code}"
    return {
        "referral_code": referral_code,
        "referralCode": referral_code,
        "shareable_link": shareable_link,
        "shareableLink": shareable_link,
    }


@router.get("/me/referral-count")
async def my_customer_referral_count(
    customer: dict = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db),
) -> dict:
    result = await db.execute(
        text(
            """
            SELECT COUNT(*)::int AS valid_count, COALESCE(SUM(COALESCE(bonus_amount, 0)), 0)::numeric AS bonus_total
            FROM customer_referrals
            WHERE referrer_customer_id=:customer_id AND is_valid=TRUE
            """
        ),
        {"customer_id": customer["customer_id"]},
    )
    row = dict(result.mappings().first() or {"valid_count": 0, "bonus_total": 0})
    return {
        "valid_count": row["valid_count"] or 0,
        "validCount": row["valid_count"] or 0,
        "bonus_amount": row["bonus_total"] or 0,
        "bonusAmount": row["bonus_total"] or 0,
    }


@router.post("/register", status_code=201)
async def register_customer(body: CustomerRegisterIn, db: AsyncSession = Depends(get_db)) -> dict:
    phone = clean_phone(body.phone_number)
    email = str(body.email).lower() if body.email else None
    full_name = body.full_name.strip()

    if not PHONE_RE.fullmatch(phone):
        raise HTTPException(400, "Enter a valid 10-digit mobile number")
    if body.confirm_password is not None and body.password != body.confirm_password:
        raise HTTPException(400, "Password and confirm password must match")
    if not password_is_strong(body.password):
        raise HTTPException(400, "Password must be at least 8 characters and include one letter and one number")
    if not body.terms_accepted:
        raise HTTPException(400, "You must accept the terms and conditions")

    for field, value in {"phone": phone, "email": email or ""}.items():
        message = await duplicate_message(db, field, value)
        if message:
            raise HTTPException(400, message)

    phone_target, _ = normalize_target(phone, "registration_phone")
    if not await is_recently_verified(db, phone_target, "registration_phone"):
        raise HTTPException(400, "Verify your mobile number first")

    referral_code_used = (body.referral_code or "").strip().upper() or None
    referrer = await customer_referrer_for_code(db, referral_code_used)
    referred_by_customer_id = referrer["customer_id"] if referrer else None
    if referral_code_used:
        if not referrer:
            raise HTTPException(400, "Referral code is invalid")

        phone_seen = await fetch_one(
            db,
            "SELECT 1 FROM users WHERE phone=:phone AND 'customer'=ANY(roles) AND status <> 'DELETED' LIMIT 1",
            {"phone": phone},
        )
        if phone_seen:
            await record_invalid_customer_referral_attempt(db, referred_by_customer_id, phone)
            await db.commit()
            raise HTTPException(400, "This mobile number is already registered.")

    user_id = uid("u")
    referral_code = await generate_customer_referral_code(db)
    result = await db.execute(
        text(
            """
            INSERT INTO users
              (id,name,phone,email,password_hash,roles,status,terms_accepted,terms_accepted_at,referral_code,referred_by_customer_id)
            VALUES
              (:id,:name,:phone,:email,:password_hash,ARRAY['customer'],'ACTIVE',TRUE,now(),:referral_code,:referred_by_customer_id)
            RETURNING *
            """
        ),
        {
            "id": user_id,
            "name": full_name,
            "phone": phone,
            "email": email,
            "password_hash": hash_password(body.password),
            "referral_code": referral_code,
            "referred_by_customer_id": referred_by_customer_id,
        },
    )
    user = dict(result.mappings().first())
    wallet_result = await db.execute(
        text("INSERT INTO customer_wallets (wallet_id,customer_id,balance,created_at,updated_at) VALUES (gen_random_uuid(),:customer_id,0,now(),now()) RETURNING wallet_id"),
        {"customer_id": user["customer_id"]},
    )
    wallet_id = wallet_result.scalar_one()

    if referred_by_customer_id:
        await ensure_customer_wallet_by_customer_id(db, referred_by_customer_id)
        await db.execute(
            text(
                """
                INSERT INTO customer_referrals
                  (id,referrer_customer_id,referred_customer_id,referred_phone_number,is_valid,bonus_amount,created_at)
                VALUES
                  (gen_random_uuid(),:referrer,:referred,:phone,TRUE,:referrer_bonus,now())
                """
            ),
            {
                "referrer": referred_by_customer_id,
                "referred": user["customer_id"],
                "phone": phone,
                "referrer_bonus": CUSTOMER_REFERRER_BONUS,
            },
        )
        await db.execute(
            text(
                """
                UPDATE customer_wallets
                SET balance=balance + :amount, updated_at=now()
                WHERE customer_id=:customer_id
                """
            ),
            {"amount": CUSTOMER_REFERRER_BONUS, "customer_id": referred_by_customer_id},
        )
        await db.execute(
            text(
                """
                UPDATE customer_wallets
                SET balance=balance + :amount, updated_at=now()
                WHERE customer_id=:customer_id
                """
            ),
            {"amount": CUSTOMER_REFERRED_BONUS, "customer_id": user["customer_id"]},
        )
        await db.execute(
            text(
                """
                INSERT INTO notifications (id,to_ref,channel,title,body)
                VALUES (:id,:to_ref,'in_app',:title,:body)
                """
            ),
            {
                "id": uid("n"),
                "to_ref": "user:" + referrer["id"],
                "title": "Customer referral bonus credited",
                "body": f"Your referral was successful. Rs {CUSTOMER_REFERRER_BONUS} has been added to your TailoraHub wallet.",
            },
        )
        await db.execute(
            text(
                """
                INSERT INTO notifications (id,to_ref,channel,title,body)
                VALUES (:id,:to_ref,'in_app',:title,:body)
                """
            ),
            {
                "id": uid("n"),
                "to_ref": "user:" + user["id"],
                "title": "Welcome referral bonus credited",
                "body": f"Your referral signup bonus is active. Rs {CUSTOMER_REFERRED_BONUS} has been added to your TailoraHub wallet.",
            },
        )

    tokens = await create_token_pair(db, user["id"], user.get("roles") or ["customer"])
    tokens.pop("_refresh_token_hash", None)
    await db.commit()
    return {
        **tokens,
        "role": "customer",
        "user": public_customer(user, wallet_id),
        "customer": public_customer(user, wallet_id),
    }
