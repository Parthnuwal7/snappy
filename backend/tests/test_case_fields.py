"""Richer litigation fields + priority on case files."""
from app.models.models import db, Client
from app.models.auth import User


def _client_id(app_client, firm_id):
    with app_client.application.app_context():
        c = Client(firm_id=firm_id, created_by_user_id=User.query.filter_by(
            email='owner@firm.com').first().id, name='X Corp')
        db.session.add(c)
        db.session.commit()
        return c.id


def test_meta_includes_priorities(client, make_owner):
    headers, _ = make_owner()
    body = client.get('/api/v1/case-files/meta', headers=headers).get_json()
    keys = [p['key'] for p in body['priorities']]
    assert keys == ['low', 'normal', 'high', 'urgent']


def test_create_with_litigation_fields(client, make_owner):
    headers, firm_id = make_owner()
    cid = _client_id(client, firm_id)
    resp = client.post('/api/v1/case-files', headers=headers, json={
        'title': 'X vs State', 'client_id': cid,
        'priority': 'high', 'jurisdiction': 'Delhi',
        'act_section': 'Art. 226', 'opposing_counsel': 'Adv. Rao',
        'filing_date': '2026-05-01',
    })
    assert resp.status_code == 201
    body = resp.get_json()
    assert body['priority'] == 'high'
    assert body['jurisdiction'] == 'Delhi'
    assert body['act_section'] == 'Art. 226'
    assert body['opposing_counsel'] == 'Adv. Rao'
    assert body['filing_date'] == '2026-05-01'


def test_create_defaults_priority_to_normal(client, make_owner):
    headers, firm_id = make_owner()
    cid = _client_id(client, firm_id)
    body = client.post('/api/v1/case-files', headers=headers, json={
        'title': 'M', 'client_id': cid}).get_json()
    assert body['priority'] == 'normal'


def test_create_rejects_invalid_priority(client, make_owner):
    headers, firm_id = make_owner()
    cid = _client_id(client, firm_id)
    resp = client.post('/api/v1/case-files', headers=headers, json={
        'title': 'M', 'client_id': cid, 'priority': 'panic'})
    assert resp.status_code == 400


def test_patch_updates_litigation_fields(client, make_owner):
    headers, firm_id = make_owner()
    cid = _client_id(client, firm_id)
    created = client.post('/api/v1/case-files', headers=headers, json={
        'title': 'M', 'client_id': cid}).get_json()
    resp = client.patch(f"/api/v1/case-files/{created['id']}", headers=headers, json={
        'priority': 'urgent', 'jurisdiction': 'Mumbai', 'filing_date': '2026-06-15'})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body['priority'] == 'urgent'
    assert body['jurisdiction'] == 'Mumbai'
    assert body['filing_date'] == '2026-06-15'
