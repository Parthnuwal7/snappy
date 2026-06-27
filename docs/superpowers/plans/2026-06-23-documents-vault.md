# Documents & Evidence Vault Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Per-case document vault — upload/list/download/delete files (pleadings, wakalatnama, evidence, drafts) stored in a private Supabase bucket, metadata in Postgres, optionally linked to a timeline step.

**Architecture:** A `CaseDocument` row holds metadata; bytes live in a private `case-documents` bucket. All storage I/O goes through a thin, monkeypatchable `document_storage` service so the API tests on SQLite without Supabase. Firm-scoped + gated by a new `documents` RBAC module. Download is always a short-lived signed URL.

**Tech Stack:** Flask, SQLAlchemy, Supabase Storage, Supabase JWT, React + TS (Vite), TanStack Query, lucide-react.

## Global Constraints

- Firm-scoped (`firm_id`); attribution `uploaded_by_user_id`. RBAC-only access via a new `documents` CRUD module.
- A document belongs to a `case_file`; `event_id` (timeline step) is optional. No version chains — each upload is its own row.
- Limits: ≤ 25 MB; extensions `pdf, jpg, jpeg, png, doc, docx, xls, xlsx, txt`. `doc_type` from a fixed vocabulary (default `other`).
- `storage_path` is internal — never serialized in `to_dict`.
- Storage I/O via `app/services/document_storage.py` module-level functions (monkeypatched in tests); raise `StorageError` when Supabase unconfigured → API maps to 503.
- Object key: `{firm_id}/{case_file_id}/{uuid4}.{ext}`.
- Migration `011_case_documents.sql` is delivered for Parth to apply; the `case-documents` bucket is created manually in Supabase. **Do not run git commits** — Parth handles git; end each task at green.

---

### Task 1: Documents catalog

**Files:**
- Create: `backend/app/case/documents.py`
- Test: `backend/tests/test_documents_catalog.py`

**Interfaces:**
- Produces: `DOC_TYPES: list[dict]`, `DOC_TYPE_KEYS: set[str]`, `DEFAULT_DOC_TYPE="other"`, `MAX_DOCUMENT_BYTES=26214400`, `ALLOWED_EXTENSIONS: set[str]`, `is_valid_doc_type(key)->bool`, `is_allowed_filename(name)->bool`, `extension_of(name)->str`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_documents_catalog.py
from app.case.documents import (
    DOC_TYPES, DOC_TYPE_KEYS, DEFAULT_DOC_TYPE, MAX_DOCUMENT_BYTES,
    ALLOWED_EXTENSIONS, is_valid_doc_type, is_allowed_filename, extension_of,
)


def test_doc_types_include_legal_vocabulary():
    assert {"pleading", "wakalatnama", "evidence", "order",
            "correspondence", "draft", "other"} <= DOC_TYPE_KEYS
    assert all("label" in d for d in DOC_TYPES)


def test_defaults_and_limits():
    assert DEFAULT_DOC_TYPE == "other"
    assert MAX_DOCUMENT_BYTES == 25 * 1024 * 1024


def test_doc_type_validation():
    assert is_valid_doc_type("evidence")
    assert not is_valid_doc_type("smoke")


def test_filename_rules():
    assert is_allowed_filename("petition.pdf")
    assert is_allowed_filename("Scan.JPG")
    assert not is_allowed_filename("malware.exe")
    assert not is_allowed_filename("noext")
    assert extension_of("Scan.JPG") == "jpg"
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && python -m pytest tests/test_documents_catalog.py -q`
Expected: FAIL — `No module named 'app.case.documents'`

- [ ] **Step 3: Implement**

```python
# backend/app/case/documents.py
"""Document vault catalog: fixed doc-type vocabulary + upload constraints."""

