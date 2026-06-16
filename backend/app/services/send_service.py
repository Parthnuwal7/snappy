"""Orchestrates sending an invoice over a channel (email / whatsapp).

Pure-ish coordinator: it renders the message, builds the public link, dispatches
(or builds a wa.me URL), and records the send on the invoice. The HTTP endpoint
is a thin wrapper around `send_invoice`.
"""
from datetime import datetime
from urllib.parse import quote

from app.utils.invoice_links import build_link
from app.utils.phone import normalize_e164
from app.services import message_templates as mt


class SendError(Exception):
    """Raised when a send cannot proceed (missing recipient, bad channel...)."""


def _record_sent(invoice, channel):
    """Stamp the invoice as sent; promote draft -> sent (never paid/void)."""
    invoice.sent_at = datetime.utcnow()
    invoice.sent_channel = channel
    if invoice.status == 'draft':
        invoice.status = 'sent'


def build_whatsapp_url(phone_e164, text):
    return f"https://wa.me/{phone_e164}?text={quote(text)}"


def send_invoice(invoice, firm, client, channel, *, pdf_bytes=None,
                 subject=None, body=None, transport=None, base_url=None,
                 currency='INR'):
    """Send `invoice` to `client` over `channel`.

    Returns a dict describing the result. For 'whatsapp' it includes
    `whatsapp_url` for the frontend to open. Caller commits the DB session.
    """
    link = build_link(invoice.user_id, invoice.id, base_url=base_url)
    context = mt.build_context(invoice, firm, client, link, currency=currency)

    if channel == 'email':
        if not getattr(client, 'email', None):
            raise SendError('Client has no email address')
        # Provided overrides are still run through the formatter so placeholders
        # (notably {invoice_link}, which the client can't compute) resolve.
        default_subject, default_body = mt.render_email(firm, context)
        subject = mt.render(subject, context) if subject is not None else default_subject
        body = mt.render(body, context) if body is not None else default_body

        if transport is None:
            from app.services.email_service import get_transport
            transport = get_transport()

        pdf_name = f"Invoice_{invoice.invoice_number.replace('/', '_')}.pdf"
        transport.send(
            to=client.email,
            subject=subject,
            body=body,
            pdf_bytes=pdf_bytes,
            pdf_name=pdf_name,
            from_name=getattr(firm, 'firm_name', None) if firm else None,
            reply_to=getattr(firm, 'firm_email', None) if firm else None,
        )
        _record_sent(invoice, 'email')
        return {'channel': 'email', 'sent_to': client.email}

    if channel == 'whatsapp':
        phone = normalize_e164(getattr(client, 'phone', None))
        if not phone:
            raise SendError('Client has no valid phone number')
        text = mt.render(body, context) if body is not None else mt.render_whatsapp(firm, context)
        url = build_whatsapp_url(phone, text)
        # Best-effort: we can't confirm the user actually taps send in WhatsApp.
        _record_sent(invoice, 'whatsapp')
        return {'channel': 'whatsapp', 'whatsapp_url': url}

    raise SendError(f"Unknown channel: {channel}")
