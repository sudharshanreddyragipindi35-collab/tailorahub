from __future__ import annotations

import csv
from datetime import date
from decimal import Decimal
from io import StringIO

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.core.database import get_db
from app.schemas.admin import PlatformSettingsIn


router = APIRouter()
DISPUTE_STATUSES = {"open", "in_review", "resolved", "rejected"}


class AdminDisputePatchIn(BaseModel):
    status: str
    resolution_notes: str | None = Field(default=None, alias="resolutionNotes")
    refund_amount: Decimal | None = Field(default=None, alias="refundAmount", ge=0)


def money_decimal(value) -> Decimal:
    return Decimal(str(value or 0)).quantize(Decimal("0.01"))


@router.get("/scaffold")
async def admin_scaffold(_: dict = Depends(require_admin)) -> dict:
    return {"module": "admin", "ready": True}


@router.get("/finance/settings")
async def finance_settings(
    _: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    settings = await _ensure_platform_settings(db)
    await db.commit()
    return _settings_payload(settings)


@router.patch("/finance/settings")
async def update_finance_settings(
    body: PlatformSettingsIn,
    _: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    result = await db.execute(
        text(
            """
            INSERT INTO platform_settings
              (id,commission_percentage,gst_percentage,platform_fee_percentage,updated_at)
            VALUES
              (1,:commission,:gst,:platform_fee,now())
            ON CONFLICT (id) DO UPDATE SET
              commission_percentage=EXCLUDED.commission_percentage,
              gst_percentage=EXCLUDED.gst_percentage,
              platform_fee_percentage=EXCLUDED.platform_fee_percentage,
              updated_at=now()
            RETURNING *
            """
        ),
        {
            "commission": body.commission_percentage,
            "gst": body.gst_percentage,
            "platform_fee": body.platform_fee_percentage,
        },
    )
    await db.commit()
    return _settings_payload(dict(result.mappings().first()))


@router.get("/finance/wallet")
async def finance_wallet(
    date_from: date | None = Query(default=None, alias="dateFrom"),
    date_to: date | None = Query(default=None, alias="dateTo"),
    _: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    wallet = await _ensure_admin_wallet(db)
    totals, transactions = await _admin_wallet_transactions(db, date_from, date_to)
    await db.commit()
    return _admin_wallet_payload(wallet, totals, transactions)


@router.get("/finance/wallet/export")
async def finance_wallet_export(
    date_from: date | None = Query(default=None, alias="dateFrom"),
    date_to: date | None = Query(default=None, alias="dateTo"),
    _: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> Response:
    _, transactions = await _admin_wallet_transactions(db, date_from, date_to)
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "type", "amount", "order_code", "source_booking_id", "tailor", "customer", "created_at"])
    for row in transactions:
        writer.writerow([
            row["id"],
            row["type"],
            row["amount"],
            row.get("orderCode") or row.get("order_code"),
            row.get("sourceBookingId") or row.get("source_booking_id"),
            row.get("shop") or "",
            row.get("customerName") or row.get("customer_name") or "",
            row.get("createdAt") or row.get("created_at") or "",
        ])
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=admin-wallet-transactions.csv"},
    )


def _node_from_row(row: dict) -> dict:
    tailor_uuid = str(row["tailor_id"])
    return {
        "tailor_id": tailor_uuid,
        "tailorId": tailor_uuid,
        "legacy_id": row.get("legacy_id"),
        "legacyId": row.get("legacy_id"),
        "shop": row.get("shop"),
        "owner_name": row.get("owner_name"),
        "ownerName": row.get("owner_name"),
        "full_name": row.get("full_name"),
        "fullName": row.get("full_name"),
        "email": row.get("email"),
        "phone_number": row.get("phone_number"),
        "phoneNumber": row.get("phone_number"),
        "referral_code": row.get("referral_code"),
        "referralCode": row.get("referral_code"),
        "referred_by_tailor_id": str(row["referred_by_tailor_id"]) if row.get("referred_by_tailor_id") else None,
        "referredByTailorId": str(row["referred_by_tailor_id"]) if row.get("referred_by_tailor_id") else None,
        "depth": int(row.get("depth") or 0),
        "joined_at": row.get("joined_at").isoformat() if row.get("joined_at") else None,
        "joinedAt": row.get("joined_at").isoformat() if row.get("joined_at") else None,
        "children": [],
    }


def _customer_node_from_row(row: dict) -> dict:
    customer_uuid = str(row["customer_id"])
    return {
        "customer_id": customer_uuid,
        "customerId": customer_uuid,
        "id": row.get("id"),
        "name": row.get("name"),
        "email": row.get("email"),
        "phone": row.get("phone"),
        "profile_image": row.get("profile_image"),
        "profileImage": row.get("profile_image"),
        "referral_code": row.get("referral_code"),
        "referralCode": row.get("referral_code"),
        "referred_by_customer_id": str(row["referred_by_customer_id"]) if row.get("referred_by_customer_id") else None,
        "referredByCustomerId": str(row["referred_by_customer_id"]) if row.get("referred_by_customer_id") else None,
        "depth": int(row.get("depth") or 0),
        "joined_at": row.get("joined_at").isoformat() if row.get("joined_at") else None,
        "joinedAt": row.get("joined_at").isoformat() if row.get("joined_at") else None,
        "children": [],
    }


def _dispute_payload(row: dict) -> dict:
    dispute_id = str(row["id"])
    return {
        "id": dispute_id,
        "booking_id": row.get("booking_id"),
        "bookingId": row.get("booking_id"),
        "order_code": row.get("order_code"),
        "orderCode": row.get("order_code"),
        "booking_status": row.get("booking_status"),
        "bookingStatus": row.get("booking_status"),
        "customer_id": row.get("customer_id"),
        "customerId": row.get("customer_id"),
        "customer_name": row.get("customer_name"),
        "customerName": row.get("customer_name"),
        "customer_phone": row.get("customer_phone"),
        "customerPhone": row.get("customer_phone"),
        "customer_email": row.get("customer_email"),
        "customerEmail": row.get("customer_email"),
        "tailor_id": row.get("tailor_id"),
        "tailorId": row.get("tailor_id"),
        "shop": row.get("shop"),
        "owner_name": row.get("owner_name"),
        "ownerName": row.get("owner_name"),
        "reason": row.get("reason"),
        "photo_url": row.get("photo_url"),
        "photoUrl": row.get("photo_url"),
        "photo_name": row.get("photo_name"),
        "photoName": row.get("photo_name"),
        "photo_media_type": row.get("photo_media_type"),
        "photoMediaType": row.get("photo_media_type"),
        "status": row.get("status"),
        "resolution_notes": row.get("resolution_notes"),
        "resolutionNotes": row.get("resolution_notes"),
        "refund_amount": row.get("refund_amount") or 0,
        "refundAmount": row.get("refund_amount") or 0,
        "created_at": row.get("created_at"),
        "createdAt": row.get("created_at"),
        "updated_at": row.get("updated_at"),
        "updatedAt": row.get("updated_at"),
        "resolved_at": row.get("resolved_at"),
        "resolvedAt": row.get("resolved_at"),
    }


def _settings_payload(row: dict) -> dict:
    return {
        "id": row.get("id", 1),
        "commission_percentage": row.get("commission_percentage"),
        "commissionPercentage": row.get("commission_percentage"),
        "gst_percentage": row.get("gst_percentage"),
        "gstPercentage": row.get("gst_percentage"),
        "platform_fee_percentage": row.get("platform_fee_percentage"),
        "platformFeePercentage": row.get("platform_fee_percentage"),
        "updated_at": row.get("updated_at"),
        "updatedAt": row.get("updated_at"),
    }


def _admin_wallet_payload(wallet: dict | None, totals: dict, transactions: list[dict]) -> dict:
    balance = wallet.get("balance") if wallet else 0
    return {
        "wallet_id": str(wallet["wallet_id"]) if wallet else None,
        "walletId": str(wallet["wallet_id"]) if wallet else None,
        "balance": balance or 0,
        "commission_total": totals.get("commission_total") or 0,
        "commissionTotal": totals.get("commission_total") or 0,
        "gst_platform_charge_total": totals.get("gst_platform_charge_total") or 0,
        "gstPlatformChargeTotal": totals.get("gst_platform_charge_total") or 0,
        "transactions": transactions,
    }


def _admin_wallet_tx_payload(row: dict) -> dict:
    return {
        "id": str(row["id"]),
        "type": row.get("type"),
        "amount": row.get("amount"),
        "source_booking_id": row.get("source_booking_id"),
        "sourceBookingId": row.get("source_booking_id"),
        "order_code": row.get("order_code"),
        "orderCode": row.get("order_code"),
        "source_tailor_id": str(row["source_tailor_id"]) if row.get("source_tailor_id") else None,
        "sourceTailorId": str(row["source_tailor_id"]) if row.get("source_tailor_id") else None,
        "source_customer_id": row.get("source_customer_id"),
        "sourceCustomerId": row.get("source_customer_id"),
        "shop": row.get("shop"),
        "customer_name": row.get("customer_name"),
        "customerName": row.get("customer_name"),
        "created_at": row.get("created_at"),
        "createdAt": row.get("created_at"),
    }


async def _ensure_platform_settings(db: AsyncSession) -> dict:
    result = await db.execute(
        text("INSERT INTO platform_settings (id) VALUES (1) ON CONFLICT (id) DO UPDATE SET id=EXCLUDED.id RETURNING *")
    )
    return dict(result.mappings().first())


async def _ensure_admin_wallet(db: AsyncSession) -> dict:
    ledger_balance = await _admin_wallet_ledger_balance(db)
    wallet = await db.execute(text("SELECT * FROM admin_wallet ORDER BY updated_at ASC LIMIT 1"))
    row = wallet.mappings().first()
    if row:
        wallet_row = dict(row)
        if money_decimal(wallet_row.get("balance")) != ledger_balance:
            result = await db.execute(
                text("UPDATE admin_wallet SET balance=:balance, updated_at=now() WHERE wallet_id=:wallet_id RETURNING *"),
                {"balance": ledger_balance, "wallet_id": wallet_row["wallet_id"]},
            )
            return dict(result.mappings().first())
        return wallet_row
    result = await db.execute(
        text("INSERT INTO admin_wallet (wallet_id,balance,updated_at) VALUES (gen_random_uuid(),:balance,now()) RETURNING *"),
        {"balance": ledger_balance},
    )
    return dict(result.mappings().first())


async def _admin_wallet_ledger_balance(db: AsyncSession) -> Decimal:
    result = await db.execute(text("SELECT COALESCE(SUM(amount),0) AS balance FROM admin_wallet_transactions"))
    row = result.mappings().first()
    return money_decimal(row["balance"] if row else 0)


async def _admin_wallet_transactions(db: AsyncSession, date_from: date | None, date_to: date | None) -> tuple[dict, list[dict]]:
    params = {"date_from": date_from, "date_to": date_to}
    totals_result = await db.execute(
        text(
            """
            SELECT
              COALESCE(SUM(CASE WHEN type='commission' THEN amount ELSE 0 END),0) AS commission_total,
              COALESCE(SUM(CASE WHEN type='gst_platform_charge' THEN amount ELSE 0 END),0) AS gst_platform_charge_total
            FROM admin_wallet_transactions
            WHERE (CAST(:date_from AS date) IS NULL OR created_at::date >= CAST(:date_from AS date))
              AND (CAST(:date_to AS date) IS NULL OR created_at::date <= CAST(:date_to AS date))
            """
        ),
        params,
    )
    totals = dict(totals_result.mappings().first() or {})
    rows_result = await db.execute(
        text(
            """
            SELECT
              awt.*,
              o.code AS order_code,
              t.shop,
              u.name AS customer_name
            FROM admin_wallet_transactions awt
            LEFT JOIN orders o ON o.id=awt.source_booking_id
            LEFT JOIN tailors t ON t.tailor_id=awt.source_tailor_id
            LEFT JOIN users u ON u.id=awt.source_customer_id
            WHERE (CAST(:date_from AS date) IS NULL OR awt.created_at::date >= CAST(:date_from AS date))
              AND (CAST(:date_to AS date) IS NULL OR awt.created_at::date <= CAST(:date_to AS date))
            ORDER BY awt.created_at DESC
            """
        ),
        params,
    )
    transactions = [_admin_wallet_tx_payload(dict(row)) for row in rows_result.mappings().all()]
    return totals, transactions


@router.get("/referrals/tree/{tailor_id}")
async def referral_tree(
    tailor_id: str,
    _: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    root_result = await db.execute(
        text(
            """
            SELECT tailor_id
            FROM tailors
            WHERE tailor_id::text=:tailor_id OR id=:tailor_id
            LIMIT 1
            """
        ),
        {"tailor_id": tailor_id},
    )
    root_uuid = root_result.scalar_one_or_none()
    if not root_uuid:
        raise HTTPException(status_code=404, detail="Tailor not found")

    result = await db.execute(
        text(
            """
            WITH RECURSIVE referral_tree AS (
              SELECT
                t.tailor_id,
                t.id AS legacy_id,
                t.shop,
                t.owner_name,
                t.full_name,
                t.email,
                t.phone_number,
                t.referral_code,
                t.referred_by_tailor_id,
                NULL::uuid AS parent_tailor_id,
                0::int AS depth,
                ARRAY[t.tailor_id] AS path,
                COALESCE(t.created_at, t.created) AS joined_at
              FROM tailors t
              WHERE t.tailor_id=:root_uuid

              UNION ALL

              SELECT
                child.tailor_id,
                child.id AS legacy_id,
                child.shop,
                child.owner_name,
                child.full_name,
                child.email,
                child.phone_number,
                child.referral_code,
                child.referred_by_tailor_id,
                parent.tailor_id AS parent_tailor_id,
                parent.depth + 1 AS depth,
                parent.path || child.tailor_id AS path,
                COALESCE(child.created_at, child.created) AS joined_at
              FROM tailors child
              JOIN referral_tree parent
                ON (
                  child.referred_by_tailor_id=parent.tailor_id
                  OR EXISTS (
                    SELECT 1
                    FROM referrals r
                    WHERE r.referrer_tailor_id=parent.tailor_id
                      AND r.referred_tailor_id=child.tailor_id
                  )
                )
              WHERE NOT child.tailor_id = ANY(parent.path)
            )
            SELECT
              tailor_id,
              legacy_id,
              shop,
              owner_name,
              full_name,
              email,
              phone_number,
              referral_code,
              referred_by_tailor_id,
              parent_tailor_id,
              depth,
              joined_at
            FROM referral_tree
            ORDER BY depth, shop, owner_name
            """
        ),
        {"root_uuid": root_uuid},
    )
    rows = [dict(row) for row in result.mappings().all()]
    nodes: dict[str, dict] = {}
    parent_ids: dict[str, str | None] = {}
    root_key = str(root_uuid)

    for row in rows:
        key = str(row["tailor_id"])
        if key in nodes:
            continue
        nodes[key] = _node_from_row(row)
        parent_ids[key] = str(row["parent_tailor_id"]) if row.get("parent_tailor_id") else None

    for key, node in nodes.items():
        if key == root_key:
            continue
        parent_key = parent_ids.get(key)
        if parent_key and parent_key in nodes:
            nodes[parent_key]["children"].append(node)

    for node in nodes.values():
        node["direct_referrals"] = len(node["children"])
        node["directReferrals"] = len(node["children"])

    return {
        "root_tailor_id": root_key,
        "rootTailorId": root_key,
        "total_tailors": len(nodes),
        "totalTailors": len(nodes),
        "tree": nodes.get(root_key),
    }


@router.get("/customer-referrals/tree/{customer_id}")
async def customer_referral_tree(
    customer_id: str,
    _: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    root_result = await db.execute(
        text(
            """
            SELECT customer_id
            FROM users
            WHERE (customer_id::text=:customer_id OR id=:customer_id)
              AND 'customer'=ANY(roles)
              AND status <> 'DELETED'
            LIMIT 1
            """
        ),
        {"customer_id": customer_id},
    )
    root_uuid = root_result.scalar_one_or_none()
    if not root_uuid:
        raise HTTPException(status_code=404, detail="Customer not found")

    result = await db.execute(
        text(
            """
            WITH RECURSIVE referral_tree AS (
              SELECT
                u.customer_id,
                u.id,
                u.name,
                u.email,
                u.phone,
                u.profile_image,
                u.referral_code,
                u.referred_by_customer_id,
                NULL::uuid AS parent_customer_id,
                0::int AS depth,
                ARRAY[u.customer_id] AS path,
                u.joined AS joined_at
              FROM users u
              WHERE u.customer_id=:root_uuid

              UNION ALL

              SELECT
                child.customer_id,
                child.id,
                child.name,
                child.email,
                child.phone,
                child.profile_image,
                child.referral_code,
                child.referred_by_customer_id,
                parent.customer_id AS parent_customer_id,
                parent.depth + 1 AS depth,
                parent.path || child.customer_id AS path,
                child.joined AS joined_at
              FROM users child
              JOIN referral_tree parent
                ON (
                  child.referred_by_customer_id=parent.customer_id
                  OR EXISTS (
                    SELECT 1
                    FROM customer_referrals cr
                    WHERE cr.referrer_customer_id=parent.customer_id
                      AND cr.referred_customer_id=child.customer_id
                      AND cr.is_valid=TRUE
                  )
                )
              WHERE 'customer'=ANY(child.roles)
                AND child.status <> 'DELETED'
                AND NOT child.customer_id = ANY(parent.path)
            )
            SELECT
              customer_id,
              id,
              name,
              email,
              phone,
              profile_image,
              referral_code,
              referred_by_customer_id,
              parent_customer_id,
              depth,
              joined_at
            FROM referral_tree
            ORDER BY depth, name
            """
        ),
        {"root_uuid": root_uuid},
    )
    rows = [dict(row) for row in result.mappings().all()]
    nodes: dict[str, dict] = {}
    parent_ids: dict[str, str | None] = {}
    root_key = str(root_uuid)

    for row in rows:
        key = str(row["customer_id"])
        if key in nodes:
            continue
        nodes[key] = _customer_node_from_row(row)
        parent_ids[key] = str(row["parent_customer_id"]) if row.get("parent_customer_id") else None

    for key, node in nodes.items():
        if key == root_key:
            continue
        parent_key = parent_ids.get(key)
        if parent_key and parent_key in nodes:
            nodes[parent_key]["children"].append(node)

    for node in nodes.values():
        node["valid_referrals"] = len(node["children"])
        node["validReferrals"] = len(node["children"])

    return {
        "root_customer_id": root_key,
        "rootCustomerId": root_key,
        "total_customers": len(nodes),
        "totalCustomers": len(nodes),
        "tree": nodes.get(root_key),
    }


@router.get("/disputes")
async def dispute_queue(
    _: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    result = await db.execute(
        text(
            """
            SELECT
              d.*,
              o.code AS order_code,
              o.status AS booking_status,
              o.tailor_id,
              u.name AS customer_name,
              u.phone AS customer_phone,
              u.email AS customer_email,
              t.shop,
              t.owner_name
            FROM disputes d
            JOIN orders o ON o.id=d.booking_id
            JOIN users u ON u.id=d.customer_id
            LEFT JOIN tailors t ON t.id=o.tailor_id
            ORDER BY
              CASE d.status
                WHEN 'open' THEN 1
                WHEN 'in_review' THEN 2
                WHEN 'resolved' THEN 3
                ELSE 4
              END,
              d.created_at DESC
            """
        )
    )
    return [_dispute_payload(dict(row)) for row in result.mappings().all()]


@router.patch("/disputes/{dispute_id}")
async def update_dispute(
    dispute_id: str,
    body: AdminDisputePatchIn,
    _: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    status = body.status.strip().lower()
    if status not in DISPUTE_STATUSES:
        raise HTTPException(400, "Invalid dispute status")
    dispute_result = await db.execute(
        text(
            """
            SELECT d.*, o.code AS order_code, o.status AS booking_status, o.tailor_id,
                   u.customer_id AS customer_uuid, u.name AS customer_name, u.phone AS customer_phone, u.email AS customer_email,
                   t.shop, t.owner_name
            FROM disputes d
            JOIN orders o ON o.id=d.booking_id
            JOIN users u ON u.id=d.customer_id
            LEFT JOIN tailors t ON t.id=o.tailor_id
            WHERE d.id=:id
            FOR UPDATE OF d
            """
        ),
        {"id": dispute_id},
    )
    dispute = dict(dispute_result.mappings().first() or {})
    if not dispute:
        raise HTTPException(404, "Dispute not found")

    existing_refund = Decimal(str(dispute.get("refund_amount") or 0))
    requested_refund = body.refund_amount
    if requested_refund is not None and requested_refund > existing_refund:
        credit_amount = requested_refund - existing_refund
        await db.execute(
            text(
                """
                INSERT INTO customer_wallets (wallet_id,customer_id,balance,created_at,updated_at)
                VALUES (gen_random_uuid(),:customer_id,0,now(),now())
                ON CONFLICT (customer_id) DO NOTHING
                """
            ),
            {"customer_id": dispute["customer_uuid"]},
        )
        await db.execute(
            text("UPDATE customer_wallets SET balance=balance + :amount, updated_at=now() WHERE customer_id=:customer_id"),
            {"amount": credit_amount, "customer_id": dispute["customer_uuid"]},
        )

    await db.execute(
        text(
            """
            UPDATE disputes
            SET status=CAST(:status AS dispute_status_type),
                resolution_notes=COALESCE(:resolution_notes,resolution_notes),
                refund_amount=COALESCE(:refund_amount,refund_amount),
                updated_at=now(),
                resolved_at=CASE WHEN :status IN ('resolved','rejected') THEN now() ELSE NULL END
            WHERE id=:id
            """
        ),
        {
            "id": dispute_id,
            "status": status,
            "resolution_notes": body.resolution_notes,
            "refund_amount": requested_refund,
        },
    )
    if status in {"resolved", "rejected"}:
        await db.execute(
            text(
                """
                UPDATE orders
                SET status=CASE
                  WHEN status='disputed' AND (tracker_stage='Delivered' OR delivered_at IS NOT NULL OR completed_at IS NOT NULL)
                    THEN 'completed'
                  ELSE status
                END
                WHERE id=:booking_id
                """
            ),
            {"booking_id": dispute["booking_id"]},
        )
    await db.commit()
    updated = await db.execute(
        text(
            """
            SELECT
              d.*,
              o.code AS order_code,
              o.status AS booking_status,
              o.tailor_id,
              u.name AS customer_name,
              u.phone AS customer_phone,
              u.email AS customer_email,
              t.shop,
              t.owner_name
            FROM disputes d
            JOIN orders o ON o.id=d.booking_id
            JOIN users u ON u.id=d.customer_id
            LEFT JOIN tailors t ON t.id=o.tailor_id
            WHERE d.id=:id
            """
        ),
        {"id": dispute_id},
    )
    return _dispute_payload(dict(updated.mappings().first()))
