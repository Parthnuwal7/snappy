"""The /me endpoint must surface the caller's firm membership + permissions."""
import pytest

from app.models.models import db
from app.models.auth import User, Role
from app.rbac.permissions import ALL_PERMISSIONS


def test_me_includes_owner_membership_with_all_permissions(client, make_owner):
    headers, firm_id = make_owner()
    body = client.get('/api/v1/auth/me', headers=headers).get_json()
    membership = body['membership']
    assert membership['firm_id'] == firm_id
    assert membership['role']['name'] == 'Owner'
    assert set(membership['permissions']) == set(ALL_PERMISSIONS)


def test_me_membership_reflects_limited_role(client, make_owner):
    headers, firm_id = make_owner()
    # Make a member with a bare custom role and read /me as them.
    with client.application.app_context():
        bare = Role(firm_id=firm_id, name='Bare',
                    permissions=['clients.read'], is_system=False)
        db.session.add(bare)
        db.session.commit()
        db.session.add(User(supabase_id='sb-bare', email='bare@firm.com',
                            firm_id=firm_id, role_id=bare.id))
        db.session.commit()
    import jwt as _pyjwt
    token = _pyjwt.encode({'sub': 'sb-bare', 'email': 'bare@firm.com',
                           'aud': 'authenticated'}, 'test-secret', algorithm='HS256')
    body = client.get('/api/v1/auth/me',
                      headers={'Authorization': f'Bearer {token}'}).get_json()
    assert body['membership']['permissions'] == ['clients.read']
    assert body['membership']['role']['name'] == 'Bare'


def test_me_membership_null_when_no_firm(client, make_owner, monkeypatch):
    # A user with a Supabase identity but no firm yet (pre-onboarding / invited).
    make_owner()  # ensures jwt secret is monkeypatched to 'test-secret'
    with client.application.app_context():
        db.session.add(User(supabase_id='sb-lonely', email='lonely@x.com'))
        db.session.commit()
    import jwt as _pyjwt
    token = _pyjwt.encode({'sub': 'sb-lonely', 'email': 'lonely@x.com',
                           'aud': 'authenticated'}, 'test-secret', algorithm='HS256')
    body = client.get('/api/v1/auth/me',
                      headers={'Authorization': f'Bearer {token}'}).get_json()
    assert body['membership'] is None
