from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.otp import OTP_TTL_MINUTES, OtpFlowError, issue_otp, verify_otp
from app.api.v1.session_tokens import create_token_pair, revoke_refresh_session, rotate_refresh_session
from app.core.database import get_db
from app.emailer import send_email
from app.integrations import sms_service
from app.schemas.auth import ForgotPasswordIn, LoginIn, ResetPasswordIn
from app.security import hash_password, verify_password


router = APIRouter()
PHONE_RE = re.compile(r"^[6-9]\d{9}$")


class RefreshIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    refresh_token: str = Field(alias="refreshToken", min_length=20)


@router.post("/logout", status_code=204, response_class=Response)
async def logout(body: RefreshIn, db: AsyncSession = Depends(get_db)) -> Response:
    await revoke_refresh_session(db, body.refresh_token)
    await db.commit()
    return Response(status_code=204)


def clean_phone(value: str) -> str:
    return re.sub(r"\D", "", value or "")


def password_is_strong(value: str) -> bool:
    return len(value or "") >= 8 and bool(re.search(r"[A-Za-z]", value)) and bool(re.search(r"\d", value))


def mask_target(target: str) -> str:
    if "@" in target:
        name, domain = target.split("@", 1)
        visible = name[:2] + "***" if len(name) > 2 else name[:1] + "***"
        return f"{visible}@{domain}"
    return f"******{target[-4:]}"


async def fetch_one(db: AsyncSession, sql: str, params: dict | None = None) -> dict | None:
    result = await db.execute(text(sql), params or {})
    row = result.mappings().first()
    return dict(row) if row else None


def public_user(row: dict) -> dict:
    return {
        "id": row["user_id"],
        "name": row["user_name"],
        "phone": row.get("user_phone"),
        "email": row.get("user_email"),
        "roles": row.get("roles") or [],
        "zoneId": row.get("user_zone_id"),
        "address": row.get("user_address"),
        "profileImage": row.get("profile_image"),
        "status": row.get("user_status"),
        "joined": row.get("joined"),
    }


def public_tailor(row: dict) -> dict:
    return {
        "id": row["tailor_pk"],
        "tailorId": str(row.get("tailor_id")),
        "userId": row["user_id"],
        "shop": row["shop"],
        "ownerName": row["owner_name"],
        "zoneId": row["zone_id"],
        "shopAddress": row.get("shop_address"),
        "email": row.get("tailor_email") or row.get("user_email"),
        "phone": row.get("phone_number") or row.get("user_phone"),
        "username": row.get("username"),
        "expertise": row.get("expertise") or [],
        "years": row.get("years") or 0,
        "bio": row.get("bio"),
        "approvalStatus": row.get("approval_status"),
        "verified": bool(row.get("verified")),
        "accountStatus": row.get("account_status"),
        "availability": row.get("availability"),
        "availableSlots": row.get("available_slots") or 0,
        "maxNewOrders": row.get("max_new_orders") or 0,
        "referralCode": row.get("referral_code"),
        "aadhaarVerified": bool(row.get("aadhaar_verified")),
    }


async def resolve_tailor(db: AsyncSession, identifier: str) -> dict:
    raw = identifier.strip()
    ident = raw.lower()
    phone = clean_phone(raw)
    row = await fetch_one(
        db,
        """SELECT
             u.id AS user_id, u.name AS user_name, u.phone AS user_phone, u.email AS user_email,
             u.password_hash AS user_password_hash, u.roles, u.zone_id AS user_zone_id,
             u.address AS user_address, u.profile_image, u.status AS user_status, u.joined,
             t.id AS tailor_pk, t.tailor_id, t.shop, t.owner_name, t.zone_id, t.shop_address,
             t.phone_number, t.email AS tailor_email, t.username, t.password_hash AS tailor_password_hash,
             t.expertise, t.years, t.bio, t.approval_status, t.verified, t.account_status,
             t.availability, t.available_slots, t.max_new_orders, t.referral_code, t.aadhaar_verified
           FROM tailors t
           JOIN users u ON u.id=t.user_id
           WHERE t.deleted_at IS NULL
             AND u.status='ACTIVE'
             AND 'tailor'=ANY(u.roles)
             AND t.account_status='ACTIVE'
             AND (
               lower(t.username)=:ident
               OR t.phone_number=:phone
               OR u.phone=:phone
               OR lower(t.email)=:ident
               OR lower(u.email)=:ident
             )
           LIMIT 1""",
        {"ident": ident, "phone": phone if PHONE_RE.fullmatch(phone) else ""},
    )
    if not row:
        raise HTTPException(401, "Tailor account not found")
    return row


