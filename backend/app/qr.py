"""Wallet QR code generation.

The QR encodes only an opaque `tailorahub:wallet:{wallet_id}` payment
token -- never a UPI ID or bank detail (see file 09's security note) -- so
scanning it only ever reveals which wallet to credit, resolved server-side
by the payment endpoint.
"""

from base64 import b64encode
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


def generate_tailor_profile_qr(profile_url: str) -> str:
    """Return a print-quality QR image for a public tailor profile URL.

    The QR deliberately encodes a normal HTTPS URL (not contact information,
    payment credentials, or an authenticated API URL) so it is safe to print
    and share in a tailor's shop.
    """
    code = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=12,
        border=4,
    )
    code.add_data(profile_url)
    code.make(fit=True)
    image = code.make_image(fill_color="#111827", back_color="white")
    output = BytesIO()
    image.save(output, format="PNG")
    return "data:image/png;base64," + b64encode(output.getvalue()).decode("ascii")
