from __future__ import annotations

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import text

from app.core.database import AsyncSessionLocal


scheduler = AsyncIOScheduler(timezone="Asia/Kolkata")


async def recalculate_tailor_experience() -> None:
    """Future job: update cached experience_display values if needed."""


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
    """Future job: reconcile wallet balances against transaction history."""


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


def configure_jobs() -> AsyncIOScheduler:
    if not scheduler.get_jobs():
        scheduler.add_job(cleanup_expired_otps, "interval", minutes=15, id="cleanup_expired_otps")
        scheduler.add_job(recalculate_tailor_experience, "cron", hour=0, minute=5, id="recalculate_tailor_experience")
        scheduler.add_job(reconcile_wallets, "cron", hour=1, minute=0, id="reconcile_wallets")
        scheduler.add_job(expire_manual_booking_requests, "interval", minutes=1, id="expire_manual_booking_requests", max_instances=1, coalesce=True)
    return scheduler
