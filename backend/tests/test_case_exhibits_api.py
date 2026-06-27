import io
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


def _fake_storage(monkeypatch):
    monkeypatch.setattr('app.services.document_storage.put_object',
                        lambda path, data, content_type: None)
    monkeypatch.setattr('app.services.document_storage.signed_url',
                        lambda path, ttl=3600: f'https://signed/{path}')
    monkeypatch.setattr('app.services.document_storage.remove_object',
                        lambda path: None)


def test_exhibit_crud(client, make_owner):
    headers, firm_id = make_owner()
    case_id = _case(client, headers, firm_id)
    ex = client.post(f'/api/v1/case-files/{case_id}/exhibits', headers=headers,
                     json={'exhibit_mark': 'Ex. P-1', 'description': 'Sale deed',
                           'party': 'petitioner'}).get_json()
    assert ex['status'] == 'marked'
    assert len(client.get(f'/api/v1/case-files/{case_id}/exhibits', headers=headers).get_json()) == 1

    upd = client.patch(f"/api/v1/case-exhibits/{ex['id']}", headers=headers,
                       json={'status': 'admitted'}).get_json()
    assert upd['status'] == 'admitted'
    assert client.delete(f"/api/v1/case-exhibits/{ex['id']}", headers=headers).status_code == 200


def test_exhibit_invalid_status_rejected(client, make_owner):
    headers, firm_id = make_owner()
    case_id = _case(client, headers, firm_id)
    assert client.post(f'/api/v1/case-files/{case_id}/exhibits', headers=headers,
                       json={'exhibit_mark': 'Ex. P-1', 'status': 'teleported'}).status_code == 400


def test_exhibit_link_nulled_on_document_delete(client, make_owner, monkeypatch):
    _fake_storage(monkeypatch)
    headers, firm_id = make_owner()
    case_id = _case(client, headers, firm_id)
    doc = client.post(f'/api/v1/case-files/{case_id}/documents', headers=headers,
                      data={'title': 'Deed', 'doc_type': 'evidence',
                            'file': (io.BytesIO(b'%PDF-1.4 x'), 'deed.pdf')},
                      content_type='multipart/form-data').get_json()
    ex = client.post(f'/api/v1/case-files/{case_id}/exhibits', headers=headers,
                     json={'exhibit_mark': 'Ex. P-1', 'document_id': doc['id']}).get_json()
    assert ex['document_id'] == doc['id']
    client.delete(f"/api/v1/case-documents/{doc['id']}", headers=headers)
    refreshed = client.get(f'/api/v1/case-files/{case_id}/exhibits', headers=headers).get_json()[0]
    assert refreshed['document_id'] is None


def test_exhibits_firm_isolation(client, make_owner):
    headers, firm_id = make_owner()
    headers_b, _ = make_owner(supabase_id='sb-b', email='b@firm.com', firm_name='B')
    case_id = _case(client, headers, firm_id)
    ex = client.post(f'/api/v1/case-files/{case_id}/exhibits', headers=headers,
                     json={'exhibit_mark': 'Ex. P-1'}).get_json()
    assert client.patch(f"/api/v1/case-exhibits/{ex['id']}", headers=headers_b,
                        json={'status': 'admitted'}).status_code == 404
    assert client.get(f'/api/v1/case-files/{case_id}/exhibits', headers=headers_b).status_code == 404