async def resolve_customer(db: AsyncSession, identifier: str) -> dict:
    raw = identifier.strip()
    ident = raw.lower()
    phone = clean_phone(raw)
    row = await fetch_one(
        db,
        """SELECT
             u.id AS user_id, u.customer_id, u.name AS user_name, u.phone AS user_phone,
             u.email AS user_email, u.password_hash AS user_password_hash, u.roles,
             u.zone_id AS user_zone_id, u.address AS user_address, u.profile_image,
             u.status AS user_status, u.joined, u.referral_code, u.terms_accepted,
             cw.wallet_id
           FROM users u
           LEFT JOIN customer_wallets cw ON cw.customer_id=u.customer_id
           WHERE u.status='ACTIVE'
             AND 'customer'=ANY(u.roles)
             AND (u.phone=:phone OR lower(u.email)=:ident)
           LIMIT 1""",
        {"ident": ident, "phone": phone if PHONE_RE.fullmatch(phone) else ""},
    )
    if not row:
        raise HTTPException(401, "Customer account not found")
    return row


def login_target(row: dict, prefer_email: bool = False) -> tuple[str, bool]:
    email = (row.get("tailor_email") or row.get("user_email") or "").strip().lower()
    phone = clean_phone(row.get("phone_number") or row.get("user_phone") or "")
    if prefer_email and email:
        return email, True
    if phone and PHONE_RE.fullmatch(phone):
        return phone, False
    if email:
        return email, True
    raise HTTPException(400, "No verified phone or email is available for this tailor")


def customer_login_target(row: dict, prefer_email: bool = False) -> tuple[str, bool]:
    email = (row.get("user_email") or "").strip().lower()
    phone = clean_phone(row.get("user_phone") or "")
    if prefer_email and email:
        return email, True
    if phone and PHONE_RE.fullmatch(phone):
        return phone, False
    if email:
        return email, True
    raise HTTPException(400, "No phone or email is available for this customer")


async def send_code(db: AsyncSession, row: dict, purpose: str, prefer_email: bool = False) -> dict:
    target, is_email = login_target(row, prefer_email=prefer_email)
    try:
        code, expires_at = await issue_otp(db, target, purpose)
        await db.commit()
    except OtpFlowError as exc:
        await db.rollback()
        raise HTTPException(exc.status_code, exc.message)

    if is_email:
        delivery = send_email(target, "Your TailoraHub verification code", f"Your verification code is {code}. It is valid for {OTP_TTL_MINUTES} minutes.", purpose="verify")
        mock_mode = delivery.get("mode") == "mock"
    else:
        delivery = sms_service().send_otp(target, code)
        mock_mode = delivery.get("mode") == "mock"

    return {
        "otpSent": True,
        "target": mask_target(target),
        "channel": "email" if is_email else "sms",
        "expiresInSeconds": OTP_TTL_MINUTES * 60,
        "devOtp": code if mock_mode else None,
    }


