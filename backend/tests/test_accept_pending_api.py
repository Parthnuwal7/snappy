"""Direct-signup reconciliation: POST /invites/accept-pending (no token)."""
import jwt as _pyjwt
from app.models.models import db
from app.models.auth import User, Role, Firm
from app.services import invite_service


def _token(sub, email):
    return {'Authorization': 'Bearer ' + _pyjwt.encode(
        {'sub': sub, 'email': email, 'aud': 'authenticated'},
        'test-secret', algorithm='HS256')}


def test_accept_pending_routes_into_firm(client, make_owner):
    headers, firm_id = make_owner()
    with client.application.app_context():
        staff_id = Role.query.filter_by(firm_id=firm_id, name='Staff').first().id
        owner_id = User.query.filter_by(email='owner@firm.com').first().id
        invite_service.create_invite(firm_id=firm_id, email='direct@firm.com',
                                     role_id=staff_id, invited_by=owner_id)
        db.session.commit()
        firm_count_before = Firm.query.count()
    resp = client.post('/api/v1/invites/accept-pending',
                       headers=_token('sb-direct', 'direct@firm.com'))
    assert resp.status_code == 200
    body = resp.get_json()
    assert body['firm_id'] == firm_id
    with client.application.app_context():
        u = User.query.filter_by(email='direct@firm.com').first()
        assert u.firm_id == firm_id
        assert u.role_id == staff_id
        assert u.is_onboarded is True
        # No second firm was provisioned.
        assert Firm.query.count() == firm_count_before


def test_accept_pending_without_invite_returns_400(client, make_owner):
    make_owner()
    resp = client.post('/api/v1/invites/accept-pending',
                       headers=_token('sb-none', 'noinvite@firm.com'))
    assert resp.status_code == 400
