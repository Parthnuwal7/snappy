from datetime import date, timedelta
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


def _d(offset):
    return (date.today() + timedelta(days=offset)).isoformat()


def test_hearing_sets_next_date_to_soonest_future(client, make_owner):
    headers, firm_id = make_owner()
    case_id = _case(client, headers, firm_id)
    client.post(f'/api/v1/case-files/{case_id}/events', headers=headers,
                json={'event_date': _d(20), 'kind': 'hearing', 'title': 'Hearing', 'purpose': 'evidence'})
    client.post(f'/api/v1/case-files/{case_id}/events', headers=headers,
                json={'event_date': _d(5), 'kind': 'hearing', 'title': 'Hearing'})
    cf = client.get(f'/api/v1/case-files/{case_id}', headers=headers).get_json()
    assert cf['next_hearing_date'] == _d(5)  # the soonest future hearing


def test_past_hearing_does_not_set_next_date(client, make_owner):
    headers, firm_id = make_owner()
    case_id = _case(client, headers, firm_id)
    client.post(f'/api/v1/case-files/{case_id}/events', headers=headers,
                json={'event_date': _d(-3), 'kind': 'hearing', 'title': 'Past hearing'})
    cf = client.get(f'/api/v1/case-files/{case_id}', headers=headers).get_json()
    assert cf['next_hearing_date'] is None


def test_event_carries_purpose_and_outcome(client, make_owner):
    headers, firm_id = make_owner()
    case_id = _case(client, headers, firm_id)
    ev = client.post(f'/api/v1/case-files/{case_id}/events', headers=headers,
                     json={'event_date': _d(7), 'kind': 'hearing', 'title': 'Hearing',
                           'purpose': 'arguments'}).get_json()
    assert ev['purpose'] == 'arguments'
    upd = client.patch(f"/api/v1/case-events/{ev['id']}", headers=headers,
                       json={'outcome': 'Adjourned for evidence'}).get_json()
    assert upd['outcome'] == 'Adjourned for evidence'


def test_deleting_only_hearing_clears_next_date(client, make_owner):
    headers, firm_id = make_owner()
    case_id = _case(client, headers, firm_id)
    ev = client.post(f'/api/v1/case-files/{case_id}/events', headers=headers,
                     json={'event_date': _d(9), 'kind': 'hearing', 'title': 'Hearing'}).get_json()
    client.delete(f"/api/v1/case-events/{ev['id']}", headers=headers)
    cf = client.get(f'/api/v1/case-files/{case_id}', headers=headers).get_json()
    assert cf['next_hearing_date'] is None
