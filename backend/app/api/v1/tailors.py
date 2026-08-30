from __future__ import annotations

from datetime import date
from decimal import Decimal
import json
import re
import secrets
import string
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_tailor
from app.api.v1.otp import is_recently_verified, normalize_target
from app.api.v1.session_tokens import create_token_pair
from app.core.database import get_db
from app.integrations import aadhaar_kyc_service
from app.pagination import PageParams
from app.qr import generate_wallet_qr
from app.schemas.services import TailorServiceIn, TailorServicePatchIn
from app.schemas.tailors import TailorAadhaarVerifyIn, TailorAvailabilityCheckIn, TailorLocationIn, TailorRegisterIn
from app.security import encrypt_aadhaar, hash_aadhaar, hash_password, is_valid_aadhaar_format


router = APIRouter()

PHONE_RE = re.compile(r"^[6-9]\d{9}$")
SERVICE_CATEGORIES = {"Blouse", "Shirt", "Pant", "Combo", "Other"}


def uid(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def clean_phone(value: str) -> str:
    return re.sub(r"\D", "", value or "")


def password_is_strong(value: str) -> bool:
    return len(value or "") >= 8 and bool(re.search(r"[A-Za-z]", value)) and bool(re.search(r"\d", value))


def normalize_name(value: str | None) -> str:
    return re.sub(r"\s+", " ", (value or "").strip()).casefold()


def kyc_dob(value) -> date | None:
    if not value:
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


async def fetch_one(db: AsyncSession, sql: str, params: dict | None = None) -> dict | None:
    result = await db.execute(text(sql), params or {})
    row = result.mappings().first()
    return dict(row) if row else None


async def generate_tailor_referral_code(db: AsyncSession) -> str:
    alphabet = string.ascii_uppercase + string.digits
    while True:
        code = "".join(secrets.choice(alphabet) for _ in range(8))
        if not await fetch_one(db, "SELECT 1 FROM tailors WHERE referral_code=:code", {"code": code}):
            return code


def public_user(row: dict) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "phone": row.get("phone"),
        "email": row.get("email"),
        "roles": row.get("roles") or [],
        "zoneId": row.get("zone_id"),
        "address": row.get("address"),
        "profileImage": row.get("profile_image"),
        "status": row.get("status"),
        "joined": row.get("joined"),
    }


def public_tailor(row: dict | None) -> dict | None:
    if not row:
        return None
    return {
        "id": row["id"],
        "tailorId": str(row["tailor_id"]),
        "userId": row["user_id"],
        "shop": row["shop"],
        "ownerName": row["owner_name"],
        "zoneId": row["zone_id"],
        "shopAddress": row.get("shop_address"),
        "email": row.get("email"),
        "phone": row.get("phone_number"),
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
        "experienceYearsBase": float(row.get("experience_years_base") or 0),
        "stitchingSinceDate": row.get("stitching_since_date"),
        "termsAccepted": bool(row.get("terms_accepted")),
        "created": row.get("created"),
    }


def public_location(row: dict | None) -> dict | None:
    if not row:
        return None
    return {
        "id": str(row["id"]),
        "tailorId": str(row["tailor_id"]),
        "addressText": row.get("address_text"),
        "latitude": float(row["latitude"]) if row.get("latitude") is not None else None,
        "longitude": float(row["longitude"]) if row.get("longitude") is not None else None,
        "isFixed": bool(row.get("is_fixed")),
        "createdAt": row.get("created_at"),
        "updatedAt": row.get("updated_at"),
    }


def service_combo_items(value) -> list[str]:
    if not value:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        try:
            decoded = json.loads(value)
            if isinstance(decoded, list):
                return [str(item).strip() for item in decoded if str(item).strip()]
        except json.JSONDecodeError:
            return [item.strip() for item in value.split(",") if item.strip()]
    return []


