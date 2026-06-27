from app.models.models import db, Client
from app.models.auth import User


def _lead(client, headers, **over):
    payload = {'contact_name': 'Mehta', 'phone': '99', 'email': 'm@x.com',
               'matter_summary': 'Property dispute', 'intake_notes': 'Heard the facts'}
    payload.update(over)
    return client.post('/api/v1/leads', headers=headers, json=payload).get_json()


def test_convert_creates_case_client_and_intake_note(client, make_owner):
    headers, firm_id = make_owner()
    lead = _lead(client, headers)
    case = client.post(f"/api/v1/leads/{lead['id']}/convert", headers=headers,
                       json={'title': 'Mehta v. State'}).get_json()
    assert case['stage'] == 'engaged'
    assert case['title'] == 'Mehta v. State'
    assert case['case_number'].startswith('CF/')
    assert case['lead_id'] == lead['id']

    # A new client was created from the lead contact.
    assert case['client_name'] == 'Mehta'

    # Intake notes landed as the first (pinned) case note.
    notes = client.get(f"/api/v1/case-files/{case['id']}/notes", headers=headers).get_json()
    assert any('Heard the facts' in n['body'] for n in notes)
    assert notes[0]['pinned'] is True

    # Lead is now accepted and linked.
    refreshed = client.get(f"/api/v1/leads/{lead['id']}", headers=headers).get_json()
    assert refreshed['status'] == 'accepted'
    assert refreshed['converted_case_file_id'] == case['id']
    assert refreshed['decided_at'] is not None


def test_convert_with_existing_client(client, make_owner):
    headers, firm_id = make_owner()
    with client.application.app_context():
        c = Client(firm_id=firm_id, created_by_user_id=User.query.filter_by(
            email='owner@firm.com').first().id, name='Existing Co')
        db.session.add(c); db.session.commit()
        cid = c.id
    lead = _lead(client, headers)
    case = client.post(f"/api/v1/leads/{lead['id']}/convert", headers=headers,
                       json={'client_id': cid}).get_json()
    assert case['client_id'] == cid
    assert case['client_name'] == 'Existing Co'
    # Title falls back to the matter summary when not supplied.
    assert case['title'] == 'Property dispute'


def test_convert_twice_is_rejected(client, make_owner):
    headers, _ = make_owner()
    lead = _lead(client, headers)
    client.post(f"/api/v1/leads/{lead['id']}/convert", headers=headers, json={})
    again = client.post(f"/api/v1/leads/{lead['id']}/convert", headers=headers, json={})
    assert again.status_code == 400


def test_convert_isolated(client, make_owner):
    headers, _ = make_owner()
    headers_b, _ = make_owner(supabase_id='sb-b', email='b@firm.com', firm_name='B')
    lead = _lead(client, headers)
    assert client.post(f"/api/v1/leads/{lead['id']}/convert", headers=headers_b, json={}).status_code == 404
