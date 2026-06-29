"""GET /auth/me surfaces profile fields, derived setup state, and pending invites."""
import jwt as _pyjwt
from app.models.models import db
from app.models.auth import User, Role, BankAccount, FirmInvite
from app.services import invite_service


def _token(sub, email):
    return {'Authorization': 'Bearer ' + _pyjwt.encode(
        {'sub': sub, 'email': email, 'aud': 'authenticated'},
        'test-secret', algorithm='HS256')}


def _onboard(client, headers, full_name='Owner O', firm_name='Owner Firm'):
    return client.post('/api/v1/auth/onboard', headers=headers,
                       json={'full_name': full_name, 'firm_name': firm_name})


def test_me_setup_all_false_after_minimal_onboard(client, make_owner):
    make_owner()
    h = _token('sb-me', 'me@firm.com')
    _onboard(client, h)
    body = client.get('/api/v1/auth/me', headers=h).get_json()
    assert body['profile']['full_name'] == 'Owner O'
    assert body['profile']['checklist_dismissed'] is False
    s = body['setup']
    assert s == {'bank': False, 'branding': False, 'billing': False,
                 'team': False, 'dismissed': False, 'complete': False}


def test_me_setup_flips_true_as_data_appears(client, make_owner):
    make_owner()
    h = _token('sb-me2', 'me2@firm.com')
    _onboard(client, h, firm_name='Filled Firm')
    with client.application.app_context():
        u = User.query.filter_by(email='me2@firm.com').first()
        firm_id = u.firm_id
        fd = u.firm_details
        fd.logo_path = 'logos/x.png'
        fd.billing_terms = 'Net 30'
        db.session.add(BankAccount(user_id=u.id, firm_id=firm_id,
                                   created_by_user_id=u.id, bank_name='SBI'))
        staff = Role.query.filter_by(firm_id=firm_id, name='Staff').first()
        invite_service.create_invite(firm_id=firm_id, email='t@firm.com',
                                     role_id=staff.id, invited_by=u.id)
        db.session.commit()
    s = client.get('/api/v1/auth/me', headers=h).get_json()['setup']
    assert s == {'bank': True, 'branding': True, 'billing': True,
                 'team': True, 'dismissed': False, 'complete': True}


def test_me_surfaces_pending_invite_for_firmless_user(client, make_owner):
    headers, firm_id = make_owner()
    with client.application.app_context():
        staff = Role.query.filter_by(firm_id=firm_id, name='Staff').first()
        owner_id = User.query.filter_by(email='owner@firm.com').first().id
        invite_service.create_invite(firm_id=firm_id, email='invitee@firm.com',
                                     role_id=staff.id, invited_by=owner_id)
        db.session.commit()
        db.session.add(User(supabase_id='sb-inv', email='invitee@firm.com'))
        db.session.commit()
    body = client.get('/api/v1/auth/me', headers=_token('sb-inv', 'invitee@firm.com')).get_json()
    assert body['pending_invite'] is not None
    assert body['pending_invite']['role_name'] == 'Staff'
    assert body['pending_invite']['firm_name']  # firm display name present
