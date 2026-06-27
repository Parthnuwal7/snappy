from app.models.models import db, Client
from app.models.auth import User


def _cid(client, firm_id):
    with client.application.app_context():
        c = Client(firm_id=firm_id, created_by_user_id=User.query.filter_by(
            email='owner@firm.com').first().id, name='X')
        db.session.add(c); db.session.commit()
        return c.id


def test_meta_includes_expense_categories(client, make_owner):
    headers, _ = make_owner()
    body = client.get('/api/v1/case-files/meta', headers=headers).get_json()
    assert {c['key'] for c in body['expense_categories']} >= {'court_fee', 'travel', 'misc'}


def test_create_records_initial_stage_and_agreed_fee(client, make_owner):
    headers, firm_id = make_owner()
    cid = _cid(client, firm_id)
    created = client.post('/api/v1/case-files', headers=headers,
                          json={'title': 'M', 'client_id': cid, 'agreed_fee': 50000}).get_json()
    assert created['agreed_fee'] == 50000.0
    hist = client.get(f"/api/v1/case-files/{created['id']}/stage-history", headers=headers).get_json()
    assert len(hist) == 1
    assert hist[0]['from_stage'] is None and hist[0]['to_stage'] == 'engaged'


def test_move_and_patch_record_stage_changes(client, make_owner):
    headers, firm_id = make_owner()
    cid = _cid(client, firm_id)
    cf = client.post('/api/v1/case-files', headers=headers, json={'title': 'M', 'client_id': cid}).get_json()
    client.patch(f"/api/v1/case-files/{cf['id']}/move", headers=headers, json={'stage': 'filed'})
    client.patch(f"/api/v1/case-files/{cf['id']}", headers=headers, json={'stage': 'hearings_evidence'})
    client.patch(f"/api/v1/case-files/{cf['id']}", headers=headers, json={'title': 'no stage change'})
    hist = client.get(f"/api/v1/case-files/{cf['id']}/stage-history", headers=headers).get_json()
    assert [h['to_stage'] for h in hist] == ['engaged', 'filed', 'hearings_evidence']