async def send_customer_code(db: AsyncSession, row: dict, purpose: str, prefer_email: bool = False) -> dict:
    target, is_email = customer_login_target(row, prefer_email=prefer_email)
    try:
        code, _ = await issue_otp(db, target, purpose)
        await db.commit()
    except OtpFlowError as exc:
        await db.rollback()
        raise HTTPException(exc.status_code, exc.message)

    if is_email:
        delivery = send_email(target, "Your TailoraHub verification code", f"Your verification code is {code}. It is valid for {OTP_TTL_MINUTES} minutes.", purpose="verify")
        mock_mode = delivery.get("mode") == "mock"
    else:
        delivery = sms_service().send_otp(target, code)
        mock_mode = delivery.get("mode") == "mock"

    return {
        "otpSent": True,
        "target": mask_target(target),
        "channel": "email" if is_email else "sms",
        "expiresInSeconds": OTP_TTL_MINUTES * 60,
        "devOtp": code if mock_mode else None,
    }


async def verify_code(db: AsyncSession, row: dict, purpose: str, code: str, prefer_email: bool = False) -> None:
    target, _ = login_target(row, prefer_email=prefer_email)
    try:
        matched = await verify_otp(db, target, purpose, code)
        await db.commit()
    except OtpFlowError as exc:
        await db.rollback()
        raise HTTPException(exc.status_code, exc.message)
    if not matched:
        raise HTTPException(401, "Incorrect code")


async def verify_customer_code(db: AsyncSession, row: dict, purpose: str, code: str, prefer_email: bool = False) -> None:
    target, _ = customer_login_target(row, prefer_email=prefer_email)
    try:
        matched = await verify_otp(db, target, purpose, code)
        await db.commit()
    except OtpFlowError as exc:
        await db.rollback()
        raise HTTPException(exc.status_code, exc.message)
    if not matched:
        raise HTTPException(401, "Incorrect code")


async def auth_payload(db: AsyncSession, row: dict) -> dict:
    roles = row.get("roles") or ["tailor"]
    tokens = await create_token_pair(db, row["user_id"], roles)
    await db.commit()
    tokens.pop("_refresh_token_hash", None)
    return {
        **tokens,
        "role": "tailor",
        "user": public_user(row),
        "tailor": public_tailor(row),
        "tailorPending": row.get("approval_status") == "PENDING_APPROVAL",
    }


def customer_public_payload(row: dict) -> dict:
    customer_id = str(row["customer_id"])
    wallet_id = str(row["wallet_id"]) if row.get("wallet_id") else None
    return {
        "id": row["user_id"],
        "customer_id": customer_id,
        "customerId": customer_id,
        "name": row["user_name"],
        "fullName": row["user_name"],
        "phone": row.get("user_phone"),
        "phoneNumber": row.get("user_phone"),
        "email": row.get("user_email"),
        "roles": row.get("roles") or ["customer"],
        "status": row.get("user_status"),
        "referral_code": row.get("referral_code"),
        "referralCode": row.get("referral_code"),
        "wallet_id": wallet_id,
        "walletId": wallet_id,
        "joined": row.get("joined"),
    }


async def customer_auth_payload(db: AsyncSession, row: dict) -> dict:
    roles = row.get("roles") or ["customer"]
    tokens = await create_token_pair(db, row["user_id"], roles)
    await db.commit()
    tokens.pop("_refresh_token_hash", None)
    customer = customer_public_payload(row)
    return {
        **tokens,
        "role": "customer",
        "user": public_user(row),
        "customer": customer,
    }


@router.get("/scaffold")
async def auth_scaffold() -> dict:
    return {"module": "auth", "ready": True}


@router.post("/login")
async def tailor_login(body: LoginIn, db: AsyncSession = Depends(get_db)) -> dict:
    row = await resolve_tailor(db, body.identifier)
    if body.mode == "password":
        if not body.password:
            raise HTTPException(400, "Password is required")
        tailor_hash = row.get("tailor_password_hash")
        valid = verify_password(body.password, tailor_hash) if tailor_hash else verify_password(body.password, row.get("user_password_hash"))
        if not valid:
            raise HTTPException(401, "Invalid tailor credentials")
        return await auth_payload(db, row)

    if body.otp:
        await verify_code(db, row, "login", body.otp)
        return await auth_payload(db, row)
    return await send_code(db, row, "login")


