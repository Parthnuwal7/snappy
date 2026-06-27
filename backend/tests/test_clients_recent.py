"""Tests for the recent-clients query helper."""
from datetime import date
from app.models.models import db, Client, Invoice
from app.models.auth import User
from app.services.firm_service import provision_firm_for_user
from app.api.clients import recent_clients_for_firm


def test_recent_clients_orders_by_latest_invoice(app):
    with app.app_context():
        db.create_all()
        user = User(supabase_id='sb-test-1', email='t@example.com')
        db.session.add(user)
        db.session.flush()
        tenant = provision_firm_for_user(user, 'T Firm')
        fid = tenant.id
        a = Client(firm_id=fid, created_by_user_id=user.id, name='Alpha')
        b = Client(firm_id=fid, created_by_user_id=user.id, name='Beta')
        c = Client(firm_id=fid, created_by_user_id=user.id, name='Gamma (never billed)')
        db.session.add_all([a, b, c])
        db.session.flush()
        # Beta billed most recently, Alpha earlier. Gamma never billed.
        db.session.add(Invoice(firm_id=fid, created_by_user_id=user.id, invoice_number='INV/0001',
                               client_id=a.id, invoice_date=date(2026, 1, 1)))
        db.session.add(Invoice(firm_id=fid, created_by_user_id=user.id, invoice_number='INV/0002',
                               client_id=b.id, invoice_date=date(2026, 6, 1)))
        db.session.commit()

        result = recent_clients_for_firm(fid, limit=6)
        names = [c['name'] for c in result]
        assert names == ['Beta', 'Alpha']
