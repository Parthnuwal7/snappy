"""Tests for the invoice send orchestration service."""
from datetime import date
import pytest

from app.models.models import db, Client, Invoice, InvoiceItem
from app.models.auth import User, FirmDetails
from app.services.send_service import send_invoice, SendError


class FakeTransport:
    """Captures the email instead of hitting a provider."""
    def __init__(self):
        self.sent = None

    def send(self, **kwargs):
        self.sent = kwargs
        return {'id': 'fake'}


def _seed(app, *, email='client@example.com', phone='9876543210', status='draft'):
    with app.app_context():
        db.create_all()
        user = User(supabase_id='sb-send', email='u@example.com')
        db.session.add(user)
        db.session.flush()
        firm = FirmDetails(user_id=user.id, firm_name='Acme', firm_address='X',
                           firm_email='acme@firm.com', currency='INR')
        db.session.add(firm)
        client = Client(user_id=user.id, name='Rao', email=email, phone=phone)
        db.session.add(client)
        db.session.flush()
        inv = Invoice(user_id=user.id, invoice_number='INV/0007', client_id=client.id,
                      invoice_date=date(2026, 6, 1), due_date=date(2026, 7, 1),
                      total=5900, status=status)
        inv.items.append(InvoiceItem(description='Work', quantity=1, rate=5900, amount=5900))
        db.session.add(inv)
        db.session.commit()
        return user.id, inv.id, firm.id, client.id


def test_email_send_records_sent_and_promotes_draft(app):
    _seed(app)
    with app.app_context():
        inv = Invoice.query.first()
        firm = FirmDetails.query.first()
        client = Client.query.first()
        transport = FakeTransport()
        result = send_invoice(inv, firm, client, 'email', pdf_bytes=b'%PDF',
                              transport=transport, base_url='https://app')
        db.session.commit()

        assert result['channel'] == 'email'
        assert transport.sent['to'] == 'client@example.com'
        assert transport.sent['reply_to'] == 'acme@firm.com'
        assert transport.sent['from_name'] == 'Acme'
        assert transport.sent['pdf_bytes'] == b'%PDF'
        assert 'INV/0007' in transport.sent['subject']
        assert inv.sent_channel == 'email'
        assert inv.sent_at is not None
        assert inv.status == 'sent'  # draft -> sent


def test_email_send_leaves_paid_status_untouched(app):
    _seed(app, status='paid')
    with app.app_context():
        inv = Invoice.query.first()
        send_invoice(inv, FirmDetails.query.first(), Client.query.first(),
                     'email', pdf_bytes=b'%PDF', transport=FakeTransport(),
                     base_url='https://app')
        assert inv.status == 'paid'
        assert inv.sent_channel == 'email'


def test_email_without_recipient_raises(app):
    _seed(app, email=None)
    with app.app_context():
        inv = Invoice.query.first()
        with pytest.raises(SendError):
            send_invoice(inv, FirmDetails.query.first(), Client.query.first(),
                         'email', pdf_bytes=b'%PDF', transport=FakeTransport())


def test_whatsapp_returns_url_and_records(app):
    _seed(app)
    with app.app_context():
        inv = Invoice.query.first()
        result = send_invoice(inv, FirmDetails.query.first(), Client.query.first(),
                              'whatsapp', base_url='https://app')
        db.session.commit()
        assert result['channel'] == 'whatsapp'
        assert result['whatsapp_url'].startswith('https://wa.me/919876543210?text=')
        assert inv.sent_channel == 'whatsapp'
        assert inv.status == 'sent'


def test_whatsapp_without_phone_raises(app):
    _seed(app, phone=None)
    with app.app_context():
        inv = Invoice.query.first()
        with pytest.raises(SendError):
            send_invoice(inv, FirmDetails.query.first(), Client.query.first(),
                         'whatsapp')


def test_edited_body_still_gets_link_injected(app):
    # The dialog leaves {invoice_link} as a literal token; the server must
    # resolve it even when the user supplied a custom body.
    _seed(app)
    with app.app_context():
        inv = Invoice.query.first()
        transport = FakeTransport()
        send_invoice(inv, FirmDetails.query.first(), Client.query.first(), 'email',
                     pdf_bytes=b'%PDF', transport=transport, base_url='https://app',
                     subject='Sub', body='See {invoice_link} please')
        body = transport.sent['body']
        assert '{invoice_link}' not in body
        assert f'https://app/i/{inv.user_id}/{inv.id}/' in body


def test_unknown_channel_raises(app):
    _seed(app)
    with app.app_context():
        inv = Invoice.query.first()
        with pytest.raises(SendError):
            send_invoice(inv, FirmDetails.query.first(), Client.query.first(), 'sms')
