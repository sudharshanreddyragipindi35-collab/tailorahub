"""Wallet QR code generation.

The QR encodes only an opaque `tailorahub:wallet:{wallet_id}` payment
token -- never a UPI ID or bank detail (see file 09's security note) -- so
scanning it only ever reveals which wallet to credit, resolved server-side
by the payment endpoint.
"""

from pathlib import Path

import qrcode

from .settings import settings

WALLET_QR_DIR = settings.base_dir / "uploads" / "wallets"


def wallet_payment_token(wallet_id: str) -> str:
    return f"tailorahub:wallet:{wallet_id}"


def generate_wallet_qr(wallet_id: str) -> str:
    """Writes uploads/wallets/{wallet_id}.png and returns its public URL path."""
    WALLET_QR_DIR.mkdir(parents=True, exist_ok=True)
    image = qrcode.make(wallet_payment_token(wallet_id))
    target: Path = WALLET_QR_DIR / f"{wallet_id}.png"
    image.save(target)
    return f"/uploads/wallets/{wallet_id}.png"
