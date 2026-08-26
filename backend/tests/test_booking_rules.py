from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest

from app.services.booking_rules import APP_TIMEZONE, BookingRuleError, calculate_booking


def future_dates(days=5):
    today = datetime.now(APP_TIMEZONE).date()
    return today + timedelta(days=max(0, days - 1)), today


@pytest.mark.parametrize("quantity,urgent_days,charge", [(1, 1, "150.00"), (2, 1, "150.00"), (2, 2, "100.00"), (4, 3, "50.00")])
def test_server_calculates_urgent_price_once(quantity, urgent_days, charge):
    delivery, appointment = future_dates(urgent_days)
    result = calculate_booking(unit_price="400.00", service_quantity=quantity, is_combo=False,
        combo_items=[], urgent_days=urgent_days, delivery_date=delivery,
        appointment_date=appointment, appointment_slot="08:00-10:00",
        now=datetime.combine(datetime.now(APP_TIMEZONE).date(), datetime.min.time(), APP_TIMEZONE))
    assert result.urgent_charge == Decimal(charge)
    assert result.final_amount == Decimal("400.00") * quantity + Decimal(charge)


def test_one_day_allows_combo():
    delivery, appointment = future_dates(1)
    result = calculate_booking(unit_price=500, service_quantity=1, is_combo=True, combo_items=["shirt", "pant"],
        urgent_days=1, delivery_date=delivery, appointment_date=appointment, appointment_slot="08:00-10:00",
        now=datetime.combine(datetime.now(APP_TIMEZONE).date(), datetime.min.time(), APP_TIMEZONE))
    assert result.urgent_charge == Decimal("150.00")


def test_regular_and_urgent_measurement_cutoffs_are_48_and_12_hours():
    delivery, appointment = future_dates(6)
    regular = calculate_booking(unit_price=100, service_quantity=1, is_combo=False, combo_items=[], urgent_days=None,
        delivery_date=delivery, appointment_date=appointment, appointment_slot="08:00-10:00",
        now=datetime.combine(datetime.now(APP_TIMEZONE).date(), datetime.min.time(), APP_TIMEZONE))
    urgent_delivery, urgent_appointment = future_dates(3)
    urgent = calculate_booking(unit_price=100, service_quantity=4, is_combo=False, combo_items=[], urgent_days=3,
        delivery_date=urgent_delivery, appointment_date=urgent_appointment, appointment_slot="08:00-10:00",
        now=datetime.combine(datetime.now(APP_TIMEZONE).date(), datetime.min.time(), APP_TIMEZONE))
    assert regular.delivery_deadline - regular.measurement_cutoff == timedelta(hours=48)
    assert urgent.delivery_deadline - urgent.measurement_cutoff == timedelta(hours=12)


def test_measurement_date_must_not_be_after_delivery():
    today = datetime.now(APP_TIMEZONE).date()
    with pytest.raises(BookingRuleError):
        calculate_booking(unit_price=100, service_quantity=1, is_combo=False, combo_items=[], urgent_days=1,
            delivery_date=today, appointment_date=today + timedelta(days=1), appointment_slot="20:00-22:00",
            now=datetime.combine(today, datetime.min.time(), APP_TIMEZONE))


def test_urgent_completion_requires_matching_delivery_date():
    today = datetime.now(APP_TIMEZONE).date()
    with pytest.raises(BookingRuleError):
        calculate_booking(unit_price=100, service_quantity=1, is_combo=False, combo_items=[], urgent_days=1,
            delivery_date=today + timedelta(days=2), appointment_date=today,
            appointment_slot="08:00-10:00", now=datetime.combine(today, datetime.min.time(), APP_TIMEZONE))
