"""NPCI UPI deep-link builder + QR PNG renderer.

Single source of truth for the ``upi://pay?…`` string used by both the PDF
(rendered server-side via segno) and the web invoice views (string handed to
the frontend, which draws the QR itself).
"""
from io import BytesIO
from urllib.parse import urlencode

import segno


def compose_note(upi_note, invoice_no):
    """Transaction note: user default prefixed onto the invoice number."""
    upi_note = (upi_note or '').strip()
    return f"{upi_note} — {invoice_no}" if upi_note else (invoice_no or '')


def build_upi_uri(upi_id, payee_name, amount=None, note=None, invoice_no=None):
    """Build a URL-encoded ``upi://pay`` deep link.

    Returns ``''`` when ``upi_id`` is missing (caller renders no QR). ``am`` is
    included only when ``amount`` is a positive number, formatted to 2 decimals.
    """
    if not upi_id:
        return ''
    params = [('pa', upi_id), ('pn', payee_name or ''), ('cu', 'INR')]
    if amount is not None and float(amount) > 0:
        params.insert(2, ('am', f"{float(amount):.2f}"))
    if note:
        params.append(('tn', note))
    if invoice_no:
        params.append(('tr', invoice_no))
    return 'upi://pay?' + urlencode(params)


def qr_png(uri):
    """Render ``uri`` to PNG bytes. Returns ``b''`` for an empty uri."""
    if not uri:
        return b''
    buf = BytesIO()
    segno.make(uri, error='m').save(buf, kind='png', scale=4, border=2)
    return buf.getvalue()
