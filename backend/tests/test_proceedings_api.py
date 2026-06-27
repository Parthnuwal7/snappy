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


def test_record_proceedings_sets_outcome_and_next_date(client, make_owner):
    headers, firm_id = make_owner()
    case_id = _case(client, headers, firm_id)
    cur = client.post(f'/api/v1/case-files/{case_id}/events', headers=headers,
                      json={'event_date': _d(0), 'kind': 'hearing', 'title': 'Hearing'}).get_json()
    resp = client.post(f'/api/v1/case-files/{case_id}/proceedings', headers=headers,
                       json={'current_event_id': cur['id'], 'outcome': 'Reply filed; adjourned',
                             'purpose': 'evidence', 'next_date': _d(10)}).get_json()
    assert resp['case_file']['next_hearing_date'] == _d(10)
    assert resp['next_event']['purpose'] == 'evidence'

    events = client.get(f'/api/v1/case-files/{case_id}/events', headers=headers).get_json()
    disposed = next(e for e in events if e['id'] == cur['id'])
    assert disposed['outcome'] == 'Reply filed; adjourned'
    assert len([e for e in events if e['kind'] == 'hearing']) == 2


def test_proceedings_requires_next_date(client, make_owner):
    headers, firm_id = make_owner()
    case_id = _case(client, headers, firm_id)
    assert client.post(f'/api/v1/case-files/{case_id}/proceedings', headers=headers,
                       json={'outcome': 'x'}).status_code == 400


def test_next_date_upserts_soonest_hearing(client, make_owner):
    headers, firm_id = make_owner()
    case_id = _case(client, headers, firm_id)
    # No hearings yet -> creates one.
    client.post(f'/api/v1/case-files/{case_id}/next-date', headers=headers, json={'next_date': _d(8)})
    cf = client.get(f'/api/v1/case-files/{case_id}', headers=headers).get_json()
    assert cf['next_hearing_date'] == _d(8)
    # Correcting it -> moves the same hearing, not a second one.
    client.post(f'/api/v1/case-files/{case_id}/next-date', headers=headers, json={'next_date': _d(12)})
    cf = client.get(f'/api/v1/case-files/{case_id}', headers=headers).get_json()
    assert cf['next_hearing_date'] == _d(12)
    hearings = [e for e in client.get(f'/api/v1/case-files/{case_id}/events', headers=headers).get_json()
                if e['kind'] == 'hearing']
    assert len(hearings) == 1


def test_proceedings_isolated(client, make_owner):
    headers, firm_id = make_owner()
    headers_b, _ = make_owner(supabase_id='sb-b', email='b@firm.com', firm_name='B')
    case_id = _case(client, headers, firm_id)
    assert client.post(f'/api/v1/case-files/{case_id}/proceedings', headers=headers_b,
                       json={'next_date': _d(3)}).status_code == 404
