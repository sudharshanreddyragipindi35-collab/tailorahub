from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from email.message import EmailMessage
import base64
import json
from pathlib import Path
import re
import smtplib
from urllib import parse, request
import uuid

from .settings import settings


@dataclass
class IntegrationResult:
    ok: bool
    provider: str
    mode: str
    data: dict

    def as_dict(self) -> dict:
        return {"ok": self.ok, "provider": self.provider, "mode": self.mode, **self.data}


class EmailService:
    def send(self, to_email: str, subject: str, body: str) -> dict:
        raise NotImplementedError


class MockEmailService(EmailService):
    def send(self, to_email: str, subject: str, body: str) -> dict:
        outbox = Path(settings.email_outbox)
        outbox.parent.mkdir(parents=True, exist_ok=True)
        with outbox.open("a", encoding="utf-8") as f:
            f.write("\n--- " + datetime.now(timezone.utc).isoformat() + " ---\n")
            f.write("To: " + to_email + "\n")
            f.write("Subject: " + subject + "\n\n")
            f.write(body + "\n")
        return IntegrationResult(True, "mock", "mock", {"delivered": False, "via": "outbox", "file": str(outbox)}).as_dict()


class SmtpEmailService(EmailService):
    def send(self, to_email: str, subject: str, body: str) -> dict:
        msg = EmailMessage()
        msg["From"] = settings.email_from_address
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.set_content(body)
        if settings.smtp_secure:
            server = smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=20)
        else:
            server = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20)
        with server:
            if settings.smtp_starttls and not settings.smtp_secure:
                server.starttls()
            if settings.smtp_user:
                server.login(settings.smtp_user, settings.smtp_pass)
            server.send_message(msg)
        return IntegrationResult(True, "smtp", "live", {"delivered": True, "via": "smtp"}).as_dict()


class ApiEmailService(EmailService):
    def send(self, to_email: str, subject: str, body: str) -> dict:
        if not settings.email_api_key:
            return MockEmailService().send(to_email, subject, body)
        if settings.email_provider == "sendgrid":
            payload = {
                "personalizations": [{"to": [{"email": to_email}]}],
                "from": {"email": settings.email_from_address},
                "subject": subject,
                "content": [{"type": "text/plain", "value": body}],
            }
            req = request.Request(
                "https://api.sendgrid.com/v3/mail/send",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Authorization": f"Bearer {settings.email_api_key}", "Content-Type": "application/json"},
                method="POST",
            )
            try:
                with request.urlopen(req, timeout=20) as res:
                    return IntegrationResult(res.status in {200, 202}, "sendgrid", "live", {"delivered": res.status in {200, 202}, "statusCode": res.status}).as_dict()
            except Exception as exc:
                return IntegrationResult(False, "sendgrid", "live", {"delivered": False, "reason": str(exc)}).as_dict()
        return IntegrationResult(False, settings.email_provider, "not_configured", {"delivered": False, "reason": "Live email adapter is not implemented yet"}).as_dict()


def email_service() -> EmailService:
    if settings.email_provider == "smtp" or settings.smtp_host:
        return SmtpEmailService()
    if settings.email_provider in {"sendgrid", "ses"}:
        return ApiEmailService()
    return MockEmailService()


class SmsService:
    def send_otp(self, phone_number: str, code: str) -> dict:
        raise NotImplementedError


class MockSmsService(SmsService):
    def send_otp(self, phone_number: str, code: str) -> dict:
        print(f"[MOCK SMS OTP] to={phone_number} code={code}")
        return IntegrationResult(True, "mock", "mock", {"sent": False, "code": code}).as_dict()


class LiveSmsService(SmsService):
    def send_otp(self, phone_number: str, code: str) -> dict:
        if not settings.sms_api_key:
            return MockSmsService().send_otp(phone_number, code)
        if settings.sms_provider == "twilio" and settings.sms_api_secret and settings.sms_sender_id:
            sid = settings.sms_api_secret
            token = settings.sms_api_key
            url = f"https://api.twilio.com/2010-04-01/Accounts/{parse.quote(sid)}/Messages.json"
            payload = parse.urlencode({"To": "+91" + phone_number[-10:], "From": settings.sms_sender_id, "Body": f"Your TailoraHub OTP is {code}."}).encode("utf-8")
            auth = base64.b64encode(f"{sid}:{token}".encode("utf-8")).decode("ascii")
            req = request.Request(url, data=payload, headers={"Authorization": f"Basic {auth}"}, method="POST")
            try:
                with request.urlopen(req, timeout=20) as res:
                    return IntegrationResult(res.status in {200, 201}, "twilio", "live", {"sent": res.status in {200, 201}, "statusCode": res.status}).as_dict()
            except Exception as exc:
                return IntegrationResult(False, "twilio", "live", {"sent": False, "reason": str(exc)}).as_dict()
        return IntegrationResult(False, settings.sms_provider, "not_configured", {"sent": False, "reason": "Live SMS adapter is not implemented yet"}).as_dict()


