from __future__ import annotations

import time
import hashlib
import hmac
import json
from datetime import date, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from app.api.v1 import bookings as bookings_module, otp as otp_module
from app import main as main_module
from app.settings import settings


app = main_module.app


def _engine_or_skip():
    engine = create_engine(settings.database_url, future=True)
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:  # pragma: no cover - local DB may be absent in CI
        pytest.skip(f"Postgres is not available for dashboard flow smoke test: {exc}")
    return engine


def _delete_in(conn, table: str, column: str, values: list[str]) -> None:
    if not values:
        return
    table_exists = conn.execute(text("SELECT to_regclass(:table_name)"), {"table_name": table}).scalar()
    if not table_exists:
        return
    params = {f"v{i}": value for i, value in enumerate(values)}
    placeholders = ", ".join(f":v{i}" for i in range(len(values)))
    conn.execute(text(f"DELETE FROM {table} WHERE {column} IN ({placeholders})"), params)


def _cleanup_flow_data(engine, phone: str, email: str, username: str) -> None:
    with engine.begin() as conn:
        user_rows = conn.execute(
            text("SELECT id, customer_id::text AS customer_id FROM users WHERE phone=:phone OR lower(email)=:email OR name IN ('Flow Smoke Customer','Flow Smoke Tailor')"),
            {"phone": phone, "email": email},
        ).mappings().all()
        user_ids = [row["id"] for row in user_rows]
        customer_ids = [row["customer_id"] for row in user_rows]
        tailor_rows = conn.execute(
            text(
                """
                SELECT id, tailor_id::text AS tailor_id, user_id
                FROM tailors
                WHERE phone_number=:phone
                   OR lower(email)=:email
                   OR lower(username)=:username
                   OR owner_name='Flow Smoke Tailor'
                   OR user_id IN (
                     SELECT id FROM users WHERE phone=:phone OR lower(email)=:email
                   )
                """
            ),
            {"phone": phone, "email": email, "username": username},
        ).mappings().all()
        tailor_ids = [row["id"] for row in tailor_rows]
        tailor_uuids = [row["tailor_id"] for row in tailor_rows]
        user_ids = sorted(set(user_ids + [row["user_id"] for row in tailor_rows]))

        requirement_ids = []
        if user_ids:
            params = {f"u{i}": value for i, value in enumerate(user_ids)}
            placeholders = ", ".join(f":u{i}" for i in range(len(user_ids)))
            requirement_ids = [
                row["id"]
                for row in conn.execute(
                    text(f"SELECT id FROM booking_requirements WHERE customer_id IN ({placeholders})"),
                    params,
                ).mappings().all()
            ]

        booking_request_ids = []
        if requirement_ids or tailor_ids:
            clauses = []
            params = {}
            if requirement_ids:
                params.update({f"r{i}": value for i, value in enumerate(requirement_ids)})
                clauses.append("requirement_id IN (" + ", ".join(f":r{i}" for i in range(len(requirement_ids))) + ")")
            if tailor_ids:
                params.update({f"t{i}": value for i, value in enumerate(tailor_ids)})
                clauses.append("tailor_id IN (" + ", ".join(f":t{i}" for i in range(len(tailor_ids))) + ")")
            booking_request_ids = [
                row["id"]
                for row in conn.execute(
                    text("SELECT id FROM booking_requests WHERE " + " OR ".join(clauses)),
                    params,
                ).mappings().all()
            ]

        order_ids = []
        order_clauses = []
        order_params = {}
        if user_ids:
            order_params.update({f"ou{i}": value for i, value in enumerate(user_ids)})
            order_clauses.append("customer_id IN (" + ", ".join(f":ou{i}" for i in range(len(user_ids))) + ")")
        if tailor_ids:
            order_params.update({f"ot{i}": value for i, value in enumerate(tailor_ids)})
            order_clauses.append("tailor_id IN (" + ", ".join(f":ot{i}" for i in range(len(tailor_ids))) + ")")
        if requirement_ids:
            order_params.update({f"orq{i}": value for i, value in enumerate(requirement_ids)})
            order_clauses.append("requirement_id IN (" + ", ".join(f":orq{i}" for i in range(len(requirement_ids))) + ")")
        if booking_request_ids:
            order_params.update({f"obr{i}": value for i, value in enumerate(booking_request_ids)})
            order_clauses.append("request_id IN (" + ", ".join(f":obr{i}" for i in range(len(booking_request_ids))) + ")")
        if order_clauses:
            order_ids = [
                row["id"]
                for row in conn.execute(
                    text("SELECT id FROM orders WHERE " + " OR ".join(order_clauses)),
                    order_params,
                ).mappings().all()
            ]

        if order_ids:
            _delete_in(conn, "admin_wallet_transactions", "source_booking_id", order_ids)
            _delete_in(conn, "payment_webhook_events", "booking_id", order_ids)
            _delete_in(conn, "payment_intents", "booking_id", order_ids)
            _delete_in(conn, "disputes", "booking_id", order_ids)
            _delete_in(conn, "wallet_transactions", "reference_booking_id", order_ids)
            _delete_in(conn, "payments", "order_id", order_ids)
            _delete_in(conn, "additional_charges", "order_id", order_ids)
            _delete_in(conn, "order_status_history", "order_id", order_ids)
            _delete_in(conn, "reviews", "order_id", order_ids)
            _delete_in(conn, "notifications", "order_id", order_ids)

        ticket_ids = []
        ticket_clauses = []
        ticket_params = {}
        if user_ids:
            ticket_params.update({f"tu{i}": value for i, value in enumerate(user_ids)})
            ticket_clauses.append("requester_id IN (" + ", ".join(f":tu{i}" for i in range(len(user_ids))) + ")")
        if order_ids:
            ticket_params.update({f"to{i}": value for i, value in enumerate(order_ids)})
            ticket_clauses.append("order_id IN (" + ", ".join(f":to{i}" for i in range(len(order_ids))) + ")")
        if ticket_clauses:
            ticket_ids = [
                row["id"]
                for row in conn.execute(
                    text("SELECT id FROM support_tickets WHERE " + " OR ".join(ticket_clauses)),
                    ticket_params,
                ).mappings().all()
            ]
        _delete_in(conn, "support_messages", "ticket_id", ticket_ids)
        _delete_in(conn, "support_tickets", "id", ticket_ids)
        _delete_in(conn, "orders", "id", order_ids)
        _delete_in(conn, "booking_request_groups", "customer_id", user_ids)
        _delete_in(conn, "booking_requests", "id", booking_request_ids)
        _delete_in(conn, "booking_requirements", "id", requirement_ids)

        refs = [f"user:{user_id}" for user_id in user_ids] + [f"tailor:{tailor_id}" for tailor_id in tailor_ids]
        _delete_in(conn, "notifications", "to_ref", refs)
        _delete_in(conn, "customer_favorite_tailors", "customer_id", user_ids)
        _delete_in(conn, "tailor_followers", "customer_id", user_ids)
        _delete_in(conn, "customer_favorite_tailors", "tailor_id", tailor_ids)
        _delete_in(conn, "tailor_followers", "tailor_id", tailor_ids)
        _delete_in(conn, "tailor_offers", "tailor_id", tailor_ids)
        _delete_in(conn, "tailor_services", "tailor_id", tailor_ids)
        _delete_in(conn, "tailor_locations", "tailor_id", tailor_uuids)
        _delete_in(conn, "withdrawal_requests", "tailor_id", tailor_uuids)
        _delete_in(conn, "tailor_wallets", "tailor_id", tailor_uuids)
        _delete_in(conn, "referrals", "referrer_tailor_id", tailor_uuids)
        _delete_in(conn, "referrals", "referred_tailor_id", tailor_uuids)
        _delete_in(conn, "tailors", "id", tailor_ids)
        _delete_in(conn, "customer_referrals", "referred_phone_number", [phone])
        _delete_in(conn, "customer_referrals", "referrer_customer_id", customer_ids)
        _delete_in(conn, "customer_referrals", "referred_customer_id", customer_ids)
        _delete_in(conn, "customer_wallets", "customer_id", customer_ids)
        _delete_in(conn, "otp_verifications", "target", [phone, email])
        _delete_in(conn, "refresh_sessions", "user_id", user_ids)
        _delete_in(conn, "users", "id", user_ids)
        conn.execute(text("UPDATE admin_wallet SET balance=COALESCE((SELECT SUM(amount) FROM admin_wallet_transactions),0), updated_at=now()"))


