# Case System UX — Plan 5: Evidence Exhibit Register Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the case file an Evidence tab that is a proper exhibit register — each exhibit has a court-style mark (Ex. P-1 / D-1), a producing party, an admitted/objected/denied status, and links to the underlying document and the hearing it came in through.

**Architecture:** A code-defined catalog (`app/case/exhibits.py`) supplies the status vocabulary and producing-party suggestions. A `CaseExhibit` model (firm-scoped, hung off the case file) stores the register rows with optional `document_id`/`hearing_event_id` links. A `case_exhibits` API (gated by `case_files` permissions, matching notes/expenses) does CRUD; deleting a document or event nulls the matching exhibit links. `/case-files/meta` gains `exhibit_statuses` + `exhibit_parties`. The "Mark an exhibit" rail action flips to available. The frontend adds an Evidence tab rendering the register table with add/edit/delete, reusing the case's existing document and hearing-event lists for the links.

**Tech Stack:** Flask + SQLAlchemy (SQLite in tests via `db.create_all`), pytest; React + TypeScript + Vite, TanStack Query, Tailwind tokens.

## Global Constraints

- Never run git commits/pushes — Parth does git. Stage only; run the gate and report.
- Migrations are SQL files for Parth to apply. New file: `016_case_exhibits.sql`.
- Exhibits gated by `case_files` permissions (read → list; update → create/edit/delete), consistent with `case_notes`/`case_expenses`. No new RBAC module.
- Exhibit `status` is validated against the catalog; `party` is stored free-form with catalog suggestions in `/meta`.
- Auto-suggesting the next mark per party is out of scope — `exhibit_mark` is a free text field (placeholder `Ex. P-1`).
- Backend stays green (`pytest`); frontend builds clean (`npm run build`).

---

### Task 1: Exhibit catalog + `CaseExhibit` model + migration 016

**Files:**
- Create: `backend/app/case/exhibits.py`
- Modify: `backend/app/models/case.py` (add `CaseExhibit`; add `exhibits` relationship to `CaseFile`)
- Modify: `backend/app/main.py:61` (import `CaseExhibit`)
- Create: `backend/migrations/016_case_exhibits.sql`
- Test: `backend/tests/test_case_exhibit_models.py`

**Interfaces:**
- Produces: `EXHIBIT_STATUSES` (list of `{key,label}`), `EXHIBIT_STATUS_KEYS` (set), `DEFAULT_EXHIBIT_STATUS = "marked"`, `EXHIBIT_PARTIES` (list of `{key,label}`), `is_valid_exhibit_status(key)`. `CaseExhibit(firm_id, case_file_id, exhibit_mark, description, party, status, document_id, hearing_event_id, created_by_user_id, created_at)` with `to_dict()`; `CaseFile.exhibits` (cascade delete-orphan).

- [ ] **Step 1: Write the failing catalog + model test**

Create `backend/tests/test_case_exhibit_models.py`:

```python
from app.case.exhibits import (
    EXHIBIT_STATUSES, EXHIBIT_STATUS_KEYS, DEFAULT_EXHIBIT_STATUS,
    EXHIBIT_PARTIES, is_valid_exhibit_status,
)
from app.models.models import db, Client
from app.models.case import CaseFile, CaseExhibit


def test_exhibit_catalog():
    assert DEFAULT_EXHIBIT_STATUS == "marked"
    assert {s["key"] for s in EXHIBIT_STATUSES} == EXHIBIT_STATUS_KEYS
    assert {"marked", "admitted", "objected", "denied"} == EXHIBIT_STATUS_KEYS
    assert is_valid_exhibit_status("admitted")
    assert not is_valid_exhibit_status("teleported")
    assert all("label" in p for p in EXHIBIT_PARTIES)


def _case(app):
    with app.app_context():
        c = Client(firm_id=1, created_by_user_id=1, name='X')
        db.session.add(c); db.session.flush()
        cf = CaseFile(firm_id=1, created_by_user_id=1, case_number='CF/2026/0001',
                      title='M', client_id=c.id)
        db.session.add(cf); db.session.commit()
        return cf.id


def test_exhibit_defaults_and_to_dict(app):
    cf_id = _case(app)
    with app.app_context():
        ex = CaseExhibit(firm_id=1, case_file_id=cf_id, created_by_user_id=1,
                         exhibit_mark='Ex. P-1', description='Sale deed', party='petitioner')
        db.session.add(ex); db.session.commit()
        d = ex.to_dict()
        assert d['exhibit_mark'] == 'Ex. P-1'
        assert d['status'] == 'marked'
        assert d['document_id'] is None and d['hearing_event_id'] is None
        assert d['party'] == 'petitioner'
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd backend && python -m pytest tests/test_case_exhibit_models.py -v`
Expected: FAIL — `app.case.exhibits` / `CaseExhibit` missing.

