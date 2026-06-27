from app.models.models import db, Client
from app.models.auth import User


def _case(client, headers, firm_id):
    with client.application.app_context():
        c = Client(firm_id=firm_id, created_by_user_id=User.query.filter_by(
            email='owner@firm.com').first().id, name='X')
        db.session.add(c); db.session.commit()
        cid = c.id
    return client.post('/api/v1/case-files', headers=headers,
                       json={'title': 'M', 'client_id': cid}).get_json()['id']


def test_note_crud_and_pin(client, make_owner):
    headers, firm_id = make_owner()
    case_id = _case(client, headers, firm_id)
    n = client.post(f'/api/v1/case-files/{case_id}/notes', headers=headers,
                    json={'body': 'limitation angle weak'}).get_json()
    assert n['pinned'] is False
    lst = client.get(f'/api/v1/case-files/{case_id}/notes', headers=headers).get_json()
    assert len(lst) == 1

    pinned = client.patch(f"/api/v1/case-notes/{n['id']}", headers=headers,
                          json={'pinned': True, 'body': 'limitation is weak'}).get_json()
    assert pinned['pinned'] is True
    assert pinned['body'] == 'limitation is weak'

    assert client.delete(f"/api/v1/case-notes/{n['id']}", headers=headers).status_code == 200
    assert client.get(f'/api/v1/case-files/{case_id}/notes', headers=headers).get_json() == []


def test_note_requires_body(client, make_owner):
    headers, firm_id = make_owner()
    case_id = _case(client, headers, firm_id)
    assert client.post(f'/api/v1/case-files/{case_id}/notes', headers=headers,
                       json={'body': '   '}).status_code == 400


def test_notes_pinned_first(client, make_owner):
    headers, firm_id = make_owner()
    case_id = _case(client, headers, firm_id)
    client.post(f'/api/v1/case-files/{case_id}/notes', headers=headers, json={'body': 'first'})
    second = client.post(f'/api/v1/case-files/{case_id}/notes', headers=headers, json={'body': 'second'}).get_json()
    client.patch(f"/api/v1/case-notes/{second['id']}", headers=headers, json={'pinned': True})
    lst = client.get(f'/api/v1/case-files/{case_id}/notes', headers=headers).get_json()
    assert lst[0]['body'] == 'second'  # pinned floats to the top


def test_deleting_event_detaches_note(client, make_owner):
    headers, firm_id = make_owner()
    case_id = _case(client, headers, firm_id)
    ev = client.post(f'/api/v1/case-files/{case_id}/events', headers=headers,
                     json={'event_date': '2026-06-01', 'kind': 'hearing', 'title': 'Hearing'}).get_json()
    note = client.post(f'/api/v1/case-files/{case_id}/notes', headers=headers,
                       json={'body': 'carry originals', 'event_id': ev['id']}).get_json()
    assert note['event_id'] == ev['id']
    client.delete(f"/api/v1/case-events/{ev['id']}", headers=headers)
    refreshed = client.get(f'/api/v1/case-files/{case_id}/notes', headers=headers).get_json()[0]
    assert refreshed['event_id'] is None


def test_notes_firm_isolation(client, make_owner):
    headers, firm_id = make_owner()
    headers_b, _ = make_owner(supabase_id='sb-b', email='b@firm.com', firm_name='B')
    case_id = _case(client, headers, firm_id)
    n = client.post(f'/api/v1/case-files/{case_id}/notes', headers=headers, json={'body': 'x'}).get_json()
    assert client.patch(f"/api/v1/case-notes/{n['id']}", headers=headers_b, json={'body': 'y'}).status_code == 404
    assert client.get(f'/api/v1/case-files/{case_id}/notes', headers=headers_b).status_code == 404