DOC_TYPES = [
    {"key": "pleading",       "label": "Pleading"},
    {"key": "wakalatnama",    "label": "Wakalatnama"},
    {"key": "evidence",       "label": "Evidence / Exhibit"},
    {"key": "order",          "label": "Order / Judgment"},
    {"key": "correspondence", "label": "Correspondence"},
    {"key": "draft",          "label": "Draft"},
    {"key": "other",          "label": "Other"},
]
DOC_TYPE_KEYS = {d["key"] for d in DOC_TYPES}
DEFAULT_DOC_TYPE = "other"

MAX_DOCUMENT_BYTES = 25 * 1024 * 1024  # 25 MB
ALLOWED_EXTENSIONS = {"pdf", "jpg", "jpeg", "png", "doc", "docx", "xls", "xlsx", "txt"}


def is_valid_doc_type(key):
    return key in DOC_TYPE_KEYS


def extension_of(filename):
    return filename.rsplit(".", 1)[1].lower() if "." in filename else ""


def is_allowed_filename(filename):
    return extension_of(filename) in ALLOWED_EXTENSIONS
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend && python -m pytest tests/test_documents_catalog.py -q`
Expected: PASS (4 passed)

---

### Task 2: CaseDocument model

**Files:**
- Modify: `backend/app/models/case.py` (add `CaseDocument`)
- Modify: `backend/app/main.py` (import `CaseDocument` so `create_all` builds it)
- Test: `backend/tests/test_document_model.py`

**Interfaces:**
- Produces: `CaseDocument` (`case_documents`): `id, firm_id, case_file_id, event_id, uploaded_by_user_id, title, doc_type, file_name, mime_type, size_bytes, storage_path, description, created_at`; `to_dict()` omits `storage_path`; `CaseFile.documents` relationship (cascade delete).

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_document_model.py
from datetime import date
from app.models.models import db, Client
from app.models.auth import User
from app.models.case import CaseFile, CaseEvent, CaseDocument
from app.services.firm_service import provision_firm_for_user


def _case(app):
    with app.app_context():
        u = User(supabase_id='sb-d', email='d@firm.com')
        db.session.add(u); db.session.commit()
        firm = provision_firm_for_user(u, 'Acme')
        c = Client(firm_id=firm.id, created_by_user_id=u.id, name='X')
        db.session.add(c); db.session.commit()
        cf = CaseFile(firm_id=firm.id, created_by_user_id=u.id,
                      case_number='CF/2026/0001', title='M', client_id=c.id)
        db.session.add(cf); db.session.commit()
        return firm.id, u.id, cf.id


def test_to_dict_omits_storage_path(app):
    firm_id, uid, cf_id = _case(app)
    with app.app_context():
        d = CaseDocument(firm_id=firm_id, case_file_id=cf_id, uploaded_by_user_id=uid,
                         title='Petition', doc_type='pleading', file_name='p.pdf',
                         mime_type='application/pdf', size_bytes=1234,
                         storage_path=f'{firm_id}/{cf_id}/abc.pdf')
        db.session.add(d); db.session.commit()
        out = d.to_dict()
        assert out['title'] == 'Petition'
        assert out['doc_type'] == 'pleading'
        assert out['size_bytes'] == 1234
        assert 'storage_path' not in out


def test_documents_cascade_on_case_delete(app):
    firm_id, uid, cf_id = _case(app)
    with app.app_context():
        db.session.add(CaseDocument(firm_id=firm_id, case_file_id=cf_id, uploaded_by_user_id=uid,
                                    title='D', doc_type='other', file_name='d.pdf',
                                    storage_path='x'))
        db.session.commit()
        cf = CaseFile.query.get(cf_id)
        db.session.delete(cf); db.session.commit()
        assert CaseDocument.query.filter_by(case_file_id=cf_id).count() == 0
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && python -m pytest tests/test_document_model.py -q`
Expected: FAIL — `cannot import name 'CaseDocument'`

- [ ] **Step 3: Add the model**

In `backend/app/models/case.py`, add to the imports line at top (already present: `from datetime import datetime, date`). Add a relationship on `CaseFile` and the new class. In `CaseFile`, after the `events` relationship, add:

```python
    documents = db.relationship('CaseDocument', back_populates='case_file',
                                cascade='all, delete-orphan')
```