- [ ] **Step 3: Create the exhibit catalog**

Create `backend/app/case/exhibits.py`:

```python
"""Evidence exhibit register catalog: status vocabulary + producing-party
suggestions. Mirrors the court convention of marking exhibits (Ex. P-1 / D-1)
and tracking their admission."""

EXHIBIT_STATUSES = [
    {"key": "marked",   "label": "Marked"},
    {"key": "admitted", "label": "Admitted"},
    {"key": "objected", "label": "Objected"},
    {"key": "denied",   "label": "Denied"},
]
EXHIBIT_STATUS_KEYS = {s["key"] for s in EXHIBIT_STATUSES}
DEFAULT_EXHIBIT_STATUS = "marked"

EXHIBIT_PARTIES = [
    {"key": "petitioner", "label": "Petitioner / Plaintiff"},
    {"key": "respondent", "label": "Respondent / Defendant"},
    {"key": "court",      "label": "Court"},
]


def is_valid_exhibit_status(key):
    return key in EXHIBIT_STATUS_KEYS
```

- [ ] **Step 4: Add the `exhibits` relationship to `CaseFile`**

In `backend/app/models/case.py`, in the `CaseFile` relationships block (after the `notes` relationship), add:

```python
    exhibits = db.relationship('CaseExhibit', back_populates='case_file',
                               cascade='all, delete-orphan')
```

- [ ] **Step 5: Add the `CaseExhibit` model**

At the end of `backend/app/models/case.py`, add:

```python
class CaseExhibit(db.Model):
    __tablename__ = 'case_exhibits'

    id = db.Column(db.Integer, primary_key=True)
    firm_id = db.Column(db.Integer, db.ForeignKey('firms.id'), index=True)
    case_file_id = db.Column(db.Integer, db.ForeignKey('case_files.id'), index=True)
    exhibit_mark = db.Column(db.String(40))
    description = db.Column(db.String(300))
    party = db.Column(db.String(40))
    status = db.Column(db.String(20), nullable=False, default='marked')
    document_id = db.Column(db.Integer, db.ForeignKey('case_documents.id'))
    hearing_event_id = db.Column(db.Integer, db.ForeignKey('case_events.id'))
    created_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    case_file = db.relationship('CaseFile', back_populates='exhibits')

    def to_dict(self):
        return {
            'id': self.id,
            'firm_id': self.firm_id,
            'case_file_id': self.case_file_id,
            'exhibit_mark': self.exhibit_mark,
            'description': self.description,
            'party': self.party,
            'status': self.status,
            'document_id': self.document_id,
            'hearing_event_id': self.hearing_event_id,
            'created_by_user_id': self.created_by_user_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
```

- [ ] **Step 6: Register the model in `main.py`**

In `backend/app/main.py:61`, append `, CaseExhibit` to the `from app.models.case import ...` line.

- [ ] **Step 7: Run the catalog + model test to verify it passes**

Run: `cd backend && python -m pytest tests/test_case_exhibit_models.py -v`
Expected: PASS.

- [ ] **Step 8: Create migration 016**

Create `backend/migrations/016_case_exhibits.sql`:

