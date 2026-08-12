from __future__ import annotations

import hmac
from hashlib import sha256

from app.core.config import get_settings


def verify_payment_webhook_signature(payload: bytes, signature: str) -> bool:
    secret = get_settings().payment_webhook_secret
    if not secret:
        return False
    expected = hmac.new(secret.encode("utf-8"), payload, sha256).hexdigest()
    return hmac.compare_digest(expected, signature or "")