At the end of the file add:

```python
class CaseDocument(db.Model):
    __tablename__ = 'case_documents'

    id = db.Column(db.Integer, primary_key=True)
    firm_id = db.Column(db.Integer, db.ForeignKey('firms.id'), index=True)
    case_file_id = db.Column(db.Integer, db.ForeignKey('case_files.id'), index=True)
    event_id = db.Column(db.Integer, db.ForeignKey('case_events.id'), index=True)
    uploaded_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    title = db.Column(db.String(300), nullable=False)
    doc_type = db.Column(db.String(40), nullable=False, default='other')
    file_name = db.Column(db.String(300))
    mime_type = db.Column(db.String(120))
    size_bytes = db.Column(db.Integer)
    storage_path = db.Column(db.String(500), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    case_file = db.relationship('CaseFile', back_populates='documents')

    def to_dict(self):
        return {
            'id': self.id,
            'firm_id': self.firm_id,
            'case_file_id': self.case_file_id,
            'event_id': self.event_id,
            'uploaded_by_user_id': self.uploaded_by_user_id,
            'title': self.title,
            'doc_type': self.doc_type,
            'file_name': self.file_name,
            'mime_type': self.mime_type,
            'size_bytes': self.size_bytes,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
```

- [ ] **Step 4: Wire into startup**

In `backend/app/main.py`, change the case import line to include `CaseDocument`:

```python
        from app.models.case import CaseFile, CaseParty, CaseEvent, CaseDocument  # ensure case tables are created
```

- [ ] **Step 5: Run to verify it passes**

Run: `cd backend && python -m pytest tests/test_document_model.py -q`
Expected: PASS (2 passed)

---

### Task 3: Storage service

**Files:**
- Create: `backend/app/services/document_storage.py`
- Test: `backend/tests/test_document_storage.py`

**Interfaces:**
- Produces: `BUCKET="case-documents"`; `StorageError`; `build_storage_path(firm_id, case_file_id, ext)->str`; `put_object(storage_path, data, content_type)->None`; `signed_url(storage_path, ttl=3600)->str`; `remove_object(storage_path)->None`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_document_storage.py
from app.services import document_storage as ds


def test_build_storage_path_namespaced():
    path = ds.build_storage_path(7, 42, 'pdf')
    assert path.startswith('7/42/')
    assert path.endswith('.pdf')
    # uuid segment differs each call
    assert ds.build_storage_path(7, 42, 'pdf') != path


def test_bucket_name():
    assert ds.BUCKET == 'case-documents'
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && python -m pytest tests/test_document_storage.py -q`
Expected: FAIL — `No module named 'app.services.document_storage'`

- [ ] **Step 3: Implement**

```python
# backend/app/services/document_storage.py
"""Thin wrapper over Supabase Storage for case documents.

Module-level functions so tests can monkeypatch them without a network call.
Bytes live in a private bucket; download is always a short-lived signed URL.
"""
import uuid

BUCKET = "case-documents"


class StorageError(Exception):
    """Raised when storage is unconfigured or the provider call fails."""


def build_storage_path(firm_id, case_file_id, ext):
    return f"{firm_id}/{case_file_id}/{uuid.uuid4().hex}.{ext}"


def _bucket():
    from app.services.supabase_client import get_supabase_client
    try:
        client = get_supabase_client()
    except ValueError as e:
        raise StorageError(f"Storage not configured: {e}") from e
    return client.storage.from_(BUCKET)


def put_object(storage_path, data, content_type):
    try:
        _bucket().upload(storage_path, data,
                         file_options={'content-type': content_type or 'application/octet-stream'})
    except StorageError:
        raise
    except Exception as e:
        raise StorageError(f"Upload failed: {e}") from e


def signed_url(storage_path, ttl=3600):
    try:
        result = _bucket().create_signed_url(storage_path, expires_in=ttl)
    except StorageError:
        raise
    except Exception as e:
        raise StorageError(f"Could not sign URL: {e}") from e
    url = (result or {}).get('signedURL') or (result or {}).get('signedUrl')
    if not url:
        raise StorageError("No signed URL returned")
    return url


