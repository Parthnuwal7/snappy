"""Transactional email sending behind a pluggable transport.

v1 ships `ResendTransport`. A future `GmailOAuthTransport` (Phase 2 — let firms
send from their own Gmail) can implement the same `EmailTransport` interface and
be selected per-firm without touching callers.

ResendTransport talks to Resend's REST API directly with `requests` (already a
dependency) rather than pulling in the Resend SDK — the surface we need is one
POST, and keeping the dep list small avoids version churn.
"""
import base64
import os


class EmailError(Exception):
    """Raised when an email fails to send (misconfig or provider error)."""


class EmailTransport:
    """Interface for sending one invoice email with a PDF attachment."""

    def send(self, *, to, subject, body, pdf_bytes=None, pdf_name=None,
             from_name=None, reply_to=None, cc=None):  # pragma: no cover - interface
        raise NotImplementedError


class ResendTransport(EmailTransport):
    """Send via Resend's HTTP API (https://resend.com)."""

    ENDPOINT = 'https://api.resend.com/emails'

    def __init__(self, api_key=None, from_address=None):
        self.api_key = api_key or os.getenv('RESEND_API_KEY')
        self.from_address = from_address or os.getenv('INVOICE_EMAIL_FROM', 'invoices@snappyco.org')

    def send(self, *, to, subject, body, pdf_bytes=None, pdf_name=None,
             from_name=None, reply_to=None, cc=None):
        if not self.api_key:
            raise EmailError('RESEND_API_KEY is not configured')

        # Display name in the From header, e.g. "Acme Legal <invoices@snappyco.org>".
        sender = f"{from_name} <{self.from_address}>" if from_name else self.from_address

        payload = {
            'from': sender,
            'to': [to],
            'subject': subject,
            # Body is plain text; send as both text and minimal html for clients
            # that prefer html. \n -> <br> keeps the layout readable.
            'text': body,
            'html': '<div style="white-space:pre-wrap">' + _escape_html(body) + '</div>',
        }
        if reply_to:
            payload['reply_to'] = reply_to
        if cc:
            payload['cc'] = [cc]
        if pdf_bytes is not None:
            payload['attachments'] = [{
                'filename': pdf_name or 'invoice.pdf',
                'content': base64.b64encode(pdf_bytes).decode('ascii'),
            }]

        import requests
        try:
            resp = requests.post(
                self.ENDPOINT,
                json=payload,
                headers={'Authorization': f'Bearer {self.api_key}'},
                timeout=30,
            )
        except requests.RequestException as e:
            raise EmailError(f'Email provider request failed: {e}') from e

        if resp.status_code >= 400:
            raise EmailError(f'Email provider error {resp.status_code}: {resp.text}')
        return resp.json() if resp.content else {}


def _escape_html(text: str) -> str:
    return (text.replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;'))


# Default transport factory. Swappable in tests / future Phase 2.
def get_transport() -> EmailTransport:
    return ResendTransport()
