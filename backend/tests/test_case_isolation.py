from app.models.models import db, Client
from app.models.auth import User


def _case_for(client, headers, firm_id, email):
    with client.application.app_context():
        c = Client(firm_id=firm_id, created_by_user_id=User.query.filter_by(
            email=email).first().id, name='X')
        db.session.add(c)
        db.session.commit()
        cid = c.id
    return client.post('/api/v1/case-files', headers=headers,
                       json={'title': 'Secret', 'client_id': cid}).get_json()['id']


def test_case_not_visible_or_mutable_across_firms(client, make_owner):
    headers_a, firm_a = make_owner()
    headers_b, firm_b = make_owner(supabase_id='sb-b', email='b@firm.com', firm_name='B')
    case_a = _case_for(client, headers_a, firm_a, 'owner@firm.com')

    listing_b = client.get('/api/v1/case-files', headers=headers_b).get_json()
    assert all(c['id'] != case_a for c in listing_b)

    assert client.get(f'/api/v1/case-files/{case_a}', headers=headers_b).status_code == 404
    assert client.patch(f'/api/v1/case-files/{case_a}', headers=headers_b,
                        json={'title': 'hack'}).status_code == 404
    assert client.patch(f'/api/v1/case-files/{case_a}/move', headers=headers_b,
                        json={'stage': 'closed'}).status_code == 404
    assert client.delete(f'/api/v1/case-files/{case_a}', headers=headers_b).status_code == 404

    assert client.get(f'/api/v1/case-files/{case_a}', headers=headers_a).status_code == 200
