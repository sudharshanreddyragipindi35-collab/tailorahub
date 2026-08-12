from __future__ import annotations

import re

from app.security import is_valid_aadhaar_format


PHONE_RE = re.compile(r"^[6-9]\d{9}$")


def is_indian_phone(value: str) -> bool:
    return bool(PHONE_RE.fullmatch((value or "").strip()))


def is_valid_aadhaar(value: str) -> bool:
    return is_valid_aadhaar_format((value or "").strip())