def remove_object(storage_path):
    try:
        _bucket().remove([storage_path])
    except StorageError:
        raise
    except Exception as e:
        raise StorageError(f"Delete failed: {e}") from e
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend && python -m pytest tests/test_document_storage.py -q`
Expected: PASS (2 passed)

---

### Task 4: `documents` RBAC module

**Files:**
- Modify: `backend/app/rbac/permissions.py`
- Test: `backend/tests/test_documents_permissions.py`

**Interfaces:** extends `MODULES`/`ALL_PERMISSIONS`/`DEFAULT_ROLES` with `documents.create/read/update/delete`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_documents_permissions.py
from app.rbac.permissions import MODULES, ALL_PERMISSIONS, DEFAULT_ROLES


def test_documents_module_present():
    mod = next((m for m in MODULES if m['key'] == 'documents'), None)
    assert mod and mod['actions'] == ['create', 'read', 'update', 'delete']


def test_documents_permissions_registered():
    for a in ('create', 'read', 'update', 'delete'):
        assert f'documents.{a}' in ALL_PERMISSIONS


def test_default_role_grants():
    assert 'documents.read' in DEFAULT_ROLES['Staff']
    assert 'documents.create' in DEFAULT_ROLES['Staff']
    assert 'documents.delete' not in DEFAULT_ROLES['Staff']
    assert 'documents.delete' in DEFAULT_ROLES['Partner']
    assert set(DEFAULT_ROLES['Owner']) == ALL_PERMISSIONS
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && python -m pytest tests/test_documents_permissions.py -q`
Expected: FAIL — module is None

- [ ] **Step 3: Add module + grants**

In `backend/app/rbac/permissions.py`, add to `MODULES` (after the `case_files` entry):

```python
    {"key": "documents", "label": "Documents", "actions": CRUD},
```

Add to the `Partner` `_perms(...)`: `("documents", CRUD),`
Add to the `Associate` `_perms(...)`: `("documents", ["create", "read", "update"]),`
Add to the `Staff` `_perms(...)`: `("documents", ["create", "read"]),`

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend && python -m pytest tests/test_documents_permissions.py tests/test_rbac_permissions.py -q`
Expected: PASS

---

### Task 5: Documents API

**Files:**
- Create: `backend/app/api/case_documents.py`
- Modify: `backend/app/main.py` (import + register blueprint)
- Modify: `backend/app/api/case_files.py` (add `doc_types` to `/case-files/meta`)
- Modify: `backend/app/api/case_events.py` (on event delete, null out documents' `event_id`)
- Test: `backend/tests/test_documents_api.py`

**Interfaces:**
- Consumes: `CaseDocument`, `CaseFile`, `CaseEvent`; `document_storage` (put/signed/remove/build_path); `is_valid_doc_type`, `is_allowed_filename`, `extension_of`, `MAX_DOCUMENT_BYTES`, `DEFAULT_DOC_TYPE`, `DOC_TYPES`.
- Produces routes: `GET/POST /case-files/<case_id>/documents`, `GET /case-documents/<doc_id>/download`, `PATCH/DELETE /case-documents/<doc_id>`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_documents_api.py
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
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd backend && python -m pytest tests/test_documents_api.py -q`
Expected: FAIL — 404s / missing `doc_types`

- [ ] **Step 3: Create the blueprint**