```sql
-- 016_case_exhibits.sql — evidence exhibit register (Ex. P-1/D-1 marks).
-- Additive/non-destructive. Apply in the Supabase SQL editor.
BEGIN;

CREATE TABLE IF NOT EXISTS public.case_exhibits (
  id SERIAL PRIMARY KEY,
  firm_id INTEGER REFERENCES public.firms(id),
  case_file_id INTEGER REFERENCES public.case_files(id) ON DELETE CASCADE,
  exhibit_mark VARCHAR(40),
  description VARCHAR(300),
  party VARCHAR(40),
  status VARCHAR(20) NOT NULL DEFAULT 'marked',
  document_id INTEGER REFERENCES public.case_documents(id),
  hearing_event_id INTEGER REFERENCES public.case_events(id),
  created_by_user_id INTEGER REFERENCES public.users(id),
  created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_case_exhibits_case_file_id ON public.case_exhibits (case_file_id);
CREATE INDEX IF NOT EXISTS ix_case_exhibits_firm_id ON public.case_exhibits (firm_id);

COMMIT;
```

- [ ] **Step 9: Run the full suite + stage (do NOT commit)**

Run: `cd backend && python -m pytest -q`
Expected: PASS (270).

```bash
git add backend/app/case/exhibits.py backend/app/models/case.py backend/app/main.py backend/migrations/016_case_exhibits.sql backend/tests/test_case_exhibit_models.py
```

---

### Task 2: Exhibits API + meta + rail flip + delete cleanup

**Files:**
- Create: `backend/app/api/case_exhibits.py`
- Modify: `backend/app/main.py:12` (import), `:88` (register blueprint)
- Modify: `backend/app/api/case_files.py` (`/meta` adds exhibit catalogs; import)
- Modify: `backend/app/case/stages.py` (flip `mark_exhibit` to `available: True`)
- Modify: `backend/app/api/case_events.py` (null `CaseExhibit.hearing_event_id` on event delete)
- Modify: `backend/app/api/case_documents.py` (null `CaseExhibit.document_id` on doc delete)
- Test: `backend/tests/test_case_exhibits_api.py`, `backend/tests/test_case_files_api.py`, `backend/tests/test_case_stages.py`

**Interfaces:**
- Produces: blueprint `case_exhibits` with `GET/POST /case-files/<id>/exhibits`, `PATCH/DELETE /case-exhibits/<id>`. Accepts `exhibit_mark, description, party, status, document_id, hearing_event_id`; rejects an invalid `status` with 400. `/meta` gains `exhibit_statuses`, `exhibit_parties`. `STAGE_GUIDES["hearings_evidence"]` action `mark_exhibit` becomes `available: True`.

- [ ] **Step 1: Write the failing API test**

Create `backend/tests/test_case_exhibits_api.py`:

```python
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
    from app.services import document_storage
    monkeypatch.setattr(document_storage, 'put_object', lambda *a, **k: None)
    monkeypatch.setattr(document_storage, 'remove_object', lambda *a, **k: None)
    headers, firm_id = make_owner()
    case_id = _case(client, headers, firm_id)
    import io
    doc = client.post(f'/api/v1/case-files/{case_id}/documents', headers=headers,
                      data={'title': 'Deed', 'doc_type': 'evidence',
                            'file': (io.BytesIO(b'x'), 'deed.pdf')},
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
```

> Note: the document-delete test mirrors the upload contract used in `backend/tests/test_case_documents_api.py`. If the field names differ there (e.g. the file part key or the storage monkeypatch targets), copy that test's exact setup before running.

- [ ] **Step 2: Run it to verify it fails**

Run: `cd backend && python -m pytest tests/test_case_exhibits_api.py -v`
Expected: FAIL — `/exhibits` routes 404.

- [ ] **Step 3: Create the exhibits blueprint**

Create `backend/app/api/case_exhibits.py`:

