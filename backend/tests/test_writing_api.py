def test_writing_meta(client, make_owner):
    headers, _ = make_owner()
    m = client.get('/api/v1/writing/meta', headers=headers).get_json()
    assert any(f['source'] == 'petitioner' for f in m['merge_fields'])
    assert any(t['key'] == 'wakalatnama' for t in m['builtin_templates'])
    assert any(c['key'] == 'notice' for c in m['template_categories'])


def test_template_crud(client, make_owner):
    headers, _ = make_owner()
    t = client.post('/api/v1/templates', headers=headers, json={'name': 'My notice', 'category': 'notice', 'body': '<p>{{court}}</p>'}).get_json()
    assert t['name'] == 'My notice'
    assert len(client.get('/api/v1/templates', headers=headers).get_json()) == 1
    client.patch(f"/api/v1/templates/{t['id']}", headers=headers, json={'name': 'Renamed'})
    assert client.get(f"/api/v1/templates/{t['id']}", headers=headers).get_json()['name'] == 'Renamed'
    assert client.delete(f"/api/v1/templates/{t['id']}", headers=headers).status_code == 200


def test_draft_crud_and_case_filter(client, make_owner):
    headers, firm_id = make_owner()
    from app.models.models import db, Client
    from app.models.auth import User
    with client.application.app_context():
        c = Client(firm_id=firm_id, created_by_user_id=User.query.filter_by(email='owner@firm.com').first().id, name='X')
        db.session.add(c); db.session.commit(); cid = c.id
    case_id = client.post('/api/v1/case-files', headers=headers, json={'title': 'M', 'client_id': cid}).get_json()['id']
    d = client.post('/api/v1/drafts', headers=headers, json={'title': 'Reply', 'body': '<p>hi</p>', 'case_file_id': case_id}).get_json()
    assert d['case_number'].startswith('CF/')
    client.post('/api/v1/drafts', headers=headers, json={'title': 'Unlinked', 'body': '<p>x</p>'})
    assert len(client.get(f'/api/v1/drafts?case_file_id={case_id}', headers=headers).get_json()) == 1
    assert len(client.get('/api/v1/drafts', headers=headers).get_json()) == 2
    client.patch(f"/api/v1/drafts/{d['id']}", headers=headers, json={'body': '<p>edited</p>'})
    assert client.get(f"/api/v1/drafts/{d['id']}", headers=headers).get_json()['body'] == '<p>edited</p>'


def test_writing_firm_isolation(client, make_owner):
    headers, _ = make_owner()
    headers_b, _ = make_owner(supabase_id='sb-b', email='b@firm.com', firm_name='B')
    d = client.post('/api/v1/drafts', headers=headers, json={'title': 'x', 'body': '<p/>'}).get_json()
    assert client.get(f"/api/v1/drafts/{d['id']}", headers=headers_b).status_code == 404
    assert client.get('/api/v1/drafts', headers=headers_b).get_json() == []


def test_draft_requires_title(client, make_owner):
    headers, _ = make_owner()
    assert client.post('/api/v1/drafts', headers=headers, json={'body': '<p/>'}).status_code == 400
