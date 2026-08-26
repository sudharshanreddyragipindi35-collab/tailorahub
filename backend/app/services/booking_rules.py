from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal, ROUND_HALF_UP
from zoneinfo import ZoneInfo


APP_TIMEZONE = ZoneInfo("Asia/Kolkata")
SLOT_BOUNDS: dict[str, tuple[time, time]] = {
    "08:00-10:00": (time(8), time(10)),
    "10:00-12:00": (time(10), time(12)),
    "12:00-14:00": (time(12), time(14)),
    "14:00-16:00": (time(14), time(16)),
    "16:00-18:00": (time(16), time(18)),
    "18:00-20:00": (time(18), time(20)),
    "20:00-22:00": (time(20), time(22)),
}
URGENT_RULES: dict[int, Decimal] = {
    1: Decimal("150.00"),
    2: Decimal("100.00"),
    3: Decimal("50.00"),
}


class BookingRuleError(ValueError):
    pass


@dataclass(frozen=True)
class BookingCalculation:
    unit_price: Decimal
    service_quantity: int
    garments_per_service: int
    total_garment_quantity: int
    base_amount: Decimal
    urgent_days: int | None
    urgent_charge: Decimal
    final_amount: Decimal
    delivery_deadline: datetime
    measurement_cutoff: datetime
    appointment_start: datetime
    appointment_end: datetime


def money(value: object) -> Decimal:
    return Decimal(str(value or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def combo_garment_count(is_combo: bool, combo_items: object) -> int:
    if not is_combo:
        return 1
    if isinstance(combo_items, list):
        count = len([item for item in combo_items if str(item).strip()])
        return max(2, count)
    return 2


def urgent_charge_for(urgent_days: int | None, total_garments: int, is_combo: bool) -> Decimal:
    if urgent_days is None:
        return Decimal("0.00")
    if urgent_days not in URGENT_RULES:
        raise BookingRuleError("Choose a valid urgent completion option.")
    return URGENT_RULES[urgent_days]


def zoned_slot(slot_date: date, slot_value: str) -> tuple[datetime, datetime]:
    bounds = SLOT_BOUNDS.get(slot_value)
    if not bounds:
        raise BookingRuleError("Choose a valid appointment time slot.")
    return (
        datetime.combine(slot_date, bounds[0], APP_TIMEZONE),
        datetime.combine(slot_date, bounds[1], APP_TIMEZONE),
    )


def calculate_booking(
    *,
    unit_price: object,
    service_quantity: int,
    is_combo: bool,
    combo_items: object,
    urgent_days: int | None,
    delivery_date: date,
    appointment_date: date,
    appointment_slot: str,
    now: datetime | None = None,
) -> BookingCalculation:
    current = (now or datetime.now(APP_TIMEZONE)).astimezone(APP_TIMEZONE)
    if service_quantity < 1:
        raise BookingRuleError("Quantity must be at least one.")
    if delivery_date < current.date() or appointment_date < current.date():
        raise BookingRuleError("Past delivery or measurement dates are not allowed.")
    if urgent_days is not None and delivery_date != current.date() + timedelta(days=max(0, urgent_days - 1)):
        raise BookingRuleError(f"Within {urgent_days} day completion requires the matching delivery date.")
    if appointment_date > delivery_date:
        raise BookingRuleError("Measurement appointment must be on or before the delivery date.")
    appointment_start, appointment_end = zoned_slot(appointment_date, appointment_slot)
    if appointment_start <= current:
        raise BookingRuleError("Selected appointment time slot has already expired. Choose a later slot.")
    garments_per_service = combo_garment_count(is_combo, combo_items)
    total_garments = service_quantity * garments_per_service
    charge = urgent_charge_for(urgent_days, total_garments, is_combo)
    unit = money(unit_price)
    base = money(unit * service_quantity)
    final = money(base + charge)
    delivery_deadline = datetime.combine(delivery_date + timedelta(days=1), time.min, APP_TIMEZONE)
    measurement_cutoff = delivery_deadline - timedelta(hours=12 if urgent_days in {1, 2, 3} else 48)
    if appointment_end > measurement_cutoff:
        raise BookingRuleError("The selected measurement slot finishes after the measurement deadline.")
    if measurement_cutoff - current < timedelta(0):
        raise BookingRuleError("No valid measurement time remains for this delivery date.")
    return BookingCalculation(
        unit_price=unit,
        service_quantity=service_quantity,
        garments_per_service=garments_per_service,
        total_garment_quantity=total_garments,
        base_amount=base,
        urgent_days=urgent_days,
        urgent_charge=charge,
        final_amount=final,
        delivery_deadline=delivery_deadline,
        measurement_cutoff=measurement_cutoff,
        appointment_start=appointment_start,
        appointment_end=appointment_end,
    )