```python
"""Case evidence exhibit-register API. Firm-scoped, gated by case_files
permissions (read = list, update = create/edit/delete)."""
from flask import Blueprint, request, jsonify, g
from app.models.models import db
from app.models.case import CaseFile, CaseExhibit
from app.middleware.jwt_auth import jwt_required
from app.middleware.firm_context import require_permission
from app.case.exhibits import DEFAULT_EXHIBIT_STATUS, is_valid_exhibit_status

bp = Blueprint('case_exhibits', __name__)

FIELDS = ('exhibit_mark', 'description', 'party', 'document_id', 'hearing_event_id')


def _case_or_404(case_id):
    return CaseFile.query.filter_by(id=case_id, firm_id=g.firm_id).first()


def _exhibit_or_404(exhibit_id):
    return CaseExhibit.query.filter_by(id=exhibit_id, firm_id=g.firm_id).first()


@bp.route('/case-files/<int:case_id>/exhibits', methods=['GET'])
@jwt_required
@require_permission('case_files.read')
def list_exhibits(case_id):
    if not _case_or_404(case_id):
        return jsonify({'error': 'Case not found'}), 404
    rows = CaseExhibit.query.filter_by(case_file_id=case_id).order_by(CaseExhibit.id).all()
    return jsonify([e.to_dict() for e in rows])


@bp.route('/case-files/<int:case_id>/exhibits', methods=['POST'])
@jwt_required
@require_permission('case_files.update')
def create_exhibit(case_id):
    if not _case_or_404(case_id):
        return jsonify({'error': 'Case not found'}), 404
    data = request.get_json() or {}
    status = data.get('status', DEFAULT_EXHIBIT_STATUS)
    if not is_valid_exhibit_status(status):
        return jsonify({'error': 'Invalid status'}), 400
    ex = CaseExhibit(firm_id=g.firm_id, case_file_id=case_id, created_by_user_id=g.user.id,
                     status=status, **{f: data.get(f) for f in FIELDS})
    db.session.add(ex)
    db.session.commit()
    return jsonify(ex.to_dict()), 201


@bp.route('/case-exhibits/<int:exhibit_id>', methods=['PATCH'])
@jwt_required
@require_permission('case_files.update')
def update_exhibit(exhibit_id):
    ex = _exhibit_or_404(exhibit_id)
    if not ex:
        return jsonify({'error': 'Exhibit not found'}), 404
    data = request.get_json() or {}
    if 'status' in data:
        if not is_valid_exhibit_status(data['status']):
            return jsonify({'error': 'Invalid status'}), 400
        ex.status = data['status']
    for field in FIELDS:
        if field in data:
            setattr(ex, field, data[field])
    db.session.commit()
    return jsonify(ex.to_dict())


@bp.route('/case-exhibits/<int:exhibit_id>', methods=['DELETE'])
@jwt_required
@require_permission('case_files.update')
def delete_exhibit(exhibit_id):
    ex = _exhibit_or_404(exhibit_id)
    if not ex:
        return jsonify({'error': 'Exhibit not found'}), 404
    db.session.delete(ex)
    db.session.commit()
    return jsonify({'message': 'Exhibit deleted'})
```

- [ ] **Step 4: Register the blueprint**

In `backend/app/main.py:12`, append `, case_exhibits` to the `from app.api import ...` line.
After line 88 (`app.register_blueprint(case_notes.bp, ...)`), add:

```python
    app.register_blueprint(case_exhibits.bp, url_prefix='/api/v1')
```

- [ ] **Step 5: Add the exhibit catalogs to `/meta`**

Write the failing meta assertion first — append to `backend/tests/test_case_files_api.py`:

```python
def test_meta_includes_exhibit_catalogs(client, make_owner):
    headers, _ = make_owner()
    body = client.get('/api/v1/case-files/meta', headers=headers).get_json()
    assert {s['key'] for s in body['exhibit_statuses']} == {'marked', 'admitted', 'objected', 'denied'}
    assert any(p['key'] == 'petitioner' for p in body['exhibit_parties'])
```

Then in `backend/app/api/case_files.py`, add the import:

```python
from app.case.exhibits import EXHIBIT_STATUSES, EXHIBIT_PARTIES
```
and extend the `case_meta` return dict with:

```python
                    'exhibit_statuses': EXHIBIT_STATUSES,
                    'exhibit_parties': EXHIBIT_PARTIES,
```

- [ ] **Step 6: Flip the `mark_exhibit` rail action to available**

Write the failing assertion first — append to `backend/tests/test_case_stages.py`:

