"""Tests for the firm profile + members API (firm-scoped, permission-gated)."""
import pytest

from app.models.models import db
from app.models.auth import User, Firm, Role
from app.services.firm_service import provision_firm_for_user


def _add_member(firm_id, *, supabase_id, email, role_name):
    """Create a second user inside an existing firm with the named role."""
    role = Role.query.filter_by(firm_id=firm_id, name=role_name).first()
    user = User(supabase_id=supabase_id, email=email,
                firm_id=firm_id, role_id=role.id)
    db.session.add(user)
    db.session.commit()
    return user.id


def test_get_firm_returns_tenant_and_profile(client, make_owner):
    headers, firm_id = make_owner()
    resp = client.get('/api/v1/firm', headers=headers)
    assert resp.status_code == 200
    body = resp.get_json()
    assert body['id'] == firm_id
    assert body['name'] == 'Test Firm'


def test_patch_firm_renames_tenant(client, make_owner):
    headers, firm_id = make_owner()
    resp = client.patch('/api/v1/firm', headers=headers, json={'name': 'Renamed LLP'})
    assert resp.status_code == 200
    assert resp.get_json()['name'] == 'Renamed LLP'
    with client.application.app_context():
        assert Firm.query.get(firm_id).name == 'Renamed LLP'


def test_list_members_includes_owner_and_their_role(client, make_owner):
    headers, firm_id = make_owner()
    with client.application.app_context():
        _add_member(firm_id, supabase_id='sb-assoc', email='a@firm.com',
                    role_name='Associate')
    resp = client.get('/api/v1/firm/members', headers=headers)
    assert resp.status_code == 200
    members = resp.get_json()
    assert len(members) == 2
    by_email = {m['email']: m for m in members}
    assert by_email['owner@firm.com']['role_name'] == 'Owner'
    assert by_email['a@firm.com']['role_name'] == 'Associate'


def test_change_member_role(client, make_owner):
    headers, firm_id = make_owner()
    with client.application.app_context():
        member_id = _add_member(firm_id, supabase_id='sb-assoc',
                                email='a@firm.com', role_name='Associate')
        partner_id = Role.query.filter_by(firm_id=firm_id, name='Partner').first().id
    resp = client.patch(f'/api/v1/firm/members/{member_id}', headers=headers,
                        json={'role_id': partner_id})
    assert resp.status_code == 200
    assert resp.get_json()['role_name'] == 'Partner'


def test_cannot_demote_last_owner(client, make_owner):
    headers, firm_id = make_owner()
    with client.application.app_context():
        owner = User.query.filter_by(email='owner@firm.com').first()
        owner_id = owner.id
        partner_id = Role.query.filter_by(firm_id=firm_id, name='Partner').first().id
    resp = client.patch(f'/api/v1/firm/members/{owner_id}', headers=headers,
                        json={'role_id': partner_id})
    assert resp.status_code == 409


def test_cannot_remove_last_owner(client, make_owner):
    headers, firm_id = make_owner()
    with client.application.app_context():
        owner_id = User.query.filter_by(email='owner@firm.com').first().id
    resp = client.delete(f'/api/v1/firm/members/{owner_id}', headers=headers)
    assert resp.status_code == 409


def test_remove_member(client, make_owner):
    headers, firm_id = make_owner()
    with client.application.app_context():
        member_id = _add_member(firm_id, supabase_id='sb-staff',
                                email='s@firm.com', role_name='Staff')
    resp = client.delete(f'/api/v1/firm/members/{member_id}', headers=headers)
    assert resp.status_code == 200
    with client.application.app_context():
        assert User.query.get(member_id).firm_id is None


def test_permissions_catalog_lists_modules(client, make_owner):
    headers, _ = make_owner()
    resp = client.get('/api/v1/firm/permissions/catalog', headers=headers)
    assert resp.status_code == 200
    body = resp.get_json()
    keys = {m['key'] for m in body['modules']}
    assert {'clients', 'invoices', 'members', 'roles'} <= keys


def test_members_endpoint_denies_without_permission(client, make_owner):
    # A Staff member lacks members.read on default seed? Staff has members.read.
    # Use a role with no members.read: create a bare custom role.
    headers, firm_id = make_owner()
    with client.application.app_context():
        bare = Role(firm_id=firm_id, name='Bare', permissions=[], is_system=False)
        db.session.add(bare)
        db.session.commit()
        user = User(supabase_id='sb-bare', email='bare@firm.com',
                    firm_id=firm_id, role_id=bare.id)
        db.session.add(user)
        db.session.commit()
    import jwt as _pyjwt
    token = _pyjwt.encode({'sub': 'sb-bare', 'email': 'bare@firm.com',
                           'aud': 'authenticated'}, 'test-secret', algorithm='HS256')
    bare_headers = {'Authorization': f'Bearer {token}'}
    resp = client.get('/api/v1/firm/members', headers=bare_headers)
    assert resp.status_code == 403