@router.post("/customer-login")
async def customer_login(body: LoginIn, db: AsyncSession = Depends(get_db)) -> dict:
    row = await resolve_customer(db, body.identifier)
    prefer_email = "@" in body.identifier
    if body.mode == "password":
        if not body.password:
            raise HTTPException(400, "Password is required")
        if not verify_password(body.password, row.get("user_password_hash")):
            raise HTTPException(401, "Invalid customer credentials")
        return await customer_auth_payload(db, row)

    if body.otp:
        await verify_customer_code(db, row, "login", body.otp, prefer_email=prefer_email)
        return await customer_auth_payload(db, row)
    return await send_customer_code(db, row, "login", prefer_email=prefer_email)


@router.post("/refresh")
async def refresh_session(body: RefreshIn, db: AsyncSession = Depends(get_db)) -> dict:
    try:
        tokens = await rotate_refresh_session(db, body.refresh_token)
        await db.commit()
    except Exception:
        await db.rollback()
        raise HTTPException(401, "Refresh token expired or revoked")
    return tokens


@router.post("/forgot-password")
async def forgot_password(body: ForgotPasswordIn, db: AsyncSession = Depends(get_db)) -> dict:
    row = await resolve_tailor(db, body.identifier)
    prefer_email = "@" in body.identifier
    return await send_code(db, row, "forgot_password", prefer_email=prefer_email)


@router.post("/reset-password")
async def reset_password(body: ResetPasswordIn, db: AsyncSession = Depends(get_db)) -> dict:
    if body.new_password != body.confirm_password:
        raise HTTPException(400, "Password and confirm password must match")
    if not password_is_strong(body.new_password):
        raise HTTPException(400, "Password must be at least 8 characters and include one letter and one number")
    row = await resolve_tailor(db, body.identifier)
    prefer_email = "@" in body.identifier
    await verify_code(db, row, "forgot_password", body.otp, prefer_email=prefer_email)
    password_hash = hash_password(body.new_password)
    if "customer" not in (row.get("roles") or []):
        await db.execute(text("UPDATE users SET password_hash=:hash WHERE id=:id"), {"hash": password_hash, "id": row["user_id"]})
    await db.execute(text("UPDATE tailors SET password_hash=:hash, updated_at=now() WHERE id=:id"), {"hash": password_hash, "id": row["tailor_pk"]})
    await db.commit()
    return {"reset": True, "message": "Password updated. You can now sign in."}


@router.post("/customer-forgot-password")
async def customer_forgot_password(body: ForgotPasswordIn, db: AsyncSession = Depends(get_db)) -> dict:
    row = await resolve_customer(db, body.identifier)
    prefer_email = "@" in body.identifier
    return await send_customer_code(db, row, "forgot_password", prefer_email=prefer_email)


@router.post("/customer-reset-password")
async def customer_reset_password(body: ResetPasswordIn, db: AsyncSession = Depends(get_db)) -> dict:
    if body.new_password != body.confirm_password:
        raise HTTPException(400, "Password and confirm password must match")
    if not password_is_strong(body.new_password):
        raise HTTPException(400, "Password must be at least 8 characters and include one letter and one number")
    row = await resolve_customer(db, body.identifier)
    prefer_email = "@" in body.identifier
    await verify_customer_code(db, row, "forgot_password", body.otp, prefer_email=prefer_email)
    await db.execute(
        text("UPDATE users SET password_hash=:hash WHERE id=:id"),
        {"hash": hash_password(body.new_password), "id": row["user_id"]},
    )
    await db.commit()
    return {"reset": True, "message": "Password updated. You can now sign in."}