```python
def test_mark_exhibit_action_is_available():
    actions = {a["key"]: a for a in STAGE_GUIDES["hearings_evidence"]["actions"]}
    assert actions["mark_exhibit"]["available"] is True
```

Then in `backend/app/case/stages.py`, in `STAGE_GUIDES["hearings_evidence"]`, change the `mark_exhibit` action's `"available": False` to `"available": True`.

- [ ] **Step 7: Null exhibit links on event/document delete**

In `backend/app/api/case_events.py` `delete_event`, extend the import line to `from app.models.case import CaseDocument, CaseNote, CaseExhibit` and add:

```python
    CaseExhibit.query.filter_by(hearing_event_id=event.id).update({'hearing_event_id': None})
```

In `backend/app/api/case_documents.py` `delete_document`, change `from app.models.case import CaseNote` to `from app.models.case import CaseNote, CaseExhibit` and add:

```python
    CaseExhibit.query.filter_by(document_id=doc.id).update({'document_id': None})
```

- [ ] **Step 8: Run the new tests + full suite**

Run: `cd backend && python -m pytest tests/test_case_exhibits_api.py tests/test_case_files_api.py tests/test_case_stages.py -q && python -m pytest -q`
Expected: PASS (276).

- [ ] **Step 9: Stage (do NOT commit)**

```bash
git add backend/app/api/case_exhibits.py backend/app/main.py backend/app/api/case_files.py backend/app/case/stages.py backend/app/api/case_events.py backend/app/api/case_documents.py backend/tests/test_case_exhibits_api.py backend/tests/test_case_files_api.py backend/tests/test_case_stages.py
```

---

### Task 3: Frontend — Evidence tab

**Files:**
- Modify: `frontend/src/api.ts` (`CaseExhibit` type + methods; `CaseMeta` adds exhibit catalogs)
- Modify: `frontend/src/pages/CaseDetail.tsx` (add `evidence` tab + register UI; wire `mark_exhibit` rail action)
- Gate: `npm run build` clean.

**Interfaces:**
- Consumes: existing `api.getCaseDocuments`, `api.getCaseEvents` (for the link dropdowns); `CaseMeta.exhibit_statuses`, `CaseMeta.exhibit_parties`.
- Produces: `api.getCaseExhibits(caseId)`, `api.addCaseExhibit(caseId, data)`, `api.updateCaseExhibit(id, data)`, `api.deleteCaseExhibit(id)`; `CaseExhibit` interface.

- [ ] **Step 1: Add the `CaseExhibit` type + API methods + meta fields**

In `frontend/src/api.ts`, extend `CaseMeta` (the interface from Plan 3) by adding:

```ts
  exhibit_statuses: { key: string; label: string }[];
  exhibit_parties: { key: string; label: string }[];
```

Add the interface near the other case types:

```ts
export interface CaseExhibit {
  id: number;
  case_file_id: number;
  exhibit_mark: string | null;
  description: string | null;
  party: string | null;
  status: string;
  document_id: number | null;
  hearing_event_id: number | null;
  created_at: string | null;
}
```

Add to the `api` object, after the case-notes methods:

```ts
  // ---- Case exhibits ----------------------------------------------------
  getCaseExhibits: (caseId: number) =>
    fetchAPI<CaseExhibit[]>(`${API_BASE_URL}/case-files/${caseId}/exhibits`),

  addCaseExhibit: (caseId: number, data: Partial<CaseExhibit>) =>
    fetchAPI<CaseExhibit>(`${API_BASE_URL}/case-files/${caseId}/exhibits`, {
      method: 'POST', body: JSON.stringify(data),
    }),

  updateCaseExhibit: (id: number, data: Partial<CaseExhibit>) =>
    fetchAPI<CaseExhibit>(`${API_BASE_URL}/case-exhibits/${id}`, {
      method: 'PATCH', body: JSON.stringify(data),
    }),

  deleteCaseExhibit: (id: number) =>
    fetchAPI<{ message: string }>(`${API_BASE_URL}/case-exhibits/${id}`, { method: 'DELETE' }),
```

- [ ] **Step 2: Add `evidence` to the tab union + tab bar**