```python
# backend/app/api/case_documents.py
"""Case document vault API — firm-scoped, gated by the documents RBAC module."""
from flask import Blueprint, request, jsonify, g
from app.models.models import db
from app.models.case import CaseFile, CaseEvent, CaseDocument
from app.middleware.jwt_auth import jwt_required
from app.middleware.firm_context import require_permission
from app.services import document_storage
from app.case.documents import (
    DEFAULT_DOC_TYPE, MAX_DOCUMENT_BYTES, is_valid_doc_type,
    is_allowed_filename, extension_of,
)

bp = Blueprint('case_documents', __name__)


def _doc_or_404(doc_id):
    return CaseDocument.query.filter_by(id=doc_id, firm_id=g.firm_id).first()


@bp.route('/case-files/<int:case_id>/documents', methods=['GET'])
@jwt_required
@require_permission('documents.read')
def list_documents(case_id):
    case_file = CaseFile.query.filter_by(id=case_id, firm_id=g.firm_id).first()
    if not case_file:
        return jsonify({'error': 'Case not found'}), 404
    query = CaseDocument.query.filter_by(case_file_id=case_id)
    doc_type = request.args.get('doc_type')
    event_id = request.args.get('event_id', type=int)
    if doc_type:
        query = query.filter_by(doc_type=doc_type)
    if event_id:
        query = query.filter_by(event_id=event_id)
    docs = query.order_by(CaseDocument.created_at.desc(), CaseDocument.id.desc()).all()
    return jsonify([d.to_dict() for d in docs])


@bp.route('/case-files/<int:case_id>/documents', methods=['POST'])
@jwt_required
@require_permission('documents.create')
def upload_document(case_id):
    case_file = CaseFile.query.filter_by(id=case_id, firm_id=g.firm_id).first()
    if not case_file:
        return jsonify({'error': 'Case not found'}), 404

    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    upload = request.files['file']
    if not upload.filename:
        return jsonify({'error': 'No file selected'}), 400
    if not is_allowed_filename(upload.filename):
        return jsonify({'error': 'File type not allowed'}), 400

    title = (request.form.get('title') or '').strip()
    if not title:
        return jsonify({'error': 'Title is required'}), 400
    doc_type = request.form.get('doc_type') or DEFAULT_DOC_TYPE
    if not is_valid_doc_type(doc_type):
        return jsonify({'error': 'Invalid doc_type'}), 400

    event_id = request.form.get('event_id', type=int)
    if event_id:
        event = CaseEvent.query.filter_by(id=event_id, case_file_id=case_id).first()
        if not event:
            return jsonify({'error': 'Timeline step not found for this case'}), 400

    data = upload.read()
    if len(data) > MAX_DOCUMENT_BYTES:
        return jsonify({'error': 'File too large (max 25MB)'}), 400

    ext = extension_of(upload.filename)
    storage_path = document_storage.build_storage_path(g.firm_id, case_id, ext)
    try:
        document_storage.put_object(storage_path, data, upload.mimetype)
    except document_storage.StorageError as e:
        return jsonify({'error': str(e)}), 503

    doc = CaseDocument(
        firm_id=g.firm_id, case_file_id=case_id, event_id=event_id,
        uploaded_by_user_id=g.user.id, title=title, doc_type=doc_type,
        file_name=upload.filename, mime_type=upload.mimetype,
        size_bytes=len(data), storage_path=storage_path,
        description=request.form.get('description'),
    )
    db.session.add(doc)
    db.session.commit()
    return jsonify(doc.to_dict()), 201


@bp.route('/case-documents/<int:doc_id>/download', methods=['GET'])
@jwt_required
@require_permission('documents.read')
def download_document(doc_id):
    doc = _doc_or_404(doc_id)
    if not doc:
        return jsonify({'error': 'Document not found'}), 404
    try:
        url = document_storage.signed_url(doc.storage_path)
    except document_storage.StorageError as e:
        return jsonify({'error': str(e)}), 503
    return jsonify({'url': url})


@bp.route('/case-documents/<int:doc_id>', methods=['PATCH'])
@jwt_required
@require_permission('documents.update')
def update_document(doc_id):
    doc = _doc_or_404(doc_id)
    if not doc:
        return jsonify({'error': 'Document not found'}), 404
    data = request.get_json() or {}
    if 'title' in data:
        doc.title = (data['title'] or '').strip() or doc.title
    if 'doc_type' in data:
        if not is_valid_doc_type(data['doc_type']):
            return jsonify({'error': 'Invalid doc_type'}), 400
        doc.doc_type = data['doc_type']
    if 'description' in data:
        doc.description = data['description']
    if 'event_id' in data:
        if data['event_id'] is None:
            doc.event_id = None
        else:
            event = CaseEvent.query.filter_by(id=data['event_id'],
                                              case_file_id=doc.case_file_id).first()
            if not event:
                return jsonify({'error': 'Timeline step not found for this case'}), 400
            doc.event_id = event.id
    db.session.commit()
    return jsonify(doc.to_dict())


@bp.route('/case-documents/<int:doc_id>', methods=['DELETE'])
@jwt_required
@require_permission('documents.delete')
def delete_document(doc_id):
    doc = _doc_or_404(doc_id)
    if not doc:
        return jsonify({'error': 'Document not found'}), 404
    try:
        document_storage.remove_object(doc.storage_path)
    except document_storage.StorageError:
        pass  # best-effort; still drop the row
    db.session.delete(doc)
    db.session.commit()
    return jsonify({'message': 'Document deleted'})
```

