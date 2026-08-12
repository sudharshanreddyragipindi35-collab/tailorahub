from fastapi import APIRouter

from . import admin, auth, bookings, customers, otp, payments, referrals, services, tailors, wallet


api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(tailors.router, prefix="/tailors", tags=["tailors"])
api_router.include_router(customers.router, prefix="/customers", tags=["customers"])
api_router.include_router(otp.router, prefix="/otp", tags=["otp"])
api_router.include_router(wallet.router, prefix="/wallet", tags=["wallet"])
api_router.include_router(payments.router, prefix="/payments", tags=["payments"])
api_router.include_router(referrals.router, prefix="/referrals", tags=["referrals"])
api_router.include_router(services.router, prefix="/services", tags=["services"])
api_router.include_router(bookings.router, prefix="/bookings", tags=["bookings"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])


@api_router.get("/health", tags=["system"])
async def api_v1_health() -> dict:
    return {"ok": True, "api": "v1"}