In `frontend/src/pages/CaseDetail.tsx`:
- Change the `Tab` type (line 21) to:
  ```tsx
  type Tab = 'overview' | 'timeline' | 'documents' | 'evidence' | 'fees';
  ```
- In the tab bar `.map` array (line 231), change `(['overview', 'timeline', 'documents', 'fees'] as const)` to:
  ```tsx
  (['overview', 'timeline', 'documents', 'evidence', 'fees'] as const)
  ```

- [ ] **Step 3: Wire the `mark_exhibit` rail action**

In `CaseDetail.tsx`, in the `railAction` switch (added in Plan 3), add a case:

```tsx
      case 'mark_exhibit': setTab('evidence'); break;
```

- [ ] **Step 4: Add the exhibits query + mutations**

In `CaseDetail.tsx`, after the `notes` query (added in Plan 4), add:

```tsx
  const { data: exhibits = [] } = useQuery({
    queryKey: ['case-exhibits', caseId], queryFn: () => api.getCaseExhibits(caseId),
  });
```

After the expenses mutations (around line 176), add:

```tsx
  const [exhibit, setExhibit] = useState({ exhibit_mark: '', description: '', party: '', status: 'marked', document_id: '', hearing_event_id: '' });
  const invalidateExhibits = () => queryClient.invalidateQueries({ queryKey: ['case-exhibits', caseId] });
  const addExhibit = useMutation({
    mutationFn: () => api.addCaseExhibit(caseId, {
      exhibit_mark: exhibit.exhibit_mark, description: exhibit.description,
      party: exhibit.party || null, status: exhibit.status,
      document_id: exhibit.document_id ? Number(exhibit.document_id) : null,
      hearing_event_id: exhibit.hearing_event_id ? Number(exhibit.hearing_event_id) : null,
    }),
    onSuccess: () => { invalidateExhibits(); setExhibit({ exhibit_mark: '', description: '', party: '', status: 'marked', document_id: '', hearing_event_id: '' }); showToast('Exhibit added'); },
    onError: (e) => showToast(errMsg(e), 'error'),
  });
  const setExhibitStatus = useMutation({
    mutationFn: ({ id, status }: { id: number; status: string }) => api.updateCaseExhibit(id, { status }),
    onSuccess: invalidateExhibits,
    onError: (e) => showToast(errMsg(e), 'error'),
  });
  const deleteExhibit = useMutation({
    mutationFn: (id: number) => api.deleteCaseExhibit(id),
    onSuccess: invalidateExhibits,
    onError: (e) => showToast(errMsg(e), 'error'),
  });
  const hearings = events.filter((ev) => ev.kind === 'hearing');
```

- [ ] **Step 5: Render the Evidence tab**

In `CaseDetail.tsx`, after the Documents panel `{tab === 'documents' && (...)}` and before the Fees panel `{tab === 'fees' && (...)}`, insert:

```tsx
      {/* Evidence — exhibit register */}
      {tab === 'evidence' && (
        <div className="max-w-3xl">
          {canUpdate && (
            <form onSubmit={(e) => { e.preventDefault(); addExhibit.mutate(); }} className="card p-4 mb-4 space-y-2">
              <div className="grid grid-cols-2 gap-2">
                <input value={exhibit.exhibit_mark} placeholder="Mark — e.g. Ex. P-1"
                  onChange={(e) => setExhibit({ ...exhibit, exhibit_mark: e.target.value })} className="field-input font-mono" />
                <select value={exhibit.party} onChange={(e) => setExhibit({ ...exhibit, party: e.target.value })} className="field-select">
                  <option value="">— Producing party —</option>
                  {(meta?.exhibit_parties ?? []).map((p) => <option key={p.key} value={p.key}>{p.label}</option>)}
                </select>
              </div>
              <input value={exhibit.description} placeholder="Description"
                onChange={(e) => setExhibit({ ...exhibit, description: e.target.value })} className="field-input" />
              <div className="grid grid-cols-3 gap-2">
                <select value={exhibit.status} onChange={(e) => setExhibit({ ...exhibit, status: e.target.value })} className="field-select">
                  {(meta?.exhibit_statuses ?? []).map((s) => <option key={s.key} value={s.key}>{s.label}</option>)}
                </select>
                <select value={exhibit.document_id} onChange={(e) => setExhibit({ ...exhibit, document_id: e.target.value })} className="field-select">
                  <option value="">— Link file —</option>
                  {documents.map((d) => <option key={d.id} value={d.id}>{d.title}</option>)}
                </select>
                <select value={exhibit.hearing_event_id} onChange={(e) => setExhibit({ ...exhibit, hearing_event_id: e.target.value })} className="field-select">
                  <option value="">— Hearing —</option>
                  {hearings.map((h) => <option key={h.id} value={h.id}>{h.event_date} · {h.title}</option>)}
                </select>
              </div>
              <div className="flex justify-end">
                <button type="submit" className="btn-primary" disabled={addExhibit.isPending}><Plus size={14} /> Add exhibit</button>
              </div>
            </form>
          )}
          <div className="border border-rule divide-y divide-rule">
            {exhibits.map((ex) => {
              const doc = documents.find((d) => d.id === ex.document_id);
              return (
                <div key={ex.id} className="bg-surface flex items-center gap-3 px-4 py-2.5 group">
                  <span className="text-2xs font-mono text-oxblood w-16 shrink-0">{ex.exhibit_mark}</span>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm text-ink truncate">{ex.description}</div>
                    <div className="text-2xs text-ink-muted">
                      {ex.party}{doc && <button onClick={() => openDoc(doc.id)} className="ml-2 text-oxblood hover:underline">{doc.title}</button>}
                    </div>
                  </div>
                  {canUpdate ? (
                    <select value={ex.status} onChange={(e) => setExhibitStatus.mutate({ id: ex.id, status: e.target.value })}
                      className="field-select w-32 text-2xs">
                      {(meta?.exhibit_statuses ?? []).map((s) => <option key={s.key} value={s.key}>{s.label}</option>)}
                    </select>
                  ) : (
                    <span className="text-2xs uppercase tracking-eyebrow text-ink-muted">{ex.status}</span>
                  )}
                  {canUpdate && <button onClick={() => deleteExhibit.mutate(ex.id)} className="p-1 text-ink-muted hover:text-oxblood opacity-0 group-hover:opacity-100"><Trash2 size={13} /></button>}
                </div>
              );
            })}
            {exhibits.length === 0 && <div className="bg-surface px-4 py-3 text-sm text-ink-muted">No exhibits marked yet.</div>}
          </div>
        </div>
      )}
```

- [ ] **Step 6: Build the frontend**

Run: `cd frontend && npm run build`
Expected: build succeeds, no TypeScript errors.

- [ ] **Step 7: Stage (do NOT commit)**

```bash
git add frontend/src/api.ts frontend/src/pages/CaseDetail.tsx
```

---

## Self-Review

**Spec coverage (against `2026-06-25-case-system-ux-design.md` §E + §H):**
- Exhibit register: mark, producing party, status (marked/admitted/objected/denied), linked file, linked hearing → Tasks 1-3. ✓
- `case_exhibits` table + migration → Task 1. ✓
- Evidence tab distinct from Documents → Task 3. ✓
- Rail "Mark an exhibit" now live → Task 2 Step 6 + Task 3 Step 3. ✓
- Links survive file/hearing deletion → Task 2 Step 7. ✓
- `/meta` exhibit catalogs → Task 2 Step 5. ✓

**Deferred-by-design:** auto-suggesting the next mark per party (free text mark instead). Editing mark/description/party after creation is via re-create or the status dropdown only in this pass — full inline edit of every field can follow if needed (status, the most-changed field, is inline-editable).

**Placeholder scan:** none.

**Type consistency:** `CaseExhibit` fields match between `case.py` `to_dict`, the API (`FIELDS` + `status`), and the FE interface. `exhibit_statuses`/`exhibit_parties` shape (`{key,label}`) matches `EXHIBIT_STATUSES`/`EXHIBIT_PARTIES`. The doc-delete test's upload contract must match `test_case_documents_api.py` (flagged in Task 2 Step 1).