def normalize_service_category(value: str | None, is_combo: bool | None = None) -> str:
    requested = (value or ("Combo" if is_combo else "Other")).strip()
    for category in SERVICE_CATEGORIES:
        if category.casefold() == requested.casefold():
            return category
    raise HTTPException(400, "Category must be Blouse, Shirt, Pant, Combo, or Other")


def public_tailor_service(row: dict | None) -> dict | None:
    if not row:
        return None
    legacy_id = row["id"]
    service_uuid = str(row["service_id"])
    name = row.get("service_name") or row.get("name")
    combo_items = service_combo_items(row.get("combo_items"))
    is_active = row.get("is_active")
    if is_active is None:
        is_active = row.get("active", True)
    return {
        "id": legacy_id,
        "serviceId": legacy_id,
        "service_id": service_uuid,
        "serviceUuid": service_uuid,
        "tailorId": row.get("tailor_id"),
        "tailor_id": row.get("tailor_id"),
        "serviceName": name,
        "service_name": name,
        "name": name,
        "category": row.get("category") or "Other",
        "price": int(row.get("price") or 0),
        "isCombo": bool(row.get("is_combo")),
        "is_combo": bool(row.get("is_combo")),
        "comboItems": combo_items,
        "combo_items": combo_items,
        "description": row.get("description"),
        "isActive": bool(is_active),
        "is_active": bool(is_active),
        "days": row.get("days"),
        "createdAt": row.get("created_at"),
        "created_at": row.get("created_at"),
        "updatedAt": row.get("updated_at"),
        "updated_at": row.get("updated_at"),
    }


async def find_tailor_service(db: AsyncSession, tailor_legacy_id: str, service_id: str) -> dict | None:
    return await fetch_one(
        db,
        """
        SELECT *
        FROM tailor_services
        WHERE tailor_id=:tailor_id
          AND (id=:service_id OR service_id::text=:service_id)
        """,
        {"tailor_id": tailor_legacy_id, "service_id": service_id},
    )


async def duplicate_message(db: AsyncSession, field: str, value: str) -> str | None:
    cleaned = value.strip()
    if field == "phone":
        phone = clean_phone(cleaned)
        if not PHONE_RE.fullmatch(phone):
            return "Enter a valid 10-digit mobile number"
        taken = await fetch_one(
            db,
            """SELECT 1 FROM tailors WHERE phone_number=:phone AND deleted_at IS NULL
               UNION ALL
               SELECT 1 FROM users WHERE phone=:phone AND 'tailor'=ANY(roles) AND status <> 'DELETED'
               LIMIT 1""",
            {"phone": phone},
        )
        return "This mobile number is already registered." if taken else None
    if field == "email":
        email = cleaned.lower()
        taken = await fetch_one(
            db,
            """SELECT 1 FROM tailors WHERE lower(email)=:email AND deleted_at IS NULL
               UNION ALL
               SELECT 1 FROM users WHERE lower(email)=:email AND 'tailor'=ANY(roles) AND status <> 'DELETED'
               LIMIT 1""",
            {"email": email},
        )
        return "This email is already registered." if taken else None
    if field == "aadhaar":
        if not is_valid_aadhaar_format(cleaned):
            return "Enter a valid 12-digit Aadhaar number"
        taken = await fetch_one(db, "SELECT 1 FROM tailors WHERE aadhaar_number_hash=:hash", {"hash": hash_aadhaar(cleaned)})
        return "This Aadhaar number is already registered." if taken else None
    if field == "username":
        if len(cleaned) < 4:
            return "Username must be at least 4 characters"
        taken = await fetch_one(db, "SELECT 1 FROM tailors WHERE lower(username)=:username AND deleted_at IS NULL", {"username": cleaned.lower()})
        return "This username is taken." if taken else None
    raise HTTPException(400, "Unsupported field")


