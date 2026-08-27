from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import ENUM, JSONB, UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class SchemaBase(DeclarativeBase):
    pass


# NOTE: these models mirror schema.sql (the app's real source of truth,
# executed directly via app/db.py:run_schema()) closely enough for Alembic
# autogenerate to produce sane diffs -- main.py itself never imports this
# module and runs entirely on raw SQL. Customer identity is the existing
# role-based `users` table, and booking/order state is the existing `orders`
# table; no parallel ORM-only customers/bookings tables are introduced.


class TailorRegistrationStatus(str, Enum):
    pending_verification = "pending_verification"
    active = "active"
    suspended = "suspended"


class WalletTransactionType(str, Enum):
    credit = "credit"
    debit = "debit"


class WalletTransactionStatus(str, Enum):
    pending = "pending"
    success = "success"
    failed = "failed"


class WithdrawalDestinationType(str, Enum):
    bank_account = "bank_account"
    upi_id = "upi_id"


class OtpPurpose(str, Enum):
    registration_phone = "registration_phone"
    registration_email = "registration_email"
    login = "login"
    forgot_password = "forgot_password"
    delivery = "delivery"
    withdrawal = "withdrawal"


class BookingStatus(str, Enum):
    searching = "searching"
    waiting_list = "waiting_list"
    auto_approved = "auto_approved"
    tailor_confirmed = "tailor_confirmed"
    measurement_pending = "measurement_pending"
    measurement_done = "measurement_done"
    in_progress = "in_progress"
    ready_for_delivery = "ready_for_delivery"
    out_for_delivery = "out_for_delivery"
    payment_pending = "payment_pending"
    paid = "paid"
    delivered = "delivered"
    completed = "completed"
    disputed = "disputed"
    cancelled = "cancelled"


class BookingMeasurementMode(str, Enum):
    tailor_visits_customer = "tailor_visits_customer"
    customer_visits_tailor = "customer_visits_tailor"


class BookingTrackerStage(str, Enum):
    order_placed = "Order Placed"
    measurement_scheduled = "Measurement Scheduled"
    measurement_done = "Measurement Done"
    stitching_in_progress = "Stitching in Progress"
    ready_for_delivery = "Ready for Delivery"
    out_for_delivery = "Out for Delivery"
    delivered = "Delivered"


class PaymentMethodSelection(str, Enum):
    cash = "cash"
    wallet = "wallet"
    qr = "qr"


class BookingPaymentStatus(str, Enum):
    pending = "pending"
    paid = "paid"
    failed = "failed"


class DisputeStatus(str, Enum):
    open = "open"
    in_review = "in_review"
    resolved = "resolved"
    rejected = "rejected"


class AdminWalletTransactionType(str, Enum):
    commission = "commission"
    gst_platform_charge = "gst_platform_charge"