- [ ] **Step 4: Register + meta + event-delete null-out**

In `backend/app/main.py`: add `case_documents` to the `from app.api import ...` line and register:
```python
    app.register_blueprint(case_documents.bp, url_prefix='/api/v1')
```

In `backend/app/api/case_files.py`, import the doc types and add them to `/case-files/meta`:
```python
from app.case.documents import DOC_TYPES
```
Change the meta return to:
```python
    return jsonify({'stages': STAGES, 'event_kinds': EVENT_KINDS,
                    'priorities': PRIORITIES, 'doc_types': DOC_TYPES})
```

In `backend/app/api/case_events.py`, in `delete_event`, before `db.session.delete(event)`, detach any documents pinned to this step:
```python
    from app.models.case import CaseDocument
    CaseDocument.query.filter_by(event_id=event.id).update({'event_id': None})
```

- [ ] **Step 5: Run to verify it passes**

Run: `cd backend && python -m pytest tests/test_documents_api.py -q`
Expected: PASS (8 passed)

---

### Task 6: Migration `011`

**Files:**
- Create: `backend/migrations/011_case_documents.sql`

- [ ] **Step 1: Write the migration**

```sql
-- 011_case_documents.sql — Case document vault (sub-project 3).
-- Additive, non-destructive. Apply in the Supabase SQL editor.
-- ALSO create a PRIVATE bucket named 'case-documents' in Storage (dashboard).
BEGIN;

CREATE TABLE IF NOT EXISTS public.case_documents (
  id SERIAL PRIMARY KEY,
  firm_id INTEGER REFERENCES public.firms(id),
  case_file_id INTEGER REFERENCES public.case_files(id) ON DELETE CASCADE,
  event_id INTEGER REFERENCES public.case_events(id) ON DELETE SET NULL,
  uploaded_by_user_id INTEGER REFERENCES public.users(id),
  title VARCHAR(300) NOT NULL,
  doc_type VARCHAR(40) NOT NULL DEFAULT 'other',
  file_name VARCHAR(300),
  mime_type VARCHAR(120),
  size_bytes INTEGER,
  storage_path VARCHAR(500) NOT NULL,
  description TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_case_documents_firm_id ON public.case_documents (firm_id);
CREATE INDEX IF NOT EXISTS ix_case_documents_case_file_id ON public.case_documents (case_file_id);
CREATE INDEX IF NOT EXISTS ix_case_documents_event_id ON public.case_documents (event_id);

COMMIT;

-- Manual: Supabase dashboard → Storage → New bucket → name 'case-documents',
-- Private. Permissions need no migration (Owners dynamic; others via Roles editor).
```

- [ ] **Step 2: Sanity-check** the column names/types match `CaseDocument` in `app/models/case.py`.

---

### Task 7: Frontend API client

**Files:**
- Modify: `frontend/src/api.ts`
- Test: `cd frontend && npm run build`

**Interfaces:**
- Produces `CaseDocument` type; `CaseMeta` gains `doc_types`; methods `getCaseDocuments`, `uploadCaseDocument`, `getDocumentDownloadUrl`, `updateCaseDocument`, `deleteCaseDocument`.

