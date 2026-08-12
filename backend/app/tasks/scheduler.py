from __future__ import annotations

from apscheduler.schedulers.asyncio import AsyncIOScheduler


scheduler = AsyncIOScheduler(timezone="Asia/Kolkata")


async def recalculate_tailor_experience() -> None:
    """Future job: update cached experience_display values if needed."""


async def cleanup_expired_otps() -> None:
    """Future job: remove expired OTP rows from Redis/PostgreSQL."""


async def reconcile_wallets() -> None:
    """Future job: reconcile wallet balances against transaction history."""


def configure_jobs() -> AsyncIOScheduler:
    if not scheduler.get_jobs():
        scheduler.add_job(cleanup_expired_otps, "interval", minutes=15, id="cleanup_expired_otps")
        scheduler.add_job(recalculate_tailor_experience, "cron", hour=0, minute=5, id="recalculate_tailor_experience")
        scheduler.add_job(reconcile_wallets, "cron", hour=1, minute=0, id="reconcile_wallets")
    return scheduler
