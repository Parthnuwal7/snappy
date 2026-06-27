"""Tests for the Roles CRUD API (the module x action permission grid)."""
import pytest

from app.models.models import db
from app.models.auth import User, Role


def test_list_roles_returns_seeded_defaults(client, make_owner):
    headers, firm_id = make_owner()
    resp = client.get('/api/v1/firm/roles', headers=headers)
    assert resp.status_code == 200
    names = {r['name'] for r in resp.get_json()}
    assert {'Owner', 'Partner', 'Associate', 'Staff'} <= names


def test_create_role_with_valid_permissions(client, make_owner):
    headers, firm_id = make_owner()
    resp = client.post('/api/v1/firm/roles', headers=headers, json={
        'name': 'Paralegal',
        'description': 'Doc prep',
        'permissions': ['clients.read', 'invoices.read', 'invoices.create'],
    })
    assert resp.status_code == 201
    body = resp.get_json()
    assert body['name'] == 'Paralegal'
    assert set(body['permissions']) == {'clients.read', 'invoices.read', 'invoices.create'}
    assert body['is_system'] is False


def test_create_role_rejects_unknown_permission(client, make_owner):
    headers, firm_id = make_owner()
    resp = client.post('/api/v1/firm/roles', headers=headers, json={
        'name': 'Bogus',
        'permissions': ['clients.read', 'matters.teleport'],
    })
    assert resp.status_code == 400


def test_create_role_rejects_duplicate_name(client, make_owner):
    headers, firm_id = make_owner()
    resp = client.post('/api/v1/firm/roles', headers=headers, json={
        'name': 'Partner', 'permissions': [],
    })
    assert resp.status_code == 409


def test_update_role_permissions(client, make_owner):
    headers, firm_id = make_owner()
    with client.application.app_context():
        role_id = Role.query.filter_by(firm_id=firm_id, name='Staff').first().id
    resp = client.patch(f'/api/v1/firm/roles/{role_id}', headers=headers, json={
        'permissions': ['clients.read', 'clients.create', 'clients.update'],
    })
    assert resp.status_code == 200
    assert set(resp.get_json()['permissions']) == {
        'clients.read', 'clients.create', 'clients.update'}


def test_cannot_edit_owner_system_role(client, make_owner):
    headers, firm_id = make_owner()
    with client.application.app_context():
        owner_id = Role.query.filter_by(firm_id=firm_id, name='Owner').first().id
    resp = client.patch(f'/api/v1/firm/roles/{owner_id}', headers=headers, json={
        'permissions': ['clients.read'],
    })
    assert resp.status_code == 403


def test_cannot_delete_owner_system_role(client, make_owner):
    headers, firm_id = make_owner()
    with client.application.app_context():
        owner_id = Role.query.filter_by(firm_id=firm_id, name='Owner').first().id
    resp = client.delete(f'/api/v1/firm/roles/{owner_id}', headers=headers)
    assert resp.status_code == 403


def test_delete_unused_role(client, make_owner):
    headers, firm_id = make_owner()
    with client.application.app_context():
        role_id = Role.query.filter_by(firm_id=firm_id, name='Associate').first().id
    resp = client.delete(f'/api/v1/firm/roles/{role_id}', headers=headers)
    assert resp.status_code == 200
    with client.application.app_context():
        assert Role.query.get(role_id) is None


def test_cannot_delete_role_in_use(client, make_owner):
    headers, firm_id = make_owner()
    with client.application.app_context():
        role = Role.query.filter_by(firm_id=firm_id, name='Staff').first()
        role_id = role.id
        db.session.add(User(supabase_id='sb-x', email='x@firm.com',
                            firm_id=firm_id, role_id=role_id))
        db.session.commit()
    resp = client.delete(f'/api/v1/firm/roles/{role_id}', headers=headers)
    assert resp.status_code == 409


def test_roles_isolated_per_firm(client, make_owner):
    headers_a, _ = make_owner()
    headers_b, firm_b = make_owner(supabase_id='sb-b', email='b@firm.com',
                                   firm_name='Firm B')
    # Owner of firm B creates a role; firm A must not see it.
    client.post('/api/v1/firm/roles', headers=headers_b,
                json={'name': 'BOnly', 'permissions': []})
    names_a = {r['name'] for r in client.get('/api/v1/firm/roles', headers=headers_a).get_json()}
    assert 'BOnly' not in names_a