class Tailor(SchemaBase):
    __tablename__ = "tailors"

    tailor_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    full_name: Mapped[str | None] = mapped_column(String(160))
    phone_number: Mapped[str | None] = mapped_column(String(10), unique=True)
    email: Mapped[str | None] = mapped_column(String(255), unique=True)
    dob: Mapped[date | None] = mapped_column(Date)
    aadhaar_number_hash: Mapped[str | None] = mapped_column(String(128), unique=True)
    aadhaar_number_encrypted: Mapped[str | None] = mapped_column(Text)
    aadhaar_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    username: Mapped[str | None] = mapped_column(String(80), unique=True)
    password_hash: Mapped[str | None] = mapped_column(String(255))
    bio: Mapped[str | None] = mapped_column(Text)
    experience_years_base: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0, nullable=False)
    stitching_since_date: Mapped[date | None] = mapped_column(Date)
    experience_display: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    terms_accepted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    terms_accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    referral_code: Mapped[str | None] = mapped_column(String(40), unique=True)
    referred_by_tailor_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("tailors.tailor_id"))
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    status: Mapped[TailorRegistrationStatus] = mapped_column(
        ENUM(TailorRegistrationStatus, name="tailor_registration_status", create_type=False),
        default=TailorRegistrationStatus.pending_verification,
        nullable=False,
    )
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class TailorLocation(SchemaBase):
    __tablename__ = "tailor_locations"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    tailor_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("tailors.tailor_id"), nullable=False)
    address_text: Mapped[str | None] = mapped_column(Text)
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 7))
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 7))
    is_fixed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class TailorWallet(SchemaBase):
    __tablename__ = "tailor_wallets"

    wallet_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    tailor_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("tailors.tailor_id"), unique=True, nullable=False)
    upi_id: Mapped[str | None] = mapped_column(String(160))
    bank_account_number: Mapped[str | None] = mapped_column(Text)
    bank_ifsc: Mapped[str | None] = mapped_column(String(20))
    qr_code_url: Mapped[str | None] = mapped_column(Text)
    balance: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class WalletTransaction(SchemaBase):
    __tablename__ = "wallet_transactions"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    wallet_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("tailor_wallets.wallet_id"), nullable=False)
    type: Mapped[WalletTransactionType] = mapped_column(ENUM(WalletTransactionType, name="wallet_transaction_type", create_type=False), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    reference_booking_id: Mapped[str | None] = mapped_column(Text)
    status: Mapped[WalletTransactionStatus] = mapped_column(ENUM(WalletTransactionStatus, name="wallet_transaction_status", create_type=False), default=WalletTransactionStatus.pending, nullable=False)
    withdrawal_destination: Mapped[WithdrawalDestinationType | None] = mapped_column(ENUM(WithdrawalDestinationType, name="withdrawal_destination_type", create_type=False))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Referral(SchemaBase):
    __tablename__ = "referrals"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    referrer_tailor_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("tailors.tailor_id"), nullable=False)
    referred_tailor_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("tailors.tailor_id"), nullable=False)
    referral_code_used: Mapped[str] = mapped_column(String(40), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class TailorService(SchemaBase):
    __tablename__ = "tailor_services"

    service_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    tailor_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    service_name: Mapped[str | None] = mapped_column(String(160))
    category: Mapped[str | None] = mapped_column(String(80))
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    is_combo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    combo_items: Mapped[dict | list | None] = mapped_column(JSONB)
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class OtpVerification(SchemaBase):
    __tablename__ = "otp_verifications"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    target: Mapped[str] = mapped_column(String(255), nullable=False)
    otp_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    purpose: Mapped[OtpPurpose] = mapped_column(ENUM(OtpPurpose, name="otp_purpose", create_type=False), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class RefreshSession(SchemaBase):
    __tablename__ = "refresh_sessions"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    user_id: Mapped[str] = mapped_column(Text, nullable=False)
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    replaced_by_token_hash: Mapped[str | None] = mapped_column(String(128))
    last_activity_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Customer(SchemaBase):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    customer_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    phone: Mapped[str] = mapped_column(String(10), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255))
    password_hash: Mapped[str | None] = mapped_column(String(255))
    terms_accepted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    referral_code: Mapped[str | None] = mapped_column(String(40), unique=True)
    referred_by_customer_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))
    joined: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class CustomerWallet(SchemaBase):
    __tablename__ = "customer_wallets"

    wallet_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    # References users.customer_id (the "customer identity" UUID folded onto
    # the existing users table -- see schema.sql's "Build step 01b"); users
    # isn't modeled in this file, so no ORM-level ForeignKey here.
    customer_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), unique=True, nullable=False)
    balance: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class CustomerReferral(SchemaBase):
    __tablename__ = "customer_referrals"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    # Both reference users.customer_id -- see CustomerWallet.customer_id note.
    referrer_customer_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    referred_customer_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))
    referred_phone_number: Mapped[str] = mapped_column(String(10), nullable=False)
    is_valid: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    bonus_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Booking(SchemaBase):
    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    code: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    customer_id: Mapped[str] = mapped_column(Text, nullable=False)
    tailor_id: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, default="ACCEPTED", nullable=False)
    measurement_mode: Mapped[str] = mapped_column(Text, default="SHOP", nullable=False)
    measurement_done_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cloth_collected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    tracker_stage: Mapped[BookingTrackerStage] = mapped_column(ENUM(BookingTrackerStage, name="booking_tracker_stage", create_type=False), default=BookingTrackerStage.order_placed, nullable=False)
    customer_location_address: Mapped[str | None] = mapped_column(Text)
    customer_location_lat: Mapped[Decimal | None] = mapped_column(Numeric(10, 7))
    customer_location_lng: Mapped[Decimal | None] = mapped_column(Numeric(10, 7))
    customer_location_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delivery_otp_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    otp_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    payment_method_selected: Mapped[PaymentMethodSelection | None] = mapped_column(ENUM(PaymentMethodSelection, name="payment_method_selection", create_type=False))
    payment_method_selected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    payment_status: Mapped[str] = mapped_column(Text, default="PENDING", nullable=False)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    commission_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    gst_platform_charge_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    dispute_raised: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Dispute(SchemaBase):
    __tablename__ = "disputes"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    # References orders.id / users.id (both TEXT, legacy tables not modeled
    # here) -- see the module note at the top of this file.
    booking_id: Mapped[str] = mapped_column(Text, nullable=False)
    customer_id: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    photo_url: Mapped[str | None] = mapped_column(Text)
    photo_name: Mapped[str | None] = mapped_column(Text)
    photo_media_type: Mapped[str | None] = mapped_column(Text)
    status: Mapped[DisputeStatus] = mapped_column(ENUM(DisputeStatus, name="dispute_status_type", create_type=False), default=DisputeStatus.open, nullable=False)
    resolution_notes: Mapped[str | None] = mapped_column(Text)
    refund_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AdminWallet(SchemaBase):
    __tablename__ = "admin_wallet"

    wallet_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    balance: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AdminWalletTransaction(SchemaBase):
    __tablename__ = "admin_wallet_transactions"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    type: Mapped[AdminWalletTransactionType] = mapped_column(ENUM(AdminWalletTransactionType, name="admin_wallet_transaction_type", create_type=False), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    # References orders.id / users.id (TEXT, legacy tables not modeled here).
    source_booking_id: Mapped[str] = mapped_column(Text, nullable=False)
    source_tailor_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("tailors.tailor_id"))
    source_customer_id: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class PlatformSettings(SchemaBase):
    __tablename__ = "platform_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    commission_percentage: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("20.00"), nullable=False)
    gst_percentage: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("18.00"), nullable=False)
    platform_fee_percentage: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("2.00"), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_by_admin_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True))
