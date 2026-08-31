import hashlib

from .integrations import email_service
from .tasks.queue import enqueue_task


def send_email(to_email: str, subject: str, body: str, purpose: str = "default") -> dict:
    """Queue an email using a purpose-specific verified sender alias."""
    key = hashlib.sha256(f"email|{to_email.lower()}|{subject}|{body}|{purpose}".encode("utf-8")).hexdigest()
    queued = enqueue_task(
        "email_delivery",
        {"to": to_email, "subject": subject, "body": body, "purpose": purpose},
        f"email:{key}",
    )
    if queued["mode"] == "inline":
        return queued["result"]
    return {"ok": True, "provider": "sqs", "mode": "queued", "delivered": False, "jobId": queued["jobId"]}