def test_three_dashboard_flow_allows_separate_customer_and_tailor_credentials(monkeypatch):
    engine = _engine_or_skip()
    # This test validates the three-role workflow, not production network policy.
    # Network restriction behavior is covered independently and remains enabled
    # whenever ADMIN_ALLOWED_NETWORKS is configured in a running environment.
    monkeypatch.setattr(main_module, "ADMIN_ALLOWED_NETWORKS", [])
    monkeypatch.setattr(otp_module.secrets, "randbelow", lambda upper_bound: 123456)
    gateway_secret = "integration-secret"
    webhook_secret = "integration-webhook-secret"
    monkeypatch.setattr(settings, "razorpay_webhook_secret", webhook_secret)
    monkeypatch.setattr(bookings_module, "razorpay_credentials", lambda: ("rzp_test_integration", gateway_secret))
    monkeypatch.setattr(bookings_module, "create_razorpay_order_sync", lambda key, secret, payload: {"id": "order_integration_123", "status": "created"})
    suffix = str(time.time_ns())[-9:]
    phone = "9" + suffix
    email = f"flow.{suffix}@example.com"
    username = f"flowtailor{suffix[-5:]}"
    customer_password = "Customer123"
    tailor_password = "Tailor123"

    _cleanup_flow_data(engine, phone, email, username)
    try:
        with TestClient(app) as client:
            phone_otp = client.post("/api/v1/otp/send", json={"target": phone, "purpose": "registration_phone"})
            assert phone_otp.status_code == 200, phone_otp.text
            phone_code = phone_otp.json().get("dev_otp") or phone_otp.json().get("devOtp")
            assert phone_code
            assert client.post(
                "/api/v1/otp/verify",
                json={"target": phone, "purpose": "registration_phone", "otp": phone_code},
            ).status_code == 200

            customer_register = client.post(
                "/api/v1/customers/register",
                json={
                    "full_name": "Flow Smoke Customer",
                    "phone_number": phone,
                    "email": email,
                    "password": customer_password,
                    "confirm_password": customer_password,
                    "terms_accepted": True,
                },
            )
            assert customer_register.status_code == 201, customer_register.text

            customer_login = client.post(
                "/api/v1/auth/customer-login",
                json={"identifier": phone, "mode": "password", "password": customer_password},
            )
            assert customer_login.status_code == 200, customer_login.text
            customer_token = customer_login.json()["token"]

            tailor_phone_available = client.post(
                "/api/v1/tailors/check-availability",
                json={"field": "phone", "value": phone},
            )
            assert tailor_phone_available.status_code == 200, tailor_phone_available.text
            assert tailor_phone_available.json()["available"] is True

            email_otp = client.post("/api/v1/otp/send", json={"target": email, "purpose": "registration_email"})
            assert email_otp.status_code == 200, email_otp.text
            email_code = email_otp.json().get("dev_otp") or email_otp.json().get("devOtp")
            assert email_code
            assert client.post(
                "/api/v1/otp/verify",
                json={"target": email, "purpose": "registration_email", "otp": email_code},
            ).status_code == 200

            tailor_register = client.post(
                "/api/v1/tailors/register",
                json={
                    "full_name": "Flow Smoke Tailor",
                    "phone_number": phone,
                    "email": email,
                    "dob": "1990-01-01",
                    "aadhaar_number": "999999990019",
                    "username": username,
                    "password": tailor_password,
                    "confirm_password": tailor_password,
                    "experience_years_base": 5,
                    "stitching_since_date": "2019-01-01",
                    "terms_accepted": True,
                    "shop_name": "Flow Smoke Studio",
                    "zone_id": "tnagar",
                    "address_text": "T Nagar, Chennai",
                    "latitude": 13.0418,
                    "longitude": 80.2341,
                    "expertise": ["Blouse"],
                    "services": [{"name": "Blouse Stitching", "price": 650, "days": 5}],
                },
            )
            assert tailor_register.status_code == 201, tailor_register.text
            tailor_json = tailor_register.json()
            tailor_legacy_id = tailor_json["tailor"]["id"]
            tailor_uuid = tailor_json["tailor"]["tailorId"]

            wrong_tailor_login = client.post(
                "/api/v1/auth/login",
                json={"identifier": username, "mode": "password", "password": customer_password},
            )
            assert wrong_tailor_login.status_code == 401

            tailor_login = client.post(
                "/api/v1/auth/login",
                json={"identifier": username, "mode": "password", "password": tailor_password},
            )
            assert tailor_login.status_code == 200, tailor_login.text
            tailor_token = tailor_login.json()["token"]

            admin_login = client.post("/api/auth/admin/login", json={"username": "admin", "password": settings.admin_password})
            assert admin_login.status_code == 200, admin_login.text
            admin_token = admin_login.json()["token"]
            approved = client.post(
                f"/api/admin/tailors/{tailor_legacy_id}/approve",
                headers={"Authorization": f"Bearer {admin_token}"},
            )
            assert approved.status_code == 200, approved.text

            customer_headers = {"Authorization": f"Bearer {customer_token}"}
            tailor_headers = {"Authorization": f"Bearer {tailor_token}"}
            listed = client.get("/api/customer/tailors", headers=customer_headers)
            assert listed.status_code == 200, listed.text
            assert any(row["id"] == tailor_legacy_id for row in listed.json())

            nearby = client.get(
                "/api/v1/customers/nearby-tailors",
                params={"latitude": 13.0418, "longitude": 80.2341, "radius_km": 50},
                headers=customer_headers,
            )
            assert nearby.status_code == 200, nearby.text
            assert any(row["tailorId"] == tailor_uuid for row in nearby.json())

            services = client.get(f"/api/v1/tailors/{tailor_uuid}/services")
            assert services.status_code == 200, services.text
            service_id = services.json()[0]["serviceId"]

            booking = client.post(
                "/api/v1/bookings",
                json={
                    "tailorId": tailor_uuid,
                    "serviceId": service_id,
                    "quantity": 1,
                    "measurementMode": "customer_visits_tailor",
                        "preferredDate": (date.today() + timedelta(days=5)).isoformat(),
                        "appointmentDate": (date.today() + timedelta(days=1)).isoformat(),
                        "appointmentSlot": "08:00-10:00",
                },
                headers=customer_headers,
            )
            assert booking.status_code == 200, booking.text
            booking_id = booking.json()["booking"]["id"]

            tailor_dashboard = client.get("/api/tailor/dashboard", headers=tailor_headers)
            assert tailor_dashboard.status_code == 200, tailor_dashboard.text
            assert any(row["id"] == booking_id for row in tailor_dashboard.json()["orders"])

            gated_otp = client.post(f"/api/v1/bookings/{booking_id}/send-delivery-otp", headers=tailor_headers)
            assert gated_otp.status_code == 403

            pay_request = client.post(
                f"/api/v1/bookings/{booking_id}/pay",
                json={"method": "razorpay", "idempotencyKey": f"payment-{booking_id}"},
                headers=customer_headers,
            )
            assert pay_request.status_code == 200, pay_request.text
            payment_json = pay_request.json()
            assert payment_json["paymentIntent"]["status"] == "pending"
            tailor_credit_amount = Decimal(str(payment_json["breakdown"]["tailor_credit_amount"]))

            wallet_before_verification = client.get("/api/v1/wallet/me", headers=tailor_headers)
            assert wallet_before_verification.status_code == 200, wallet_before_verification.text
            assert Decimal(str(wallet_before_verification.json()["balance"])) == Decimal("0")

            still_gated_otp = client.post(f"/api/v1/bookings/{booking_id}/send-delivery-otp", headers=tailor_headers)
            assert still_gated_otp.status_code == 403

            gateway_payment_id = "pay_integration_123"
            webhook_payload = json.dumps(
                {
                    "event": "payment.captured",
                    "payload": {
                        "payment": {
                            "entity": {
                                "id": gateway_payment_id,
                                "order_id": "order_integration_123",
                                "status": "captured",
                            }
                        }
                    },
                },
                separators=(",", ":"),
            ).encode()
            invalid_webhook = client.post(
                "/api/v1/payments/webhooks/razorpay",
                content=webhook_payload,
                headers={"Content-Type": "application/json", "X-Razorpay-Signature": "invalid"},
            )
            assert invalid_webhook.status_code == 401
            webhook_signature = hmac.new(webhook_secret.encode(), webhook_payload, hashlib.sha256).hexdigest()
            webhook_headers = {
                "Content-Type": "application/json",
                "X-Razorpay-Signature": webhook_signature,
                "X-Razorpay-Event-Id": f"evt_{suffix}",
            }
            captured_webhook = client.post(
                "/api/v1/payments/webhooks/razorpay",
                content=webhook_payload,
                headers=webhook_headers,
            )
            assert captured_webhook.status_code == 200, captured_webhook.text
            assert captured_webhook.json()["status"] == "completed"
            duplicate_webhook = client.post(
                "/api/v1/payments/webhooks/razorpay",
                content=webhook_payload,
                headers=webhook_headers,
            )
            assert duplicate_webhook.status_code == 200, duplicate_webhook.text
            assert duplicate_webhook.json()["duplicate"] is True

            signature = hmac.new(gateway_secret.encode(), f"order_integration_123|{gateway_payment_id}".encode(), hashlib.sha256).hexdigest()
            verified_payment = client.post(f"/api/v1/bookings/{booking_id}/razorpay/verify", json={
                "razorpay_order_id": "order_integration_123",
                "razorpay_payment_id": gateway_payment_id,
                "razorpay_signature": signature,
            }, headers=customer_headers)
            assert verified_payment.status_code == 200, verified_payment.text

            wallet_after_payment = client.get("/api/v1/wallet/me", headers=tailor_headers)
            assert wallet_after_payment.status_code == 200, wallet_after_payment.text
            paid_wallet_balance = Decimal(str(wallet_after_payment.json()["balance"]))
            assert paid_wallet_balance == tailor_credit_amount

            dashboard_after_payment = client.get("/api/tailor/dashboard", headers=tailor_headers)
            assert dashboard_after_payment.status_code == 200, dashboard_after_payment.text
            assert Decimal(str(dashboard_after_payment.json()["stats"]["earnings"])) == paid_wallet_balance

            delivery_otp = client.post(f"/api/v1/bookings/{booking_id}/send-delivery-otp", headers=tailor_headers)
            assert delivery_otp.status_code == 200, delivery_otp.text

            completed = client.post(
                f"/api/v1/bookings/{booking_id}/verify-delivery-otp",
                json={"otp": "223456"},
                headers=tailor_headers,
            )
            assert completed.status_code == 200, completed.text
            assert completed.json()["booking"]["status"] == "completed"
            commission = Decimal(str(completed.json()["booking"]["commissionAmount"]))

            wallet_after_completion = client.get("/api/v1/wallet/me", headers=tailor_headers)
            assert wallet_after_completion.status_code == 200, wallet_after_completion.text
            completed_wallet_balance = Decimal(str(wallet_after_completion.json()["balance"]))
            assert commission > 0
            assert completed_wallet_balance == paid_wallet_balance

            dashboard_after_completion = client.get("/api/tailor/dashboard", headers=tailor_headers)
            assert dashboard_after_completion.status_code == 200, dashboard_after_completion.text
            completion_stats = dashboard_after_completion.json()["stats"]
            assert Decimal(str(completion_stats["earnings"])) == completed_wallet_balance
            assert completion_stats["active_orders"] == 0
            assert completion_stats["completed_orders"] == 1

            metrics = client.get("/api/admin/metrics", headers={"Authorization": f"Bearer {admin_token}"})
            assert metrics.status_code == 200, metrics.text

            finance_wallet = client.get("/api/v1/admin/finance/wallet", headers={"Authorization": f"Bearer {admin_token}"})
            assert finance_wallet.status_code == 200, finance_wallet.text
            assert "transactions" in finance_wallet.json()

            filtered_finance_wallet = client.get(
                "/api/v1/admin/finance/wallet",
                params={"dateFrom": "2026-08-01", "dateTo": "2026-08-10"},
                headers={"Authorization": f"Bearer {admin_token}"},
            )
            assert filtered_finance_wallet.status_code == 200, filtered_finance_wallet.text
    finally:
        _cleanup_flow_data(engine, phone, email, username)
