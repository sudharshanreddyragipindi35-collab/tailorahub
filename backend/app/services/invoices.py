from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import textwrap
import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.emailer import send_email
from app.services.media_storage import get_media_storage


def _pdf_escape(value: str) -> str:
    return str(value).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def build_invoice_pdf(lines: list[str]) -> bytes:
    """Create a small, dependency-free PDF suitable for an invoice attachment."""
    wrapped: list[str] = []
    for line in lines:
        wrapped.extend(textwrap.wrap(str(line), width=92) or [""])
    commands = ["BT", "/F1 11 Tf", "50 790 Td", "14 TL"]
    for index, line in enumerate(wrapped):
        if index:
            commands.append("T*")
        commands.append(f"({_pdf_escape(line)}) Tj")
    commands.append("ET")
    stream = "\n".join(commands).encode("latin-1", "replace")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    output = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for number, obj in enumerate(objects, 1):
        offsets.append(len(output))
        output.extend(f"{number} 0 obj\n".encode("ascii"))
        output.extend(obj)
        output.extend(b"\nendobj\n")
    xref = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    output.extend(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode("ascii"))
    return bytes(output)


def _money(value) -> str:
    return f"Rs {Decimal(str(value or 0)).quantize(Decimal('0.01')):,.2f}"


async def ensure_invoice_for_payment(
    db: AsyncSession,
    booking_id: str,
    payment_intent_id: str,
    gateway_payment_id: str,
    gateway_order_id: str,
) -> dict:
    existing = await db.execute(
        text("SELECT * FROM invoices WHERE gateway_payment_id=:payment_id OR payment_intent_id=:intent_id LIMIT 1"),
        {"payment_id": gateway_payment_id, "intent_id": payment_intent_id},
    )
    row = existing.mappings().first()
    if row:
        return dict(row)

    details_result = await db.execute(
        text(
            """
            SELECT o.id AS booking_id, o.code AS booking_code, o.service_name, o.quantity,
                   o.base_price, o.additional_total, o.total, o.appointment_date,
                   o.appointment_slot, o.ts AS booking_created_at,
                   u.id AS customer_id, u.name AS customer_name, u.email AS customer_email,
                   u.phone AS customer_phone, t.shop AS tailor_name
            FROM orders o
            JOIN users u ON u.id=o.customer_id
            JOIN tailors t ON t.id=o.tailor_id
            WHERE o.id=:booking_id
            """
        ),
        {"booking_id": booking_id},
    )
    details = details_result.mappings().first()
    if not details:
        raise ValueError("Booking not found while generating invoice")

    invoice_number = f"TH-INV-{datetime.now(timezone.utc):%Y%m%d}-{uuid.uuid4().hex[:8].upper()}"
    amount = Decimal(str(details["total"] or 0))
    date_text = datetime.now(timezone.utc).strftime("%d %b %Y, %H:%M UTC")
    lines = [
        "TailoraHub",
        "Payment Invoice",
        "",
        f"Invoice number: {invoice_number}",
        f"Invoice date: {date_text}",
        "Payment status: PAID",
        f"Booking ID: {details['booking_code'] or details['booking_id']}",
        "",
        f"Customer: {details['customer_name'] or 'Customer'}",
        f"Email: {details['customer_email'] or 'Not provided'}",
        f"Phone: {details['customer_phone'] or 'Not provided'}",
        f"Tailor: {details['tailor_name'] or 'Tailor'}",
        f"Service: {details['service_name']} (Qty {details['quantity'] or 1})",
        f"Service amount: {_money(details['base_price'])}",
        f"Additional charges: {_money(details['additional_total'])}",
        f"Total paid: {_money(amount)}",
        "Currency: INR",
        "",
        f"Razorpay order ID: {gateway_order_id}",
        f"Razorpay payment ID: {gateway_payment_id}",
        "Thank you for choosing TailoraHub.",
    ]
    pdf = build_invoice_pdf(lines)
    reference = get_media_storage().store_private_bytes(
        f"private/invoices/{details['customer_id']}/{invoice_number}.pdf", pdf, "application/pdf"
    )
    inserted = await db.execute(
        text(
            """
            INSERT INTO invoices
              (invoice_number,booking_id,payment_intent_id,customer_id,gateway_payment_id,gateway_order_id,
               amount,currency,pdf_reference,email_status)
            VALUES (:number,:booking_id,:intent_id,:customer_id,:payment_id,:order_id,:amount,'INR',:pdf,'pending')
            ON CONFLICT (gateway_payment_id) DO NOTHING
            RETURNING *
            """
        ),
        {
            "number": invoice_number,
            "booking_id": booking_id,
            "intent_id": payment_intent_id,
            "customer_id": details["customer_id"],
            "payment_id": gateway_payment_id,
            "order_id": gateway_order_id,
            "amount": amount,
            "pdf": reference,
        },
    )
    invoice = inserted.mappings().first()
    if not invoice:
        invoice = (await db.execute(text("SELECT * FROM invoices WHERE gateway_payment_id=:payment_id"), {"payment_id": gateway_payment_id})).mappings().first()
    invoice = dict(invoice)
    if invoice.get("email_status") in {"sent", "queued"}:
        return invoice

    subject = f"Payment Successful - TailoraHub Invoice {invoice['invoice_number']}"
    body = (
        f"Hi {details['customer_name'] or 'Customer'},\n\n"
        f"We have successfully received your payment for booking {details['booking_code']}.\n\n"
        f"Invoice Number: {invoice['invoice_number']}\n"
        f"Booking ID: {details['booking_code']}\n"
        f"Transaction ID: {gateway_payment_id}\n"
        f"Amount Paid: {_money(amount)}\n"
        f"Payment Date: {date_text}\n"
        "Payment Status: Paid\n\n"
        "Your detailed payment invoice is attached as a PDF.\n\n"
        "Regards,\nTailoraHub Team"
    )
    try:
        delivery = send_email(
            details["customer_email"],
            subject,
            body,
            purpose="payments",
            attachments=[{"filename": f"{invoice['invoice_number']}.pdf", "maintype": "application", "subtype": "pdf", "data": pdf}],
        )
    except Exception as exc:
        delivery = {"ok": False, "reason": type(exc).__name__}
    email_status = "sent" if delivery.get("mode") == "live" and delivery.get("delivered") else "queued" if delivery.get("ok") else "failed"
    await db.execute(
        text("UPDATE invoices SET email_status=:status,email_error=:error,emailed_at=CASE WHEN :status='sent' THEN now() ELSE emailed_at END WHERE id=:id"),
        {"status": email_status, "error": None if delivery.get("ok") else delivery.get("reason"), "id": invoice["id"]},
    )
    invoice.update({"email_status": email_status})
    return invoice
