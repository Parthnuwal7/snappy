import pytest

from app.models.models import db, Client
from app.models.auth import User


def _client_id(app_client, firm_id):
    with app_client.application.app_context():
        c = Client(firm_id=firm_id, created_by_user_id=User.query.filter_by(
            email='owner@firm.com').first().id, name='X Corp')
        db.session.add(c)
        db.session.commit()
        return c.id


def test_meta_lists_stages_and_kinds(client, make_owner):
    headers, _ = make_owner()
    body = client.get('/api/v1/case-files/meta', headers=headers).get_json()
    assert [s['key'] for s in body['stages']][0] == 'engaged'
    assert 'hearing' in body['event_kinds']


def test_meta_includes_stage_guides_and_flow(client, make_owner):
    headers, _ = make_owner()
    body = client.get('/api/v1/case-files/meta', headers=headers).get_json()
    assert 'stage_guides' in body and 'engaged' in body['stage_guides']
    assert body['stage_guides']['engaged']['actions'][0]['key'] == 'note'
    assert body['stage_flow']['engaged'] == 'notice'
    assert body['stage_flow']['closed'] is None


def test_meta_includes_exhibit_catalogs(client, make_owner):
    headers, _ = make_owner()
    body = client.get('/api/v1/case-files/meta', headers=headers).get_json()
    assert {s['key'] for s in body['exhibit_statuses']} == {'marked', 'admitted', 'objected', 'denied'}
    assert any(p['key'] == 'petitioner' for p in body['exhibit_parties'])


def test_meta_includes_hearing_purposes(client, make_owner):
    headers, _ = make_owner()
    body = client.get('/api/v1/case-files/meta', headers=headers).get_json()
    assert any(p['key'] == 'evidence' for p in body['hearing_purposes'])


def test_create_case_autonumbers_and_adds_parties(client, make_owner):
    headers, firm_id = make_owner()
    cid = _client_id(client, firm_id)
    resp = client.post('/api/v1/case-files', headers=headers, json={
        'title': 'X vs State', 'client_id': cid, 'court': 'Delhi HC',
        'parties': [{'name': 'X', 'role': 'petitioner'},
                    {'name': 'State', 'role': 'respondent'}],
    })
    assert resp.status_code == 201
    body = resp.get_json()
    assert body['case_number'].startswith('CF/')
    assert body['stage'] == 'engaged'
    assert len(body['parties']) == 2


def test_create_rejects_other_firms_client(client, make_owner):
    headers, _ = make_owner()
    headers_b, firm_b = make_owner(supabase_id='sb-b', email='b@firm.com', firm_name='B')
    cid_b = _client_id(client, firm_b)
    resp = client.post('/api/v1/case-files', headers=headers, json={
        'title': 'Bad', 'client_id': cid_b})
    assert resp.status_code == 404


def test_list_and_get_detail(client, make_owner):
    headers, firm_id = make_owner()
    cid = _client_id(client, firm_id)
    created = client.post('/api/v1/case-files', headers=headers, json={
        'title': 'Matter A', 'client_id': cid}).get_json()
    listing = client.get('/api/v1/case-files', headers=headers).get_json()
    assert any(c['id'] == created['id'] for c in listing)
    detail = client.get(f"/api/v1/case-files/{created['id']}", headers=headers).get_json()
    assert detail['title'] == 'Matter A'
    assert 'parties' in detail


def test_patch_updates_fields_and_replaces_parties(client, make_owner):
    headers, firm_id = make_owner()
    cid = _client_id(client, firm_id)
    created = client.post('/api/v1/case-files', headers=headers, json={
        'title': 'Matter A', 'client_id': cid,
        'parties': [{'name': 'Old', 'role': 'petitioner'}]}).get_json()
    resp = client.patch(f"/api/v1/case-files/{created['id']}", headers=headers, json={
        'title': 'Matter A (amended)',
        'parties': [{'name': 'New', 'role': 'appellant'}]})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body['title'] == 'Matter A (amended)'
    assert len(body['parties']) == 1
    assert body['parties'][0]['name'] == 'New'


def test_move_changes_stage(client, make_owner):
    headers, firm_id = make_owner()
    cid = _client_id(client, firm_id)
    created = client.post('/api/v1/case-files', headers=headers, json={
        'title': 'Matter A', 'client_id': cid}).get_json()
    resp = client.patch(f"/api/v1/case-files/{created['id']}/move", headers=headers,
                        json={'stage': 'filed', 'position': 2})
    assert resp.status_code == 200
    assert resp.get_json()['stage'] == 'filed'


def test_move_rejects_invalid_stage(client, make_owner):
    headers, firm_id = make_owner()
    cid = _client_id(client, firm_id)
    created = client.post('/api/v1/case-files', headers=headers, json={
        'title': 'M', 'client_id': cid}).get_json()
    resp = client.patch(f"/api/v1/case-files/{created['id']}/move", headers=headers,
                        json={'stage': 'nowhere'})
    assert resp.status_code == 400


def test_delete_case(client, make_owner):
    headers, firm_id = make_owner()
    cid = _client_id(client, firm_id)
    created = client.post('/api/v1/case-files', headers=headers, json={
        'title': 'M', 'client_id': cid}).get_json()
    assert client.delete(f"/api/v1/case-files/{created['id']}", headers=headers).status_code == 200
    assert client.get(f"/api/v1/case-files/{created['id']}", headers=headers).status_code == 404