def sms_service() -> SmsService:
    if settings.sms_provider in {"twilio", "msg91"}:
        return LiveSmsService()
    return MockSmsService()


class AadhaarKycService:
    def verify(self, aadhaar_number: str, full_name: str | None = None) -> dict:
        raise NotImplementedError


class MockAadhaarKycService(AadhaarKycService):
    def verify(self, aadhaar_number: str, full_name: str | None = None) -> dict:
        verified = bool(re.fullmatch(r"\d{12}", aadhaar_number or ""))
        return IntegrationResult(verified, "mock", "mock", {"verified": verified, "fullName": full_name, "reason": None if verified else "Aadhaar must be 12 digits"}).as_dict()


class LiveAadhaarKycService(AadhaarKycService):
    def verify(self, aadhaar_number: str, full_name: str | None = None) -> dict:
        if not settings.aadhaar_kyc_api_key or not settings.aadhaar_kyc_base_url:
            return MockAadhaarKycService().verify(aadhaar_number, full_name)
        return IntegrationResult(False, settings.aadhaar_kyc_provider, "not_configured", {"verified": False, "reason": "Live Aadhaar KYC adapter is not implemented yet"}).as_dict()


def aadhaar_kyc_service() -> AadhaarKycService:
    if settings.aadhaar_kyc_provider == "mock":
        return MockAadhaarKycService()
    return LiveAadhaarKycService()


class PaymentService:
    def capture(self, amount: int, reference: str, method: str = "manual") -> dict:
        raise NotImplementedError


class MockPaymentService(PaymentService):
    def capture(self, amount: int, reference: str, method: str = "manual") -> dict:
        return IntegrationResult(True, "mock", "mock", {"status": "success", "txnRef": f"mock_{uuid.uuid4().hex[:12]}", "amount": amount, "reference": reference, "method": method}).as_dict()


class RazorpayPaymentService(PaymentService):
    def capture(self, amount: int, reference: str, method: str = "manual") -> dict:
        if not settings.payment_api_key or not settings.payment_api_secret:
            return MockPaymentService().capture(amount, reference, method)
        auth = base64.b64encode(f"{settings.payment_api_key}:{settings.payment_api_secret}".encode("utf-8")).decode("ascii")
        amount_paise = int(amount) * 100
        try:
            if reference.startswith("pay_"):
                payload = parse.urlencode({"amount": amount_paise, "currency": "INR"}).encode("utf-8")
                url = f"https://api.razorpay.com/v1/payments/{parse.quote(reference)}/capture"
            else:
                payload = json.dumps({"amount": amount_paise, "currency": "INR", "receipt": reference}).encode("utf-8")
                url = "https://api.razorpay.com/v1/orders"
            req = request.Request(
                url,
                data=payload,
                headers={"Authorization": f"Basic {auth}", "Content-Type": "application/json"},
                method="POST",
            )
            with request.urlopen(req, timeout=20) as res:
                raw = res.read().decode("utf-8")
                data = json.loads(raw) if raw else {}
                return IntegrationResult(res.status in {200, 201}, "razorpay", "live", {"status": "success", "txnRef": data.get("id") or reference, "amount": amount, "reference": reference, "method": method, "rawStatus": data.get("status")}).as_dict()
        except Exception as exc:
            return IntegrationResult(False, "razorpay", "live", {"status": "failed", "reason": str(exc)}).as_dict()


def payment_service() -> PaymentService:
    if settings.payment_provider == "razorpay":
        return RazorpayPaymentService()
    return MockPaymentService()


class PayoutService:
    def withdraw(self, amount: int, destination: str) -> dict:
        if not settings.payout_api_key:
            return IntegrationResult(True, "mock", "mock", {"status": "success", "txnRef": f"mock_payout_{uuid.uuid4().hex[:12]}", "amount": amount, "destination": destination}).as_dict()
        return IntegrationResult(False, "payout", "not_configured", {"status": "failed", "reason": "Live payout adapter is deferred until payout credentials are present"}).as_dict()


class MapsService:
    def public_config(self) -> dict:
        return {
            "provider": settings.maps_provider,
            "configured": bool(settings.maps_api_key),
            "mode": "live" if settings.maps_api_key and settings.maps_provider != "mock" else "mock",
        }


payout_service = PayoutService()
maps_service = MapsService()
