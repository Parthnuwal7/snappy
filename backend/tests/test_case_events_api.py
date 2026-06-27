from app.models.models import db, Client
from app.models.auth import User


def _case(client, headers, firm_id):
    with client.application.app_context():
        c = Client(firm_id=firm_id, created_by_user_id=User.query.filter_by(
            email='owner@firm.com').first().id, name='X')
        db.session.add(c)
        db.session.commit()
        cid = c.id
    return client.post('/api/v1/case-files', headers=headers,
                       json={'title': 'M', 'client_id': cid}).get_json()['id']


def test_add_and_list_events_ordered(client, make_owner):
    headers, firm_id = make_owner()
    case_id = _case(client, headers, firm_id)
    client.post(f'/api/v1/case-files/{case_id}/events', headers=headers,
                json={'event_date': '2026-06-10', 'kind': 'hearing', 'title': 'Second hearing'})
    client.post(f'/api/v1/case-files/{case_id}/events', headers=headers,
                json={'event_date': '2026-06-01', 'kind': 'filing', 'title': 'Petition filed'})
    events = client.get(f'/api/v1/case-files/{case_id}/events', headers=headers).get_json()
    assert [e['title'] for e in events] == ['Petition filed', 'Second hearing']  # by event_date


def test_add_event_rejects_invalid_kind(client, make_owner):
    headers, firm_id = make_owner()
    case_id = _case(client, headers, firm_id)
    resp = client.post(f'/api/v1/case-files/{case_id}/events', headers=headers,
                       json={'event_date': '2026-06-01', 'kind': 'bogus', 'title': 'X'})
    assert resp.status_code == 400


def test_edit_and_delete_event(client, make_owner):
    headers, firm_id = make_owner()
    case_id = _case(client, headers, firm_id)
    ev = client.post(f'/api/v1/case-files/{case_id}/events', headers=headers,
                     json={'event_date': '2026-06-01', 'kind': 'note', 'title': 'Note'}).get_json()
    upd = client.patch(f"/api/v1/case-events/{ev['id']}", headers=headers,
                       json={'title': 'Note (edited)', 'notes': 'detail'})
    assert upd.status_code == 200
    assert upd.get_json()['title'] == 'Note (edited)'
    assert client.delete(f"/api/v1/case-events/{ev['id']}", headers=headers).status_code == 200


def test_events_isolated_by_firm(client, make_owner):
    headers, firm_id = make_owner()
    headers_b, _ = make_owner(supabase_id='sb-b', email='b@firm.com', firm_name='B')
    case_id = _case(client, headers, firm_id)
    ev = client.post(f'/api/v1/case-files/{case_id}/events', headers=headers,
                     json={'event_date': '2026-06-01', 'kind': 'note', 'title': 'N'}).get_json()
    assert client.patch(f"/api/v1/case-events/{ev['id']}", headers=headers_b,
                        json={'title': 'hack'}).status_code == 404
    assert client.get(f'/api/v1/case-files/{case_id}/events', headers=headers_b).status_code == 404
