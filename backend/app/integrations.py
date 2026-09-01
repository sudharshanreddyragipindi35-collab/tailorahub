from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from email.message import EmailMessage
from email.utils import parseaddr
import base64
import json
from pathlib import Path
import re
import smtplib
from urllib import parse, request
import uuid
import hashlib
from typing import Iterable

from .settings import settings
from .services.external_resilience import external_call, external_timeout_seconds, safe_provider_error


@dataclass
class IntegrationResult:
    ok: bool
    provider: str
    mode: str
    data: dict

    def as_dict(self) -> dict:
        return {"ok": self.ok, "provider": self.provider, "mode": self.mode, **self.data}


class EmailService:
    def send(self, to_email: str, subject: str, body: str, purpose: str = "default", attachments: Iterable[dict] | None = None) -> dict:
        raise NotImplementedError


def _sender_for(purpose: str) -> str:
    return {
        "verify": settings.email_from_verify,
        "bookings": settings.email_from_bookings,
        "support": settings.email_from_support,
        "payments": settings.email_from_payments,
        "admin": settings.email_from_admin,
    }.get((purpose or "default").lower(), settings.email_from_default)


def _sender_parts(sender: str) -> tuple[str, str]:
    """Return provider-safe address and optional display name."""
    name, address = parseaddr(sender)
    return address or sender, name


class MockEmailService(EmailService):
    def send(self, to_email: str, subject: str, body: str, purpose: str = "default", attachments: Iterable[dict] | None = None) -> dict:
        outbox = Path(settings.email_outbox)
        outbox.parent.mkdir(parents=True, exist_ok=True)
        with outbox.open("a", encoding="utf-8") as f:
            f.write("\n--- " + datetime.now(timezone.utc).isoformat() + " ---\n")
            f.write("To: " + to_email + "\n")
            f.write("From: " + _sender_for(purpose) + "\n")
            f.write("Subject: " + subject + "\n\n")
            f.write(body + "\n")
        return IntegrationResult(True, "mock", "mock", {"delivered": False, "via": "outbox", "file": str(outbox)}).as_dict()


class SmtpEmailService(EmailService):
    def send(self, to_email: str, subject: str, body: str, purpose: str = "default", attachments: Iterable[dict] | None = None) -> dict:
        msg = EmailMessage()
        msg["From"] = _sender_for(purpose)
        msg["To"] = to_email
        msg["Subject"] = subject
        if settings.email_reply_to:
            msg["Reply-To"] = settings.email_reply_to
        msg.set_content(body)
        for attachment in attachments or []:
            data = attachment.get("data") or b""
            if isinstance(data, str):
                data = data.encode("utf-8")
            msg.add_attachment(
                data,
                maintype=str(attachment.get("maintype") or "application"),
                subtype=str(attachment.get("subtype") or "octet-stream"),
                filename=str(attachment.get("filename") or "attachment"),
            )
        def deliver() -> None:
            if settings.smtp_secure:
                server = smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=external_timeout_seconds())
            else:
                server = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=external_timeout_seconds())
            with server:
                if settings.smtp_starttls and not settings.smtp_secure:
                    server.starttls()
                if settings.smtp_user:
                    server.login(settings.smtp_user, settings.smtp_pass)
                server.send_message(msg)

        try:
            external_call("smtp", "send_email", deliver, retry_safe=False)
            return IntegrationResult(True, "smtp", "live", {"delivered": True, "via": "smtp"}).as_dict()
        except Exception as exc:
            return IntegrationResult(False, "smtp", "live", {"delivered": False, "reason": safe_provider_error(exc)}).as_dict()


