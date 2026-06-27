from datetime import date, timedelta
from app.models.models import db, Client
from app.models.auth import User


def _case(client, headers, firm_id, title='M'):
    with client.application.app_context():
        c = Client(firm_id=firm_id, created_by_user_id=User.query.filter_by(
            email='owner@firm.com').first().id, name='Acme')
        db.session.add(c); db.session.commit()
        cid = c.id
    return client.post('/api/v1/case-files', headers=headers,
                       json={'title': title, 'client_id': cid}).get_json()['id']


def _d(offset):
    return (date.today() + timedelta(days=offset)).isoformat()


def test_calendar_lists_hearings_in_window(client, make_owner):
    headers, firm_id = make_owner()
    case_id = _case(client, headers, firm_id, title='Sharma v. State')
    client.post(f'/api/v1/case-files/{case_id}/events', headers=headers,
                json={'event_date': _d(5), 'kind': 'hearing', 'title': 'Hearing', 'purpose': 'evidence'})
    client.post(f'/api/v1/case-files/{case_id}/events', headers=headers,
                json={'event_date': _d(2), 'kind': 'note', 'title': 'A note'})
    rows = client.get(f'/api/v1/calendar?from={_d(0)}&to={_d(30)}', headers=headers).get_json()
    assert len(rows) == 1  # only the hearing
    assert rows[0]['case_title'] == 'Sharma v. State'
    assert rows[0]['client_name'] == 'Acme'
    assert rows[0]['purpose'] == 'evidence'


def test_calendar_window_excludes_outside(client, make_owner):
    headers, firm_id = make_owner()
    case_id = _case(client, headers, firm_id)
    client.post(f'/api/v1/case-files/{case_id}/events', headers=headers,
                json={'event_date': _d(90), 'kind': 'hearing', 'title': 'Far hearing'})
    rows = client.get(f'/api/v1/calendar?from={_d(0)}&to={_d(30)}', headers=headers).get_json()
    assert rows == []


def test_calendar_firm_isolation(client, make_owner):
    headers, firm_id = make_owner()
    headers_b, _ = make_owner(supabase_id='sb-b', email='b@firm.com', firm_name='B')
    case_id = _case(client, headers, firm_id)
    client.post(f'/api/v1/case-files/{case_id}/events', headers=headers,
                json={'event_date': _d(5), 'kind': 'hearing', 'title': 'Hearing'})
    assert client.get(f'/api/v1/calendar?from={_d(0)}&to={_d(30)}', headers=headers_b).get_json() == []
