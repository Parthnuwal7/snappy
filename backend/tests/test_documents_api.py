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
    calls = {'put': [], 'removed': []}
    monkeypatch.setattr('app.services.document_storage.put_object',
                        lambda path, data, content_type: calls['put'].append(path))
    monkeypatch.setattr('app.services.document_storage.signed_url',
                        lambda path, ttl=3600: f'https://signed/{path}')
    monkeypatch.setattr('app.services.document_storage.remove_object',
                        lambda path: calls['removed'].append(path))
    return calls


def _upload(client, headers, case_id, filename='petition.pdf', title='Petition',
            doc_type='pleading', content=b'%PDF-1.4 data'):
    return client.post(
        f'/api/v1/case-files/{case_id}/documents', headers=headers,
        data={'title': title, 'doc_type': doc_type,
              'file': (io.BytesIO(content), filename)},
        content_type='multipart/form-data')


def test_upload_creates_row_and_calls_storage(client, make_owner, monkeypatch):
    calls = _fake_storage(monkeypatch)
    headers, firm_id = make_owner()
    case_id = _case(client, headers, firm_id)
    resp = _upload(client, headers, case_id)
    assert resp.status_code == 201
    body = resp.get_json()
    assert body['title'] == 'Petition'
    assert body['doc_type'] == 'pleading'
    assert 'storage_path' not in body
    assert len(calls['put']) == 1
    assert calls['put'][0].startswith(f'{firm_id}/{case_id}/')


def test_list_documents(client, make_owner, monkeypatch):
    _fake_storage(monkeypatch)
    headers, firm_id = make_owner()
    case_id = _case(client, headers, firm_id)
    _upload(client, headers, case_id)
    docs = client.get(f'/api/v1/case-files/{case_id}/documents', headers=headers).get_json()
    assert len(docs) == 1


def test_download_returns_signed_url(client, make_owner, monkeypatch):
    _fake_storage(monkeypatch)
    headers, firm_id = make_owner()
    case_id = _case(client, headers, firm_id)
    doc = _upload(client, headers, case_id).get_json()
    resp = client.get(f"/api/v1/case-documents/{doc['id']}/download", headers=headers)
    assert resp.status_code == 200
    assert resp.get_json()['url'].startswith('https://signed/')


def test_reject_disallowed_extension(client, make_owner, monkeypatch):
    _fake_storage(monkeypatch)
    headers, firm_id = make_owner()
    case_id = _case(client, headers, firm_id)
    resp = _upload(client, headers, case_id, filename='x.exe')
    assert resp.status_code == 400


def test_reject_bad_doc_type(client, make_owner, monkeypatch):
    _fake_storage(monkeypatch)
    headers, firm_id = make_owner()
    case_id = _case(client, headers, firm_id)
    resp = _upload(client, headers, case_id, doc_type='nonsense')
    assert resp.status_code == 400


def test_delete_removes_row_and_object(client, make_owner, monkeypatch):
    calls = _fake_storage(monkeypatch)
    headers, firm_id = make_owner()
    case_id = _case(client, headers, firm_id)
    doc = _upload(client, headers, case_id).get_json()
    assert client.delete(f"/api/v1/case-documents/{doc['id']}", headers=headers).status_code == 200
    assert len(calls['removed']) == 1
    assert client.get(f"/api/v1/case-documents/{doc['id']}/download", headers=headers).status_code == 404


def test_documents_isolated_across_firms(client, make_owner, monkeypatch):
    _fake_storage(monkeypatch)
    headers, firm_id = make_owner()
    headers_b, _ = make_owner(supabase_id='sb-b', email='b@firm.com', firm_name='B')
    case_id = _case(client, headers, firm_id)
    doc = _upload(client, headers, case_id).get_json()
    assert client.get(f"/api/v1/case-documents/{doc['id']}/download", headers=headers_b).status_code == 404
    assert client.get(f'/api/v1/case-files/{case_id}/documents', headers=headers_b).status_code == 404


def test_meta_includes_doc_types(client, make_owner):
    headers, _ = make_owner()
    body = client.get('/api/v1/case-files/meta', headers=headers).get_json()
    keys = {d['key'] for d in body['doc_types']}
    assert {'pleading', 'wakalatnama', 'evidence'} <= keys