class ApiEmailService(EmailService):
    def send(self, to_email: str, subject: str, body: str, purpose: str = "default", attachments: Iterable[dict] | None = None) -> dict:
        sender = _sender_for(purpose)
        sender_email, sender_name = _sender_parts(sender)
        if settings.email_provider == "ses":
            try:
                import boto3
                from botocore.config import Config

                client = boto3.client(
                    "sesv2",
                    region_name=settings.aws_ses_region,
                    config=Config(
                        connect_timeout=settings.external_connect_timeout_seconds,
                        read_timeout=settings.external_response_timeout_seconds,
                        retries={"total_max_attempts": 1, "mode": "standard"},
                    ),
                )
                response = external_call(
                    "ses",
                    "send_email",
                    lambda: client.send_email(
                        FromEmailAddress=sender,
                        Destination={"ToAddresses": [to_email]},
                        Content={"Simple": {"Subject": {"Data": subject}, "Body": {"Text": {"Data": body}}}},
                    ),
                    retry_safe=False,
                )
                return IntegrationResult(True, "ses", "live", {"delivered": True, "messageId": response.get("MessageId")}).as_dict()
            except Exception as exc:
                return IntegrationResult(False, "ses", "live", {"delivered": False, "reason": safe_provider_error(exc)}).as_dict()
        if settings.email_provider == "sendgrid":
            if not settings.email_api_key:
                return IntegrationResult(False, "sendgrid", "not_configured", {"delivered": False, "reason": "EMAIL_API_KEY is required"}).as_dict()
            payload = {
                "personalizations": [{"to": [{"email": to_email}]}],
                "from": {"email": sender_email, **({"name": sender_name} if sender_name else {})},
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
                def deliver() -> int:
                    with request.urlopen(req, timeout=external_timeout_seconds()) as res:
                        return res.status

                status = external_call("sendgrid", "send_email", deliver, retry_safe=False)
                return IntegrationResult(status in {200, 202}, "sendgrid", "live", {"delivered": status in {200, 202}, "statusCode": status}).as_dict()
            except Exception as exc:
                return IntegrationResult(False, "sendgrid", "live", {"delivered": False, "reason": safe_provider_error(exc)}).as_dict()
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
            return IntegrationResult(False, settings.sms_provider, "not_configured", {"sent": False, "reason": "SMS_API_KEY is required"}).as_dict()
        if settings.sms_provider == "twilio" and settings.sms_api_secret and settings.sms_sender_id:
            sid = settings.sms_api_secret
            token = settings.sms_api_key
            url = f"https://api.twilio.com/2010-04-01/Accounts/{parse.quote(sid)}/Messages.json"
            payload = parse.urlencode({"To": "+91" + phone_number[-10:], "From": settings.sms_sender_id, "Body": f"Your TailoraHub verification code is {code}. It is valid for 10 minutes. Do not share this code with anyone. - TailoraHub"}).encode("utf-8")
            auth = base64.b64encode(f"{sid}:{token}".encode("utf-8")).decode("ascii")
            req = request.Request(url, data=payload, headers={"Authorization": f"Basic {auth}"}, method="POST")
            try:
                def deliver() -> int:
                    with request.urlopen(req, timeout=external_timeout_seconds()) as res:
                        return res.status

                status = external_call("twilio", "send_otp", deliver, retry_safe=False)
                return IntegrationResult(status in {200, 201}, "twilio", "live", {"sent": status in {200, 201}, "statusCode": status}).as_dict()
            except Exception as exc:
                return IntegrationResult(False, "twilio", "live", {"sent": False, "reason": safe_provider_error(exc)}).as_dict()
        if settings.sms_provider == "msg91" and settings.sms_otp_template_id:
            base_url = settings.sms_api_base_url or "https://control.msg91.com/api/v5/otp"
            query = parse.urlencode({
                "template_id": settings.sms_otp_template_id,
                "mobile": "91" + phone_number[-10:],
            })
            req = request.Request(
                f"{base_url}?{query}",
                data=json.dumps({"otp": code}).encode("utf-8"),
                headers={"Content-Type": "application/json", "authkey": settings.sms_api_key},
                method="POST",
            )
            try:
                def deliver() -> int:
                    with request.urlopen(req, timeout=external_timeout_seconds()) as res:
                        return res.status

                status = external_call("msg91", "send_otp", deliver, retry_safe=False)
                return IntegrationResult(status in {200, 201}, "msg91", "live", {"sent": status in {200, 201}, "statusCode": status}).as_dict()
            except Exception as exc:
                return IntegrationResult(False, "msg91", "live", {"sent": False, "reason": safe_provider_error(exc)}).as_dict()
        return IntegrationResult(False, settings.sms_provider, "not_configured", {"sent": False, "reason": "Live SMS adapter is not implemented yet"}).as_dict()


def sms_service_now() -> SmsService:
    if settings.sms_provider in {"twilio", "msg91"}:
        return LiveSmsService()
    return MockSmsService()


class QueuedSmsService(SmsService):
    def send_otp(self, phone_number: str, code: str) -> dict:
        from app.tasks.queue import enqueue_task

        digest = hashlib.sha256(f"sms|{phone_number}|{code}".encode("utf-8")).hexdigest()
        queued = enqueue_task("sms_otp_delivery", {"phone": phone_number, "code": code}, f"sms:{digest}")
        if queued["mode"] == "inline":
            return queued["result"]
        return IntegrationResult(True, "sqs", "queued", {"sent": False, "jobId": queued["jobId"]}).as_dict()


def sms_service() -> SmsService:
    return QueuedSmsService()


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
            def deliver() -> tuple[int, dict]:
                with request.urlopen(req, timeout=external_timeout_seconds()) as res:
                    raw = res.read().decode("utf-8")
                    return res.status, json.loads(raw) if raw else {}

            status, data = external_call("razorpay", "capture_or_create", deliver, retry_safe=False)
            return IntegrationResult(status in {200, 201}, "razorpay", "live", {"status": "success", "txnRef": data.get("id") or reference, "amount": amount, "reference": reference, "method": method, "rawStatus": data.get("status")}).as_dict()
        except Exception as exc:
            return IntegrationResult(False, "razorpay", "live", {"status": "failed", "reason": safe_provider_error(exc)}).as_dict()


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
