"""Tests for the public (unauthenticated) invoice endpoints."""
from datetime import date

from app.models.models import db, Client, Invoice, InvoiceItem
from app.models.auth import User, FirmDetails
from app.services.firm_service import provision_firm_for_user
from app.utils.invoice_links import sign


def _seed(app, status='sent'):
    with app.app_context():
        db.create_all()
        user = User(supabase_id='sb-pub', email='u@example.com')
        db.session.add(user)
        db.session.flush()
        tenant = provision_firm_for_user(user, 'Acme')
        db.session.add(FirmDetails(user_id=user.id, firm_id=tenant.id,
                                   firm_name='Acme', firm_address='X'))
        client = Client(firm_id=tenant.id, created_by_user_id=user.id,
                        name='Rao', email='c@example.com')
        db.session.add(client)
        db.session.flush()
        inv = Invoice(firm_id=tenant.id, created_by_user_id=user.id,
                      invoice_number='INV/0007', client_id=client.id,
                      invoice_date=date(2026, 6, 1), total=5900, status=status)
        inv.items.append(InvoiceItem(description='Work', quantity=1, rate=5900, amount=5900))
        db.session.add(inv)
        db.session.commit()
        return user.id, inv.id


def test_valid_signature_returns_safe_subset(app, client):
    user_id, inv_id = _seed(app)
    sig = sign(user_id, inv_id)
    resp = client.get(f'/api/v1/public/invoices/{user_id}/{inv_id}?sig={sig}')
    assert resp.status_code == 200
    body = resp.get_json()
    assert body['invoice_number'] == 'INV/0007'
    assert body['client_name'] == 'Rao'
    assert body['firm']['firm_name'] == 'Acme'
    assert len(body['items']) == 1
    # Must not leak internal identifiers.
    assert 'user_id' not in body
    assert 'client_id' not in body


def test_bad_signature_is_forbidden(app, client):
    user_id, inv_id = _seed(app)
    resp = client.get(f'/api/v1/public/invoices/{user_id}/{inv_id}?sig=deadbeef')
    assert resp.status_code == 403


def test_void_invoice_not_available(app, client):
    user_id, inv_id = _seed(app, status='void')
    sig = sign(user_id, inv_id)
    resp = client.get(f'/api/v1/public/invoices/{user_id}/{inv_id}?sig={sig}')
    assert resp.status_code == 404
