import hashlib

from .integrations import email_service
from .tasks.queue import enqueue_task


def send_email(to_email: str, subject: str, body: str) -> dict:
    key = hashlib.sha256(f"email|{to_email.lower()}|{subject}|{body}".encode("utf-8")).hexdigest()
    queued = enqueue_task(
        "email_delivery",
        {"to": to_email, "subject": subject, "body": body},
        f"email:{key}",
    )
    if queued["mode"] == "inline":
        return queued["result"]
    return {"ok": True, "provider": "sqs", "mode": "queued", "delivered": False, "jobId": queued["jobId"]}
