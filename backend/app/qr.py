"""Wallet QR code generation.

The QR encodes only an opaque `tailorahub:wallet:{wallet_id}` payment
token -- never a UPI ID or bank detail (see file 09's security note) -- so
scanning it only ever reveals which wallet to credit, resolved server-side
by the payment endpoint.
"""

from io import BytesIO

import qrcode

from .services.media_storage import get_media_storage


def wallet_payment_token(wallet_id: str) -> str:
    return f"tailorahub:wallet:{wallet_id}"


def generate_wallet_qr(wallet_id: str) -> str:
    """Stores an opaque wallet QR through the configured media backend."""
    image = qrcode.make(wallet_payment_token(wallet_id))
    output = BytesIO()
    image.save(output, format="PNG")
    return get_media_storage().store_bytes(
        f"wallets/{wallet_id}.png",
        output.getvalue(),
        "image/png",
    )
