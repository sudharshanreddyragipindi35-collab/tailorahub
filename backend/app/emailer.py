import hashlib
import base64

from .integrations import email_service
from .tasks.queue import enqueue_task


def send_email(to_email: str, subject: str, body: str, purpose: str = "default", attachments: list[dict] | None = None) -> dict:
    """Queue an email using a purpose-specific verified sender alias."""
    key = hashlib.sha256(f"email|{to_email.lower()}|{subject}|{body}|{purpose}".encode("utf-8")).hexdigest()
    encoded_attachments = []
    for attachment in attachments or []:
        data = attachment.get("data") or b""
        if isinstance(data, str):
            data = data.encode("utf-8")
        encoded_attachments.append({
            "filename": attachment.get("filename") or "attachment",
            "maintype": attachment.get("maintype") or "application",
            "subtype": attachment.get("subtype") or "octet-stream",
            "data": base64.b64encode(data).decode("ascii"),
        })
    queued = enqueue_task(
        "email_delivery",
        {"to": to_email, "subject": subject, "body": body, "purpose": purpose, "attachments": encoded_attachments},
        f"email:{key}",
    )
    if queued["mode"] == "inline":
        return queued["result"]
    return {"ok": True, "provider": "sqs", "mode": "queued", "delivered": False, "jobId": queued["jobId"]}