- [ ] **Step 1: Add the type + meta field**

In `frontend/src/api.ts`, after the `CaseEvent` interface add:

```typescript
export interface CaseDocument {
  id: number;
  firm_id: number;
  case_file_id: number;
  event_id?: number | null;
  uploaded_by_user_id: number;
  title: string;
  doc_type: string;
  file_name?: string;
  mime_type?: string;
  size_bytes?: number;
  description?: string;
  created_at?: string;
}
```

In the `CaseMeta` interface add: `doc_types: { key: string; label: string }[];`

- [ ] **Step 2: Add the methods**

In the `api` object (near the other case methods), add:

```typescript
  getCaseDocuments: (caseId: number) =>
    fetchAPI<CaseDocument[]>(`${API_BASE_URL}/case-files/${caseId}/documents`),

  uploadCaseDocument: async (caseId: number, file: File,
                             meta: { title: string; doc_type: string; description?: string; event_id?: number }) => {
    const { supabase } = await import('./lib/supabase');
    const { data: { session } } = await supabase.auth.getSession();
    const form = new FormData();
    form.append('file', file);
    form.append('title', meta.title);
    form.append('doc_type', meta.doc_type);
    if (meta.description) form.append('description', meta.description);
    if (meta.event_id) form.append('event_id', String(meta.event_id));
    const resp = await fetch(`${API_BASE_URL}/case-files/${caseId}/documents`, {
      method: 'POST',
      headers: session?.access_token ? { Authorization: `Bearer ${session.access_token}` } : {},
      body: form,
    });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ error: resp.statusText }));
      throw new Error(err.error || `Upload failed: ${resp.status}`);
    }
    return resp.json() as Promise<CaseDocument>;
  },

  getDocumentDownloadUrl: (docId: number) =>
    fetchAPI<{ url: string }>(`${API_BASE_URL}/case-documents/${docId}/download`),

  updateCaseDocument: (docId: number, data: Partial<CaseDocument>) =>
    fetchAPI<CaseDocument>(`${API_BASE_URL}/case-documents/${docId}`, {
      method: 'PATCH', body: JSON.stringify(data),
    }),

  deleteCaseDocument: (docId: number) =>
    fetchAPI<{ message: string }>(`${API_BASE_URL}/case-documents/${docId}`, { method: 'DELETE' }),
```

- [ ] **Step 3: Typecheck**

Run: `cd frontend && npm run build`
Expected: `tsc` clean, vite build completes.

---

### Task 8: Frontend Documents panel on case detail

**Files:**
- Modify: `frontend/src/pages/CaseDetail.tsx`
- Test: `cd frontend && npm run build` + manual

**Interfaces:**
- Consumes: `api.getCaseDocuments/uploadCaseDocument/getDocumentDownloadUrl/deleteCaseDocument`, `meta.doc_types`, `usePermissions`.

- [ ] **Step 1: Add a Documents panel to the side column**

In `frontend/src/pages/CaseDetail.tsx`:

1. Add permission flags near the others: `const canUploadDocs = has('documents.create'); const canDeleteDocs = has('documents.delete');`
2. Add the documents query (near the invoices query):

```tsx
  const { data: documents = [] } = useQuery({
    queryKey: ['case-documents', caseId], queryFn: () => api.getCaseDocuments(caseId),
  });
```

3. Add upload + delete state/mutations:

```tsx
  const [docTitle, setDocTitle] = useState('');
  const [docType, setDocType] = useState('other');
  const [docFile, setDocFile] = useState<File | null>(null);

  const uploadDoc = useMutation({
    mutationFn: () => api.uploadCaseDocument(caseId, docFile as File,
      { title: docTitle, doc_type: docType }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['case-documents', caseId] });
      setDocTitle(''); setDocType('other'); setDocFile(null); showToast('Document uploaded');
    },
    onError: (e) => showToast(errMsg(e), 'error'),
  });

  const deleteDoc = useMutation({
    mutationFn: (docId: number) => api.deleteCaseDocument(docId),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['case-documents', caseId] }); },
    onError: (e) => showToast(errMsg(e), 'error'),
  });

  const openDoc = async (docId: number) => {
    try { const { url } = await api.getDocumentDownloadUrl(docId); window.open(url, '_blank'); }
    catch (e) { showToast(errMsg(e), 'error'); }
  };
```

