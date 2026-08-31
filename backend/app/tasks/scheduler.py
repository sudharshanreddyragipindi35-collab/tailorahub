from __future__ import annotations

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import text
from datetime import datetime, timezone

from app.core.database import AsyncSessionLocal
from app.tasks.queue import enqueue_task


scheduler = AsyncIOScheduler(timezone="Asia/Kolkata")


async def recalculate_tailor_experience() -> None:
    """Keep experience non-negative; detailed source dates remain authoritative."""
    async with AsyncSessionLocal() as db:
        await db.execute(text("UPDATE tailors SET years=GREATEST(COALESCE(years,0),0) WHERE years IS NULL OR years < 0"))
        await db.commit()


async def cleanup_expired_otps() -> None:
    """Remove expired short-lived security records after a small audit window."""
    async with AsyncSessionLocal() as db:
        await db.execute(
            text("DELETE FROM otp_verifications WHERE expires_at < now() - INTERVAL '1 day'")
        )
        await db.execute(
            text(
                """
                DELETE FROM refresh_sessions
                WHERE expires_at < now() - INTERVAL '7 days'
                   OR (revoked_at IS NOT NULL AND revoked_at < now() - INTERVAL '7 days')
                """
            )
        )
        await db.commit()


async def reconcile_wallets() -> None:
    """Idempotently reconcile tailor wallets against successful ledger entries."""
    async with AsyncSessionLocal() as db:
        await db.execute(text("""
            UPDATE tailor_wallets wallet
            SET balance=COALESCE(ledger.balance,0),updated_at=now()
            FROM (
              SELECT wallet_id,SUM(CASE WHEN type='credit' THEN amount ELSE -amount END) AS balance
              FROM wallet_transactions WHERE status='success' GROUP BY wallet_id
            ) ledger
            WHERE wallet.wallet_id=ledger.wallet_id AND wallet.balance IS DISTINCT FROM ledger.balance
        """))
        await db.commit()


async def reconcile_payments() -> None:
    """Idempotently expire stale payment intents for later gateway reconciliation."""
    async with AsyncSessionLocal() as db:
        await db.execute(text("UPDATE payment_intents SET status='expired',updated_at=now() WHERE status='pending' AND expires_at <= now()"))
        await db.commit()


async def expire_manual_booking_requests() -> None:
    """Expire unanswered manual approvals independently of any browser session."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            text("""
                UPDATE orders
                SET status='EXPIRED',status_reason='TAILOR_RESPONSE_TIMEOUT'
                WHERE status='PENDING_APPROVAL' AND expires_at IS NOT NULL AND expires_at <= now()
                RETURNING id,code,customer_id,tailor_id,request_group_id
            """)
        )
        expired = [dict(row) for row in result.mappings().all()]
        for order in expired:
            await db.execute(text("""UPDATE booking_request_groups g SET status='EXPIRED',closed_at=now()
                WHERE g.id=:group_id AND g.assigned_tailor_id IS NULL
                  AND NOT EXISTS (SELECT 1 FROM orders o WHERE o.request_group_id=g.id AND o.status IN ('PENDING_APPROVAL','WAITLISTED'))"""), {"group_id": order["request_group_id"]})
            await db.execute(text("""INSERT INTO notifications
                (id,to_ref,channel,title,body,order_id,notification_type,entity_type,entity_id,request_group_id,dedupe_key)
                VALUES ('ntf_' || substr(md5(random()::text),1,10),:to_ref,'in_app','Booking request expired',
                :body,:order_id,'BOOKING_EXPIRED','booking',:order_id,:group_id,:dedupe_key)
                ON CONFLICT (to_ref,dedupe_key) WHERE dedupe_key IS NOT NULL DO NOTHING"""), {
                    "to_ref": "user:" + order["customer_id"], "body": f"Booking {order['code']} was automatically cancelled because the tailor did not respond within one hour.",
                    "order_id": order["id"], "group_id": order["request_group_id"], "dedupe_key": "booking-expired:" + order["id"],
                })
        await db.commit()


SCHEDULED_HANDLERS = {
    "cleanup_expired_otps": cleanup_expired_otps,
    "recalculate_tailor_experience": recalculate_tailor_experience,
    "reconcile_wallets": reconcile_wallets,
    "reconcile_payments": reconcile_payments,
    "expire_manual_booking_requests": expire_manual_booking_requests,
}


def enqueue_scheduled(name: str, bucket: str) -> None:
    enqueue_task("scheduled_job", {"name": name}, f"schedule:{name}:{bucket}")


def configure_jobs() -> AsyncIOScheduler:
    if not scheduler.get_jobs():
        scheduler.add_job(lambda: enqueue_scheduled("cleanup_expired_otps", str(int(datetime.now(timezone.utc).timestamp()) // 900)), "interval", minutes=15, id="cleanup_expired_otps")
        scheduler.add_job(lambda: enqueue_scheduled("recalculate_tailor_experience", datetime.now(timezone.utc).strftime("%Y%m%d")), "cron", hour=0, minute=5, id="recalculate_tailor_experience")
        scheduler.add_job(lambda: enqueue_scheduled("reconcile_wallets", datetime.now(timezone.utc).strftime("%Y%m%d")), "cron", hour=1, minute=0, id="reconcile_wallets")
        scheduler.add_job(lambda: enqueue_scheduled("reconcile_payments", str(int(datetime.now(timezone.utc).timestamp()) // 300)), "interval", minutes=5, id="reconcile_payments")
        scheduler.add_job(lambda: enqueue_scheduled("expire_manual_booking_requests", str(int(datetime.now(timezone.utc).timestamp()) // 60)), "interval", minutes=1, id="expire_manual_booking_requests", max_instances=1, coalesce=True)
    return scheduler