async def save_location_record(db: AsyncSession, tailor: dict, body: TailorLocationIn, allow_update: bool) -> dict:
    if not body.confirmed:
        raise HTTPException(400, "Confirm this location before saving")

    existing = await fetch_one(
        db,
        "SELECT * FROM tailor_locations WHERE tailor_id=:tailor_id AND is_fixed=TRUE ORDER BY updated_at DESC LIMIT 1",
        {"tailor_id": tailor["tailor_id"]},
    )
    if existing and not allow_update:
        raise HTTPException(409, "Fixed location already saved. Use the Update Location flow to change it.")

    if existing:
        result = await db.execute(
            text(
                """UPDATE tailor_locations
                   SET address_text=:address_text, latitude=:latitude, longitude=:longitude, is_fixed=TRUE, updated_at=now()
                   WHERE id=:id
                   RETURNING *"""
            ),
            {
                "id": existing["id"],
                "address_text": body.address_text,
                "latitude": body.latitude,
                "longitude": body.longitude,
            },
        )
        row = dict(result.mappings().first())
    else:
        result = await db.execute(
            text(
                """INSERT INTO tailor_locations (id,tailor_id,address_text,latitude,longitude,is_fixed,created_at,updated_at)
                   VALUES (gen_random_uuid(),:tailor_id,:address_text,:latitude,:longitude,TRUE,now(),now())
                   RETURNING *"""
            ),
            {
                "tailor_id": tailor["tailor_id"],
                "address_text": body.address_text,
                "latitude": body.latitude,
                "longitude": body.longitude,
            },
        )
        row = dict(result.mappings().first())

    await db.execute(
        text("""UPDATE tailors SET shop_address=:address_text, lat=:latitude, lng=:longitude, updated_at=now() WHERE tailor_id=:tailor_id"""),
        {
            "tailor_id": tailor["tailor_id"],
            "address_text": body.address_text,
            "latitude": body.latitude,
            "longitude": body.longitude,
        },
    )
    return row


@router.get("/scaffold")
async def tailors_scaffold() -> dict:
    return {"module": "tailors", "ready": True}


@router.post("/check-availability")
async def check_availability(body: TailorAvailabilityCheckIn, db: AsyncSession = Depends(get_db)) -> dict:
    message = await duplicate_message(db, body.field.strip().lower(), body.value)
    return {"available": message is None, "message": message}


@router.post("/verify-aadhaar")
async def verify_aadhaar(body: TailorAadhaarVerifyIn) -> dict:
    aadhaar = body.aadhaar_number.strip()
    if not is_valid_aadhaar_format(aadhaar):
        raise HTTPException(400, "Enter a valid 12-digit Aadhaar number")
    kyc = aadhaar_kyc_service().verify(aadhaar, body.full_name)
    if not kyc.get("verified"):
        raise HTTPException(400, kyc.get("reason") or "Aadhaar verification failed")
    return {
        "verified": True,
        "fullName": kyc.get("fullName") or body.full_name,
        "dob": kyc.get("dob") or (body.dob.isoformat() if body.dob else None),
        "provider": kyc.get("provider"),
        "mode": kyc.get("mode"),
    }


@router.post("/me/location")
async def save_my_fixed_location(
    body: TailorLocationIn,
    tailor: dict = Depends(get_current_tailor),
    db: AsyncSession = Depends(get_db),
) -> dict:
    row = await save_location_record(db, tailor, body, allow_update=False)
    await db.commit()
    return public_location(row)


@router.patch("/me/location")
async def update_my_fixed_location(
    body: TailorLocationIn,
    tailor: dict = Depends(get_current_tailor),
    db: AsyncSession = Depends(get_db),
) -> dict:
    row = await save_location_record(db, tailor, body, allow_update=True)
    await db.commit()
    return public_location(row)