4. Render a Documents panel inside the `<aside>` (after the Billing block), importing `Upload`, `Download`, `Paperclip` from lucide-react (add to the existing import):

```tsx
          <div>
            <div className="eyebrow mb-3">Documents</div>
            {canUploadDocs && (
              <div className="card p-3 mb-3 space-y-2">
                <input value={docTitle} placeholder="Title" onChange={(e) => setDocTitle(e.target.value)} className="field-input" />
                <div className="flex gap-2">
                  <select value={docType} onChange={(e) => setDocType(e.target.value)} className="field-select flex-1">
                    {(meta?.doc_types ?? []).map((d) => <option key={d.key} value={d.key}>{d.label}</option>)}
                  </select>
                </div>
                <input type="file" onChange={(e) => setDocFile(e.target.files?.[0] ?? null)} className="text-xs" />
                <button onClick={() => uploadDoc.mutate()}
                  disabled={!docFile || !docTitle || uploadDoc.isPending}
                  className="btn-primary w-full justify-center disabled:opacity-50">
                  <Upload size={14} /> Upload
                </button>
              </div>
            )}
            <div className="border border-rule divide-y divide-rule">
              {documents.map((d) => (
                <div key={d.id} className="bg-surface flex items-center gap-2 px-4 py-2.5 group">
                  <Paperclip size={13} className="text-ink-faint shrink-0" />
                  <button onClick={() => openDoc(d.id)} className="text-sm text-ink flex-1 text-left hover:text-oxblood truncate">
                    {d.title}
                  </button>
                  <span className="text-2xs uppercase tracking-eyebrow text-ink-muted">{d.doc_type}</span>
                  <button onClick={() => openDoc(d.id)} className="p-1 text-ink-muted hover:text-ink"><Download size={13} /></button>
                  {canDeleteDocs && (
                    <button onClick={() => { if (confirm(`Delete "${d.title}"?`)) deleteDoc.mutate(d.id); }}
                      className="p-1 text-ink-muted hover:text-oxblood opacity-0 group-hover:opacity-100"><Trash2 size={13} /></button>
                  )}
                </div>
              ))}
              {documents.length === 0 && (
                <div className="bg-surface px-4 py-3 text-sm text-ink-muted">No documents yet.</div>
              )}
            </div>
          </div>
```

- [ ] **Step 2: Typecheck**

Run: `cd frontend && npm run build`
Expected: `tsc` clean, vite build completes.

---

### Task 9: Full regression + smoke

- [ ] `cd backend && python -m pytest -q` → all green (existing + new document tests).
- [ ] `cd frontend && npm run build` → clean.
- [ ] Manual (after migration + bucket): open a case → upload a PDF with a title + doc-type → it lists → click to download (opens signed URL) → delete it.
- [ ] Hand `011_case_documents.sql` to Parth; create the private `case-documents` bucket in Supabase.

---

## Self-Review notes

- **Spec coverage:** catalog (T1), model+to_dict-omits-path+cascade (T2), storage service (T3), RBAC module+grants (T4), API upload/list/download/patch/delete + meta doc_types + event-delete null-out (T5), migration+bucket (T6), frontend client (T7), documents panel (T8), regression (T9). All spec sections mapped.
- **Type consistency:** `storage_path`, `doc_type`, `event_id`, `build_storage_path`, `put_object`, `signed_url`, `remove_object`, `StorageError`, `CaseDocument`, `getCaseDocuments`/`uploadCaseDocument`/`getDocumentDownloadUrl` consistent across tasks.
- **Deferred:** per-step attach UI (only `event_id` plumbing now); version chains; separate evidence register. Matches spec scope.
- **Git:** no commit steps — Parth handles git; each task gates on green.
