from base64 import b64decode
from datetime import date, datetime, timedelta, timezone
import ipaddress
import json
import logging
from pathlib import Path
import re
import secrets
import string
import time
import uuid

import jwt
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from . import otp
from .api.v1 import api_router
from .api.v1.bookings import create_razorpay_order, require_razorpay_credentials, verify_razorpay_signature
from .db import db_session, fetch_all, fetch_one, run_schema
from .emailer import send_email
from .integrations import aadhaar_kyc_service, maps_service, payment_service, sms_service
from .pagination import PageParams
from .qr import generate_wallet_qr
from .core.security import create_refresh_token, decode_refresh_token
from .security import (
    create_token,
    decode_token,
    encrypt_aadhaar,
    hash_aadhaar,
    hash_password,
    hash_refresh_token,
    is_valid_aadhaar_format,
    verify_password,
)
from .settings import settings
from .services.media_storage import MediaStorageError, get_media_storage, validate_file_signature
from .services.tracker_service import tracker_connections
from .tasks.queue import enqueue_task
from .middleware.traffic import TrafficProtectionMiddleware
from .observability import configure_logging, emit_metric, reset_request_id, set_request_id


UPLOADS_DIR = settings.base_dir / "uploads"
media_storage = get_media_storage()
configure_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title="TailoraHub API", version="1.0.0")
if settings.media_storage_backend == "local":
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")
app.add_middleware(TrafficProtectionMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins + ["http://localhost:3000", "http://127.0.0.1:5173"],
    allow_origin_regex=r"^http://(localhost|127\.0\.0\.1):\d+$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _configured_networks(values: list[str], setting_name: str) -> list[ipaddress.IPv4Network | ipaddress.IPv6Network]:
    networks = []
    for value in values:
        try:
            networks.append(ipaddress.ip_network(value, strict=False))
        except ValueError as exc:
            raise RuntimeError(f"Invalid {setting_name} entry: {value}") from exc
    return networks


ADMIN_ALLOWED_NETWORKS = _configured_networks(settings.admin_allowed_networks, "ADMIN_ALLOWED_NETWORKS")
ADMIN_TRUSTED_PROXY_NETWORKS = _configured_networks(settings.admin_trusted_proxy_networks, "ADMIN_TRUSTED_PROXY_NETWORKS")


def _ip_in_networks(value: str, networks: list[ipaddress.IPv4Network | ipaddress.IPv6Network]) -> bool:
    try:
        address = ipaddress.ip_address(value.strip())
    except ValueError:
        return False
    return any(address.version == network.version and address in network for network in networks)


def _request_client_ip(request: Request) -> str:
    peer = request.client.host if request.client else ""
    if not _ip_in_networks(peer, ADMIN_TRUSTED_PROXY_NETWORKS):
        return peer
    forwarded = [part.strip() for part in request.headers.get("x-forwarded-for", "").split(",") if part.strip()]
    for candidate in reversed(forwarded):
        if not _ip_in_networks(candidate, ADMIN_TRUSTED_PROXY_NETWORKS):
            return candidate
    return peer


@app.middleware("http")
async def restrict_admin_network(request: Request, call_next):
    path = request.url.path.rstrip("/")
    is_admin_request = (
        path == "/api/auth/admin/login"
        or path.startswith("/api/admin/")
        or path == "/api/admin"
        or path.startswith("/api/v1/admin/")
        or path == "/api/v1/admin"
    )
    if is_admin_request and ADMIN_ALLOWED_NETWORKS:
        client_ip = _request_client_ip(request)
        if not _ip_in_networks(client_ip, ADMIN_ALLOWED_NETWORKS):
            return JSONResponse(status_code=403, content={"detail": "Administrator access is not available from this network."})
    return await call_next(request)


REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{8,128}$")


@app.middleware("http")
async def observe_request(request: Request, call_next):
    supplied_request_id = request.headers.get("x-request-id", "").strip()
    request_id = supplied_request_id if REQUEST_ID_PATTERN.fullmatch(supplied_request_id) else uuid.uuid4().hex
    token = set_request_id(request_id)
    started = time.perf_counter()
    try:
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        route = getattr(request.scope.get("route"), "path", "unmatched")
        status_code = response.status_code
        logger.log(
            logging.WARNING if status_code >= 500 else logging.INFO,
            "http_request_completed",
            extra={
                "event": "http_request_completed",
                "http_method": request.method,
                "route": route,
                "status_code": status_code,
                "duration_ms": duration_ms,
            },
        )
        if status_code >= 500:
            emit_metric("Http5xx", 1)
        response.headers["X-Request-ID"] = request_id
        return response
    except Exception:
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        route = getattr(request.scope.get("route"), "path", "unmatched")
        logger.exception(
            "http_request_failed",
            extra={
                "event": "http_request_failed",
                "http_method": request.method,
                "route": route,
                "status_code": 500,
                "duration_ms": duration_ms,
            },
        )
        emit_metric("Http5xx", 1)
        raise
    finally:
        reset_request_id(token)

app.include_router(api_router, prefix="/api/v1")
bearer = HTTPBearer(auto_error=False)

GARMENTS = [
    {"id": "blouse", "name": "Saree Blouse", "base": 450, "days": 4},
    {"id": "salwar", "name": "Salwar / Kurta", "base": 650, "days": 5},
    {"id": "lehenga", "name": "Lehenga", "base": 2800, "days": 12},
    {"id": "shirt", "name": "Shirt", "base": 500, "days": 4},
    {"id": "trousers", "name": "Trousers", "base": 550, "days": 4},
    {"id": "suit", "name": "Suit (2-piece)", "base": 4800, "days": 14},
    {"id": "alteration", "name": "Alteration", "base": 180, "days": 2},
    {"id": "bridal", "name": "Bridal / Occasion", "base": 5500, "days": 21},
]
ZONES = [
    {"id": "tnagar", "name": "T. Nagar"},
    {"id": "annanagar", "name": "Anna Nagar"},
    {"id": "adyar", "name": "Adyar"},
    {"id": "velachery", "name": "Velachery"},
    {"id": "mylapore", "name": "Mylapore"},
]
ACCOUNT_STATUSES = ["ACTIVE", "INACTIVE", "SUSPENDED", "BLOCKED", "DELETED"]
APPROVAL_STATUSES = ["PENDING_APPROVAL", "APPROVED", "REJECTED"]
PAYMENT_STATUSES = ["PENDING", "PROCESSING", "PAID", "FAILED", "REFUNDED"]
AVAILABILITY_STATUSES = ["AVAILABLE", "FEW_SLOTS_AVAILABLE", "BUSY", "NOT_AVAILABLE"]
SUPPORT_STATUSES = ["OPEN", "PENDING", "WAITING_ON_CUSTOMER", "RESOLVED", "CLOSED"]
SUPPORT_PRIORITIES = ["LOW", "NORMAL", "HIGH", "URGENT"]
VALID_OTP_PURPOSES = {"registration_phone", "registration_email", "login", "forgot_password", "delivery", "withdrawal", "measurement_arrival"}
PHONE_RE = re.compile(r"^[6-9]\d{9}$")
ORDER_STATUSES = [
    "REQUESTED",
    "ACCEPTED",
    "MEASUREMENT_SCHEDULED",
    "MEASUREMENT_COMPLETED",
    "CLOTH_RECEIVED",
    "CUTTING_STARTED",
    "CUTTING_COMPLETED",
    "STITCHING_STARTED",
    "STITCHING_IN_PROGRESS",
    "STITCHING_COMPLETED",
    "READY_FOR_DELIVERY",
    "READY_FOR_HANDOVER",
    "PAYMENT_PENDING",
    "PAYMENT_COMPLETED",
    "DELIVERY_PENDING",
    "DELIVERED",
    "COMPLETED",
    "CANCELLED",
]


class AdminLogin(BaseModel):
    username: str
    password: str


class RoleLogin(BaseModel):
    role: str
    identifier: str
    password: str


class OtpRequest(BaseModel):
    email: EmailStr


class OtpVerify(BaseModel):
    email: EmailStr
    otp: str = Field(min_length=4, max_length=12)


class RefreshRequest(BaseModel):
    refreshToken: str | None = None
    refresh_token: str | None = None


class ServiceIn(BaseModel):
    garmentId: str | None = None
    name: str
    description: str | None = None
    price: int = Field(gt=0)
    days: int = Field(default=5, gt=0)


class RegisterIn(BaseModel):
    role: str = "customer"
    name: str
    email: EmailStr
    phone: str
    password: str | None = None
    zoneId: str | None = "tnagar"
    address: str | None = None
    lat: float | None = None
    lng: float | None = None
    profileImage: str | None = None
    vehicle: str | None = None
    shop: str | None = None
    specs: list[str] = Field(default_factory=list)
    services: list[ServiceIn] = Field(default_factory=list)
    years: int = 1
    workingHours: str | None = None
    bio: str | None = None
    portfolio: list[str] = Field(default_factory=list)
    bank: str | None = None
    idProof: str | None = None
    shopProof: str | None = None
    # Tailor KYC/identity fields (file 05) -- only enforced when role == "tailor".
    username: str | None = None
    aadhaarNumber: str | None = None
    dob: date | None = None
    stitchingSinceDate: date | None = None
    experienceYearsBase: float | None = None
    referralCode: str | None = None
    termsAccepted: bool = False


class OtpSendIn(BaseModel):
    target: str = Field(min_length=3)
    purpose: str


class OtpVerifyIn(BaseModel):
    target: str = Field(min_length=3)
    purpose: str
    otp: str = Field(min_length=4, max_length=8)


class CheckAvailabilityIn(BaseModel):
    field: str
    value: str = Field(min_length=1)
    role: str | None = None


class BookingCreate(BaseModel):
    tailorIds: list[str] = Field(min_length=1)
    serviceId: str | None = None
    garmentId: str | None = None
    serviceName: str | None = None
    quantity: int = Field(default=1, gt=0)
    requirements: str | None = None
    preferredDate: date | None = None
    instructions: str | None = None
    measurementMode: str = "SHOP"
    address: str | None = None
    lat: float | None = None
    lng: float | None = None
    visitDate: date | None = None
    visitSlot: str | None = None
    visitNotes: str | None = None


class RazorpayCreateOrderIn(BaseModel):
    amount: int
    currency: str = Field(default="INR", min_length=3, max_length=3)
    receipt: str | None = Field(default=None, max_length=40)


class RazorpayVerifyPaymentIn(BaseModel):
    razorpay_order_id: str | None = None
    order_id: str | None = None
    razorpay_payment_id: str | None = None
    payment_id: str | None = None
    razorpay_signature: str | None = None


@app.post("/api/create-order")
async def create_standard_razorpay_order(body: RazorpayCreateOrderIn):
    if settings.app_env == "production":
        raise HTTPException(404, "Use the authenticated booking payment endpoint.")
    if body.amount < 100:
        raise HTTPException(400, "Amount must be at least 100 paise.")
    currency = body.currency.strip().upper()
    if currency != "INR":
        raise HTTPException(400, "Only INR payments are supported.")
    key_id, key_secret = require_razorpay_credentials()
    receipt = (body.receipt or f"TH-{uuid.uuid4().hex[:20]}").strip()[:40]
    order = await create_razorpay_order(
        key_id,
        key_secret,
        {
            "amount": body.amount,
            "currency": currency,
            "receipt": receipt,
            "payment_capture": 1,
        },
    )
    order_id = order.get("id")
    if not order_id:
        raise HTTPException(500, "Razorpay did not return an order id.")
    return {
        "order_id": order_id,
        "razorpay_order_id": order_id,
        "amount": int(order.get("amount") or body.amount),
        "currency": order.get("currency") or currency,
        "key_id": key_id,
    }


@app.post("/api/verify-payment")
async def verify_standard_razorpay_payment(body: RazorpayVerifyPaymentIn):
    if settings.app_env == "production":
        raise HTTPException(404, "Use the authenticated booking payment endpoint.")
    order_id = (body.razorpay_order_id or body.order_id or "").strip()
    payment_id = (body.razorpay_payment_id or body.payment_id or "").strip()
    signature = (body.razorpay_signature or "").strip()
    if not order_id or not payment_id or not signature:
        raise HTTPException(400, "Missing Razorpay order id, payment id, or signature.")
    _, key_secret = require_razorpay_credentials()
    if not verify_razorpay_signature(order_id, payment_id, signature, key_secret):
        raise HTTPException(400, "Razorpay payment signature is invalid.")
    return {"ok": True, "verified": True, "order_id": order_id, "payment_id": payment_id}


class AvailabilityPatch(BaseModel):
    availability: str
    availableSlots: int | None = None
    maxNewOrders: int | None = None
    nextAvailable: date | None = None
    availabilityNote: str | None = None
    acceptingRequests: bool | None = None
    approvalMode: str | None = None


class SlotCapacityItem(BaseModel):
    slot: str
    enabled: bool = True
    capacity: int = Field(default=1, ge=0, le=100)


class SlotCapacityUpdate(BaseModel):
    date: date
    slots: list[SlotCapacityItem]


class TailorMediaUpload(BaseModel):
    name: str
    mediaType: str
    dataUrl: str


class TailorProfileImageUpload(BaseModel):
    name: str
    mediaType: str
    dataUrl: str


class TailorMediaPresign(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    mediaType: str
    sizeBytes: int = Field(gt=0)


class TailorMediaComplete(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    mediaType: str
    objectKey: str = Field(min_length=1, max_length=500)


class TailorOfferCreate(BaseModel):
    title: str = Field(min_length=3, max_length=140)
    body: str = Field(min_length=5, max_length=1000)
    discount: str | None = Field(default=None, max_length=80)
    expiresAt: date | None = None
    mediaName: str | None = None
    mediaType: str | None = None
    dataUrl: str | None = None


class TailorRequestReject(BaseModel):
    reason: str = "Rejected by tailor"


class TailorOrderUpdate(BaseModel):
    status: str | None = None
    note: str | None = None
    expectedCompletion: date | None = None
    delayReason: str | None = None


class AdditionalChargeIn(BaseModel):
    description: str
    reason: str | None = None
    amount: int = Field(gt=0)


class DeliveryOtpIn(BaseModel):
    otp: str


class PaymentIn(BaseModel):
    method: str = "manual"
    txnRef: str | None = None


class ReviewCreate(BaseModel):
    rating: float = Field(ge=1, le=5)
    body: str | None = None
    images: list[str] = Field(default_factory=list)


class SupportTicketCreate(BaseModel):
    category: str
    subject: str = Field(min_length=3, max_length=160)
    description: str = Field(min_length=5, max_length=4000)
    priority: str = "NORMAL"
    orderId: str | None = None


class SupportMessageCreate(BaseModel):
    body: str = Field(min_length=1, max_length=4000)


class SupportTicketPatch(BaseModel):
    status: str | None = None
    priority: str | None = None
    assignedTo: str | None = None
    note: str | None = None


class CustomerPatch(BaseModel):
    name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    zoneId: str | None = None
    address: str | None = None
    status: str | None = None
    reason: str | None = None


class TailorProfilePatch(BaseModel):
    # file 08: dob/Aadhaar are permanently locked -- deliberately absent from
    # this model so no request body shape can ever reach them.
    fullName: str | None = None
    bio: str | None = None
    experienceYearsBase: float | None = None
    phone: str | None = None
    email: EmailStr | None = None


class LocationIn(BaseModel):
    addressText: str = Field(min_length=1)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class TailorServiceCreate(BaseModel):
    serviceName: str = Field(min_length=1, max_length=160)
    category: str | None = None
    price: int = Field(gt=0)
    isCombo: bool = False
    comboItems: list[str] = Field(default_factory=list)
    description: str | None = None


class TailorServicePatch(BaseModel):
    serviceName: str | None = None
    category: str | None = None
    price: int | None = Field(default=None, gt=0)
    isCombo: bool | None = None
    comboItems: list[str] | None = None
    description: str | None = None
    isActive: bool | None = None


class TailorPatch(BaseModel):
    shop: str | None = None
    zoneId: str | None = None
    shopAddress: str | None = None
    bio: str | None = None
    years: int | None = None
    verified: bool | None = None
    accountStatus: str | None = None
    approvalStatus: str | None = None
    availability: str | None = None
    availableSlots: int | None = None
    featured: bool | None = None
    plan: str | None = None
    reason: str | None = None


class OrderPatch(BaseModel):
    status: str | None = None
    paymentStatus: str | None = None
    expectedCompletion: date | None = None
    notes: str | None = None
    reason: str | None = None


class ComplaintPatch(BaseModel):
    status: str | None = None
    resolution: str | None = None


class ReviewPatch(BaseModel):
    hidden: bool | None = None
    reason: str | None = None


def uid(prefix: str) -> str:
    return prefix + "_" + uuid.uuid4().hex[:12]


def clean_phone(phone: str) -> str:
    return re.sub(r"\D", "", phone or "")


def garment(gid: str | None) -> dict:
    return next((g for g in GARMENTS if g["id"] == gid), {"id": gid or "custom", "name": "Custom stitching", "base": 500, "days": 5})


def as_public_user(u: dict | None) -> dict | None:
    if not u:
        return None
    return {
        "id": u["id"],
        "name": u["name"],
        "phone": u.get("phone"),
        "email": u.get("email"),
        "roles": u.get("roles") or [],
        "zoneId": u.get("zone_id"),
        "address": u.get("address"),
        "profileImage": u.get("profile_image"),
        "status": u.get("status"),
        "joined": u.get("joined"),
        "anonymized": u.get("anonymized"),
    }


def create_session_payload(db: Session, user: dict) -> dict:
    refresh_token = create_refresh_token(user["id"])
    refresh_payload = decode_refresh_token(refresh_token)
    token_hash = hash_refresh_token(refresh_token)
    access_token = create_token(user, token_hash)
    expires_at = datetime.fromtimestamp(refresh_payload["exp"], timezone.utc)
    db.execute(
        text(
            """
            INSERT INTO refresh_sessions (id,user_id,token_hash,expires_at,last_activity_at,created_at)
            VALUES (gen_random_uuid(),:user_id,:token_hash,:expires_at,now(),now())
            """
        ),
        {"user_id": user["id"], "token_hash": token_hash, "expires_at": expires_at},
    )
    return {
        "token": access_token,
        "access_token": access_token,
        "refreshToken": refresh_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in_seconds": settings.access_token_minutes * 60,
    }


def rotate_session_payload(db: Session, refresh_token: str) -> dict:
    refresh_payload = decode_refresh_token(refresh_token)
    if refresh_payload.get("type") != "refresh":
        raise HTTPException(401, "Refresh token expired or revoked")
    old_hash = hash_refresh_token(refresh_token)
    session = fetch_one(
        db,
        """
        SELECT rs.*, u.*
        FROM refresh_sessions rs
        JOIN users u ON u.id=rs.user_id
        WHERE rs.token_hash=:token_hash
          AND rs.revoked_at IS NULL
          AND rs.expires_at > now()
          AND u.status <> 'DELETED'
        FOR UPDATE OF rs
        """,
        {"token_hash": old_hash},
    )
    if not session or session["user_id"] != refresh_payload.get("sub"):
        raise HTTPException(401, "Refresh token expired or revoked")
    if session.get("last_activity_at") and (datetime.now(timezone.utc) - session["last_activity_at"]).total_seconds() >= settings.session_inactivity_minutes * 60:
        db.execute(text("UPDATE refresh_sessions SET revoked_at=now() WHERE token_hash=:token_hash"), {"token_hash": old_hash})
        raise HTTPException(401, "Session expired due to inactivity")
    user = fetch_one(db, "SELECT * FROM users WHERE id=:id", {"id": session["user_id"]})
    next_payload = create_session_payload(db, user)
    next_hash = hash_refresh_token(next_payload["refreshToken"])
    db.execute(
        text("UPDATE refresh_sessions SET last_activity_at=:last_activity_at WHERE token_hash=:next_hash"),
        {"last_activity_at": session["last_activity_at"], "next_hash": next_hash},
    )
    db.execute(
        text("UPDATE refresh_sessions SET revoked_at=now(), replaced_by_token_hash=:next_hash WHERE token_hash=:old_hash"),
        {"next_hash": next_hash, "old_hash": old_hash},
    )
    return next_payload


def compute_experience_display(experience_years_base, stitching_since_date) -> float:
    """base + 0.1 per fully-completed month since stitching_since_date (file 08)."""
    base = float(experience_years_base or 0)
    if not stitching_since_date:
        return round(base, 1)
    today = date.today()
    months = (today.year - stitching_since_date.year) * 12 + (today.month - stitching_since_date.month)
    if today.day < stitching_since_date.day:
        months -= 1
    return round(base + max(months, 0) * 0.1, 1)


def generate_tailor_referral_code(db: Session) -> str:
    alphabet = string.ascii_uppercase + string.digits
    while True:
        code = "".join(secrets.choice(alphabet) for _ in range(8))
        if not fetch_one(db, "SELECT 1 FROM tailors WHERE referral_code=:code", {"code": code}):
            return code


def as_tailor(t: dict | None) -> dict | None:
    if not t:
        return None
    return {
        "id": t["id"],
        "userId": t["user_id"],
        "shop": t["shop"],
        "ownerName": t["owner_name"],
        "zoneId": t["zone_id"],
        "shopAddress": t.get("shop_address"),
        "lat": float(t["lat"]) if t.get("lat") is not None else None,
        "lng": float(t["lng"]) if t.get("lng") is not None else None,
        "email": t.get("email"),
        "phone": t.get("phone"),
        "expertise": t.get("expertise") or [],
        "years": t.get("years") or 1,
        "workingHours": t.get("working_hours"),
        "bio": t.get("bio"),
        "profileImage": t.get("profile_image"),
        "portfolio": t.get("portfolio") or [],
        "documents": t.get("documents") or {},
        "rating": float(t.get("rating") or 0),
        "ratingCount": t.get("rating_count") or 0,
        "completed": t.get("completed") or 0,
        "onTimePct": t.get("on_time_pct") or 100,
        "responseMins": t.get("response_mins") or 20,
        "approvalStatus": t.get("approval_status"),
        "verified": bool(t.get("verified")),
        "accountStatus": t.get("account_status"),
        "rejectReason": t.get("reject_reason"),
        "availability": t.get("availability"),
        "availableSlots": t.get("available_slots") or 0,
        "maxNewOrders": t.get("max_new_orders") or 0,
        "nextAvailable": t.get("next_available"),
        "availabilityNote": t.get("availability_note"),
        "acceptingRequests": bool(t.get("accepting_requests", True)),
        "availabilityUpdated": t.get("availability_updated"),
        "approvalMode": t.get("approval_mode") or "AUTOMATIC",
        "startingPrice": t.get("starting_price"),
        "activeOrders": t.get("active_orders") or 0,
        "favoriteCount": t.get("favorite_count") or 0,
        "followerCount": t.get("follower_count") or 0,
        "favoritedByMe": bool(t.get("favorited_by_me")),
        "followedByMe": bool(t.get("followed_by_me")),
        "plan": t.get("plan"),
        "featured": bool(t.get("featured")),
        "created": t.get("created"),
        # file 08/15: real-time-computed, safe for public display (unlike dob/aadhaar).
        "experienceDisplay": compute_experience_display(t.get("experience_years_base"), t.get("stitching_since_date")),
    }


def as_tailor_private(t: dict | None) -> dict | None:
    """Tailor's own profile view (file 08) -- adds KYC-adjacent-but-not-secret fields
    on top of as_tailor(). Never includes aadhaar_number_hash/aadhaar_number_encrypted."""
    base = as_tailor(t)
    if not base or not t:
        return base
    return {
        **base,
        "username": t.get("username"),
        "dob": t.get("dob"),
        "aadhaarVerified": bool(t.get("aadhaar_verified")),
        "experienceYearsBase": float(t.get("experience_years_base") or 0),
        "stitchingSinceDate": t.get("stitching_since_date"),
        "termsAccepted": bool(t.get("terms_accepted")),
        "referralCode": t.get("referral_code"),
        "isAvailable": bool(t.get("is_available", True)),
    }


def as_tailor_service(row: dict | None) -> dict | None:
    if not row:
        return None
    return {
        # tailor_services.id (TEXT) is what orders/booking_requests actually FK to --
        # the newer service_id UUID column exists but nothing else references it, so
        # it's deliberately not surfaced here to avoid two identifiers for one row.
        "serviceId": row["id"],
        "tailorId": row["tailor_id"],
        "serviceName": row.get("service_name") or row.get("name"),
        "category": row.get("category"),
        "price": row["price"],
        "isCombo": bool(row.get("is_combo")),
        "comboItems": row.get("combo_items") or [],
        "description": row.get("description"),
        "isActive": bool(row.get("is_active", True)),
        "days": row.get("days"),
        "createdAt": row.get("created_at"),
    }


def as_offer(row: dict | None) -> dict | None:
    if not row:
        return None
    return {
        "id": row["id"],
        "tailorId": row["tailor_id"],
        "title": row["title"],
        "body": row["body"],
        "discount": row.get("discount"),
        "mediaUrl": row.get("media_url"),
        "mediaType": row.get("media_type"),
        "active": bool(row.get("active", True)),
        "expiresAt": row.get("expires_at"),
        "createdAt": row.get("created_at"),
    }


def as_follower(row: dict | None) -> dict | None:
    if not row:
        return None
    customer_name = row.get("customer_name") or row.get("name") or "Customer"
    return {
        "customerProfileId": row["customer_profile_id"],
        "customerName": customer_name,
        "name": customer_name,
        "customerPhone": row.get("customer_phone"),
        "profileImage": row.get("profile_image"),
        "followedAt": row.get("followed_at"),
    }


def is_completed_order(row: dict | None) -> bool:
    if not row:
        return False
    return str(row.get("status") or "").lower() == "completed" or bool(row.get("completed_at"))


def current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(db_session),
    activity_at: str | None = Header(default=None, alias="X-TailoraHub-Activity-At"),
) -> dict:
    if not credentials:
        raise HTTPException(401, "Sign in required")
    try:
        payload = decode_token(credentials.credentials)
    except jwt.PyJWTError:
        raise HTTPException(401, "Session expired")
    session_id = payload.get("sid")
    if session_id:
        auth_session = fetch_one(db, "SELECT last_activity_at, revoked_at, expires_at FROM refresh_sessions WHERE token_hash=:sid", {"sid": session_id})
        now = datetime.now(timezone.utc)
        if not auth_session or auth_session.get("revoked_at") or auth_session["expires_at"] <= now:
            raise HTTPException(401, "Session expired")
        client_activity = None
        try:
            client_activity = datetime.fromtimestamp(int(activity_at or "0") / 1000, timezone.utc)
        except (TypeError, ValueError, OSError):
            pass
        effective_activity = max(auth_session["last_activity_at"], client_activity) if client_activity else auth_session["last_activity_at"]
        if (now - effective_activity).total_seconds() >= settings.session_inactivity_minutes * 60:
            db.execute(text("UPDATE refresh_sessions SET revoked_at=now() WHERE token_hash=:sid"), {"sid": session_id})
            db.commit()
            raise HTTPException(401, "Session expired due to inactivity")
        if client_activity and client_activity > auth_session["last_activity_at"] and client_activity <= now:
            db.execute(text("UPDATE refresh_sessions SET last_activity_at=:activity WHERE token_hash=:sid"), {"activity": client_activity, "sid": session_id})
            db.commit()
    user = fetch_one(db, "SELECT * FROM users WHERE id=:id", {"id": payload.get("sub")})
    if not user:
        raise HTTPException(401, "Account not found")
    if user["status"] == "DELETED":
        raise HTTPException(403, "This account has been removed")
    return user


def admin_user(user: dict = Depends(current_user)) -> dict:
    if "admin" not in (user.get("roles") or []):
        raise HTTPException(403, "Not permitted for your role")
    return user


def customer_user(user: dict = Depends(current_user)) -> dict:
    if "customer" not in (user.get("roles") or []):
        raise HTTPException(403, "Customer access required")
    if user["status"] != "ACTIVE":
        raise HTTPException(403, "Customer account is not active")
    return user


def tailor_user(user: dict = Depends(current_user)) -> dict:
    if "tailor" not in (user.get("roles") or []):
        raise HTTPException(403, "Tailor access required")
    if user["status"] != "ACTIVE":
        raise HTTPException(403, "Tailor account is not active")
    return user


def get_tailor_for_user(db: Session, user: dict) -> dict:
    tailor = fetch_one(db, "SELECT t.*, u.phone, u.email FROM tailors t JOIN users u ON u.id=t.user_id WHERE t.user_id=:uid AND t.deleted_at IS NULL", {"uid": user["id"]})
    if not tailor:
        raise HTTPException(404, "Tailor profile not found")
    return tailor


def notify(db: Session, to_ref: str, title: str, body: str, order_id: str | None = None) -> None:
    db.execute(
        text("""INSERT INTO notifications (id,to_ref,channel,title,body,order_id) VALUES (:id,:to_ref,'in_app',:title,:body,:order_id)"""),
        {"id": uid("n"), "to_ref": to_ref, "title": title, "body": body, "order_id": order_id},
    )


def notify_and_email(db: Session, to_ref: str, email: str | None, title: str, body: str, order_id: str | None = None) -> None:
    notify(db, to_ref, title, body, order_id)
    if email:
        send_email(email, title, body)


def notify_tailor_followers(db: Session, tailor_id: str, title: str, body: str) -> None:
    db.execute(
        text(
            """
            INSERT INTO notifications (id,to_ref,channel,title,body)
            SELECT 'n_' || replace(gen_random_uuid()::text,'-',''),
                   'user:' || customer_id,'in_app',:title,:body
            FROM tailor_followers
            WHERE tailor_id=:tid
            """
        ),
        {"tid": tailor_id, "title": title, "body": body},
    )


def customer_tailor_summary(db: Session, tailor_id: str, customer_id: str) -> dict:
    tailor = fetch_one(
        db,
        """SELECT t.*, u.phone, u.email, COALESCE(min(s.price),0)::int AS starting_price,
        (SELECT count(*) FROM orders o WHERE o.tailor_id=t.id AND o.status NOT IN ('COMPLETED','CANCELLED'))::int AS active_orders,
        (SELECT count(*) FROM customer_favorite_tailors cf WHERE cf.tailor_id=t.id)::int AS favorite_count,
        (SELECT count(*) FROM tailor_followers tf WHERE tf.tailor_id=t.id)::int AS follower_count,
        EXISTS(SELECT 1 FROM customer_favorite_tailors cf WHERE cf.tailor_id=t.id AND cf.customer_id=:customer_id) AS favorited_by_me,
        EXISTS(SELECT 1 FROM tailor_followers tf WHERE tf.tailor_id=t.id AND tf.customer_id=:customer_id) AS followed_by_me
        FROM tailors t
        JOIN users u ON u.id=t.user_id
        LEFT JOIN tailor_services s ON s.tailor_id=t.id AND s.active
        WHERE t.id=:id AND t.approval_status='APPROVED' AND t.account_status='ACTIVE' AND t.deleted_at IS NULL
        GROUP BY t.id, u.phone, u.email""",
        {"id": tailor_id, "customer_id": customer_id},
    )
    if not tailor:
        raise HTTPException(404, "Tailor is not available")
    return as_tailor(tailor)


def support_ticket_payload(db: Session, ticket: dict) -> dict:
    messages = fetch_all(
        db,
        "SELECT * FROM support_messages WHERE ticket_id=:id ORDER BY created_at LIMIT 500",
        {"id": ticket["id"]},
    )
    return {**ticket, "messages": messages}


def validate_support_order(db: Session, role: str, user: dict, order_id: str | None) -> None:
    if not order_id:
        return
    if role == "customer":
        order = fetch_one(db, "SELECT id FROM orders WHERE id=:id AND customer_id=:uid", {"id": order_id, "uid": user["id"]})
    else:
        tailor = get_tailor_for_user(db, user)
        order = fetch_one(db, "SELECT id FROM orders WHERE id=:id AND tailor_id=:tid", {"id": order_id, "tid": tailor["id"]})
    if not order:
        raise HTTPException(404, "Related order was not found for your account")


def create_support_ticket(db: Session, user: dict, role: str, body: SupportTicketCreate) -> dict:
    priority = body.priority.strip().upper()
    if priority not in SUPPORT_PRIORITIES:
        raise HTTPException(400, "Invalid support priority")
    category = body.category.strip()
    if not category:
        raise HTTPException(400, "Choose a support category")
    validate_support_order(db, role, user, body.orderId)
    ticket_id = uid("sup")
    code = fetch_one(db, "SELECT 'SUP-' || nextval('support_ticket_code_seq') AS code")["code"]
    db.execute(
        text(
            """INSERT INTO support_tickets
            (id,code,requester_id,requester_role,category,subject,description,priority,status,order_id)
            VALUES (:id,:code,:requester_id,:role,:category,:subject,:description,:priority,'OPEN',:order_id)"""
        ),
        {
            "id": ticket_id,
            "code": code,
            "requester_id": user["id"],
            "role": role,
            "category": category,
            "subject": body.subject.strip(),
            "description": body.description.strip(),
            "priority": priority,
            "order_id": body.orderId,
        },
    )
    db.execute(
        text("""INSERT INTO support_messages (ticket_id,author_id,author_name,author_role,body) VALUES (:ticket_id,:author_id,:author_name,:author_role,:body)"""),
        {"ticket_id": ticket_id, "author_id": user["id"], "author_name": user["name"], "author_role": role, "body": body.description.strip()},
    )
    notify(
        db,
        "admin",
        "New support ticket",
        f"{code} from {user['name']} ({role}) needs attention: {body.subject.strip()}",
        body.orderId,
    )
    db.commit()
    ticket = fetch_one(db, "SELECT st.*, u.name AS requester_name, u.email AS requester_email, u.phone AS requester_phone, o.code AS order_code FROM support_tickets st JOIN users u ON u.id=st.requester_id LEFT JOIN orders o ON o.id=st.order_id WHERE st.id=:id", {"id": ticket_id})
    return support_ticket_payload(db, ticket)


def user_support_tickets(db: Session, user: dict, role: str, page: PageParams) -> list[dict]:
    return fetch_all(
        db,
        """SELECT st.*, u.name AS requester_name, u.email AS requester_email, u.phone AS requester_phone, o.code AS order_code,
        (SELECT count(*) FROM support_messages sm WHERE sm.ticket_id=st.id)::int AS message_count
        FROM support_tickets st
        JOIN users u ON u.id=st.requester_id
        LEFT JOIN orders o ON o.id=st.order_id
        WHERE st.requester_id=:uid AND st.requester_role=:role
        ORDER BY st.last_activity_at DESC
        LIMIT :limit OFFSET :offset""",
        {"uid": user["id"], "role": role, **page.sql},
    )


def get_user_support_ticket(db: Session, user: dict, role: str, ticket_id: str) -> dict:
    ticket = fetch_one(
        db,
        """SELECT st.*, u.name AS requester_name, u.email AS requester_email, u.phone AS requester_phone, o.code AS order_code
        FROM support_tickets st
        JOIN users u ON u.id=st.requester_id
        LEFT JOIN orders o ON o.id=st.order_id
        WHERE st.id=:id AND st.requester_id=:uid AND st.requester_role=:role""",
        {"id": ticket_id, "uid": user["id"], "role": role},
    )
    if not ticket:
        raise HTTPException(404, "Support ticket not found")
    return ticket


def add_user_support_message(db: Session, user: dict, role: str, ticket_id: str, body: SupportMessageCreate) -> dict:
    ticket = get_user_support_ticket(db, user, role, ticket_id)
    if ticket["status"] == "CLOSED":
        raise HTTPException(409, "Closed tickets cannot be updated")
    next_status = "OPEN" if ticket["status"] in {"RESOLVED", "WAITING_ON_CUSTOMER", "PENDING"} else ticket["status"]
    db.execute(
        text("""INSERT INTO support_messages (ticket_id,author_id,author_name,author_role,body) VALUES (:ticket_id,:author_id,:author_name,:author_role,:body)"""),
        {"ticket_id": ticket_id, "author_id": user["id"], "author_name": user["name"], "author_role": role, "body": body.body.strip()},
    )
    db.execute(
        text("""UPDATE support_tickets SET status=:status, last_customer_reply_at=now(), last_activity_at=now(), updated_at=now(), resolved_at=NULL, closed_at=NULL WHERE id=:id"""),
        {"id": ticket_id, "status": next_status},
    )
    notify(db, "admin", "Support ticket updated", f"{ticket['code']} has a new reply from {user['name']}.", ticket.get("order_id"))
    db.commit()
    return support_ticket_payload(db, get_user_support_ticket(db, user, role, ticket_id))


def status_label(status: str | None) -> str:
    return (status or "").replace("_", " ").title()


def add_history(db: Session, order_id: str, status: str, note: str | None, by_role: str) -> None:
    db.execute(
        text("INSERT INTO order_status_history (order_id,status,note,by_role) VALUES (:order_id,:status,:note,:by_role)"),
        {"order_id": order_id, "status": status, "note": note, "by_role": by_role},
    )


MEDIA_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "video/mp4": ".mp4",
    "video/webm": ".webm",
    "video/quicktime": ".mov",
}
MAX_MEDIA_BYTES = 15 * 1024 * 1024
MAX_PROFILE_IMAGE_BYTES = 5 * 1024 * 1024
MAX_PORTFOLIO_ITEMS = 12


def media_kind(media_type: str) -> str:
    if media_type.startswith("image/"):
        return "image"
    if media_type.startswith("video/"):
        return "video"
    raise HTTPException(400, "Only photo or video files are allowed")


def decode_data_url(data_url: str, media_type: str, max_bytes: int) -> bytes:
    prefix = f"data:{media_type};base64,"
    if not data_url.startswith(prefix):
        raise HTTPException(400, "Invalid upload data")
    try:
        raw = b64decode(data_url[len(prefix):], validate=True)
    except Exception:
        raise HTTPException(400, "Upload could not be decoded")
    if not raw:
        raise HTTPException(400, "Uploaded file is empty")
    if len(raw) > max_bytes:
        raise HTTPException(413, "Uploaded file is too large")
    try:
        validate_file_signature(raw, media_type)
    except MediaStorageError as exc:
        raise HTTPException(400, str(exc)) from exc
    return raw


def delete_uploaded_media_file(entry: str) -> None:
    try:
        item = json.loads(entry)
    except (TypeError, json.JSONDecodeError):
        return
    try:
        media_storage.delete_url(str(item.get("url") or ""))
    except MediaStorageError:
        pass


def delete_uploaded_url(url: str | None) -> None:
    try:
        media_storage.delete_url(url)
    except MediaStorageError:
        pass


def queue_media_postprocess(object_key: str, content_type: str) -> None:
    enqueue_task(
        "media_postprocess",
        {"objectKey": object_key, "contentType": content_type},
        f"media-process:{object_key}",
    )


def audit(db: Session, admin: dict, action: str, target_type: str, target_id: str | None, target_name: str | None, reason: str | None = None, meta: dict | None = None) -> None:
    db.execute(
        text(
            """INSERT INTO audit_logs (admin_id,admin_name,action,target_type,target_id,target_name,reason,meta)
            VALUES (:admin_id,:admin_name,:action,:target_type,:target_id,:target_name,:reason,CAST(:meta AS jsonb))"""
        ),
        {
            "admin_id": admin["id"],
            "admin_name": admin["name"],
            "action": action,
            "target_type": target_type,
            "target_id": target_id,
            "target_name": target_name,
            "reason": reason,
            "meta": json.dumps(meta or {}),
        },
    )


def seed_admin(db: Session) -> None:
    existing = fetch_one(db, "SELECT * FROM users WHERE 'admin'=ANY(roles) LIMIT 1")
    password_hash = hash_password(settings.admin_password)
    if existing:
        password_sql = ", password_hash=:password_hash" if settings.admin_password_configured else ""
        params = {"id": existing["id"], "phone": settings.admin_phone, "email": settings.admin_email, "username": settings.admin_username}
        if settings.admin_password_configured:
            params["password_hash"] = password_hash
        db.execute(
            text(
                """UPDATE users SET name='Ops Admin', phone=:phone, email=:email, roles=ARRAY['admin'],
                status='ACTIVE', admin_username=:username""" + password_sql + """ WHERE id=:id"""
            ),
            params,
        )
    else:
        db.execute(
            text(
                """INSERT INTO users (id,name,phone,email,roles,zone_id,password_hash,admin_username)
                VALUES (:id,'Ops Admin',:phone,:email,ARRAY['admin'],'tnagar',:password_hash,:username)"""
            ),
            {"id": uid("u"), "phone": settings.admin_phone, "email": settings.admin_email, "username": settings.admin_username, "password_hash": password_hash},
        )
    db.commit()
    cred = settings.base_dir / "admin-credentials.txt"
    password_note = (
        settings.admin_password
        if not existing or settings.admin_password_configured
        else "existing password unchanged; set ADMIN_PASSWORD in backend/.env to rotate it"
    )
    cred.write_text(
        "\n".join(
            [
                "TailoraHub Admin Credentials",
                "============================",
                "Backend production: https://tailorahub.com/api",
                "Backend local: http://localhost:8001",
                "Username: " + settings.admin_username,
                "Password: " + password_note,
                "Email: " + settings.admin_email,
                "Phone: " + settings.admin_phone,
                "Updated: " + datetime.now(timezone.utc).isoformat(),
                "",
            ]
        ),
        encoding="utf-8",
    )


def seed_demo_tailors(db: Session) -> None:
    demo_tailors = [
        {
            "user_id": "u_demo_tailor_1",
            "tailor_row_id": "t_demo_tailor_1",
            "tailor_uuid": "11111111-1111-4111-8111-111111111111",
            "shop": "Anika Blouse Studio",
            "owner": "Anika Reddy",
            "phone": "9000010001",
            "email": "anika.tailor@tailorahub.com",
            "username": "anika_demo",
            "zone": "tnagar",
            "address": "Pondy Bazaar, T. Nagar, Chennai",
            "lat": 13.0418,
            "lng": 80.2341,
            "expertise": ["Blouse", "Alteration", "Embroidery"],
            "years": 8,
            "rating": 4.8,
            "rating_count": 32,
            "completed": 148,
            "availability": "AVAILABLE",
            "slots": 6,
            "note": "Accepting blouse stitching and quick alterations this week.",
            "referral": "THDEMOA1",
            "aadhaar": "999999990001",
            "services": [
                ("svc_demo_1_blouse", "blouse", "Designer Blouse", "Blouse", 650, 4),
                ("svc_demo_1_alter", "alteration", "Blouse Alteration", "Alteration", 220, 2),
            ],
        },
        {
            "user_id": "u_demo_tailor_2",
            "tailor_row_id": "t_demo_tailor_2",
            "tailor_uuid": "22222222-2222-4222-8222-222222222222",
            "shop": "Vel Stitch Works",
            "owner": "Kavitha Menon",
            "phone": "9000010002",
            "email": "velstitch.tailor@tailorahub.com",
            "username": "velstitch_demo",
            "zone": "velachery",
            "address": "100 Feet Road, Velachery, Chennai",
            "lat": 12.9791,
            "lng": 80.2210,
            "expertise": ["Kurta", "Pant", "Combo"],
            "years": 11,
            "rating": 4.6,
            "rating_count": 27,
            "completed": 203,
            "availability": "FEW_SLOTS_AVAILABLE",
            "slots": 3,
            "note": "Few slots available for kurta and pant combo orders.",
            "referral": "THDEMOV2",
            "aadhaar": "999999990002",
            "services": [
                ("svc_demo_2_kurta", "salwar", "Kurta / Salwar Set", "Shirt", 850, 5),
                ("svc_demo_2_combo", "combo", "Pant and Shirt Combo", "Combo", 1200, 6),
            ],
        },
    ]
    password_hash = hash_password("Tailor@12345")

    for tailor in demo_tailors:
        db.execute(
            text(
                """
                INSERT INTO users
                  (id,name,phone,email,password_hash,roles,zone_id,address,lat,lng,profile_image,status)
                VALUES
                  (:id,:name,:phone,:email,:password_hash,ARRAY['tailor'],:zone,:address,:lat,:lng,NULL,'ACTIVE')
                ON CONFLICT (id) DO UPDATE SET
                  name=EXCLUDED.name,
                  phone=EXCLUDED.phone,
                  email=EXCLUDED.email,
                  password_hash=EXCLUDED.password_hash,
                  roles=ARRAY['tailor'],
                  zone_id=EXCLUDED.zone_id,
                  address=EXCLUDED.address,
                  lat=EXCLUDED.lat,
                  lng=EXCLUDED.lng,
                  status='ACTIVE'
                """
            ),
            {
                "id": tailor["user_id"],
                "name": tailor["owner"],
                "phone": tailor["phone"],
                "email": tailor["email"],
                "password_hash": password_hash,
                "zone": tailor["zone"],
                "address": tailor["address"],
                "lat": tailor["lat"],
                "lng": tailor["lng"],
            },
        )
        db.execute(
            text(
                """
                INSERT INTO tailors
                  (id,user_id,shop,owner_name,zone_id,shop_address,lat,lng,profile_image,expertise,years,
                   working_hours,bio,rating,rating_count,completed,on_time_pct,response_mins,
                   approval_status,verified,account_status,availability,available_slots,max_new_orders,
                   next_available,availability_note,accepting_requests,featured,tailor_id,full_name,
                   phone_number,email,aadhaar_number_hash,aadhaar_verified,username,password_hash,
                   experience_years_base,stitching_since_date,terms_accepted,terms_accepted_at,
                   referral_code,is_available,status,created_at,updated_at)
                VALUES
                  (:id,:user_id,:shop,:owner,:zone,:address,:lat,:lng,NULL,:expertise,:years,
                   '10:00-20:00',:bio,:rating,:rating_count,:completed,98,15,
                   'APPROVED',TRUE,'ACTIVE',:availability,:slots,:slots,
                   CURRENT_DATE,:note,TRUE,TRUE,CAST(:tailor_uuid AS uuid),:full_name,
                   :phone,:email,:aadhaar_hash,TRUE,:username,:password_hash,
                   :years,CURRENT_DATE - (:years * INTERVAL '1 year'),TRUE,now(),
                   :referral,TRUE,'active',now(),now())
                ON CONFLICT (id) DO UPDATE SET
                  shop=EXCLUDED.shop,
                  owner_name=EXCLUDED.owner_name,
                  zone_id=EXCLUDED.zone_id,
                  shop_address=EXCLUDED.shop_address,
                  lat=EXCLUDED.lat,
                  lng=EXCLUDED.lng,
                  expertise=EXCLUDED.expertise,
                  years=EXCLUDED.years,
                  bio=EXCLUDED.bio,
                  rating=EXCLUDED.rating,
                  rating_count=EXCLUDED.rating_count,
                  completed=EXCLUDED.completed,
                  approval_status='APPROVED',
                  verified=TRUE,
                  account_status='ACTIVE',
                  availability=EXCLUDED.availability,
                  available_slots=EXCLUDED.available_slots,
                  max_new_orders=EXCLUDED.max_new_orders,
                  availability_note=EXCLUDED.availability_note,
                  accepting_requests=TRUE,
                  featured=TRUE,
                  full_name=EXCLUDED.full_name,
                  phone_number=EXCLUDED.phone_number,
                  email=EXCLUDED.email,
                  aadhaar_verified=TRUE,
                  username=EXCLUDED.username,
                  password_hash=EXCLUDED.password_hash,
                  experience_years_base=EXCLUDED.experience_years_base,
                  stitching_since_date=EXCLUDED.stitching_since_date,
                  terms_accepted=TRUE,
                  terms_accepted_at=COALESCE(tailors.terms_accepted_at, now()),
                  referral_code=EXCLUDED.referral_code,
                  is_available=TRUE,
                  status='active',
                  deleted_at=NULL,
                  updated_at=now()
                """
            ),
            {
                "id": tailor["tailor_row_id"],
                "user_id": tailor["user_id"],
                "shop": tailor["shop"],
                "owner": tailor["owner"],
                "full_name": tailor["owner"],
                "zone": tailor["zone"],
                "address": tailor["address"],
                "lat": tailor["lat"],
                "lng": tailor["lng"],
                "expertise": tailor["expertise"],
                "years": tailor["years"],
                "bio": f"Demo approved TailoraHub tailor for testing. {tailor['note']}",
                "rating": tailor["rating"],
                "rating_count": tailor["rating_count"],
                "completed": tailor["completed"],
                "availability": tailor["availability"],
                "slots": tailor["slots"],
                "note": tailor["note"],
                "tailor_uuid": tailor["tailor_uuid"],
                "phone": tailor["phone"],
                "email": tailor["email"],
                "aadhaar_hash": hash_aadhaar(tailor["aadhaar"]),
                "username": tailor["username"],
                "password_hash": password_hash,
                "referral": tailor["referral"],
            },
        )
        location = fetch_one(db, "SELECT id FROM tailor_locations WHERE tailor_id=CAST(:tailor_uuid AS uuid) ORDER BY created_at LIMIT 1", {"tailor_uuid": tailor["tailor_uuid"]})
        if location:
            db.execute(
                text(
                    """
                    UPDATE tailor_locations
                    SET address_text=:address, latitude=:lat, longitude=:lng, is_fixed=TRUE, updated_at=now()
                    WHERE id=:id
                    """
                ),
                {"id": location["id"], "address": tailor["address"], "lat": tailor["lat"], "lng": tailor["lng"]},
            )
        else:
            db.execute(
                text(
                    """
                    INSERT INTO tailor_locations
                      (tailor_id,address_text,latitude,longitude,is_fixed,created_at,updated_at)
                    VALUES
                      (CAST(:tailor_uuid AS uuid),:address,:lat,:lng,TRUE,now(),now())
                    """
                ),
                {"tailor_uuid": tailor["tailor_uuid"], "address": tailor["address"], "lat": tailor["lat"], "lng": tailor["lng"]},
            )
        wallet = fetch_one(db, "SELECT wallet_id FROM tailor_wallets WHERE tailor_id=CAST(:tailor_uuid AS uuid)", {"tailor_uuid": tailor["tailor_uuid"]})
        if wallet:
            wallet_id = str(wallet["wallet_id"])
        else:
            wallet_id = str(uuid.uuid4())
            db.execute(
                text(
                    """
                    INSERT INTO tailor_wallets (wallet_id,tailor_id,balance,created_at,updated_at)
                    VALUES (CAST(:wallet_id AS uuid),CAST(:tailor_uuid AS uuid),0,now(),now())
                    """
                ),
                {"wallet_id": wallet_id, "tailor_uuid": tailor["tailor_uuid"]},
            )
        db.execute(
            text("UPDATE tailor_wallets SET qr_code_url=:qr, updated_at=now() WHERE wallet_id=CAST(:wallet_id AS uuid)"),
            {"wallet_id": wallet_id, "qr": generate_wallet_qr(wallet_id)},
        )
        for service_id, garment_id, name, category, price, days in tailor["services"]:
            db.execute(
                text(
                    """
                    INSERT INTO tailor_services
                      (id,tailor_id,garment_id,name,description,price,days,active,
                       service_name,category,is_combo,combo_items,is_active,created_at,updated_at)
                    VALUES
                      (:id,:tailor_id,:garment_id,:name,:description,:price,:days,TRUE,
                       :service_name,:category,:is_combo,CAST(:combo_items AS jsonb),TRUE,now(),now())
                    ON CONFLICT (id) DO UPDATE SET
                      garment_id=EXCLUDED.garment_id,
                      name=EXCLUDED.name,
                      description=EXCLUDED.description,
                      price=EXCLUDED.price,
                      days=EXCLUDED.days,
                      active=TRUE,
                      service_name=EXCLUDED.service_name,
                      category=EXCLUDED.category,
                      is_combo=EXCLUDED.is_combo,
                      combo_items=EXCLUDED.combo_items,
                      is_active=TRUE,
                      updated_at=now()
                    """
                ),
                {
                    "id": service_id,
                    "tailor_id": tailor["tailor_row_id"],
                    "garment_id": garment_id,
                    "name": name,
                    "service_name": name,
                    "description": f"Demo {name.lower()} service",
                    "price": price,
                    "days": days,
                    "category": category,
                    "is_combo": category == "Combo",
                    "combo_items": json.dumps(["Pant", "Shirt"]) if category == "Combo" else json.dumps([]),
                },
            )
    db.commit()


@app.on_event("startup")
async def startup() -> None:
    if settings.app_env == "production":
        if settings.auto_migrate:
            raise RuntimeError("Production web containers require AUTO_MIGRATE=false; run SERVICE_ROLE=migration once")
        if settings.task_queue_backend != "sqs" or not settings.sqs_task_queue_url or not settings.sqs_task_dlq_url:
            raise RuntimeError("Production requires the SQS task queue and dead-letter queue configuration")
        if settings.media_storage_backend != "s3":
            raise RuntimeError("Production requires MEDIA_STORAGE_BACKEND=s3")
        if not settings.cloudfront_media_base_url:
            raise RuntimeError("Production requires CLOUDFRONT_MEDIA_BASE_URL")
        if settings.realtime_backplane != "redis":
            raise RuntimeError("Production requires REALTIME_BACKPLANE=redis")
        if settings.traffic_store_backend != "redis":
            raise RuntimeError("Production requires TRAFFIC_STORE_BACKEND=redis for shared caching and rate limits")
        if settings.payment_provider == "razorpay" and not settings.razorpay_webhook_secret:
            raise RuntimeError("Production Razorpay requires RAZORPAY_WEBHOOK_SECRET")
        if "localhost" in settings.redis_url or "127.0.0.1" in settings.redis_url:
            raise RuntimeError("Production REDIS_URL must point to the shared Redis/Valkey service")
    await tracker_connections.start()
    if settings.auto_migrate:
        run_schema()
    db = next(db_session())
    try:
        seed_admin(db)
        seed_demo_tailors(db)
    finally:
        db.close()


@app.on_event("shutdown")
async def shutdown() -> None:
    await tracker_connections.stop()


@app.get("/api/health")
def health(db: Session = Depends(db_session)):
    now = fetch_one(db, "SELECT now() AS now")
    return {
        "ok": True,
        "db": "connected",
        "serverTime": now["now"],
        "mediaStorage": settings.media_storage_backend,
        "realtime": tracker_connections.status,
        "trafficProtection": {
            "store": settings.traffic_store_backend,
            "rateLimiting": settings.rate_limit_enabled,
            "publicCacheTtlSeconds": settings.public_cache_ttl_seconds,
        },
    }


@app.get("/api/reference")
def reference():
    return {
        "zones": ZONES,
        "garments": GARMENTS,
        "accountStatuses": ACCOUNT_STATUSES,
        "approvalStatuses": APPROVAL_STATUSES,
        "paymentStatuses": PAYMENT_STATUSES,
        "availabilityStatuses": AVAILABILITY_STATUSES,
        "orderStatuses": ORDER_STATUSES,
        "supportStatuses": SUPPORT_STATUSES,
        "supportPriorities": SUPPORT_PRIORITIES,
        "maps": maps_service.public_config(),
    }


@app.post("/api/auth/admin/login")
def admin_login(body: AdminLogin, db: Session = Depends(db_session)):
    ident = body.username.strip().lower()
    user = fetch_one(db, "SELECT * FROM users WHERE (lower(admin_username)=:id OR lower(email)=:id) AND 'admin'=ANY(roles) AND status='ACTIVE'", {"id": ident})
    if not user or not verify_password(body.password, user.get("password_hash")):
        raise HTTPException(401, "Invalid admin credentials")
    payload = create_session_payload(db, user)
    db.commit()
    return {**payload, "user": as_public_user(user)}


@app.post("/api/auth/login")
def role_login(body: RoleLogin, db: Session = Depends(db_session)):
    role = body.role.strip().lower()
    if role not in {"customer", "tailor", "admin"}:
        raise HTTPException(400, "Choose customer, tailor or admin")
    if role == "admin":
        raise HTTPException(403, "Use the private administrator login endpoint")

    ident = body.identifier.strip().lower()
    phone = clean_phone(ident)
    user = fetch_one(
        db,
        """SELECT * FROM users
        WHERE status='ACTIVE'
          AND :role=ANY(roles)
          AND (lower(email)=:ident OR phone=:phone)
        LIMIT 1""",
        {"role": role, "ident": ident, "phone": phone},
    )
    if not user or not verify_password(body.password, user.get("password_hash")):
        raise HTTPException(401, "Invalid credentials for selected role")
    payload = {**create_session_payload(db, user), "user": as_public_user(user), "role": role}
    if role == "tailor":
        tailor = fetch_one(db, "SELECT t.*, u.phone, u.email FROM tailors t JOIN users u ON u.id=t.user_id WHERE t.user_id=:uid AND t.deleted_at IS NULL", {"uid": user["id"]})
        payload["tailor"] = as_tailor(tailor)
    db.commit()
    return payload


@app.post("/api/auth/refresh")
def refresh_auth(body: RefreshRequest, db: Session = Depends(db_session)):
    refresh_token = body.refreshToken or body.refresh_token
    if not refresh_token:
        raise HTTPException(400, "Refresh token is required")
    try:
        payload = rotate_session_payload(db, refresh_token)
        db.commit()
        return payload
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise HTTPException(401, "Refresh token expired or revoked")


@app.get("/api/me")
def me(user: dict = Depends(current_user), db: Session = Depends(db_session)):
    payload = {"user": as_public_user(user)}
    if "tailor" in (user.get("roles") or []):
        tailor = fetch_one(db, "SELECT t.*, u.phone, u.email FROM tailors t JOIN users u ON u.id=t.user_id WHERE t.user_id=:uid AND t.deleted_at IS NULL", {"uid": user["id"]})
        payload["tailor"] = as_tailor(tailor)
    return payload


@app.post("/api/auth/otp/request")
def request_otp(body: OtpRequest, db: Session = Depends(db_session)):
    email = body.email.lower()
    try:
        code, _ = otp.issue(db, email, "login")
        db.commit()
    except otp.OtpError as exc:
        db.rollback()
        raise HTTPException(429 if exc.code == "cooldown" else 400, exc.message)
    user = fetch_one(db, "SELECT id FROM users WHERE lower(email)=:email AND status <> 'DELETED'", {"email": email})
    delivery = send_email(email, "Your TailoraHub OTP", f"Your TailoraHub OTP is {code}. It is valid for {otp.OTP_TTL_MINUTES} minutes.")
    response = {"sent": True, "registered": bool(user), "channel": "email", "delivery": delivery}
    if delivery.get("mode") == "mock":
        response["devOtp"] = code
    return response


@app.post("/api/auth/otp/verify")
def verify_otp(body: OtpVerify, db: Session = Depends(db_session)):
    email = body.email.lower()
    try:
        matched = otp.verify(db, email, "login", body.otp)
        db.commit()
    except otp.OtpError as exc:
        db.rollback()
        raise HTTPException(401, exc.message)
    if not matched:
        raise HTTPException(401, "Incorrect or expired OTP")
    user = fetch_one(db, "SELECT * FROM users WHERE lower(email)=:email AND status <> 'DELETED'", {"email": email})
    if not user:
        return {"verified": True, "user": None}
    tailor = fetch_one(db, "SELECT id, approval_status FROM tailors WHERE user_id=:uid AND deleted_at IS NULL", {"uid": user["id"]})
    payload = create_session_payload(db, user)
    db.commit()
    return {**payload, "verified": True, "user": as_public_user(user), "tailorId": tailor["id"] if tailor else None, "tailorPending": bool(tailor and tailor["approval_status"] == "PENDING_APPROVAL")}


@app.post("/api/otp/send")
def send_purpose_otp(body: OtpSendIn, db: Session = Depends(db_session)):
    """Purpose-scoped OTP (file 05/07/12) -- separate from the legacy email-only
    /api/auth/otp/* pair above, which the existing login flow still uses."""
    if body.purpose not in VALID_OTP_PURPOSES:
        raise HTTPException(400, "Invalid OTP purpose")
    target = body.target.strip()
    is_email = "@" in target
    if not is_email and not PHONE_RE.match(clean_phone(target)):
        raise HTTPException(400, "Enter a valid email or 10-digit mobile number")
    try:
        code, expires_at = otp.issue(db, target, body.purpose)
    except otp.OtpError as exc:
        raise HTTPException(429 if exc.code == "cooldown" else 400, exc.message)
    db.commit()
    if is_email:
        delivery = send_email(target, "Your TailoraHub verification code", f"Your verification code is {code}. It is valid for {otp.OTP_TTL_MINUTES} minutes.")
        mock_mode = delivery.get("mode") == "mock"
    else:
        delivery = sms_service().send_otp(clean_phone(target), code)
        mock_mode = delivery.get("mode") == "mock"
    response = {"sent": True, "target": target, "purpose": body.purpose, "expiresInSeconds": otp.OTP_TTL_MINUTES * 60}
    if mock_mode:
        response["devOtp"] = code
    return response


@app.post("/api/otp/verify")
def verify_purpose_otp(body: OtpVerifyIn, db: Session = Depends(db_session)):
    if body.purpose not in VALID_OTP_PURPOSES:
        raise HTTPException(400, "Invalid OTP purpose")
    try:
        matched = otp.verify(db, body.target.strip(), body.purpose, body.otp)
    except otp.OtpError as exc:
        db.commit()
        raise HTTPException(401, exc.message)
    db.commit()
    if not matched:
        raise HTTPException(401, "Incorrect code")
    return {"verified": True, "target": body.target.strip(), "purpose": body.purpose}


@app.post("/api/auth/check-availability")
def check_availability(body: CheckAvailabilityIn, db: Session = Depends(db_session)):
    """Real-time duplicate check for registration fields (file 05) -- debounced on-blur, not just on submit."""
    value = body.value.strip()
    role = (body.role or "").strip().lower()
    if body.field == "phone":
        phone = clean_phone(value)
        if not PHONE_RE.match(phone):
            return {"available": False, "message": "Enter a valid 10-digit mobile number"}
        if role == "customer":
            taken = fetch_one(db, "SELECT 1 FROM users WHERE phone=:phone AND 'customer'=ANY(roles) AND status <> 'DELETED'", {"phone": phone})
        elif role == "tailor":
            taken = fetch_one(
                db,
                """SELECT 1 FROM tailors WHERE phone_number=:phone AND deleted_at IS NULL
                   UNION ALL
                   SELECT 1 FROM users WHERE phone=:phone AND 'tailor'=ANY(roles) AND status <> 'DELETED'
                   LIMIT 1""",
                {"phone": phone},
            )
        else:
            taken = fetch_one(db, "SELECT 1 FROM users WHERE phone=:phone AND status <> 'DELETED'", {"phone": phone})
        return {"available": not taken, "message": "This mobile number is already registered." if taken else None}
    if body.field == "email":
        if role == "customer":
            taken = fetch_one(db, "SELECT 1 FROM users WHERE lower(email)=:email AND 'customer'=ANY(roles) AND status <> 'DELETED'", {"email": value.lower()})
        elif role == "tailor":
            taken = fetch_one(
                db,
                """SELECT 1 FROM tailors WHERE lower(email)=:email AND deleted_at IS NULL
                   UNION ALL
                   SELECT 1 FROM users WHERE lower(email)=:email AND 'tailor'=ANY(roles) AND status <> 'DELETED'
                   LIMIT 1""",
                {"email": value.lower()},
            )
        else:
            taken = fetch_one(db, "SELECT 1 FROM users WHERE lower(email)=:email AND status <> 'DELETED'", {"email": value.lower()})
        return {"available": not taken, "message": "This email is already registered." if taken else None}
    if body.field == "username":
        taken = fetch_one(db, "SELECT 1 FROM tailors WHERE lower(username)=:u", {"u": value.lower()})
        return {"available": not taken, "message": "This username is taken." if taken else None}
    if body.field == "aadhaar":
        if not is_valid_aadhaar_format(value):
            return {"available": False, "message": "Enter a valid 12-digit Aadhaar number"}
        taken = fetch_one(db, "SELECT 1 FROM tailors WHERE aadhaar_number_hash=:h", {"h": hash_aadhaar(value)})
        return {"available": not taken, "message": "This Aadhaar number is already registered." if taken else None}
    raise HTTPException(400, "Unsupported field")


@app.post("/api/auth/register", status_code=201)
def register(body: RegisterIn, db: Session = Depends(db_session)):
    role = body.role if body.role in {"customer", "tailor", "delivery"} else "customer"
    phone = clean_phone(body.phone)
    if len(phone) != 10:
        raise HTTPException(400, "Enter a valid 10-digit mobile number")
    if not body.password or len(body.password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters")
    existing = fetch_one(
        db,
        "SELECT * FROM users WHERE (lower(email)=:email OR phone=:phone) AND :role=ANY(roles) AND status <> 'DELETED' LIMIT 1",
        {"email": body.email.lower(), "phone": phone, "role": role},
    )
    if existing and existing["status"] in {"BLOCKED", "DELETED"}:
        raise HTTPException(403, "This account cannot be registered. Contact support.")
    if not existing:
        roles = [role]
        user_id = uid("u")
        db.execute(
            text(
                """INSERT INTO users (id,name,phone,email,password_hash,roles,zone_id,address,lat,lng,profile_image,vehicle)
                VALUES (:id,:name,:phone,:email,:password_hash,:roles,:zone,:address,:lat,:lng,:profile_image,:vehicle)"""
            ),
            {
                "id": user_id,
                "name": body.name.strip(),
                "phone": phone,
                "email": body.email.lower(),
                "password_hash": hash_password(body.password),
                "roles": roles,
                "zone": body.zoneId or "tnagar",
                "address": body.address,
                "lat": body.lat,
                "lng": body.lng,
                "profile_image": body.profileImage,
                "vehicle": body.vehicle,
            },
        )
        user = fetch_one(db, "SELECT * FROM users WHERE id=:id", {"id": user_id})
    else:
        roles = set(existing["roles"] or [])
        roles.add(role)
        db.execute(
            text(
                """UPDATE users SET name=:name, phone=:phone, email=:email, password_hash=:password_hash,
                zone_id=:zone, address=COALESCE(:address,address), lat=COALESCE(:lat,lat), lng=COALESCE(:lng,lng),
                profile_image=COALESCE(:profile_image,profile_image), vehicle=COALESCE(:vehicle,vehicle), roles=:roles WHERE id=:id"""
            ),
            {
                "id": existing["id"],
                "name": body.name.strip(),
                "phone": phone,
                "email": body.email.lower(),
                "password_hash": hash_password(body.password),
                "zone": body.zoneId or existing["zone_id"],
                "address": body.address,
                "lat": body.lat,
                "lng": body.lng,
                "profile_image": body.profileImage,
                "vehicle": body.vehicle,
                "roles": sorted(roles),
            },
        )
        user = fetch_one(db, "SELECT * FROM users WHERE id=:id", {"id": existing["id"]})

    tailor = None
    if role == "tailor":
        if not body.shop or not (body.specs or body.services):
            raise HTTPException(400, "Shop name and at least one service or specialization are required")
        tailor = fetch_one(db, "SELECT * FROM tailors WHERE user_id=:uid AND deleted_at IS NULL", {"uid": user["id"]})
        if not tailor:
            # file 05: Aadhaar KYC + phone/email OTP verification + referral linking,
            # required only on first-time tailor creation -- dob/Aadhaar are locked
            # for good afterwards (see the re-registration UPDATE branch below, and
            # the profile PATCH endpoint, neither of which ever touch these fields).
            if not body.termsAccepted:
                raise HTTPException(400, "You must accept the terms and conditions")
            username = (body.username or "").strip()
            if not username:
                raise HTTPException(400, "Choose a username")
            if fetch_one(db, "SELECT 1 FROM tailors WHERE lower(username)=:u", {"u": username.lower()}):
                raise HTTPException(400, "This username is taken.")
            aadhaar = (body.aadhaarNumber or "").strip()
            if not is_valid_aadhaar_format(aadhaar):
                raise HTTPException(400, "Enter a valid 12-digit Aadhaar number")
            if not body.dob:
                raise HTTPException(400, "Date of birth is required")
            aadhaar_hash = hash_aadhaar(aadhaar)
            if fetch_one(db, "SELECT 1 FROM tailors WHERE aadhaar_number_hash=:h", {"h": aadhaar_hash}):
                raise HTTPException(400, "This Aadhaar number is already registered.")
            if not otp.is_recently_verified(db, phone, "registration_phone"):
                raise HTTPException(400, "Verify your mobile number first")
            if not otp.is_recently_verified(db, body.email.lower(), "registration_email"):
                raise HTTPException(400, "Verify your email first")
            kyc = aadhaar_kyc_service().verify(aadhaar, body.name.strip())
            if not kyc.get("verified"):
                raise HTTPException(400, kyc.get("reason") or "Aadhaar verification failed")

            referred_by_tailor_id = None
            if body.referralCode:
                referrer = fetch_one(db, "SELECT tailor_id FROM tailors WHERE referral_code=:code", {"code": body.referralCode.strip().upper()})
                if referrer:
                    referred_by_tailor_id = referrer["tailor_id"]

            tid = uid("t")
            docs = {"idProof": body.idProof or "Not uploaded", "shopProof": body.shopProof or "Not uploaded", "bank": body.bank or "Not provided"}
            db.execute(
                text(
                    """INSERT INTO tailors (
                        id,user_id,shop,owner_name,zone_id,shop_address,lat,lng,profile_image,expertise,years,working_hours,bio,portfolio,documents,
                        full_name,phone_number,email,username,dob,aadhaar_number_hash,aadhaar_number_encrypted,aadhaar_verified,
                        experience_years_base,stitching_since_date,terms_accepted,terms_accepted_at,referral_code,referred_by_tailor_id
                    ) VALUES (
                        :id,:user_id,:shop,:owner,:zone,:address,:lat,:lng,:profile_image,:expertise,:years,:working_hours,:bio,:portfolio,CAST(:docs AS jsonb),
                        :full_name,:phone_number,:email,:username,:dob,:aadhaar_hash,:aadhaar_encrypted,TRUE,
                        :experience_base,:stitching_since,TRUE,now(),:referral_code,:referred_by
                    )"""
                ),
                {
                    "id": tid,
                    "user_id": user["id"],
                    "shop": body.shop.strip(),
                    "owner": user["name"],
                    "zone": body.zoneId or "tnagar",
                    "address": body.address,
                    "lat": body.lat,
                    "lng": body.lng,
                    "profile_image": body.profileImage,
                    "expertise": body.specs or [s.name for s in body.services],
                    "years": body.years or 1,
                    "working_hours": body.workingHours or "10:00-20:00",
                    "bio": body.bio,
                    "portfolio": body.portfolio,
                    "docs": json.dumps(docs),
                    "full_name": body.name.strip(),
                    "phone_number": phone,
                    "email": body.email.lower(),
                    "username": username,
                    "dob": body.dob,
                    "aadhaar_hash": aadhaar_hash,
                    "aadhaar_encrypted": encrypt_aadhaar(aadhaar),
                    "experience_base": body.experienceYearsBase or 0,
                    "stitching_since": body.stitchingSinceDate,
                    "referral_code": generate_tailor_referral_code(db),
                    "referred_by": referred_by_tailor_id,
                },
            )
            if referred_by_tailor_id:
                db.execute(
                    text(
                        """INSERT INTO referrals (id, referrer_tailor_id, referred_tailor_id, referral_code_used)
                        SELECT gen_random_uuid(), :referrer, tailor_id, :code FROM tailors WHERE id=:tid"""
                    ),
                    {"referrer": referred_by_tailor_id, "code": body.referralCode.strip().upper(), "tid": tid},
                )
            new_tailor_row = fetch_one(db, "SELECT tailor_id FROM tailors WHERE id=:id", {"id": tid})
            wallet_id = str(uuid.uuid4())
            db.execute(
                text("INSERT INTO tailor_wallets (wallet_id, tailor_id, balance) VALUES (:wid, :tailor_id, 0)"),
                {"wid": wallet_id, "tailor_id": new_tailor_row["tailor_id"]},
            )
            qr_url = generate_wallet_qr(wallet_id)
            db.execute(text("UPDATE tailor_wallets SET qr_code_url=:url WHERE wallet_id=:wid"), {"url": qr_url, "wid": wallet_id})
            service_rows = body.services or []
            if not service_rows:
                service_rows = [
                    ServiceIn(garmentId=gid, name=garment(gid)["name"], description=garment(gid)["name"] + " made to measure", price=garment(gid)["base"], days=garment(gid)["days"])
                    for gid in body.specs
                ]
            for service in service_rows:
                gid = service.garmentId or service.name.lower().replace(" ", "-")
                db.execute(
                    text(
                        """INSERT INTO tailor_services (id,tailor_id,garment_id,name,description,price,days,service_name,is_active)
                        VALUES (:id,:tid,:gid,CAST(:name AS TEXT),:desc,:price,:days,CAST(:service_name AS VARCHAR(160)),TRUE)"""
                    ),
                    {"id": uid("svc"), "tid": tid, "gid": gid, "name": service.name, "service_name": service.name, "desc": service.description or service.name + " made to measure", "price": service.price, "days": service.days},
                )
            tailor = fetch_one(db, "SELECT * FROM tailors WHERE id=:id", {"id": tid})
        else:
            db.execute(
                text(
                    """UPDATE tailors SET shop=:shop, owner_name=:owner, zone_id=:zone, shop_address=COALESCE(:address,shop_address),
                    lat=COALESCE(:lat,lat), lng=COALESCE(:lng,lng), profile_image=COALESCE(:profile_image,profile_image),
                    expertise=:expertise, years=:years, working_hours=COALESCE(:working_hours,working_hours),
                    bio=COALESCE(:bio,bio), portfolio=COALESCE(:portfolio,portfolio), approval_status='PENDING_APPROVAL',
                    verified=FALSE, reject_reason=NULL WHERE id=:id"""
                ),
                {
                    "id": tailor["id"],
                    "shop": body.shop.strip(),
                    "owner": user["name"],
                    "zone": body.zoneId or tailor["zone_id"],
                    "address": body.address,
                    "lat": body.lat,
                    "lng": body.lng,
                    "profile_image": body.profileImage,
                    "expertise": body.specs or [s.name for s in body.services],
                    "years": body.years or tailor["years"],
                    "working_hours": body.workingHours,
                    "bio": body.bio,
                    "portfolio": body.portfolio or tailor["portfolio"],
                },
            )
            tailor = fetch_one(db, "SELECT * FROM tailors WHERE id=:id", {"id": tailor["id"]})
    db.commit()
    user = fetch_one(db, "SELECT * FROM users WHERE id=:id", {"id": user["id"]})
    payload = create_session_payload(db, user)
    db.commit()
    return {**payload, "user": as_public_user(user), "role": role, "tailor": as_tailor(tailor) if tailor else None, "tailorPending": bool(tailor and tailor["approval_status"] == "PENDING_APPROVAL")}


@app.get("/api/tailors")
def public_tailors(page: PageParams = Depends(PageParams), db: Session = Depends(db_session)):
    rows = fetch_all(
        db,
        """WITH order_counts AS (
          SELECT tailor_id, count(*) FILTER (WHERE status NOT IN ('COMPLETED','CANCELLED'))::int AS active_orders
          FROM orders GROUP BY tailor_id
        )
        SELECT t.*, u.phone, u.email, COALESCE(min(s.price),0)::int AS starting_price,
        COALESCE(oc.active_orders,0)::int AS active_orders
        FROM tailors t JOIN users u ON u.id=t.user_id
        LEFT JOIN tailor_services s ON s.tailor_id=t.id AND s.active
        LEFT JOIN order_counts oc ON oc.tailor_id=t.id
        WHERE t.approval_status='APPROVED' AND t.account_status='ACTIVE' AND t.deleted_at IS NULL
        GROUP BY t.id, u.phone, u.email, oc.active_orders
        ORDER BY t.featured DESC, t.rating DESC
        LIMIT :limit OFFSET :offset""",
        page.sql,
    )
    return [as_tailor(r) for r in rows]


@app.get("/api/customer/tailors")
def customer_tailors(
    q: str = "",
    service: str = "",
    availability: str | None = None,
    minRating: float = 0,
    maxPrice: int = 0,
    page: PageParams = Depends(PageParams),
    customer: dict = Depends(customer_user),
    db: Session = Depends(db_session),
):
    rows = fetch_all(
        db,
        """
        WITH order_counts AS (
          SELECT tailor_id, count(*) FILTER (WHERE status NOT IN ('COMPLETED','CANCELLED'))::int AS active_orders
          FROM orders GROUP BY tailor_id
        ), favorite_counts AS (
          SELECT tailor_id, count(*)::int AS favorite_count FROM customer_favorite_tailors GROUP BY tailor_id
        ), follower_counts AS (
          SELECT tailor_id, count(*)::int AS follower_count FROM tailor_followers GROUP BY tailor_id
        )
        SELECT t.*, u.phone, u.email, COALESCE(min(s.price),0)::int AS starting_price,
        COALESCE(oc.active_orders,0)::int AS active_orders,
        COALESCE(fc.favorite_count,0)::int AS favorite_count,
        COALESCE(flc.follower_count,0)::int AS follower_count,
        EXISTS(SELECT 1 FROM customer_favorite_tailors cf WHERE cf.tailor_id=t.id AND cf.customer_id=:customer_id) AS favorited_by_me,
        EXISTS(SELECT 1 FROM tailor_followers tf WHERE tf.tailor_id=t.id AND tf.customer_id=:customer_id) AS followed_by_me
        FROM tailors t
        JOIN users u ON u.id=t.user_id
        LEFT JOIN tailor_services s ON s.tailor_id=t.id AND s.active
        LEFT JOIN order_counts oc ON oc.tailor_id=t.id
        LEFT JOIN favorite_counts fc ON fc.tailor_id=t.id
        LEFT JOIN follower_counts flc ON flc.tailor_id=t.id
        WHERE t.approval_status='APPROVED'
          AND t.account_status='ACTIVE'
          AND t.deleted_at IS NULL
          AND (CAST(:availability AS text) IS NULL OR t.availability=CAST(:availability AS text))
          AND (:needle='' OR lower(t.shop) LIKE :like OR lower(t.owner_name) LIKE :like OR lower(t.zone_id) LIKE :like OR lower(coalesce(t.shop_address,'')) LIKE :like OR lower(array_to_string(t.expertise,',')) LIKE :like OR (:needle IN ('chennai','madras') AND t.zone_id IN ('tnagar','annanagar','adyar','velachery','mylapore')))
          AND (:service='' OR lower(coalesce(s.name,'') || ' ' || coalesce(s.garment_id,'') || ' ' || array_to_string(t.expertise,',')) LIKE :service_like)
        GROUP BY t.id, u.phone, u.email, oc.active_orders, fc.favorite_count, flc.follower_count
        HAVING (:min_rating=0 OR t.rating >= :min_rating) AND (:max_price=0 OR COALESCE(min(s.price),0) <= :max_price)
        ORDER BY t.featured DESC, t.rating DESC, t.created DESC
        LIMIT :limit OFFSET :offset
        """,
        {
            "needle": q.strip().lower(),
            "like": "%" + q.strip().lower() + "%",
            "service": service.strip().lower(),
            "service_like": "%" + service.strip().lower() + "%",
            "availability": availability,
            "min_rating": minRating,
            "max_price": maxPrice,
            "customer_id": customer["id"],
            **page.sql,
        },
    )
    return [as_tailor(r) for r in rows]


@app.get("/api/customer/tailors/{tailor_id}")
def customer_tailor_profile(tailor_id: str, customer: dict = Depends(customer_user), db: Session = Depends(db_session)):
    tailor = customer_tailor_summary(db, tailor_id, customer["id"])
    services = fetch_all(db, "SELECT * FROM tailor_services WHERE tailor_id=:id AND active ORDER BY price LIMIT 100", {"id": tailor_id})
    reviews = fetch_all(
        db,
        """SELECT r.*, u.name AS customer_name FROM reviews r JOIN users u ON u.id=r.customer_id
        WHERE r.tailor_id=:id AND r.hidden=FALSE ORDER BY r.ts DESC LIMIT 100""",
        {"id": tailor_id},
    )
    offers = fetch_all(
        db,
        """SELECT * FROM tailor_offers
        WHERE tailor_id=:id AND active=TRUE AND (expires_at IS NULL OR expires_at >= CURRENT_DATE)
        ORDER BY created_at DESC LIMIT 50""",
        {"id": tailor_id},
    )
    return {"tailor": tailor, "services": services, "reviews": reviews, "offers": [as_offer(o) for o in offers]}


@app.get("/api/customer/favorites")
def customer_favorites(page: PageParams = Depends(PageParams), customer: dict = Depends(customer_user), db: Session = Depends(db_session)):
    rows = fetch_all(
        db,
        """WITH order_counts AS (
          SELECT tailor_id, count(*) FILTER (WHERE status NOT IN ('COMPLETED','CANCELLED'))::int AS active_orders
          FROM orders GROUP BY tailor_id
        ), favorite_counts AS (
          SELECT tailor_id, count(*)::int AS favorite_count FROM customer_favorite_tailors GROUP BY tailor_id
        ), follower_counts AS (
          SELECT tailor_id, count(*)::int AS follower_count FROM tailor_followers GROUP BY tailor_id
        )
        SELECT t.*, u.phone, u.email, COALESCE(min(s.price),0)::int AS starting_price,
        COALESCE(oc.active_orders,0)::int AS active_orders,
        COALESCE(fc.favorite_count,0)::int AS favorite_count,
        COALESCE(flc.follower_count,0)::int AS follower_count,
        TRUE AS favorited_by_me,
        EXISTS(SELECT 1 FROM tailor_followers tf WHERE tf.tailor_id=t.id AND tf.customer_id=:customer_id) AS followed_by_me
        FROM customer_favorite_tailors cf
        JOIN tailors t ON t.id=cf.tailor_id
        JOIN users u ON u.id=t.user_id
        LEFT JOIN tailor_services s ON s.tailor_id=t.id AND s.active
        LEFT JOIN order_counts oc ON oc.tailor_id=t.id
        LEFT JOIN favorite_counts fc ON fc.tailor_id=t.id
        LEFT JOIN follower_counts flc ON flc.tailor_id=t.id
        WHERE cf.customer_id=:customer_id
          AND t.approval_status='APPROVED'
          AND t.account_status='ACTIVE'
          AND t.deleted_at IS NULL
        GROUP BY t.id, u.phone, u.email, cf.created_at, oc.active_orders, fc.favorite_count, flc.follower_count
        ORDER BY cf.created_at DESC
        LIMIT :limit OFFSET :offset""",
        {"customer_id": customer["id"], **page.sql},
    )
    return [as_tailor(r) for r in rows]


@app.post("/api/customer/tailors/{tailor_id}/favorite", status_code=201)
def favorite_tailor(tailor_id: str, customer: dict = Depends(customer_user), db: Session = Depends(db_session)):
    customer_tailor_summary(db, tailor_id, customer["id"])
    db.execute(
        text("""INSERT INTO customer_favorite_tailors (customer_id,tailor_id) VALUES (:customer_id,:tailor_id) ON CONFLICT DO NOTHING"""),
        {"customer_id": customer["id"], "tailor_id": tailor_id},
    )
    db.commit()
    return {"tailor": customer_tailor_summary(db, tailor_id, customer["id"])}


@app.delete("/api/customer/tailors/{tailor_id}/favorite")
def unfavorite_tailor(tailor_id: str, customer: dict = Depends(customer_user), db: Session = Depends(db_session)):
    db.execute(
        text("DELETE FROM customer_favorite_tailors WHERE customer_id=:customer_id AND tailor_id=:tailor_id"),
        {"customer_id": customer["id"], "tailor_id": tailor_id},
    )
    db.commit()
    return {"tailor": customer_tailor_summary(db, tailor_id, customer["id"])}


@app.post("/api/customer/tailors/{tailor_id}/follow", status_code=201)
def follow_tailor(tailor_id: str, customer: dict = Depends(customer_user), db: Session = Depends(db_session)):
    tailor = customer_tailor_summary(db, tailor_id, customer["id"])
    inserted = db.execute(
        text("""INSERT INTO tailor_followers (customer_id,tailor_id) VALUES (:customer_id,:tailor_id) ON CONFLICT DO NOTHING RETURNING customer_id"""),
        {"customer_id": customer["id"], "tailor_id": tailor_id},
    ).first()
    if inserted:
        notify(db, "tailor:" + tailor_id, "New follower", f"A customer profile followed {tailor['shop']}.")
    db.commit()
    return {"tailor": customer_tailor_summary(db, tailor_id, customer["id"])}


@app.delete("/api/customer/tailors/{tailor_id}/follow")
def unfollow_tailor(tailor_id: str, customer: dict = Depends(customer_user), db: Session = Depends(db_session)):
    db.execute(
        text("DELETE FROM tailor_followers WHERE customer_id=:customer_id AND tailor_id=:tailor_id"),
        {"customer_id": customer["id"], "tailor_id": tailor_id},
    )
    db.commit()
    return {"tailor": customer_tailor_summary(db, tailor_id, customer["id"])}


@app.post("/api/customer/booking-requests", status_code=201)
def create_booking_request(body: BookingCreate, customer: dict = Depends(customer_user), db: Session = Depends(db_session)):
    if settings.app_env == "production":
        raise HTTPException(410, "This legacy booking endpoint is disabled. Use /api/v1/bookings.")
    measurement_mode = body.measurementMode.upper()
    if measurement_mode not in {"HOME", "SHOP"}:
        raise HTTPException(400, "Measurement mode must be HOME or SHOP")
    if measurement_mode == "HOME" and not body.address:
        raise HTTPException(400, "Customer address is required for home measurement")

    code = fetch_one(db, "SELECT 'REQ-' || nextval('requirement_code_seq') AS code")["code"]
    first_service = None
    created_requests = []
    requirement_id = uid("req")

    db.execute(
        text(
            """INSERT INTO booking_requirements
            (id,code,customer_id,garment_id,service_name,quantity,requirements,preferred_date,instructions,measurement_mode,address,lat,lng,visit_date,visit_slot,visit_notes)
            VALUES (:id,:code,:customer_id,:garment_id,:service_name,:quantity,:requirements,:preferred_date,:instructions,:measurement_mode,:address,:lat,:lng,:visit_date,:visit_slot,:visit_notes)"""
        ),
        {
            "id": requirement_id,
            "code": code,
            "customer_id": customer["id"],
            "garment_id": body.garmentId,
            "service_name": body.serviceName or "Custom stitching",
            "quantity": body.quantity,
            "requirements": body.requirements,
            "preferred_date": body.preferredDate,
            "instructions": body.instructions,
            "measurement_mode": measurement_mode,
            "address": body.address,
            "lat": body.lat,
            "lng": body.lng,
            "visit_date": body.visitDate,
            "visit_slot": body.visitSlot,
            "visit_notes": body.visitNotes,
        },
    )

    for tailor_id in body.tailorIds:
        tailor = fetch_one(
            db,
            """SELECT t.*, u.email FROM tailors t JOIN users u ON u.id=t.user_id
            WHERE t.id=:id AND t.approval_status='APPROVED' AND t.account_status='ACTIVE' AND t.deleted_at IS NULL""",
            {"id": tailor_id},
        )
        if not tailor:
            raise HTTPException(404, f"Tailor {tailor_id} is not available")
        if tailor["availability"] == "NOT_AVAILABLE" or not tailor["accepting_requests"]:
            raise HTTPException(409, f"{tailor['shop']} is currently not accepting new orders")

        service = None
        if body.serviceId:
            service = fetch_one(db, "SELECT * FROM tailor_services WHERE id=:sid AND tailor_id=:tid AND active", {"sid": body.serviceId, "tid": tailor_id})
        if not service and body.garmentId:
            service = fetch_one(db, "SELECT * FROM tailor_services WHERE tailor_id=:tid AND garment_id=:gid AND active ORDER BY price LIMIT 1", {"tid": tailor_id, "gid": body.garmentId})
        if not service and body.serviceName:
            service = fetch_one(db, "SELECT * FROM tailor_services WHERE tailor_id=:tid AND lower(name)=:name AND active ORDER BY price LIMIT 1", {"tid": tailor_id, "name": body.serviceName.lower()})
        if not service:
            service = fetch_one(db, "SELECT * FROM tailor_services WHERE tailor_id=:tid AND active ORDER BY price LIMIT 1", {"tid": tailor_id})
        if not service:
            raise HTTPException(409, f"{tailor['shop']} has no active services")
        first_service = first_service or service
        request_id = uid("br")
        db.execute(
            text(
                """INSERT INTO booking_requests (id,requirement_id,tailor_id,service_id,quoted_price,status)
                VALUES (:id,:requirement_id,:tailor_id,:service_id,:quoted_price,'PENDING')"""
            ),
            {
                "id": request_id,
                "requirement_id": requirement_id,
                "tailor_id": tailor_id,
                "service_id": service["id"],
                "quoted_price": service["price"] * body.quantity,
            },
        )
        notify_and_email(
            db,
            "tailor:" + tailor_id,
            tailor.get("email"),
            "New TailoraHub booking request",
            "\n".join(
                [
                    f"You received a new booking request for {body.quantity} x {service['name']}.",
                    f"Requirement code: {code}",
                    f"Preferred date: {body.preferredDate or 'Not specified'}",
                    f"Measurement mode: {measurement_mode}",
                    f"Customer area: {customer.get('zone_id') or 'Not specified'}",
                    "",
                    "Open your TailoraHub Tailor Dashboard to accept or reject this request.",
                ]
            ),
        )
        created_requests.append({"id": request_id, "tailorId": tailor_id, "service": service["name"], "quotedPrice": service["price"] * body.quantity})

    if first_service:
        db.execute(
            text("UPDATE booking_requirements SET garment_id=COALESCE(:garment_id,garment_id), service_name=:service_name WHERE id=:id"),
            {"id": requirement_id, "garment_id": body.garmentId or first_service.get("garment_id"), "service_name": body.serviceName or first_service["name"]},
        )
    db.commit()
    return {"requirementId": requirement_id, "code": code, "requests": created_requests}


@app.get("/api/customer/bookings")
def customer_bookings(page: PageParams = Depends(PageParams), customer: dict = Depends(customer_user), db: Session = Depends(db_session)):
    requests = fetch_all(
        db,
        """SELECT br.*, r.code AS requirement_code, r.service_name, r.quantity, r.preferred_date, r.measurement_mode,
        t.shop, t.owner_name, s.name AS tailor_service_name
        FROM booking_requests br
        JOIN booking_requirements r ON r.id=br.requirement_id
        JOIN tailors t ON t.id=br.tailor_id
        LEFT JOIN tailor_services s ON s.id=br.service_id
        WHERE r.customer_id=:uid
        ORDER BY br.ts DESC
        LIMIT :limit OFFSET :offset""",
        {"uid": customer["id"], **page.sql},
    )
    orders = fetch_all(
        db,
        """SELECT o.*, t.shop, t.owner_name FROM orders o JOIN tailors t ON t.id=o.tailor_id
        WHERE o.customer_id=:uid ORDER BY o.ts DESC
        LIMIT :limit OFFSET :offset""",
        {"uid": customer["id"], **page.sql},
    )
    notifications = fetch_all(db, "SELECT * FROM notifications WHERE to_ref=:ref ORDER BY ts DESC LIMIT 50", {"ref": "user:" + customer["id"]})
    return {"requests": requests, "orders": orders, "notifications": notifications}


@app.post("/api/customer/notifications/read")
def mark_customer_notifications_read(customer: dict = Depends(customer_user), db: Session = Depends(db_session)):
    db.execute(text("UPDATE notifications SET read=TRUE,read_at=COALESCE(read_at,now()) WHERE to_ref=:ref AND read=FALSE"), {"ref": "user:" + customer["id"]})
    db.commit()
    return {"ok": True}


@app.post("/api/customer/notifications/{notification_id}/read")
def mark_customer_notification_read(notification_id: str, customer: dict = Depends(customer_user), db: Session = Depends(db_session)):
    row = fetch_one(db, """UPDATE notifications SET read=TRUE,read_at=COALESCE(read_at,now())
        WHERE id=:id AND to_ref=:ref RETURNING id,notification_type,entity_type,entity_id,order_id,
        booking_request_id,measurement_id,payment_id""", {"id": notification_id, "ref": "user:" + customer["id"]})
    if not row:
        raise HTTPException(404, "Notification not found")
    db.commit()
    return {"ok": True, "notification": row}


@app.get("/api/customer/orders/{order_id}/timeline")
def customer_order_timeline(order_id: str, customer: dict = Depends(customer_user), db: Session = Depends(db_session)):
    order = fetch_one(db, "SELECT * FROM orders WHERE id=:id AND customer_id=:uid", {"id": order_id, "uid": customer["id"]})
    if not order:
        raise HTTPException(404, "Order not found")
    history = fetch_all(db, "SELECT * FROM order_status_history WHERE order_id=:id ORDER BY ts LIMIT 500", {"id": order_id})
    charges = fetch_all(db, "SELECT * FROM additional_charges WHERE order_id=:id ORDER BY ts LIMIT 200", {"id": order_id})
    return {"order": order, "history": history, "charges": charges}


@app.get("/api/customer/support/tickets")
def customer_support_tickets(page: PageParams = Depends(PageParams), customer: dict = Depends(customer_user), db: Session = Depends(db_session)):
    return user_support_tickets(db, customer, "customer", page)


@app.post("/api/customer/support/tickets", status_code=201)
def create_customer_support_ticket(body: SupportTicketCreate, customer: dict = Depends(customer_user), db: Session = Depends(db_session)):
    return create_support_ticket(db, customer, "customer", body)


@app.get("/api/customer/support/tickets/{ticket_id}")
def customer_support_ticket(ticket_id: str, customer: dict = Depends(customer_user), db: Session = Depends(db_session)):
    return support_ticket_payload(db, get_user_support_ticket(db, customer, "customer", ticket_id))


@app.post("/api/customer/support/tickets/{ticket_id}/messages")
def reply_customer_support_ticket(ticket_id: str, body: SupportMessageCreate, customer: dict = Depends(customer_user), db: Session = Depends(db_session)):
    return add_user_support_message(db, customer, "customer", ticket_id, body)


@app.post("/api/customer/support/tickets/{ticket_id}/close")
def close_customer_support_ticket(ticket_id: str, customer: dict = Depends(customer_user), db: Session = Depends(db_session)):
    get_user_support_ticket(db, customer, "customer", ticket_id)
    db.execute(text("UPDATE support_tickets SET status='CLOSED', closed_at=now(), last_activity_at=now(), updated_at=now() WHERE id=:id"), {"id": ticket_id})
    db.commit()
    return support_ticket_payload(db, get_user_support_ticket(db, customer, "customer", ticket_id))


@app.post("/api/customer/orders/{order_id}/pay")
def pay_order(order_id: str, body: PaymentIn, customer: dict = Depends(customer_user), db: Session = Depends(db_session)):
    if settings.app_env == "production":
        raise HTTPException(410, "This legacy payment endpoint is disabled. Use the verified Razorpay booking checkout.")
    order = fetch_one(db, "SELECT * FROM orders WHERE id=:id AND customer_id=:uid", {"id": order_id, "uid": customer["id"]})
    if not order:
        raise HTTPException(404, "Order not found")
    payment_result = payment_service().capture(order["total"], order["code"], body.method)
    if not payment_result.get("ok"):
        raise HTTPException(502, payment_result.get("reason") or "Payment could not be completed")
    txn_ref = body.txnRef or payment_result.get("txnRef")
    db.execute(text("UPDATE orders SET payment_status='PAID', status=CASE WHEN status='PAYMENT_PENDING' THEN 'PAYMENT_COMPLETED' ELSE status END WHERE id=:id"), {"id": order_id})
    payment = fetch_one(db, "SELECT * FROM payments WHERE order_id=:id ORDER BY ts DESC LIMIT 1", {"id": order_id})
    if payment:
        db.execute(text("UPDATE payments SET amount=:amount, method=:method, status='PAID', txn_ref=:txn, updated=now() WHERE id=:id"), {"id": payment["id"], "amount": order["total"], "method": body.method, "txn": txn_ref})
    else:
        db.execute(text("INSERT INTO payments (id,order_id,amount,method,status,txn_ref) VALUES (:id,:order_id,:amount,:method,'PAID',:txn)"), {"id": uid("pay"), "order_id": order_id, "amount": order["total"], "method": body.method, "txn": txn_ref})
    add_history(db, order_id, "PAYMENT_COMPLETED", "Customer payment marked paid", "customer")
    tailor_contact = fetch_one(db, "SELECT t.shop, u.email FROM tailors t JOIN users u ON u.id=t.user_id WHERE t.id=:id", {"id": order["tailor_id"]})
    notify_and_email(
        db,
        "tailor:" + order["tailor_id"],
        tailor_contact.get("email") if tailor_contact else None,
        "TailoraHub payment received",
        f"Payment for order {order['code']} is marked paid. You can continue handover when the stitching is ready.",
        order_id,
    )
    db.commit()
    return {"ok": True, "payment": payment_result}


@app.post("/api/customer/orders/{order_id}/review", status_code=201)
def create_review(order_id: str, body: ReviewCreate, customer: dict = Depends(customer_user), db: Session = Depends(db_session)):
    order = fetch_one(db, "SELECT * FROM orders WHERE id=:id AND customer_id=:uid", {"id": order_id, "uid": customer["id"]})
    if not order:
        raise HTTPException(404, "Order not found")
    if not is_completed_order(order):
        raise HTTPException(409, "Feedback is allowed only after the order is closed with final handover OTP.")
    if order["rated"]:
        raise HTTPException(409, "This order already has feedback")
    db.execute(
        text("""INSERT INTO reviews (id,order_id,tailor_id,customer_id,rating,body,images) VALUES (:id,:order_id,:tailor_id,:customer_id,:rating,:body,:images)"""),
        {"id": uid("rev"), "order_id": order_id, "tailor_id": order["tailor_id"], "customer_id": customer["id"], "rating": body.rating, "body": body.body, "images": body.images},
    )
    db.execute(text("UPDATE orders SET rated=TRUE WHERE id=:id"), {"id": order_id})
    db.execute(
        text(
            """UPDATE tailors SET rating=(SELECT round(avg(rating)::numeric,2) FROM reviews WHERE tailor_id=:tid AND hidden=FALSE),
            rating_count=(SELECT count(*) FROM reviews WHERE tailor_id=:tid AND hidden=FALSE),
            completed=(SELECT count(*) FROM orders WHERE tailor_id=:tid AND lower(status)='completed')
            WHERE id=:tid"""
        ),
        {"tid": order["tailor_id"]},
    )
    db.commit()
    review = fetch_one(
        db,
        """SELECT r.*, u.name AS customer_name
        FROM reviews r
        JOIN users u ON u.id=r.customer_id
        WHERE r.order_id=:order_id""",
        {"order_id": order_id},
    )
    return {"ok": True, "review": review}


@app.get("/api/tailor/me")
def tailor_profile(user: dict = Depends(tailor_user), db: Session = Depends(db_session)):
    """file 08: editable profile, excludes Aadhaar entirely via as_tailor_private's fixed field whitelist."""
    return as_tailor_private(get_tailor_for_user(db, user))


@app.patch("/api/tailor/me")
def update_tailor_profile(body: TailorProfilePatch, user: dict = Depends(tailor_user), db: Session = Depends(db_session)):
    tailor = get_tailor_for_user(db, user)
    new_phone = clean_phone(body.phone) if body.phone else None
    if new_phone and new_phone != tailor.get("phone_number"):
        if not PHONE_RE.match(new_phone):
            raise HTTPException(400, "Enter a valid 10-digit mobile number")
        if not otp.is_recently_verified(db, new_phone, "registration_phone"):
            raise HTTPException(400, "Verify the new mobile number first")
        if fetch_one(db, "SELECT 1 FROM users WHERE phone=:p AND id<>:id", {"p": new_phone, "id": user["id"]}):
            raise HTTPException(400, "This mobile number is already registered.")
    new_email = body.email.lower() if body.email else None
    if new_email and new_email != (tailor.get("email") or "").lower():
        if not otp.is_recently_verified(db, new_email, "registration_email"):
            raise HTTPException(400, "Verify the new email first")
        if fetch_one(db, "SELECT 1 FROM users WHERE lower(email)=:e AND id<>:id", {"e": new_email, "id": user["id"]}):
            raise HTTPException(400, "This email is already registered.")

    db.execute(
        text(
            """UPDATE tailors SET
                full_name=COALESCE(:full_name, full_name),
                owner_name=COALESCE(:full_name, owner_name),
                bio=COALESCE(:bio, bio),
                experience_years_base=COALESCE(:experience_base, experience_years_base),
                phone_number=COALESCE(:phone, phone_number),
                email=COALESCE(:email, email)
            WHERE id=:id"""
        ),
        {
            "id": tailor["id"],
            "full_name": body.fullName.strip() if body.fullName else None,
            "bio": body.bio,
            "experience_base": body.experienceYearsBase,
            "phone": new_phone,
            "email": new_email,
        },
    )
    if new_phone or new_email:
        db.execute(
            text("UPDATE users SET phone=COALESCE(:phone, phone), email=COALESCE(:email, email) WHERE id=:id"),
            {"phone": new_phone, "email": new_email, "id": user["id"]},
        )
    db.commit()
    return as_tailor_private(get_tailor_for_user(db, user))


@app.post("/api/tailor/me/location")
def set_tailor_location(body: LocationIn, user: dict = Depends(tailor_user), db: Session = Depends(db_session)):
    """file 06: one-time fixed location from the map picker. tailors.lat/lng/shop_address
    already exist 1:1 per tailor, so 'is_fixed' is simply whether they're set yet --
    no separate tailor_locations row needed. Once set, only PATCH (below) can change it."""
    tailor = get_tailor_for_user(db, user)
    if tailor.get("lat") is not None and tailor.get("lng") is not None:
        raise HTTPException(400, "Location already set -- use Update Location to change it")
    db.execute(
        text("UPDATE tailors SET lat=:lat, lng=:lng, shop_address=:addr WHERE id=:id"),
        {"lat": body.latitude, "lng": body.longitude, "addr": body.addressText, "id": tailor["id"]},
    )
    db.commit()
    return as_tailor_private(get_tailor_for_user(db, user))


@app.patch("/api/tailor/me/location")
def update_tailor_location(body: LocationIn, user: dict = Depends(tailor_user), db: Session = Depends(db_session)):
    """Explicit 'Update Location' flow (file 06) -- re-confirmation happens client-side
    (the picker is shown again with the current pin); this always overwrites."""
    tailor = get_tailor_for_user(db, user)
    db.execute(
        text("UPDATE tailors SET lat=:lat, lng=:lng, shop_address=:addr WHERE id=:id"),
        {"lat": body.latitude, "lng": body.longitude, "addr": body.addressText, "id": tailor["id"]},
    )
    db.commit()
    return as_tailor_private(get_tailor_for_user(db, user))


@app.get("/api/tailor/me/services")
def list_my_services(page: PageParams = Depends(PageParams), user: dict = Depends(tailor_user), db: Session = Depends(db_session)):
    """Tailor's own view (file 11) -- includes inactive services, unlike the public endpoint below."""
    tailor = get_tailor_for_user(db, user)
    rows = fetch_all(db, "SELECT * FROM tailor_services WHERE tailor_id=:tid ORDER BY created_at DESC NULLS LAST LIMIT :limit OFFSET :offset", {"tid": tailor["id"], **page.sql})
    return [as_tailor_service(r) for r in rows]


@app.post("/api/tailor/me/services", status_code=201)
def create_my_service(body: TailorServiceCreate, user: dict = Depends(tailor_user), db: Session = Depends(db_session)):
    tailor = get_tailor_for_user(db, user)
    sid = uid("svc")
    db.execute(
        text(
            """INSERT INTO tailor_services (id, tailor_id, name, service_name, category, price, is_combo, combo_items, description, is_active, active)
            VALUES (:id, :tid, CAST(:name AS TEXT), CAST(:service_name AS VARCHAR(160)), :cat, :price, :combo, CAST(:items AS jsonb), :desc, TRUE, TRUE)"""
        ),
        {
            "id": sid,
            "tid": tailor["id"],
            "name": body.serviceName.strip(),
            "service_name": body.serviceName.strip(),
            "cat": body.category,
            "price": body.price,
            "combo": body.isCombo,
            "items": json.dumps(body.comboItems),
            "desc": body.description,
        },
    )
    db.commit()
    return as_tailor_service(fetch_one(db, "SELECT * FROM tailor_services WHERE id=:id", {"id": sid}))


@app.patch("/api/tailor/me/services/{service_id}")
def update_my_service(service_id: str, body: TailorServicePatch, user: dict = Depends(tailor_user), db: Session = Depends(db_session)):
    tailor = get_tailor_for_user(db, user)
    existing = fetch_one(db, "SELECT * FROM tailor_services WHERE tailor_id=:tid AND id=:sid", {"tid": tailor["id"], "sid": service_id})
    if not existing:
        raise HTTPException(404, "Service not found")
    name = body.serviceName.strip() if body.serviceName else None
    db.execute(
        text(
            """UPDATE tailor_services SET
                name=COALESCE(CAST(:name AS TEXT), name), service_name=COALESCE(CAST(:service_name AS VARCHAR(160)), service_name),
                category=COALESCE(:cat, category), price=COALESCE(:price, price),
                is_combo=COALESCE(:combo, is_combo),
                combo_items=COALESCE(CAST(:items AS jsonb), combo_items),
                description=COALESCE(:desc, description),
                is_active=COALESCE(:active, is_active), active=COALESCE(:active, active),
                updated_at=now()
            WHERE id=:id"""
        ),
        {
            "name": name,
            "service_name": name,
            "cat": body.category,
            "price": body.price,
            "combo": body.isCombo,
            "items": json.dumps(body.comboItems) if body.comboItems is not None else None,
            "desc": body.description,
            "active": body.isActive,
            "id": existing["id"],
        },
    )
    db.commit()
    return as_tailor_service(fetch_one(db, "SELECT * FROM tailor_services WHERE id=:id", {"id": existing["id"]}))


@app.delete("/api/tailor/me/services/{service_id}")
def delete_my_service(service_id: str, user: dict = Depends(tailor_user), db: Session = Depends(db_session)):
    tailor = get_tailor_for_user(db, user)
    existing = fetch_one(db, "SELECT * FROM tailor_services WHERE tailor_id=:tid AND id=:sid", {"tid": tailor["id"], "sid": service_id})
    if not existing:
        raise HTTPException(404, "Service not found")
    db.execute(text("UPDATE tailor_services SET is_active=FALSE, active=FALSE, updated_at=now() WHERE id=:id"), {"id": existing["id"]})
    db.commit()
    return {"ok": True}


@app.get("/api/tailors/{tailor_id}/services")
def public_tailor_services(tailor_id: str, page: PageParams = Depends(PageParams), db: Session = Depends(db_session)):
    """Public/customer-facing (file 11) -- active services only, viewed before booking."""
    rows = fetch_all(db, "SELECT * FROM tailor_services WHERE tailor_id=:tid AND is_active=TRUE ORDER BY name LIMIT :limit OFFSET :offset", {"tid": tailor_id, **page.sql})
    return [as_tailor_service(r) for r in rows]


@app.get("/api/tailor/dashboard")
def tailor_dashboard(page: PageParams = Depends(PageParams), user: dict = Depends(tailor_user), db: Session = Depends(db_session)):
    tailor = get_tailor_for_user(db, user)
    services = fetch_all(db, "SELECT * FROM tailor_services WHERE tailor_id=:tid ORDER BY active DESC, price LIMIT 100", {"tid": tailor["id"]})
    requests = fetch_all(
        db,
        """SELECT br.*, r.code AS requirement_code, r.service_name, r.quantity, r.requirements, r.preferred_date,
        r.instructions, r.measurement_mode, r.visit_date, r.visit_slot, r.visit_notes,
        CASE WHEN br.status='ACCEPTED' THEN u.name ELSE 'Customer' END AS customer_name,
        CASE WHEN br.status='ACCEPTED' THEN u.phone ELSE NULL END AS customer_phone,
        CASE WHEN br.status='ACCEPTED' THEN r.address ELSE NULL END AS customer_address,
        u.zone_id AS customer_area, s.name AS tailor_service_name
        FROM booking_requests br
        JOIN booking_requirements r ON r.id=br.requirement_id
        JOIN users u ON u.id=r.customer_id
        LEFT JOIN tailor_services s ON s.id=br.service_id
        WHERE br.tailor_id=:tid
        ORDER BY br.ts DESC
        LIMIT :limit OFFSET :offset""",
        {"tid": tailor["id"], **page.sql},
    )
    orders = fetch_all(
        db,
        """SELECT o.*, u.name AS customer_name,
        CASE WHEN upper(o.status) IN ('AUTO_APPROVED','CONFIRMED','ASSIGNED','TAILOR_CONFIRMED','MEASUREMENT_PENDING','MEASUREMENT_DONE','IN_PROGRESS','READY_FOR_DELIVERY','OUT_FOR_DELIVERY','PAYMENT_PENDING','PAID')
             AND (o.assigned_at IS NOT NULL OR o.request_group_id IS NULL) THEN u.phone ELSE NULL END AS customer_phone,
        CASE WHEN upper(o.status) IN ('AUTO_APPROVED','CONFIRMED','ASSIGNED','TAILOR_CONFIRMED','MEASUREMENT_PENDING','MEASUREMENT_DONE','IN_PROGRESS','READY_FOR_DELIVERY','OUT_FOR_DELIVERY','PAYMENT_PENDING','PAID')
             AND (o.assigned_at IS NOT NULL OR o.request_group_id IS NULL) THEN u.email ELSE NULL END AS customer_email,
        CASE WHEN upper(o.status) IN ('AUTO_APPROVED','CONFIRMED','ASSIGNED','TAILOR_CONFIRMED','MEASUREMENT_PENDING','MEASUREMENT_DONE','IN_PROGRESS','READY_FOR_DELIVERY','OUT_FOR_DELIVERY','PAYMENT_PENDING','PAID')
             AND (o.assigned_at IS NOT NULL OR o.request_group_id IS NULL) THEN COALESCE(o.customer_location_address,r.address) ELSE NULL END AS customer_address,
        r.visit_date, r.visit_slot
        FROM orders o
        JOIN users u ON u.id=o.customer_id
        LEFT JOIN booking_requirements r ON r.id=o.requirement_id
        WHERE o.tailor_id=:tid
        ORDER BY o.ts DESC
        LIMIT :limit OFFSET :offset""",
        {"tid": tailor["id"], **page.sql},
    )
    stats = fetch_one(
        db,
        """SELECT
        (SELECT count(*) FROM booking_requests WHERE tailor_id=:tid AND lower(status)='pending')::int AS pending_requests,
        (SELECT count(*) FROM orders WHERE tailor_id=:tid AND lower(status) NOT IN ('completed','cancelled'))::int AS active_orders,
        (SELECT count(*) FROM orders WHERE tailor_id=:tid AND lower(status)='completed')::int AS completed_orders,
        COALESCE((SELECT balance FROM tailor_wallets WHERE tailor_id=:tailor_uuid LIMIT 1),0)::int AS earnings,
        COALESCE((SELECT balance FROM tailor_wallets WHERE tailor_id=:tailor_uuid LIMIT 1),0)::int AS wallet_balance,
        (SELECT count(*) FROM tailor_followers WHERE tailor_id=:tid)::int AS followers,
        (SELECT count(*) FROM customer_favorite_tailors WHERE tailor_id=:tid)::int AS favorites""",
        {"tid": tailor["id"], "tailor_uuid": tailor["tailor_id"]},
    )
    followers = fetch_all(
        db,
        """SELECT u.id AS customer_profile_id, u.name AS customer_name, u.phone AS customer_phone,
        u.profile_image, tf.created_at AS followed_at
        FROM tailor_followers tf
        JOIN users u ON u.id=tf.customer_id
        WHERE tf.tailor_id=:tid AND u.status='ACTIVE'
        ORDER BY tf.created_at DESC
        LIMIT 100""",
        {"tid": tailor["id"]},
    )
    offers = fetch_all(db, "SELECT * FROM tailor_offers WHERE tailor_id=:tid ORDER BY active DESC, created_at DESC LIMIT 30", {"tid": tailor["id"]})
    notifications = fetch_all(db, "SELECT * FROM notifications WHERE to_ref=:ref ORDER BY ts DESC LIMIT 50", {"ref": "tailor:" + tailor["id"]})
    tailor_payload = as_tailor(tailor)
    tailor_payload["followerCount"] = stats.get("followers") or 0
    tailor_payload["favoriteCount"] = stats.get("favorites") or 0
    return {
        "tailor": tailor_payload,
        "services": services,
        "requests": requests,
        "orders": orders,
        "stats": stats,
        "followers": [as_follower(f) for f in followers],
        "offers": [as_offer(o) for o in offers],
        "notifications": notifications,
    }


@app.post("/api/tailor/notifications/read")
def mark_tailor_notifications_read(user: dict = Depends(tailor_user), db: Session = Depends(db_session)):
    tailor = get_tailor_for_user(db, user)
    db.execute(text("UPDATE notifications SET read=TRUE,read_at=COALESCE(read_at,now()) WHERE to_ref=:ref AND read=FALSE"), {"ref": "tailor:" + tailor["id"]})
    db.commit()
    return {"ok": True}


@app.post("/api/tailor/notifications/{notification_id}/read")
def mark_tailor_notification_read(notification_id: str, user: dict = Depends(tailor_user), db: Session = Depends(db_session)):
    tailor = get_tailor_for_user(db, user)
    row = fetch_one(db, """UPDATE notifications SET read=TRUE,read_at=COALESCE(read_at,now())
        WHERE id=:id AND to_ref=:ref RETURNING id,notification_type,entity_type,entity_id,order_id,
        booking_request_id,measurement_id,payment_id""", {"id": notification_id, "ref": "tailor:" + tailor["id"]})
    if not row:
        raise HTTPException(404, "Notification not found")
    db.commit()
    return {"ok": True, "notification": row}


@app.patch("/api/tailor/availability")
def update_tailor_availability(body: AvailabilityPatch, user: dict = Depends(tailor_user), db: Session = Depends(db_session)):
    if body.availability not in AVAILABILITY_STATUSES:
        raise HTTPException(400, "Invalid availability status")
    tailor = get_tailor_for_user(db, user)
    approval_mode = (body.approvalMode or tailor.get("approval_mode") or "AUTOMATIC").upper()
    if approval_mode not in {"AUTOMATIC", "MANUAL"}:
        raise HTTPException(400, "Approval mode must be AUTOMATIC or MANUAL")
    accepting = body.acceptingRequests
    if body.availability == "NOT_AVAILABLE":
        accepting = False if accepting is None else accepting
    db.execute(
        text(
            """UPDATE tailors SET availability=:availability, available_slots=COALESCE(:slots,available_slots),
            max_new_orders=COALESCE(:max_orders,max_new_orders), next_available=:next_available,
            availability_note=:note, accepting_requests=COALESCE(:accepting,accepting_requests),
            is_available=CASE
                WHEN :availability IN ('AVAILABLE','FEW_SLOTS_AVAILABLE') AND COALESCE(:accepting,accepting_requests)=TRUE THEN TRUE
                ELSE FALSE
            END,
            approval_mode=:approval_mode, availability_updated=now()
            WHERE id=:id"""
        ),
        {
            "id": tailor["id"],
            "availability": body.availability,
            "slots": body.availableSlots,
            "max_orders": body.maxNewOrders,
            "next_available": body.nextAvailable,
            "note": body.availabilityNote,
            "accepting": accepting,
            "approval_mode": approval_mode,
        },
    )
    db.commit()
    updated = fetch_one(db, "SELECT t.*, u.phone, u.email FROM tailors t JOIN users u ON u.id=t.user_id WHERE t.id=:id", {"id": tailor["id"]})
    return as_tailor(updated)


@app.get("/api/tailor/slot-capacities")
def tailor_slot_capacities(slot_date: date, user: dict = Depends(tailor_user), db: Session = Depends(db_session)):
    tailor = get_tailor_for_user(db, user)
    rows = fetch_all(db, "SELECT slot_value,enabled,capacity,booked_count FROM tailor_slot_capacities WHERE tailor_id=:id AND slot_date=:date ORDER BY slot_value", {"id": tailor["id"], "date": slot_date})
    return {"date": slot_date, "approvalMode": tailor.get("approval_mode") or "AUTOMATIC", "slots": rows}


@app.put("/api/tailor/slot-capacities")
def save_tailor_slot_capacities(body: SlotCapacityUpdate, user: dict = Depends(tailor_user), db: Session = Depends(db_session)):
    tailor = get_tailor_for_user(db, user)
    if (tailor.get("approval_mode") or "AUTOMATIC").upper() != "AUTOMATIC":
        raise HTTPException(409, "Slot capacity is available only in Automatic Approval mode")
    valid_slots = {"08:00-10:00","10:00-12:00","12:00-14:00","14:00-16:00","16:00-18:00","18:00-20:00","20:00-22:00"}
    for item in body.slots:
        if item.slot not in valid_slots:
            raise HTTPException(400, f"Invalid slot: {item.slot}")
        db.execute(text("""INSERT INTO tailor_slot_capacities (tailor_id,slot_date,slot_value,enabled,capacity)
          VALUES (:id,:date,:slot,:enabled,:capacity)
          ON CONFLICT (tailor_id,slot_date,slot_value) DO UPDATE SET enabled=EXCLUDED.enabled,capacity=EXCLUDED.capacity,updated_at=now()
          WHERE tailor_slot_capacities.booked_count <= EXCLUDED.capacity"""), {"id": tailor["id"], "date": body.date, "slot": item.slot, "enabled": item.enabled, "capacity": item.capacity})
    db.commit()
    return tailor_slot_capacities(body.date, user, db)


@app.post("/api/tailor/media", status_code=201)
def upload_tailor_media(body: TailorMediaUpload, user: dict = Depends(tailor_user), db: Session = Depends(db_session)):
    tailor = get_tailor_for_user(db, user)
    portfolio = tailor.get("portfolio") or []
    if len(portfolio) >= MAX_PORTFOLIO_ITEMS:
        raise HTTPException(409, f"Maximum {MAX_PORTFOLIO_ITEMS} portfolio items are allowed")
    kind = media_kind(body.mediaType)
    ext = MEDIA_EXTENSIONS.get(body.mediaType)
    if not ext:
        raise HTTPException(400, "Unsupported photo/video format")
    raw = decode_data_url(body.dataUrl, body.mediaType, MAX_MEDIA_BYTES)

    media_id = uid("media")
    object_key = f"tailors/{tailor['id']}/portfolio/{media_id}{ext}"
    try:
        url = media_storage.store_bytes(object_key, raw, body.mediaType)
    except MediaStorageError as exc:
        raise HTTPException(503, "Media storage is temporarily unavailable") from exc
    queue_media_postprocess(object_key, body.mediaType)
    entry = json.dumps(
        {
            "id": media_id,
            "name": body.name[:120] or f"{media_id}{ext}",
            "type": body.mediaType,
            "kind": kind,
            "url": url,
            "uploadedAt": datetime.now(timezone.utc).isoformat(),
        }
    )
    portfolio.append(entry)
    db.execute(text("UPDATE tailors SET portfolio=:portfolio WHERE id=:id"), {"id": tailor["id"], "portfolio": portfolio})
    notify_tailor_followers(
        db,
        tailor["id"],
        f"New {kind} from {tailor['shop']}",
        f"{tailor['shop']} posted a new {kind}: {body.name[:80] or 'portfolio update'}.",
    )
    db.commit()
    updated = fetch_one(db, "SELECT t.*, u.phone, u.email FROM tailors t JOIN users u ON u.id=t.user_id WHERE t.id=:id", {"id": tailor["id"]})
    return as_tailor(updated)


@app.post("/api/tailor/media/presign")
def presign_tailor_media(body: TailorMediaPresign, user: dict = Depends(tailor_user), db: Session = Depends(db_session)):
    tailor = get_tailor_for_user(db, user)
    portfolio = tailor.get("portfolio") or []
    if len(portfolio) >= MAX_PORTFOLIO_ITEMS:
        raise HTTPException(409, f"Maximum {MAX_PORTFOLIO_ITEMS} portfolio items are allowed")
    media_kind(body.mediaType)
    ext = MEDIA_EXTENSIONS.get(body.mediaType)
    if not ext:
        raise HTTPException(400, "Unsupported photo/video format")
    if body.sizeBytes > MAX_MEDIA_BYTES:
        raise HTTPException(413, "Uploaded file is too large")
    object_key = f"tailors/{tailor['id']}/portfolio/{uid('media')}{ext}"
    try:
        return media_storage.create_presigned_upload(object_key, body.mediaType, MAX_MEDIA_BYTES)
    except MediaStorageError as exc:
        raise HTTPException(503, "Direct media upload is temporarily unavailable") from exc


@app.post("/api/tailor/media/complete", status_code=201)
def complete_tailor_media(body: TailorMediaComplete, user: dict = Depends(tailor_user), db: Session = Depends(db_session)):
    tailor = get_tailor_for_user(db, user)
    portfolio = list(tailor.get("portfolio") or [])
    if len(portfolio) >= MAX_PORTFOLIO_ITEMS:
        raise HTTPException(409, f"Maximum {MAX_PORTFOLIO_ITEMS} portfolio items are allowed")
    kind = media_kind(body.mediaType)
    expected_prefix = f"tailors/{tailor['id']}/portfolio/"
    if not body.objectKey.startswith(expected_prefix):
        raise HTTPException(403, "This upload does not belong to the signed-in tailor")
    try:
        url = media_storage.validate_uploaded_object(body.objectKey, body.mediaType, MAX_MEDIA_BYTES)
    except MediaStorageError as exc:
        raise HTTPException(400, str(exc)) from exc
    queue_media_postprocess(body.objectKey, body.mediaType)
    entry = json.dumps(
        {
            "id": Path(body.objectKey).stem,
            "name": body.name[:120],
            "type": body.mediaType,
            "kind": kind,
            "url": url,
            "uploadedAt": datetime.now(timezone.utc).isoformat(),
        }
    )
    portfolio.append(entry)
    db.execute(text("UPDATE tailors SET portfolio=:portfolio WHERE id=:id"), {"id": tailor["id"], "portfolio": portfolio})
    notify_tailor_followers(db, tailor["id"], f"New {kind} from {tailor['shop']}", f"{tailor['shop']} posted a new {kind}: {body.name[:80]}.")
    db.commit()
    updated = fetch_one(db, "SELECT t.*, u.phone, u.email FROM tailors t JOIN users u ON u.id=t.user_id WHERE t.id=:id", {"id": tailor["id"]})
    return as_tailor(updated)


@app.post("/api/tailor/profile-image")
def upload_tailor_profile_image(body: TailorProfileImageUpload, user: dict = Depends(tailor_user), db: Session = Depends(db_session)):
    tailor = get_tailor_for_user(db, user)
    if not body.mediaType.startswith("image/"):
        raise HTTPException(400, "Only image files are allowed for profile picture")
    ext = MEDIA_EXTENSIONS.get(body.mediaType)
    if ext not in {".jpg", ".png", ".webp", ".gif"}:
        raise HTTPException(400, "Unsupported profile image format")
    raw = decode_data_url(body.dataUrl, body.mediaType, MAX_PROFILE_IMAGE_BYTES)
    image_id = uid("dp")
    object_key = f"tailors/{tailor['id']}/profile/{image_id}{ext}"
    try:
        url = media_storage.store_bytes(object_key, raw, body.mediaType)
    except MediaStorageError as exc:
        raise HTTPException(503, "Media storage is temporarily unavailable") from exc
    queue_media_postprocess(object_key, body.mediaType)
    delete_uploaded_url(tailor.get("profile_image"))
    db.execute(text("UPDATE tailors SET profile_image=:url WHERE id=:id"), {"id": tailor["id"], "url": url})
    db.commit()
    updated = fetch_one(db, "SELECT t.*, u.phone, u.email FROM tailors t JOIN users u ON u.id=t.user_id WHERE t.id=:id", {"id": tailor["id"]})
    return as_tailor(updated)


@app.post("/api/tailor/profile-image/presign")
def presign_tailor_profile_image(body: TailorMediaPresign, user: dict = Depends(tailor_user), db: Session = Depends(db_session)):
    tailor = get_tailor_for_user(db, user)
    if not body.mediaType.startswith("image/"):
        raise HTTPException(400, "Only image files are allowed for profile picture")
    ext = MEDIA_EXTENSIONS.get(body.mediaType)
    if ext not in {".jpg", ".png", ".webp", ".gif"}:
        raise HTTPException(400, "Unsupported profile image format")
    if body.sizeBytes > MAX_PROFILE_IMAGE_BYTES:
        raise HTTPException(413, "Uploaded file is too large")
    object_key = f"tailors/{tailor['id']}/profile/{uid('dp')}{ext}"
    try:
        return media_storage.create_presigned_upload(object_key, body.mediaType, MAX_PROFILE_IMAGE_BYTES)
    except MediaStorageError as exc:
        raise HTTPException(503, "Direct profile upload is temporarily unavailable") from exc


@app.post("/api/tailor/profile-image/complete")
def complete_tailor_profile_image(body: TailorMediaComplete, user: dict = Depends(tailor_user), db: Session = Depends(db_session)):
    tailor = get_tailor_for_user(db, user)
    if not body.mediaType.startswith("image/"):
        raise HTTPException(400, "Only image files are allowed for profile picture")
    expected_prefix = f"tailors/{tailor['id']}/profile/"
    if not body.objectKey.startswith(expected_prefix):
        raise HTTPException(403, "This upload does not belong to the signed-in tailor")
    try:
        url = media_storage.validate_uploaded_object(body.objectKey, body.mediaType, MAX_PROFILE_IMAGE_BYTES)
    except MediaStorageError as exc:
        raise HTTPException(400, str(exc)) from exc
    queue_media_postprocess(body.objectKey, body.mediaType)
    delete_uploaded_url(tailor.get("profile_image"))
    db.execute(text("UPDATE tailors SET profile_image=:url WHERE id=:id"), {"id": tailor["id"], "url": url})
    db.commit()
    updated = fetch_one(db, "SELECT t.*, u.phone, u.email FROM tailors t JOIN users u ON u.id=t.user_id WHERE t.id=:id", {"id": tailor["id"]})
    return as_tailor(updated)


@app.delete("/api/tailor/profile-image")
def delete_tailor_profile_image(user: dict = Depends(tailor_user), db: Session = Depends(db_session)):
    tailor = get_tailor_for_user(db, user)
    delete_uploaded_url(tailor.get("profile_image"))
    db.execute(text("UPDATE tailors SET profile_image=NULL WHERE id=:id"), {"id": tailor["id"]})
    db.commit()
    updated = fetch_one(db, "SELECT t.*, u.phone, u.email FROM tailors t JOIN users u ON u.id=t.user_id WHERE t.id=:id", {"id": tailor["id"]})
    return as_tailor(updated)


@app.delete("/api/tailor/media/{media_index}")
def delete_tailor_media(media_index: int, user: dict = Depends(tailor_user), db: Session = Depends(db_session)):
    tailor = get_tailor_for_user(db, user)
    portfolio = list(tailor.get("portfolio") or [])
    if media_index < 0 or media_index >= len(portfolio):
        raise HTTPException(404, "Portfolio item not found")
    removed = portfolio.pop(media_index)
    delete_uploaded_media_file(removed)
    db.execute(text("UPDATE tailors SET portfolio=:portfolio WHERE id=:id"), {"id": tailor["id"], "portfolio": portfolio})
    db.commit()
    updated = fetch_one(db, "SELECT t.*, u.phone, u.email FROM tailors t JOIN users u ON u.id=t.user_id WHERE t.id=:id", {"id": tailor["id"]})
    return as_tailor(updated)


@app.post("/api/tailor/offers", status_code=201)
def create_tailor_offer(body: TailorOfferCreate, user: dict = Depends(tailor_user), db: Session = Depends(db_session)):
    tailor = get_tailor_for_user(db, user)
    offer_id = uid("offer")
    media_url = None
    media_type = None
    if body.dataUrl or body.mediaType:
        if not body.dataUrl or not body.mediaType:
            raise HTTPException(400, "Offer media requires both media type and file data")
        media_kind(body.mediaType)
        ext = MEDIA_EXTENSIONS.get(body.mediaType)
        if not ext:
            raise HTTPException(400, "Unsupported offer media format")
        raw = decode_data_url(body.dataUrl, body.mediaType, MAX_MEDIA_BYTES)
        object_key = f"tailors/{tailor['id']}/offers/{offer_id}{ext}"
        try:
            media_url = media_storage.store_bytes(object_key, raw, body.mediaType)
        except MediaStorageError as exc:
            raise HTTPException(503, "Media storage is temporarily unavailable") from exc
        queue_media_postprocess(object_key, body.mediaType)
        media_type = body.mediaType
    db.execute(
        text(
            """INSERT INTO tailor_offers (id,tailor_id,title,body,discount,media_url,media_type,expires_at)
            VALUES (:id,:tailor_id,:title,:body,:discount,:media_url,:media_type,:expires_at)"""
        ),
        {
            "id": offer_id,
            "tailor_id": tailor["id"],
            "title": body.title.strip(),
            "body": body.body.strip(),
            "discount": body.discount.strip() if body.discount else None,
            "media_url": media_url,
            "media_type": media_type,
            "expires_at": body.expiresAt,
        },
    )
    offer_bits = [f"{tailor['shop']} posted an offer: {body.title.strip()}."]
    if body.discount:
        offer_bits.append(f"Offer: {body.discount.strip()}")
    if body.expiresAt:
        offer_bits.append(f"Valid until {body.expiresAt.isoformat()}.")
    notify_tailor_followers(db, tailor["id"], f"New offer from {tailor['shop']}", " ".join(offer_bits))
    db.commit()
    return as_offer(fetch_one(db, "SELECT * FROM tailor_offers WHERE id=:id", {"id": offer_id}))


@app.delete("/api/tailor/offers/{offer_id}")
def deactivate_tailor_offer(offer_id: str, user: dict = Depends(tailor_user), db: Session = Depends(db_session)):
    tailor = get_tailor_for_user(db, user)
    offer = fetch_one(db, "SELECT * FROM tailor_offers WHERE id=:id AND tailor_id=:tailor_id", {"id": offer_id, "tailor_id": tailor["id"]})
    if not offer:
        raise HTTPException(404, "Offer not found")
    db.execute(text("UPDATE tailor_offers SET active=FALSE WHERE id=:id"), {"id": offer_id})
    db.commit()
    return {"ok": True}


@app.get("/api/tailor/support/tickets")
def tailor_support_tickets(page: PageParams = Depends(PageParams), user: dict = Depends(tailor_user), db: Session = Depends(db_session)):
    return user_support_tickets(db, user, "tailor", page)


@app.post("/api/tailor/support/tickets", status_code=201)
def create_tailor_support_ticket(body: SupportTicketCreate, user: dict = Depends(tailor_user), db: Session = Depends(db_session)):
    return create_support_ticket(db, user, "tailor", body)


@app.get("/api/tailor/support/tickets/{ticket_id}")
def tailor_support_ticket(ticket_id: str, user: dict = Depends(tailor_user), db: Session = Depends(db_session)):
    return support_ticket_payload(db, get_user_support_ticket(db, user, "tailor", ticket_id))


@app.post("/api/tailor/support/tickets/{ticket_id}/messages")
def reply_tailor_support_ticket(ticket_id: str, body: SupportMessageCreate, user: dict = Depends(tailor_user), db: Session = Depends(db_session)):
    return add_user_support_message(db, user, "tailor", ticket_id, body)


@app.post("/api/tailor/support/tickets/{ticket_id}/close")
def close_tailor_support_ticket(ticket_id: str, user: dict = Depends(tailor_user), db: Session = Depends(db_session)):
    get_user_support_ticket(db, user, "tailor", ticket_id)
    db.execute(text("UPDATE support_tickets SET status='CLOSED', closed_at=now(), last_activity_at=now(), updated_at=now() WHERE id=:id"), {"id": ticket_id})
    db.commit()
    return support_ticket_payload(db, get_user_support_ticket(db, user, "tailor", ticket_id))


@app.post("/api/tailor/requests/{request_id}/accept")
def accept_request(request_id: str, user: dict = Depends(tailor_user), db: Session = Depends(db_session)):
    tailor = get_tailor_for_user(db, user)
    if tailor["approval_status"] != "APPROVED" or tailor["account_status"] != "ACTIVE":
        raise HTTPException(403, "Admin approval is required before accepting requests")
    br = fetch_one(db, "SELECT * FROM booking_requests WHERE id=:id AND tailor_id=:tid FOR UPDATE", {"id": request_id, "tid": tailor["id"]})
    if not br:
        raise HTTPException(404, "Request not found")
    req = fetch_one(db, "SELECT * FROM booking_requirements WHERE id=:id FOR UPDATE", {"id": br["requirement_id"]})
    if br["status"] != "PENDING" or req["status"] != "OPEN":
        raise HTTPException(409, "This request is no longer open")
    service = fetch_one(db, "SELECT * FROM tailor_services WHERE id=:id", {"id": br["service_id"]})
    if not service:
        raise HTTPException(409, "Service is no longer available")
    order_id = uid("ord")
    code = fetch_one(db, "SELECT 'ORD-' || nextval('order_code_seq') AS code")["code"]
    base_price = br["quoted_price"] or service["price"] * req["quantity"]
    expected = req["preferred_date"] or (date.today() + timedelta(days=service["days"]))
    db.execute(
        text(
            """INSERT INTO orders
            (id,code,requirement_id,request_id,customer_id,tailor_id,service_id,service_name,garment_id,quantity,status,base_price,total,measurement_mode,appointment_date,appointment_slot,address,expected_completion,notes)
            VALUES (:id,:code,:requirement_id,:request_id,:customer_id,:tailor_id,:service_id,:service_name,:garment_id,:quantity,'ACCEPTED',:base_price,:total,:measurement_mode,:appointment_date,:appointment_slot,:address,:expected_completion,:notes)"""
        ),
        {
            "id": order_id,
            "code": code,
            "requirement_id": req["id"],
            "request_id": br["id"],
            "customer_id": req["customer_id"],
            "tailor_id": tailor["id"],
            "service_id": service["id"],
            "service_name": service["name"],
            "garment_id": service["garment_id"],
            "quantity": req["quantity"],
            "base_price": base_price,
            "total": base_price,
            "measurement_mode": req["measurement_mode"],
            "appointment_date": req["visit_date"],
            "appointment_slot": req["visit_slot"],
            "address": req["address"] if req["measurement_mode"] == "HOME" else tailor["shop_address"],
            "expected_completion": expected,
            "notes": req["instructions"],
        },
    )
    db.execute(text("INSERT INTO payments (id,order_id,amount,status) VALUES (:id,:order_id,:amount,'PENDING')"), {"id": uid("pay"), "order_id": order_id, "amount": base_price})
    db.execute(text("UPDATE booking_requests SET status='ACCEPTED', responded_at=now() WHERE id=:id"), {"id": br["id"]})
    db.execute(text("UPDATE booking_requests SET status='CLOSED', responded_at=now() WHERE requirement_id=:rid AND id<>:id AND status='PENDING'"), {"rid": req["id"], "id": br["id"]})
    db.execute(text("UPDATE booking_requirements SET status='ACCEPTED' WHERE id=:id"), {"id": req["id"]})
    add_history(db, order_id, "ACCEPTED", "Tailor accepted the booking request", "tailor")
    customer_contact = fetch_one(db, "SELECT name, email FROM users WHERE id=:id", {"id": req["customer_id"]})
    notify_and_email(
        db,
        "user:" + req["customer_id"],
        customer_contact.get("email") if customer_contact else None,
        "TailoraHub booking confirmed",
        "\n".join(
            [
                f"{tailor['shop']} accepted your request.",
                f"Order ID: {code}",
                f"Service: {service['name']}",
                f"Quantity: {req['quantity']}",
                f"Measurement: {req['measurement_mode']}",
                f"Appointment: {req['visit_date'] or 'Not scheduled'} {req['visit_slot'] or ''}".strip(),
                f"Expected completion: {expected}",
                f"Estimated total: Rs {base_price}",
                "",
                "You can track this order from your Customer Dashboard.",
            ]
        ),
        order_id,
    )
    db.commit()
    return fetch_one(db, "SELECT * FROM orders WHERE id=:id", {"id": order_id})


@app.post("/api/tailor/requests/{request_id}/reject")
def reject_request(request_id: str, body: TailorRequestReject, user: dict = Depends(tailor_user), db: Session = Depends(db_session)):
    tailor = get_tailor_for_user(db, user)
    br = fetch_one(
        db,
        """SELECT br.*, r.customer_id, r.code AS requirement_code, u.email AS customer_email FROM booking_requests br
        JOIN booking_requirements r ON r.id=br.requirement_id
        JOIN users u ON u.id=r.customer_id
        WHERE br.id=:id AND br.tailor_id=:tid""",
        {"id": request_id, "tid": tailor["id"]},
    )
    if not br:
        raise HTTPException(404, "Request not found")
    if br["status"] != "PENDING":
        raise HTTPException(409, "Only pending requests can be rejected")
    db.execute(text("UPDATE booking_requests SET status='REJECTED', reject_reason=:reason, responded_at=now() WHERE id=:id"), {"id": request_id, "reason": body.reason})
    notify_and_email(
        db,
        "user:" + br["customer_id"],
        br.get("customer_email"),
        "TailoraHub booking request update",
        f"{tailor['shop']} rejected request {br['requirement_code']}. Reason: {body.reason}",
    )
    db.commit()
    return {"ok": True}


@app.patch("/api/tailor/orders/{order_id}")
def update_tailor_order(order_id: str, body: TailorOrderUpdate, user: dict = Depends(tailor_user), db: Session = Depends(db_session)):
    tailor = get_tailor_for_user(db, user)
    order = fetch_one(
        db,
        "SELECT o.*, u.email FROM orders o JOIN users u ON u.id=o.customer_id WHERE o.id=:id AND o.tailor_id=:tid",
        {"id": order_id, "tid": tailor["id"]},
    )
    if not order:
        raise HTTPException(404, "Order not found")
    if is_completed_order(order):
        raise HTTPException(409, "This order is already completed. Status updates are disabled after handover OTP verification.")
    if body.status and body.status not in ORDER_STATUSES:
        raise HTTPException(400, "Invalid order status")
    if body.status == "COMPLETED" and (order["payment_status"] != "PAID" or not order["otp_verified"]):
        raise HTTPException(409, "Completion requires paid payment and verified handover OTP")
    db.execute(
        text(
            """UPDATE orders SET status=COALESCE(:status,status), expected_completion=COALESCE(:expected,expected_completion),
            delay_reason=COALESCE(:delay,delay_reason), notes=COALESCE(:note,notes),
            payment_status=CASE WHEN :status='PAYMENT_PENDING' THEN 'PENDING' ELSE payment_status END
            WHERE id=:id"""
        ),
        {"id": order_id, "status": body.status, "expected": body.expectedCompletion, "delay": body.delayReason, "note": body.note},
    )
    if body.status:
        add_history(db, order_id, body.status, body.note or body.delayReason, "tailor")
        customer_contact = fetch_one(db, "SELECT email FROM users WHERE id=:id", {"id": order["customer_id"]})
        extra = ""
        if body.status in {"READY_FOR_DELIVERY", "READY_FOR_HANDOVER", "DELIVERY_PENDING"}:
            extra = "\nYour order is reaching handover stage. Please complete payment if pending. Handover will be completed only after email OTP verification."
        notify_and_email(
            db,
            "user:" + order["customer_id"],
            customer_contact.get("email") if customer_contact else None,
            "TailoraHub order tracker update",
            f"Order {order['code']} status: {status_label(body.status)}.\n{body.note or body.delayReason or ''}{extra}",
            order_id,
        )
    db.commit()
    return fetch_one(db, "SELECT * FROM orders WHERE id=:id", {"id": order_id})


@app.post("/api/tailor/orders/{order_id}/charges", status_code=201)
def add_charge(order_id: str, body: AdditionalChargeIn, user: dict = Depends(tailor_user), db: Session = Depends(db_session)):
    tailor = get_tailor_for_user(db, user)
    order = fetch_one(db, "SELECT * FROM orders WHERE id=:id AND tailor_id=:tid", {"id": order_id, "tid": tailor["id"]})
    if not order:
        raise HTTPException(404, "Order not found")
    if is_completed_order(order):
        raise HTTPException(409, "This order is already completed. Additional charges are disabled.")
    charge_id = uid("chg")
    db.execute(
        text("INSERT INTO additional_charges (id,order_id,description,reason,amount,added_by) VALUES (:id,:order_id,:description,:reason,:amount,:added_by)"),
        {"id": charge_id, "order_id": order_id, "description": body.description, "reason": body.reason, "amount": body.amount, "added_by": "tailor:" + tailor["id"]},
    )
    db.execute(text("UPDATE orders SET additional_total=additional_total+:amount, total=total+:amount WHERE id=:id"), {"id": order_id, "amount": body.amount})
    add_history(db, order_id, order["status"], f"Additional charge added: {body.description} Rs {body.amount}", "tailor")
    customer_contact = fetch_one(db, "SELECT email FROM users WHERE id=:id", {"id": order["customer_id"]})
    notify_and_email(
        db,
        "user:" + order["customer_id"],
        customer_contact.get("email") if customer_contact else None,
        "TailoraHub additional charge",
        f"Additional charge added for order {order['code']}.\nDescription: {body.description}\nReason: {body.reason or 'Not specified'}\nAmount: Rs {body.amount}\nUpdated total: Rs {order['total'] + body.amount}",
        order_id,
    )
    db.commit()
    return {"id": charge_id}


@app.post("/api/tailor/orders/{order_id}/delivery-otp")
def generate_delivery_otp(order_id: str, user: dict = Depends(tailor_user), db: Session = Depends(db_session)):
    tailor = get_tailor_for_user(db, user)
    order = fetch_one(
        db,
        "SELECT o.*, u.email FROM orders o JOIN users u ON u.id=o.customer_id WHERE o.id=:id AND o.tailor_id=:tid",
        {"id": order_id, "tid": tailor["id"]},
    )
    if not order:
        raise HTTPException(404, "Order not found")
    if is_completed_order(order):
        raise HTTPException(409, "This order is already completed. Delivery OTP cannot be sent again.")
    if order["payment_status"] != "PAID":
        raise HTTPException(409, "Payment must be paid before delivery OTP")
    try:
        code, _ = otp.issue(db, order_id, "delivery")
    except otp.OtpError as exc:
        db.rollback()
        raise HTTPException(429 if exc.code == "cooldown" else 400, exc.message)
    db.execute(text("UPDATE orders SET status='DELIVERY_PENDING' WHERE id=:id AND status <> 'COMPLETED'"), {"id": order_id})
    add_history(db, order_id, "DELIVERY_PENDING", "Delivery handover OTP sent to customer email", "tailor")
    notify_and_email(
        db,
        "user:" + order["customer_id"],
        order.get("email"),
        "TailoraHub handover OTP",
        f"Your handover OTP for order {order['code']} is {code}. It is valid for {otp.OTP_TTL_MINUTES} minutes. Share this OTP with the tailor only during final cloth handover.",
        order_id,
    )
    db.commit()
    return {"sent": True}


@app.post("/api/tailor/orders/{order_id}/verify-delivery")
def verify_delivery_otp(order_id: str, body: DeliveryOtpIn, user: dict = Depends(tailor_user), db: Session = Depends(db_session)):
    tailor = get_tailor_for_user(db, user)
    order = fetch_one(
        db,
        "SELECT o.*, u.email FROM orders o JOIN users u ON u.id=o.customer_id WHERE o.id=:id AND o.tailor_id=:tid",
        {"id": order_id, "tid": tailor["id"]},
    )
    if not order:
        raise HTTPException(404, "Order not found")
    if is_completed_order(order):
        raise HTTPException(409, "This order is already completed. Handover OTP cannot be verified again.")
    if order["payment_status"] != "PAID":
        raise HTTPException(409, "Payment must be paid before completion")
    try:
        matched = otp.verify(db, order_id, "delivery", body.otp)
    except otp.OtpError as exc:
        db.rollback()
        raise HTTPException(401, exc.message)
    if not matched:
        raise HTTPException(401, "Incorrect or expired delivery OTP")
    db.execute(text("UPDATE orders SET otp_verified=TRUE, status='COMPLETED', delivered_at=now(), completed_at=now() WHERE id=:id"), {"id": order_id})
    add_history(db, order_id, "COMPLETED", "Delivery OTP verified and order completed", "tailor")
    db.execute(text("UPDATE tailors SET completed=(SELECT count(*) FROM orders WHERE tailor_id=:tid AND status='COMPLETED') WHERE id=:tid"), {"tid": tailor["id"]})
    notify_and_email(
        db,
        "user:" + order["customer_id"],
        order.get("email"),
        "TailoraHub order completed",
        f"Order {order['code']} is completed after payment and handover OTP verification. You can now give feedback from Customer Dashboard.",
        order_id,
    )
    db.commit()
    return {"ok": True}


@app.get("/api/admin/metrics")
def admin_metrics(_: dict = Depends(admin_user), db: Session = Depends(db_session)):
    row = fetch_one(
        db,
        """
        SELECT
          (SELECT count(*) FROM users WHERE 'customer'=ANY(roles) AND NOT 'admin'=ANY(roles))::int AS customers,
          (SELECT count(*) FROM users WHERE 'customer'=ANY(roles) AND status='ACTIVE')::int AS active_customers,
          (SELECT count(*) FROM users WHERE 'customer'=ANY(roles) AND status IN ('SUSPENDED','BLOCKED'))::int AS suspended_customers,
          (SELECT count(*) FROM tailors WHERE deleted_at IS NULL)::int AS tailors,
          (SELECT count(*) FROM tailors WHERE approval_status='PENDING_APPROVAL' AND deleted_at IS NULL)::int AS pending_tailors,
          (SELECT count(*) FROM tailors WHERE verified AND deleted_at IS NULL)::int AS verified_tailors,
          (SELECT count(*) FROM tailors WHERE account_status='ACTIVE' AND deleted_at IS NULL)::int AS active_tailors,
          (SELECT count(*) FROM tailors WHERE account_status IN ('SUSPENDED','BLOCKED') AND deleted_at IS NULL)::int AS suspended_tailors,
          (SELECT count(*) FROM booking_requests)::int AS booking_requests,
          (SELECT count(*) FROM orders WHERE status NOT IN ('COMPLETED','CANCELLED'))::int AS active_orders,
          (SELECT count(*) FROM orders WHERE status='COMPLETED')::int AS completed_orders,
          (SELECT count(*) FROM orders WHERE status='CANCELLED')::int AS cancelled_orders,
          (SELECT COALESCE(sum(amount),0) FROM payments WHERE status='PAID')::int AS total_payments,
          (SELECT count(*) FROM payments WHERE status IN ('PENDING','PROCESSING'))::int AS pending_payments,
          (SELECT count(*) FROM support_tickets WHERE status NOT IN ('RESOLVED','CLOSED'))::int AS support_tickets,
          (SELECT count(*) FROM support_tickets WHERE requester_role='customer' AND status NOT IN ('RESOLVED','CLOSED'))::int AS customer_support,
          (SELECT count(*) FROM support_tickets WHERE requester_role='tailor' AND status NOT IN ('RESOLVED','CLOSED'))::int AS tailor_support,
          (SELECT count(*) FROM complaints WHERE status <> 'RESOLVED')::int AS complaints
        """,
    )
    return row


@app.get("/api/admin/customers")
def admin_customers(page: PageParams = Depends(PageParams), _: dict = Depends(admin_user), db: Session = Depends(db_session)):
    rows = fetch_all(db, "SELECT * FROM users WHERE 'customer'=ANY(roles) AND NOT 'admin'=ANY(roles) ORDER BY joined DESC LIMIT :limit OFFSET :offset", page.sql)
    return [as_public_user(r) for r in rows]


@app.get("/api/admin/tailors")
def admin_tailors(page: PageParams = Depends(PageParams), _: dict = Depends(admin_user), db: Session = Depends(db_session)):
    rows = fetch_all(db, "SELECT t.*, u.phone, u.email FROM tailors t JOIN users u ON u.id=t.user_id ORDER BY t.created DESC LIMIT :limit OFFSET :offset", page.sql)
    return [as_tailor(r) for r in rows]


@app.get("/api/admin/booking-requests")
def admin_booking_requests(page: PageParams = Depends(PageParams), _: dict = Depends(admin_user), db: Session = Depends(db_session)):
    return fetch_all(
        db,
        """SELECT br.*, r.code AS requirement_code, r.service_name, r.quantity, r.preferred_date, r.measurement_mode,
        r.status AS requirement_status, cu.name AS customer_name, cu.phone AS customer_phone, t.shop, t.owner_name
        FROM booking_requests br
        JOIN booking_requirements r ON r.id=br.requirement_id
        JOIN users cu ON cu.id=r.customer_id
        JOIN tailors t ON t.id=br.tailor_id
        ORDER BY br.ts DESC
        LIMIT :limit OFFSET :offset""",
        page.sql,
    )


@app.get("/api/admin/customers/{customer_id}/delete-check")
def customer_delete_check(customer_id: str, _: dict = Depends(admin_user), db: Session = Depends(db_session)):
    user = fetch_one(db, "SELECT * FROM users WHERE id=:id", {"id": customer_id})
    if not user:
        raise HTTPException(404, "Customer not found")
    row = fetch_one(
        db,
        """
        SELECT
          (SELECT count(*) FROM booking_requests br JOIN booking_requirements r ON r.id=br.requirement_id WHERE r.customer_id=:id AND br.status='PENDING')::int AS pending_requests,
          (SELECT count(*) FROM booking_requirements WHERE customer_id=:id AND status='OPEN')::int AS active_bookings,
          (SELECT count(*) FROM orders WHERE customer_id=:id AND status NOT IN ('COMPLETED','CANCELLED'))::int AS ongoing_orders,
          (SELECT count(*) FROM payments p JOIN orders o ON o.id=p.order_id WHERE o.customer_id=:id AND p.status IN ('PENDING','PROCESSING'))::int AS pending_payments,
          (SELECT count(*) FROM orders WHERE customer_id=:id AND status='COMPLETED')::int AS completed_orders
        """,
        {"id": customer_id},
    )
    row["customer"] = as_public_user(user)
    row["safeToDelete"] = row["ongoing_orders"] == 0 and row["pending_payments"] == 0
    return row


@app.patch("/api/admin/customers/{customer_id}")
def patch_customer(customer_id: str, body: CustomerPatch, admin: dict = Depends(admin_user), db: Session = Depends(db_session)):
    if body.status and body.status not in ACCOUNT_STATUSES:
        raise HTTPException(400, "Invalid status")
    user = fetch_one(db, "SELECT * FROM users WHERE id=:id", {"id": customer_id})
    if not user:
        raise HTTPException(404, "Customer not found")
    db.execute(
        text("""UPDATE users SET name=COALESCE(:name,name), email=COALESCE(:email,email), phone=COALESCE(:phone,phone), zone_id=COALESCE(:zone,zone_id), address=COALESCE(:address,address), status=COALESCE(:status,status) WHERE id=:id"""),
        {"id": customer_id, "name": body.name, "email": str(body.email).lower() if body.email else None, "phone": clean_phone(body.phone) if body.phone else None, "zone": body.zoneId, "address": body.address, "status": body.status},
    )
    audit(db, admin, "CUSTOMER_STATUS_" + body.status if body.status else "CUSTOMER_EDIT", "customer", customer_id, user["name"], body.reason, body.dict(exclude_none=True))
    db.commit()
    return as_public_user(fetch_one(db, "SELECT * FROM users WHERE id=:id", {"id": customer_id}))


@app.delete("/api/admin/customers/{customer_id}")
def delete_customer(customer_id: str, reason: str = Query("Admin deletion"), admin: dict = Depends(admin_user), db: Session = Depends(db_session)):
    check = customer_delete_check(customer_id, admin, db)
    if not check["safeToDelete"]:
        raise HTTPException(409, "Resolve active orders and pending payments before deleting this customer")
    user = fetch_one(db, "SELECT * FROM users WHERE id=:id", {"id": customer_id})
    db.execute(text("UPDATE booking_requirements SET status='CANCELLED' WHERE customer_id=:id AND status='OPEN'"), {"id": customer_id})
    db.execute(text("UPDATE booking_requests SET status='CANCELLED' WHERE requirement_id IN (SELECT id FROM booking_requirements WHERE customer_id=:id) AND status='PENDING'"), {"id": customer_id})
    db.execute(
        text("""UPDATE users SET status='DELETED', anonymized=TRUE, deleted_at=now(), name='Deleted customer', phone='deleted-' || substr(md5(random()::text),1,10), email=NULL, address=NULL, password_hash=NULL, profile_image=NULL WHERE id=:id"""),
        {"id": customer_id},
    )
    audit(db, admin, "CUSTOMER_DELETE", "customer", customer_id, user["name"], reason, {"anonymized": True})
    db.commit()
    return {"ok": True, "anonymized": True}


@app.post("/api/admin/tailors/{tailor_id}/approve")
def approve_tailor(tailor_id: str, admin: dict = Depends(admin_user), db: Session = Depends(db_session)):
    t = fetch_one(db, "SELECT t.*, u.email FROM tailors t JOIN users u ON u.id=t.user_id WHERE t.id=:id", {"id": tailor_id})
    if not t:
        raise HTTPException(404, "Tailor not found")
    db.execute(text("UPDATE tailors SET approval_status='APPROVED', verified=TRUE, account_status='ACTIVE', status='active', reject_reason=NULL WHERE id=:id"), {"id": tailor_id})
    db.execute(text("UPDATE users SET roles = CASE WHEN 'tailor'=ANY(roles) THEN roles ELSE array_append(roles,'tailor') END WHERE id=:id"), {"id": t["user_id"]})
    audit(db, admin, "TAILOR_APPROVE", "tailor", tailor_id, t["shop"], "Approved by admin")
    notify_and_email(
        db,
        "tailor:" + tailor_id,
        t.get("email"),
        "TailoraHub tailor profile approved",
        f"Congratulations. Your tailor profile for {t['shop']} has been approved and is now visible to customers. You can receive booking requests from your Tailor Dashboard.",
    )
    db.commit()
    return as_tailor(fetch_one(db, "SELECT t.*, u.phone, u.email FROM tailors t JOIN users u ON u.id=t.user_id WHERE t.id=:id", {"id": tailor_id}))


@app.post("/api/admin/tailors/{tailor_id}/reject")
def reject_tailor(tailor_id: str, reason: str = "Documents incomplete", admin: dict = Depends(admin_user), db: Session = Depends(db_session)):
    t = fetch_one(db, "SELECT t.*, u.email FROM tailors t JOIN users u ON u.id=t.user_id WHERE t.id=:id", {"id": tailor_id})
    if not t:
        raise HTTPException(404, "Tailor not found")
    db.execute(text("UPDATE tailors SET approval_status='REJECTED', verified=FALSE, reject_reason=:reason WHERE id=:id"), {"id": tailor_id, "reason": reason})
    audit(db, admin, "TAILOR_REJECT", "tailor", tailor_id, t["shop"], reason)
    notify_and_email(
        db,
        "tailor:" + tailor_id,
        t.get("email"),
        "TailoraHub tailor profile rejected",
        f"Your tailor profile for {t['shop']} was rejected. Reason: {reason}. Please update your details/documents and contact admin.",
    )
    db.commit()
    return {"ok": True}


@app.get("/api/admin/tailors/{tailor_id}/delete-check")
def tailor_delete_check(tailor_id: str, _: dict = Depends(admin_user), db: Session = Depends(db_session)):
    t = fetch_one(db, "SELECT t.*, u.phone, u.email FROM tailors t JOIN users u ON u.id=t.user_id WHERE t.id=:id", {"id": tailor_id})
    if not t:
        raise HTTPException(404, "Tailor not found")
    row = fetch_one(
        db,
        """
        SELECT
          (SELECT count(*) FROM booking_requests WHERE tailor_id=:id AND status='PENDING')::int AS pending_requests,
          (SELECT count(*) FROM booking_requests WHERE tailor_id=:id AND status='ACCEPTED')::int AS accepted_bookings,
          (SELECT count(*) FROM orders WHERE tailor_id=:id AND status NOT IN ('COMPLETED','CANCELLED'))::int AS active_orders,
          (SELECT count(*) FROM orders WHERE tailor_id=:id AND status IN ('READY_FOR_DELIVERY','DELIVERY_PENDING','DELIVERED'))::int AS pending_deliveries,
          (SELECT count(*) FROM payments p JOIN orders o ON o.id=p.order_id WHERE o.tailor_id=:id AND p.status IN ('PENDING','PROCESSING'))::int AS pending_payments
        """,
        {"id": tailor_id},
    )
    row["tailor"] = as_tailor(t)
    row["safeToDelete"] = row["active_orders"] == 0 and row["pending_payments"] == 0
    return row


@app.patch("/api/admin/tailors/{tailor_id}")
def patch_tailor(tailor_id: str, body: TailorPatch, admin: dict = Depends(admin_user), db: Session = Depends(db_session)):
    if body.accountStatus and body.accountStatus not in ACCOUNT_STATUSES:
        raise HTTPException(400, "Invalid account status")
    if body.approvalStatus and body.approvalStatus not in APPROVAL_STATUSES:
        raise HTTPException(400, "Invalid approval status")
    t = fetch_one(db, "SELECT * FROM tailors WHERE id=:id", {"id": tailor_id})
    if not t:
        raise HTTPException(404, "Tailor not found")
    db.execute(
        text(
            """UPDATE tailors SET shop=COALESCE(:shop,shop), zone_id=COALESCE(:zone,zone_id), shop_address=COALESCE(:shop_address,shop_address),
            bio=COALESCE(:bio,bio), years=COALESCE(:years,years), verified=COALESCE(:verified,verified), account_status=COALESCE(:account_status,account_status),
            approval_status=COALESCE(:approval_status,approval_status), availability=COALESCE(:availability,availability),
            available_slots=COALESCE(:slots,available_slots), featured=COALESCE(:featured,featured), plan=COALESCE(:plan,plan) WHERE id=:id"""
        ),
        {"id": tailor_id, "shop": body.shop, "zone": body.zoneId, "shop_address": body.shopAddress, "bio": body.bio, "years": body.years, "verified": body.verified, "account_status": body.accountStatus, "approval_status": body.approvalStatus, "availability": body.availability, "slots": body.availableSlots, "featured": body.featured, "plan": body.plan},
    )
    audit(db, admin, "TAILOR_STATUS_" + body.accountStatus if body.accountStatus else "TAILOR_EDIT", "tailor", tailor_id, t["shop"], body.reason, body.dict(exclude_none=True))
    db.commit()
    return as_tailor(fetch_one(db, "SELECT t.*, u.phone, u.email FROM tailors t JOIN users u ON u.id=t.user_id WHERE t.id=:id", {"id": tailor_id}))


@app.delete("/api/admin/tailors/{tailor_id}")
def delete_tailor(tailor_id: str, reason: str = Query("Admin deletion"), admin: dict = Depends(admin_user), db: Session = Depends(db_session)):
    check = tailor_delete_check(tailor_id, admin, db)
    if not check["safeToDelete"]:
        raise HTTPException(409, "Resolve active orders and pending payments before deleting this tailor")
    t = fetch_one(db, "SELECT * FROM tailors WHERE id=:id", {"id": tailor_id})
    db.execute(text("UPDATE tailors SET account_status='DELETED', approval_status='REJECTED', deleted_at=now() WHERE id=:id"), {"id": tailor_id})
    db.execute(text("UPDATE booking_requests SET status='CANCELLED' WHERE tailor_id=:id AND status='PENDING'"), {"id": tailor_id})
    audit(db, admin, "TAILOR_DELETE", "tailor", tailor_id, t["shop"], reason, {"softDeleted": True})
    db.commit()
    return {"ok": True}


@app.get("/api/admin/orders")
def admin_orders(page: PageParams = Depends(PageParams), _: dict = Depends(admin_user), db: Session = Depends(db_session)):
    return fetch_all(db, "SELECT o.*, cu.name AS customer_name, t.shop FROM orders o JOIN users cu ON cu.id=o.customer_id JOIN tailors t ON t.id=o.tailor_id ORDER BY o.ts DESC LIMIT :limit OFFSET :offset", page.sql)


@app.patch("/api/admin/orders/{order_id}")
def patch_order(order_id: str, body: OrderPatch, admin: dict = Depends(admin_user), db: Session = Depends(db_session)):
    if body.paymentStatus and body.paymentStatus not in PAYMENT_STATUSES:
        raise HTTPException(400, "Invalid payment status")
    order = fetch_one(db, "SELECT * FROM orders WHERE id=:id", {"id": order_id})
    if not order:
        raise HTTPException(404, "Order not found")
    db.execute(
        text("UPDATE orders SET status=COALESCE(:status,status), payment_status=COALESCE(:pay,payment_status), expected_completion=COALESCE(:due,expected_completion), notes=COALESCE(:notes,notes) WHERE id=:id"),
        {"id": order_id, "status": body.status, "pay": body.paymentStatus, "due": body.expectedCompletion, "notes": body.notes},
    )
    audit(db, admin, "ORDER_EDIT", "order", order_id, order["code"], body.reason, body.dict(exclude_none=True))
    db.commit()
    return fetch_one(db, "SELECT * FROM orders WHERE id=:id", {"id": order_id})


@app.post("/api/admin/orders/{order_id}/cancel")
def cancel_order(order_id: str, reason: str = "Cancelled by admin", admin: dict = Depends(admin_user), db: Session = Depends(db_session)):
    order = fetch_one(db, "SELECT * FROM orders WHERE id=:id", {"id": order_id})
    if not order:
        raise HTTPException(404, "Order not found")
    if order["status"] == "COMPLETED":
        raise HTTPException(409, "Completed orders cannot be cancelled")
    db.execute(text("UPDATE orders SET status='CANCELLED', cancel_reason=:reason WHERE id=:id"), {"id": order_id, "reason": reason})
    audit(db, admin, "ORDER_CANCEL", "order", order_id, order["code"], reason)
    db.commit()
    return {"ok": True}


@app.get("/api/admin/payments")
def admin_payments(page: PageParams = Depends(PageParams), _: dict = Depends(admin_user), db: Session = Depends(db_session)):
    return fetch_all(
        db,
        """
        SELECT
          p.*,
          o.code AS order_code,
          (lower(COALESCE(p.method,'')) <> 'cash') AS gateway_verified,
          CASE
            WHEN lower(COALESCE(p.method,'')) = 'cash' THEN 'unverified_by_gateway'
            ELSE 'gateway_verified'
          END AS verification_status
        FROM payments p
        JOIN orders o ON o.id=p.order_id
        ORDER BY p.ts DESC
        LIMIT :limit OFFSET :offset
        """,
        page.sql,
    )


@app.get("/api/admin/reviews")
def admin_reviews(page: PageParams = Depends(PageParams), _: dict = Depends(admin_user), db: Session = Depends(db_session)):
    return fetch_all(db, "SELECT r.*, cu.name AS customer_name, t.shop FROM reviews r JOIN users cu ON cu.id=r.customer_id JOIN tailors t ON t.id=r.tailor_id ORDER BY r.ts DESC LIMIT :limit OFFSET :offset", page.sql)


@app.patch("/api/admin/reviews/{review_id}")
def patch_review(review_id: str, body: ReviewPatch, admin: dict = Depends(admin_user), db: Session = Depends(db_session)):
    review = fetch_one(db, "SELECT * FROM reviews WHERE id=:id", {"id": review_id})
    if not review:
        raise HTTPException(404, "Review not found")
    hidden = body.hidden if body.hidden is not None else not review["hidden"]
    db.execute(text("UPDATE reviews SET hidden=:hidden WHERE id=:id"), {"id": review_id, "hidden": hidden})
    audit(db, admin, "REVIEW_HIDE" if hidden else "REVIEW_SHOW", "review", review_id, None, body.reason)
    db.commit()
    return {"ok": True, "hidden": hidden}


@app.get("/api/admin/complaints")
def admin_complaints(page: PageParams = Depends(PageParams), _: dict = Depends(admin_user), db: Session = Depends(db_session)):
    return fetch_all(db, "SELECT c.*, u.name AS raiser_name, o.code AS order_code FROM complaints c JOIN users u ON u.id=c.raised_by LEFT JOIN orders o ON o.id=c.order_id ORDER BY c.ts DESC LIMIT :limit OFFSET :offset", page.sql)


@app.get("/api/admin/support-tickets")
def admin_support_tickets(page: PageParams = Depends(PageParams), _: dict = Depends(admin_user), db: Session = Depends(db_session)):
    tickets = fetch_all(
        db,
        """SELECT st.*, u.name AS requester_name, u.email AS requester_email, u.phone AS requester_phone, o.code AS order_code,
        (SELECT count(*) FROM support_messages sm WHERE sm.ticket_id=st.id)::int AS message_count
        FROM support_tickets st
        JOIN users u ON u.id=st.requester_id
        LEFT JOIN orders o ON o.id=st.order_id
        ORDER BY
          CASE st.priority WHEN 'URGENT' THEN 1 WHEN 'HIGH' THEN 2 WHEN 'NORMAL' THEN 3 ELSE 4 END,
          CASE st.status WHEN 'OPEN' THEN 1 WHEN 'PENDING' THEN 2 WHEN 'WAITING_ON_CUSTOMER' THEN 3 WHEN 'RESOLVED' THEN 4 ELSE 5 END,
          st.last_activity_at DESC
        LIMIT :limit OFFSET :offset""",
        page.sql,
    )
    return tickets


@app.patch("/api/admin/support-tickets/{ticket_id}")
def patch_support_ticket(ticket_id: str, body: SupportTicketPatch, admin: dict = Depends(admin_user), db: Session = Depends(db_session)):
    ticket = fetch_one(db, "SELECT st.*, u.email, u.name AS requester_name FROM support_tickets st JOIN users u ON u.id=st.requester_id WHERE st.id=:id", {"id": ticket_id})
    if not ticket:
        raise HTTPException(404, "Support ticket not found")
    status = body.status.strip().upper() if body.status else None
    priority = body.priority.strip().upper() if body.priority else None
    if status and status not in SUPPORT_STATUSES:
        raise HTTPException(400, "Invalid support status")
    if priority and priority not in SUPPORT_PRIORITIES:
        raise HTTPException(400, "Invalid support priority")
    db.execute(
        text(
            """UPDATE support_tickets SET
            status=COALESCE(:status,status), priority=COALESCE(:priority,priority), assigned_to=COALESCE(:assigned_to,assigned_to),
            resolved_at=CASE WHEN :status='RESOLVED' THEN now() ELSE resolved_at END,
            closed_at=CASE WHEN :status='CLOSED' THEN now() ELSE closed_at END,
            last_activity_at=now(), updated_at=now()
            WHERE id=:id"""
        ),
        {"id": ticket_id, "status": status, "priority": priority, "assigned_to": body.assignedTo},
    )
    if body.note:
        db.execute(
            text("""INSERT INTO support_messages (ticket_id,author_id,author_name,author_role,body,internal) VALUES (:ticket_id,:author_id,:author_name,'admin',:body,TRUE)"""),
            {"ticket_id": ticket_id, "author_id": admin["id"], "author_name": admin["name"], "body": body.note.strip()},
        )
    audit(db, admin, "SUPPORT_UPDATE", "support_ticket", ticket_id, ticket["code"], body.note, body.dict(exclude_none=True))
    db.commit()
    updated = fetch_one(db, "SELECT st.*, u.name AS requester_name, u.email AS requester_email, u.phone AS requester_phone, o.code AS order_code FROM support_tickets st JOIN users u ON u.id=st.requester_id LEFT JOIN orders o ON o.id=st.order_id WHERE st.id=:id", {"id": ticket_id})
    return support_ticket_payload(db, updated)


@app.post("/api/admin/support-tickets/{ticket_id}/messages")
def reply_support_ticket(ticket_id: str, body: SupportMessageCreate, admin: dict = Depends(admin_user), db: Session = Depends(db_session)):
    ticket = fetch_one(db, "SELECT st.*, u.email, u.name AS requester_name FROM support_tickets st JOIN users u ON u.id=st.requester_id WHERE st.id=:id", {"id": ticket_id})
    if not ticket:
        raise HTTPException(404, "Support ticket not found")
    if ticket["status"] == "CLOSED":
        raise HTTPException(409, "Closed tickets cannot be updated")
    first_response = ticket.get("first_response_at") is None
    db.execute(
        text("""INSERT INTO support_messages (ticket_id,author_id,author_name,author_role,body) VALUES (:ticket_id,:author_id,:author_name,'admin',:body)"""),
        {"ticket_id": ticket_id, "author_id": admin["id"], "author_name": admin["name"], "body": body.body.strip()},
    )
    db.execute(
        text(
            """UPDATE support_tickets SET status='WAITING_ON_CUSTOMER',
            first_response_at=CASE WHEN :first THEN now() ELSE first_response_at END,
            last_agent_reply_at=now(), last_activity_at=now(), updated_at=now()
            WHERE id=:id"""
        ),
        {"id": ticket_id, "first": first_response},
    )
    notify_and_email(
        db,
        "user:" + ticket["requester_id"],
        ticket.get("email"),
        f"TailoraHub support replied to {ticket['code']}",
        body.body.strip(),
        ticket.get("order_id"),
    )
    audit(db, admin, "SUPPORT_REPLY", "support_ticket", ticket_id, ticket["code"], None)
    db.commit()
    updated = fetch_one(db, "SELECT st.*, u.name AS requester_name, u.email AS requester_email, u.phone AS requester_phone, o.code AS order_code FROM support_tickets st JOIN users u ON u.id=st.requester_id LEFT JOIN orders o ON o.id=st.order_id WHERE st.id=:id", {"id": ticket_id})
    return support_ticket_payload(db, updated)


@app.patch("/api/admin/complaints/{complaint_id}")
def patch_complaint(complaint_id: str, body: ComplaintPatch, admin: dict = Depends(admin_user), db: Session = Depends(db_session)):
    complaint = fetch_one(db, "SELECT * FROM complaints WHERE id=:id", {"id": complaint_id})
    if not complaint:
        raise HTTPException(404, "Complaint not found")
    db.execute(text("UPDATE complaints SET status=COALESCE(:status,status), resolution=COALESCE(:resolution,resolution) WHERE id=:id"), {"id": complaint_id, "status": body.status, "resolution": body.resolution})
    audit(db, admin, "COMPLAINT_" + (body.status or "UPDATE"), "complaint", complaint_id, complaint["subject"], body.resolution)
    db.commit()
    return {"ok": True}


@app.get("/api/admin/audit")
def admin_audit(page: PageParams = Depends(PageParams), _: dict = Depends(admin_user), db: Session = Depends(db_session)):
    return fetch_all(db, "SELECT * FROM audit_logs ORDER BY ts DESC LIMIT :limit OFFSET :offset", page.sql)