@router.get("/me/services")
async def list_my_services(
    page: PageParams = Depends(PageParams),
    tailor: dict = Depends(get_current_tailor),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    rows = await db.execute(
        text(
            """
            SELECT *
            FROM tailor_services
            WHERE tailor_id=:tailor_id
            ORDER BY COALESCE(is_active, active) DESC, category NULLS LAST, service_name NULLS LAST, name
            LIMIT :limit OFFSET :offset
            """
        ),
        {"tailor_id": tailor["id"], **page.sql},
    )
    return [public_tailor_service(dict(row)) for row in rows.mappings().all()]


@router.get("/me/waiting-list")
async def my_waiting_list(
    page: PageParams = Depends(PageParams),
    tailor: dict = Depends(get_current_tailor),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    result = await db.execute(
        text(
            """
            SELECT
              o.id,
              o.code,
              o.customer_id,
              u.name AS customer_name,
              u.phone AS customer_phone,
              u.email AS customer_email,
              o.service_id,
              o.service_name,
              o.quantity,
              o.status,
              o.payment_status,
              o.measurement_mode,
              o.customer_location_address,
              o.customer_location_lat,
              o.customer_location_lng,
              o.customer_location_confirmed_at,
              o.address,
              o.appointment_date,
              o.appointment_slot,
              o.expected_completion,
              o.total,
              o.notes,
              o.ts
            FROM orders o
            JOIN users u ON u.id=o.customer_id
            WHERE o.tailor_id=:tailor_id
              AND upper(o.status) IN ('WAITING_LIST','WAITLISTED','PENDING_APPROVAL')
            ORDER BY o.ts ASC
            LIMIT :limit OFFSET :offset
            """
        ),
        {"tailor_id": tailor["id"], **page.sql},
    )
    rows = []
    for row in result.mappings().all():
        item = dict(row)
        item["customerName"] = item.get("customer_name")
        item["customerPhone"] = item.get("customer_phone")
        item["customerEmail"] = item.get("customer_email")
        item["serviceName"] = item.get("service_name")
        item["paymentStatus"] = item.get("payment_status")
        item["measurementMode"] = item.get("measurement_mode")
        item["customerLocationAddress"] = item.get("customer_location_address")
        item["customerLocationLat"] = float(item["customer_location_lat"]) if item.get("customer_location_lat") is not None else None
        item["customerLocationLng"] = float(item["customer_location_lng"]) if item.get("customer_location_lng") is not None else None
        item["customerLocationConfirmedAt"] = item.get("customer_location_confirmed_at")
        item["appointmentDate"] = item.get("appointment_date")
        item["appointmentSlot"] = item.get("appointment_slot")
        item["expectedCompletion"] = item.get("expected_completion")
        rows.append(item)
    return rows


@router.post("/me/services", status_code=201)
async def create_my_service(
    body: TailorServiceIn,
    tailor: dict = Depends(get_current_tailor),
    db: AsyncSession = Depends(get_db),
) -> dict:
    category = normalize_service_category(body.category, body.is_combo)
    combo_items = service_combo_items(body.combo_items)
    if body.is_combo and not combo_items:
        raise HTTPException(400, "Add at least one combo item")

    legacy_id = uid("svc")
    result = await db.execute(
        text(
            """
            INSERT INTO tailor_services
              (id, tailor_id, name, service_name, category, price, is_combo, combo_items, description, is_active, active, created_at, updated_at)
            VALUES
              (:id, :tailor_id, CAST(:name AS TEXT), CAST(:service_name AS VARCHAR(160)), :category, :price, :is_combo, CAST(:combo_items AS jsonb), :description, TRUE, TRUE, now(), now())
            RETURNING *
            """
        ),
        {
            "id": legacy_id,
            "tailor_id": tailor["id"],
            "name": body.service_name,
            "service_name": body.service_name,
            "category": category,
            "price": body.price,
            "is_combo": body.is_combo,
            "combo_items": json.dumps(combo_items),
            "description": body.description,
        },
    )
    row = dict(result.mappings().first())
    await db.commit()
    return public_tailor_service(row)


@router.patch("/me/services/{service_id}")
async def update_my_service(
    service_id: str,
    body: TailorServicePatchIn,
    tailor: dict = Depends(get_current_tailor),
    db: AsyncSession = Depends(get_db),
) -> dict:
    existing = await find_tailor_service(db, tailor["id"], service_id)
    if not existing:
        raise HTTPException(404, "Service not found")

    category = normalize_service_category(body.category, body.is_combo) if body.category is not None else None
    combo_items = service_combo_items(body.combo_items) if body.combo_items is not None else None
    next_is_combo = body.is_combo if body.is_combo is not None else bool(existing.get("is_combo"))
    if next_is_combo and combo_items == []:
        raise HTTPException(400, "Add at least one combo item")

    result = await db.execute(
        text(
            """
            UPDATE tailor_services
            SET
              name=COALESCE(CAST(:name AS TEXT), name),
              service_name=COALESCE(CAST(:service_name AS VARCHAR(160)), service_name),
              category=COALESCE(:category, category),
              price=COALESCE(:price, price),
              is_combo=COALESCE(:is_combo, is_combo),
              combo_items=COALESCE(CAST(:combo_items AS jsonb), combo_items),
              description=COALESCE(:description, description),
              is_active=COALESCE(:is_active, is_active),
              active=COALESCE(:is_active, active),
              updated_at=now()
            WHERE id=:id
            RETURNING *
            """
        ),
        {
            "id": existing["id"],
            "name": body.service_name,
            "service_name": body.service_name,
            "category": category,
            "price": body.price,
            "is_combo": body.is_combo,
            "combo_items": json.dumps(combo_items) if combo_items is not None else None,
            "description": body.description,
            "is_active": body.is_active,
        },
    )
    row = dict(result.mappings().first())
    await db.commit()
    return public_tailor_service(row)


@router.delete("/me/services/{service_id}")
async def delete_my_service(
    service_id: str,
    tailor: dict = Depends(get_current_tailor),
    db: AsyncSession = Depends(get_db),
) -> dict:
    existing = await find_tailor_service(db, tailor["id"], service_id)
    if not existing:
        raise HTTPException(404, "Service not found")
    await db.execute(
        text("UPDATE tailor_services SET is_active=FALSE, active=FALSE, updated_at=now() WHERE id=:id"),
        {"id": existing["id"]},
    )
    await db.commit()
    return {"ok": True, "message": "Service removed from public profile"}


@router.get("/{tailor_id}/services")
async def public_tailor_services(tailor_id: str, page: PageParams = Depends(PageParams), db: AsyncSession = Depends(get_db)) -> list[dict]:
    tailor = await fetch_one(
        db,
        "SELECT id FROM tailors WHERE (id=:tailor_id OR tailor_id::text=:tailor_id) AND deleted_at IS NULL LIMIT 1",
        {"tailor_id": tailor_id},
    )
    if not tailor:
        raise HTTPException(404, "Tailor not found")
    rows = await db.execute(
        text(
            """
            SELECT *
            FROM tailor_services
            WHERE tailor_id=:tailor_id
              AND COALESCE(is_active, active)=TRUE
            ORDER BY category NULLS LAST, price, service_name NULLS LAST, name
            LIMIT :limit OFFSET :offset
            """
        ),
        {"tailor_id": tailor["id"], **page.sql},
    )
    return [public_tailor_service(dict(row)) for row in rows.mappings().all()]


@router.post("/register", status_code=201)
async def register_tailor(body: TailorRegisterIn, db: AsyncSession = Depends(get_db)) -> dict:
    phone = clean_phone(body.phone_number)
    email = str(body.email).lower()
    username = body.username.strip()
    aadhaar = body.aadhaar_number.strip()
    full_name = body.full_name.strip()
    gender = (body.gender or "").strip() or None

    if not PHONE_RE.fullmatch(phone):
        raise HTTPException(400, "Enter a valid 10-digit mobile number")
    if not is_valid_aadhaar_format(aadhaar):
        raise HTTPException(400, "Enter a valid 12-digit Aadhaar number")
    if body.confirm_password is not None and body.password != body.confirm_password:
        raise HTTPException(400, "Password and confirm password must match")
    if not password_is_strong(body.password):
        raise HTTPException(400, "Password must be at least 8 characters and include one letter and one number")
    if not body.terms_accepted:
        raise HTTPException(400, "You must accept the terms and conditions")
    if body.stitching_since_date > date.today():
        raise HTTPException(400, "Stitching since date cannot be in the future")
    if not body.address_text or body.latitude is None or body.longitude is None:
        raise HTTPException(400, "Confirm your fixed shop location")

    for field, value in {"phone": phone, "email": email, "aadhaar": aadhaar, "username": username}.items():
        message = await duplicate_message(db, field, value)
        if message:
            raise HTTPException(400, message)

    phone_target, _ = normalize_target(phone, "registration_phone")
    email_target, _ = normalize_target(email, "registration_email")
    if not await is_recently_verified(db, phone_target, "registration_phone"):
        raise HTTPException(400, "Verify your mobile number first")
    if not await is_recently_verified(db, email_target, "registration_email"):
        raise HTTPException(400, "Verify your email first")

    kyc = aadhaar_kyc_service().verify(aadhaar, full_name)
    if not kyc.get("verified"):
        raise HTTPException(400, kyc.get("reason") or "Aadhaar verification failed")
    kyc_name = kyc.get("fullName")
    if kyc_name and normalize_name(kyc_name) != normalize_name(full_name):
        raise HTTPException(400, "Full name must match Aadhaar name")
    returned_dob = kyc_dob(kyc.get("dob"))
    if returned_dob and returned_dob != body.dob:
        raise HTTPException(400, "DOB must match Aadhaar record")

    aadhaar_hash = hash_aadhaar(aadhaar)
    referral_code = (body.referral_code or "").strip().upper() or None
    referred_by_tailor_id = None
    if referral_code:
        referrer = await fetch_one(
            db,
            "SELECT tailor_id FROM tailors WHERE referral_code=:code AND deleted_at IS NULL",
            {"code": referral_code},
        )
        if referrer:
            referred_by_tailor_id = referrer["tailor_id"]

    user_id = uid("u")
    roles = ["tailor"]
    zone_id = body.zone_id or "tnagar"
    address_text = body.address_text
    shop_name = body.shop_name or f"{full_name.split()[0]}'s TailoraHub Studio"
    expertise = [x.strip() for x in body.expertise if x and x.strip()] or ["Custom stitching"]
    years_int = int(max(0, Decimal(body.experience_years_base)))
    services = body.services or []

    try:
        await db.execute(
            text(
                """INSERT INTO users (id,name,phone,email,password_hash,roles,zone_id,address,lat,lng,status)
                   VALUES (:id,:name,:phone,:email,:password_hash,CAST(:roles AS text[]),:zone_id,:address,:lat,:lng,'ACTIVE')"""
            ),
            {
                "id": user_id,
                "name": full_name,
                "phone": phone,
                "email": email,
                "password_hash": hash_password(body.password),
                "roles": roles,
                "zone_id": zone_id,
                "address": address_text,
                "lat": body.latitude,
                "lng": body.longitude,
            },
        )

        result = await db.execute(
            text(
                """INSERT INTO tailors (
                    id,user_id,shop,owner_name,zone_id,shop_address,lat,lng,expertise,years,bio,documents,
                    full_name,phone_number,email,username,dob,aadhaar_number_hash,aadhaar_number_encrypted,aadhaar_verified,
                    password_hash,experience_years_base,stitching_since_date,terms_accepted,terms_accepted_at,
                    referral_code,referred_by_tailor_id,status,approval_status,verified,account_status
                  ) VALUES (
                    :id,:user_id,:shop,:owner,:zone_id,:address,:lat,:lng,CAST(:expertise AS text[]),:years,:bio,CAST(:documents AS jsonb),
                    :full_name,:phone,:email,:username,:dob,:aadhaar_hash,:aadhaar_encrypted,TRUE,
                    :password_hash,:experience_years,:stitching_since,TRUE,now(),
                    :referral_code,:referred_by,'active','PENDING_APPROVAL',FALSE,'ACTIVE'
                  )
                  RETURNING *"""
            ),
            {
                "id": uid("t"),
                "user_id": user_id,
                "shop": shop_name,
                "owner": full_name,
                "zone_id": zone_id,
                "address": address_text,
                "lat": body.latitude,
                "lng": body.longitude,
                "expertise": expertise,
                "years": years_int,
                "bio": body.bio,
                "documents": json.dumps({"aadhaarVerified": True, "gender": gender}),
                "full_name": full_name,
                "phone": phone,
                "email": email,
                "username": username,
                "dob": body.dob,
                "aadhaar_hash": aadhaar_hash,
                "aadhaar_encrypted": encrypt_aadhaar(aadhaar),
                "password_hash": hash_password(body.password),
                "experience_years": body.experience_years_base,
                "stitching_since": body.stitching_since_date,
                "referral_code": await generate_tailor_referral_code(db),
                "referred_by": referred_by_tailor_id,
            },
        )
        tailor = dict(result.mappings().first())

        location_body = TailorLocationIn(
            address_text=body.address_text,
            latitude=body.latitude,
            longitude=body.longitude,
            confirmed=True,
        )
        await save_location_record(db, tailor, location_body, allow_update=False)

        if referred_by_tailor_id:
            await db.execute(
                text(
                    """INSERT INTO referrals (id, referrer_tailor_id, referred_tailor_id, referral_code_used)
                       VALUES (gen_random_uuid(), :referrer, :referred, :code)"""
                ),
                {"referrer": referred_by_tailor_id, "referred": tailor["tailor_id"], "code": referral_code},
            )

        wallet_id = uuid.uuid4()
        qr_url = generate_wallet_qr(str(wallet_id))
        await db.execute(
            text("INSERT INTO tailor_wallets (wallet_id, tailor_id, qr_code_url, balance) VALUES (:wallet_id, :tailor_id, :qr_url, 0)"),
            {"wallet_id": wallet_id, "tailor_id": tailor["tailor_id"], "qr_url": qr_url},
        )

        service_rows = services or [
            {
                "name": expertise[0],
                "garment_id": expertise[0].lower().replace(" ", "-"),
                "description": expertise[0] + " made to measure",
                "price": 500,
                "days": 5,
            }
        ]
        for service in service_rows:
            name = service.name if hasattr(service, "name") else service["name"]
            garment_id = (service.garment_id if hasattr(service, "garment_id") else service["garment_id"]) or name.lower().replace(" ", "-")
            description = service.description if hasattr(service, "description") else service["description"]
            price = service.price if hasattr(service, "price") else service["price"]
            days = service.days if hasattr(service, "days") else service["days"]
            await db.execute(
                text(
                    """INSERT INTO tailor_services (id,tailor_id,garment_id,name,description,price,days,service_name,is_active)
                       VALUES (:id,:tailor_id,:garment_id,CAST(:name AS TEXT),:description,:price,:days,CAST(:service_name AS VARCHAR(160)),TRUE)"""
                ),
                {
                    "id": uid("svc"),
                    "tailor_id": tailor["id"],
                    "garment_id": garment_id,
                    "name": name,
                    "service_name": name,
                    "description": description or f"{name} made to measure",
                    "price": price,
                    "days": days,
                },
            )

        user = await fetch_one(db, "SELECT * FROM users WHERE id=:id", {"id": user_id})
        await db.commit()
    except HTTPException:
        await db.rollback()
        raise
    except Exception:
        await db.rollback()
        raise

    tokens = await create_token_pair(db, user_id, roles)
    tokens.pop("_refresh_token_hash", None)
    await db.commit()
    return {
        **tokens,
        "role": "tailor",
        "user": public_user(user),
        "tailor": public_tailor(tailor),
        "tailor_id": tailor["tailor_id"],
        "wallet_id": wallet_id,
        "qr_code_url": qr_url,
        "tailorPending": True,
        "tailor_pending": True,
    }
