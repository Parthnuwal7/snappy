"""Tests for the invites API (create/list/revoke + public accept)."""
import pytest

from app.models.models import db
from app.models.auth import User, Role, FirmInvite
from app.services import invite_service


def test_create_invite_requires_permission(client, make_owner):
    headers, firm_id = make_owner()
    with client.application.app_context():
        bare = Role(firm_id=firm_id, name='Bare', permissions=[], is_system=False)
        db.session.add(bare)
        db.session.commit()
        db.session.add(User(supabase_id='sb-bare', email='bare@firm.com',
                            firm_id=firm_id, role_id=bare.id))
        db.session.commit()
    import jwt as _pyjwt
    token = _pyjwt.encode({'sub': 'sb-bare', 'email': 'bare@firm.com',
                           'aud': 'authenticated'}, 'test-secret', algorithm='HS256')
    resp = client.post('/api/v1/firm/invites',
                       headers={'Authorization': f'Bearer {token}'},
                       json={'email': 'x@firm.com', 'role_id': 1})
    assert resp.status_code == 403


def test_create_and_list_invite(client, make_owner, monkeypatch):
    # Stub the Supabase inviter so the endpoint never makes a real auth call,
    # and disable the Resend fallback transport.
    monkeypatch.setattr('app.services.invite_service.supabase_email_inviter',
                        lambda **kw: 'sent')
    monkeypatch.setattr('app.api.invites.get_transport', lambda: None)
    headers, firm_id = make_owner()
    with client.application.app_context():
        staff_id = Role.query.filter_by(firm_id=firm_id, name='Staff').first().id
    resp = client.post('/api/v1/firm/invites', headers=headers,
                       json={'email': 'New@Firm.com', 'role_id': staff_id})
    assert resp.status_code == 201
    body = resp.get_json()
    assert body['email'] == 'new@firm.com'
    assert body['status'] == 'pending'
    assert 'token' not in body  # never leak the token

    listed = client.get('/api/v1/firm/invites', headers=headers).get_json()
    assert any(i['email'] == 'new@firm.com' for i in listed)


def test_revoke_invite(client, make_owner, monkeypatch):
    monkeypatch.setattr('app.services.invite_service.supabase_email_inviter',
                        lambda **kw: 'sent')
    monkeypatch.setattr('app.api.invites.get_transport', lambda: None)
    headers, firm_id = make_owner()
    with client.application.app_context():
        staff_id = Role.query.filter_by(firm_id=firm_id, name='Staff').first().id
    created = client.post('/api/v1/firm/invites', headers=headers,
                          json={'email': 'new@firm.com', 'role_id': staff_id}).get_json()
    resp = client.delete(f"/api/v1/firm/invites/{created['id']}", headers=headers)
    assert resp.status_code == 200
    with client.application.app_context():
        assert FirmInvite.query.get(created['id']).status == 'revoked'


def test_public_accept_invite(client, make_owner):
    # The accept endpoint is authenticated (the joiner has a Supabase identity)
    # but firm-agnostic: the user has no firm yet.
    headers, firm_id = make_owner()
    with client.application.app_context():
        staff_id = Role.query.filter_by(firm_id=firm_id, name='Staff').first().id
        owner_id = User.query.filter_by(email='owner@firm.com').first().id
        inv = invite_service.create_invite(firm_id=firm_id, email='join@firm.com',
                                           role_id=staff_id, invited_by=owner_id)
        db.session.commit()
        token = inv.token
        # The joiner authenticates with their own Supabase token (no firm yet).
        joiner = User(supabase_id='sb-join', email='join@firm.com')
        db.session.add(joiner)
        db.session.commit()
    import jwt as _pyjwt
    jtoken = _pyjwt.encode({'sub': 'sb-join', 'email': 'join@firm.com',
                            'aud': 'authenticated'}, 'test-secret', algorithm='HS256')
    resp = client.post('/api/v1/invites/accept',
                       headers={'Authorization': f'Bearer {jtoken}'},
                       json={'token': token})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body['firm_id'] == firm_id
    with client.application.app_context():
        joined = User.query.filter_by(email='join@firm.com').first()
        assert joined.firm_id == firm_id
        assert joined.role_id == staff_id


def test_accept_invalid_token_returns_400(client, make_owner):
    make_owner()  # ensure secret monkeypatched
    with client.application.app_context():
        joiner = User(supabase_id='sb-bad', email='bad@firm.com')
        db.session.add(joiner)
        db.session.commit()
    import jwt as _pyjwt
    jtoken = _pyjwt.encode({'sub': 'sb-bad', 'email': 'bad@firm.com',
                            'aud': 'authenticated'}, 'test-secret', algorithm='HS256')
    resp = client.post('/api/v1/invites/accept',
                       headers={'Authorization': f'Bearer {jtoken}'},
                       json={'token': 'garbage'})
    assert resp.status_code == 400


def test_accept_autocreates_local_user(client, make_owner):
    # A Supabase-invited user is authenticated but has no local users row yet;
    # accept must create it on the fly (matching the invite email).
    headers, firm_id = make_owner()
    with client.application.app_context():
        staff_id = Role.query.filter_by(firm_id=firm_id, name='Staff').first().id
        owner_id = User.query.filter_by(email='owner@firm.com').first().id
        inv = invite_service.create_invite(firm_id=firm_id, email='fresh@firm.com',
                                           role_id=staff_id, invited_by=owner_id)
        db.session.commit()
        token = inv.token
        assert User.query.filter_by(supabase_id='sb-fresh').first() is None
    import jwt as _pyjwt
    jtoken = _pyjwt.encode({'sub': 'sb-fresh', 'email': 'fresh@firm.com',
                            'aud': 'authenticated'}, 'test-secret', algorithm='HS256')
    resp = client.post('/api/v1/invites/accept',
                       headers={'Authorization': f'Bearer {jtoken}'},
                       json={'token': token})
    assert resp.status_code == 200
    with client.application.app_context():
        u = User.query.filter_by(supabase_id='sb-fresh').first()
        assert u is not None
        assert u.firm_id == firm_id
        assert u.role_id == staff_id
        assert u.is_onboarded is True
