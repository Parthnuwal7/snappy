# Case System UX — Plan 4: Notes (always-on panel + pin/attach) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a first-class notes stream to the case file — an always-on panel for the advocate's running commentary, where any note can be pinned to the timeline or attached to a specific event/document.

**Architecture:** A new `CaseNote` model (firm-scoped, hung off the case file) carries `body`, a `pinned` flag, and optional `event_id`/`document_id` links. A `case_notes` API (gated by existing `case_files` permissions, matching the expenses pattern) does CRUD. Deleting a timeline event or a document nulls the corresponding note links (best-effort, so notes survive). On the frontend a `NotesPanel` lives in the case-file right sidebar beneath the stage rail (so it persists across tabs); pinned notes also surface on the Overview tab. Lead conversion now seeds the intake notes as the first (pinned) `CaseNote`.

**Tech Stack:** Flask + SQLAlchemy (SQLite in tests via `db.create_all`), pytest; React + TypeScript + Vite, TanStack Query, Tailwind tokens.

## Global Constraints

- Never run git commits/pushes — Parth does git. Stage only; run the gate and report.
- Migrations are SQL files for Parth to apply. New file: `015_case_notes.sql`.
- Notes are gated by `case_files` permissions (read → list; update → create/edit/delete), consistent with `case_expenses`. No new RBAC module.
- The model/API support `pinned` + `event_id` + `document_id` (full seam). The Plan-4 UI ships the panel + pin toggle; attaching a note to a *specific* event/document from the UI is a later refinement — the API already accepts it.
- Backend stays green (`pytest`); frontend builds clean (`npm run build`).

---

### Task 1: `CaseNote` model + migration 015

**Files:**
- Modify: `backend/app/models/case.py` (add `CaseNote`; add `notes` relationship to `CaseFile`)
- Modify: `backend/app/main.py:61` (import `CaseNote`)
- Create: `backend/migrations/015_case_notes.sql`
- Test: `backend/tests/test_case_note_models.py`

**Interfaces:**
- Produces: `CaseNote(firm_id, case_file_id, body, pinned, event_id, document_id, created_by_user_id, created_at, updated_at)` with `to_dict()`; `CaseFile.notes` relationship (cascade delete-orphan).

- [ ] **Step 1: Write the failing model test**

Create `backend/tests/test_case_note_models.py`:

```python
from datetime import date
from app.models.models import db, Client
from app.models.case import CaseFile, CaseNote


def _case(app):
    with app.app_context():
        c = Client(firm_id=1, created_by_user_id=1, name='X')
        db.session.add(c); db.session.flush()
        cf = CaseFile(firm_id=1, created_by_user_id=1, case_number='CF/2026/0001',
                      title='M', client_id=c.id)
        db.session.add(cf); db.session.commit()
        return cf.id


def test_case_note_defaults_and_to_dict(app):
    cf_id = _case(app)
    with app.app_context():
        note = CaseNote(firm_id=1, case_file_id=cf_id, created_by_user_id=1,
                        body='Client to bring originals')
        db.session.add(note); db.session.commit()
        d = note.to_dict()
        assert d['body'] == 'Client to bring originals'
        assert d['pinned'] is False
        assert d['event_id'] is None and d['document_id'] is None
        assert d['case_file_id'] == cf_id
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd backend && python -m pytest tests/test_case_note_models.py -v`
Expected: FAIL — `CaseNote` not importable.

- [ ] **Step 3: Add the `notes` relationship to `CaseFile`**

In `backend/app/models/case.py`, in the `CaseFile` relationships block (after the `expenses` relationship, around line 52-53), add:

```python
    notes = db.relationship('CaseNote', back_populates='case_file',
                            cascade='all, delete-orphan')
```

- [ ] **Step 4: Add the `CaseNote` model**

At the end of `backend/app/models/case.py`, add:

```python
class CaseNote(db.Model):
    __tablename__ = 'case_notes'

    id = db.Column(db.Integer, primary_key=True)
    firm_id = db.Column(db.Integer, db.ForeignKey('firms.id'), index=True)
    case_file_id = db.Column(db.Integer, db.ForeignKey('case_files.id'), index=True)
    body = db.Column(db.Text, nullable=False)
    pinned = db.Column(db.Boolean, nullable=False, default=False)
    event_id = db.Column(db.Integer, db.ForeignKey('case_events.id'))
    document_id = db.Column(db.Integer, db.ForeignKey('case_documents.id'))
    created_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    case_file = db.relationship('CaseFile', back_populates='notes')

    def to_dict(self):
        return {
            'id': self.id,
            'firm_id': self.firm_id,
            'case_file_id': self.case_file_id,
            'body': self.body,
            'pinned': self.pinned,
            'event_id': self.event_id,
            'document_id': self.document_id,
            'created_by_user_id': self.created_by_user_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
```

- [ ] **Step 5: Register the model in `main.py`**

In `backend/app/main.py:61`, append `, CaseNote` to the `from app.models.case import ...` line so it reads:

```python
        from app.models.case import CaseFile, CaseParty, CaseEvent, CaseDocument, CaseStageChange, CaseExpense, CaseNote  # ensure case tables are created
```

- [ ] **Step 6: Run the model test to verify it passes**

Run: `cd backend && python -m pytest tests/test_case_note_models.py -v`
Expected: PASS.

- [ ] **Step 7: Create migration 015**

Create `backend/migrations/015_case_notes.sql`:

```sql
-- 015_case_notes.sql — case notes stream (running commentary, pin/attach).
-- Additive/non-destructive. Apply in the Supabase SQL editor.
BEGIN;

CREATE TABLE IF NOT EXISTS public.case_notes (
  id SERIAL PRIMARY KEY,
  firm_id INTEGER REFERENCES public.firms(id),
  case_file_id INTEGER REFERENCES public.case_files(id) ON DELETE CASCADE,
  body TEXT NOT NULL,
  pinned BOOLEAN NOT NULL DEFAULT FALSE,
  event_id INTEGER REFERENCES public.case_events(id),
  document_id INTEGER REFERENCES public.case_documents(id),
  created_by_user_id INTEGER REFERENCES public.users(id),
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_case_notes_case_file_id ON public.case_notes (case_file_id);
CREATE INDEX IF NOT EXISTS ix_case_notes_firm_id ON public.case_notes (firm_id);

COMMIT;
```

- [ ] **Step 8: Run the full suite + stage (do NOT commit)**

Run: `cd backend && python -m pytest -q`
Expected: PASS (263).

```bash
git add backend/app/models/case.py backend/app/main.py backend/migrations/015_case_notes.sql backend/tests/test_case_note_models.py
```

---

### Task 2: `case_notes` API + link cleanup on delete

**Files:**
- Create: `backend/app/api/case_notes.py`
- Modify: `backend/app/main.py:12` (import), `:88` (register blueprint)
- Modify: `backend/app/api/case_events.py:90-99` (null `CaseNote.event_id` on event delete)
- Modify: `backend/app/api/case_documents.py:136-146` (null `CaseNote.document_id` on doc delete)
- Test: `backend/tests/test_case_notes_api.py`

**Interfaces:**
- Produces: blueprint `case_notes` with `GET/POST /case-files/<id>/notes`, `PATCH/DELETE /case-notes/<id>`. List returns pinned-first then newest. Accepts `body`, `pinned`, `event_id`, `document_id`.

- [ ] **Step 1: Write the failing API test**

Create `backend/tests/test_case_notes_api.py`:

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


def test_note_crud_and_pin(client, make_owner):
    headers, firm_id = make_owner()
    case_id = _case(client, headers, firm_id)
    n = client.post(f'/api/v1/case-files/{case_id}/notes', headers=headers,
                    json={'body': 'limitation angle weak'}).get_json()
    assert n['pinned'] is False
    lst = client.get(f'/api/v1/case-files/{case_id}/notes', headers=headers).get_json()
    assert len(lst) == 1

    pinned = client.patch(f"/api/v1/case-notes/{n['id']}", headers=headers,
                          json={'pinned': True, 'body': 'limitation is weak'}).get_json()
    assert pinned['pinned'] is True
    assert pinned['body'] == 'limitation is weak'

    assert client.delete(f"/api/v1/case-notes/{n['id']}", headers=headers).status_code == 200
    assert client.get(f'/api/v1/case-files/{case_id}/notes', headers=headers).get_json() == []


def test_note_requires_body(client, make_owner):
    headers, firm_id = make_owner()
    case_id = _case(client, headers, firm_id)
    assert client.post(f'/api/v1/case-files/{case_id}/notes', headers=headers,
                       json={'body': '   '}).status_code == 400


def test_notes_pinned_first(client, make_owner):
    headers, firm_id = make_owner()
    case_id = _case(client, headers, firm_id)
    client.post(f'/api/v1/case-files/{case_id}/notes', headers=headers, json={'body': 'first'})
    second = client.post(f'/api/v1/case-files/{case_id}/notes', headers=headers, json={'body': 'second'}).get_json()
    client.patch(f"/api/v1/case-notes/{second['id']}", headers=headers, json={'pinned': True})
    lst = client.get(f'/api/v1/case-files/{case_id}/notes', headers=headers).get_json()
    assert lst[0]['body'] == 'second'  # pinned floats to the top


def test_deleting_event_detaches_note(client, make_owner):
    headers, firm_id = make_owner()
    case_id = _case(client, headers, firm_id)
    ev = client.post(f'/api/v1/case-files/{case_id}/events', headers=headers,
                     json={'event_date': '2026-06-01', 'kind': 'hearing', 'title': 'Hearing'}).get_json()
    note = client.post(f'/api/v1/case-files/{case_id}/notes', headers=headers,
                       json={'body': 'carry originals', 'event_id': ev['id']}).get_json()
    assert note['event_id'] == ev['id']
    client.delete(f"/api/v1/case-events/{ev['id']}", headers=headers)
    refreshed = client.get(f'/api/v1/case-files/{case_id}/notes', headers=headers).get_json()[0]
    assert refreshed['event_id'] is None


def test_notes_firm_isolation(client, make_owner):
    headers, firm_id = make_owner()
    headers_b, _ = make_owner(supabase_id='sb-b', email='b@firm.com', firm_name='B')
    case_id = _case(client, headers, firm_id)
    n = client.post(f'/api/v1/case-files/{case_id}/notes', headers=headers, json={'body': 'x'}).get_json()
    assert client.patch(f"/api/v1/case-notes/{n['id']}", headers=headers_b, json={'body': 'y'}).status_code == 404
    assert client.get(f'/api/v1/case-files/{case_id}/notes', headers=headers_b).status_code == 404
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd backend && python -m pytest tests/test_case_notes_api.py -v`
Expected: FAIL — `/notes` routes 404.

- [ ] **Step 3: Create the blueprint**

Create `backend/app/api/case_notes.py`:

```python
"""Case notes API — the running-commentary stream. Firm-scoped, gated by
case_files permissions (read = list, update = create/edit/delete)."""
from flask import Blueprint, request, jsonify, g
from app.models.models import db
from app.models.case import CaseFile, CaseNote
from app.middleware.jwt_auth import jwt_required
from app.middleware.firm_context import require_permission

bp = Blueprint('case_notes', __name__)

LINK_FIELDS = ('event_id', 'document_id')


def _case_or_404(case_id):
    return CaseFile.query.filter_by(id=case_id, firm_id=g.firm_id).first()


def _note_or_404(note_id):
    return CaseNote.query.filter_by(id=note_id, firm_id=g.firm_id).first()


@bp.route('/case-files/<int:case_id>/notes', methods=['GET'])
@jwt_required
@require_permission('case_files.read')
def list_notes(case_id):
    if not _case_or_404(case_id):
        return jsonify({'error': 'Case not found'}), 404
    notes = (CaseNote.query.filter_by(case_file_id=case_id)
             .order_by(CaseNote.pinned.desc(), CaseNote.id.desc()).all())
    return jsonify([n.to_dict() for n in notes])


@bp.route('/case-files/<int:case_id>/notes', methods=['POST'])
@jwt_required
@require_permission('case_files.update')
def create_note(case_id):
    if not _case_or_404(case_id):
        return jsonify({'error': 'Case not found'}), 404
    data = request.get_json() or {}
    body = (data.get('body') or '').strip()
    if not body:
        return jsonify({'error': 'Note body is required'}), 400
    note = CaseNote(firm_id=g.firm_id, case_file_id=case_id, created_by_user_id=g.user.id,
                    body=body, pinned=bool(data.get('pinned', False)),
                    event_id=data.get('event_id'), document_id=data.get('document_id'))
    db.session.add(note)
    db.session.commit()
    return jsonify(note.to_dict()), 201


@bp.route('/case-notes/<int:note_id>', methods=['PATCH'])
@jwt_required
@require_permission('case_files.update')
def update_note(note_id):
    note = _note_or_404(note_id)
    if not note:
        return jsonify({'error': 'Note not found'}), 404
    data = request.get_json() or {}
    if 'body' in data:
        body = (data['body'] or '').strip()
        if not body:
            return jsonify({'error': 'Note body is required'}), 400
        note.body = body
    if 'pinned' in data:
        note.pinned = bool(data['pinned'])
    for field in LINK_FIELDS:
        if field in data:
            setattr(note, field, data[field])
    db.session.commit()
    return jsonify(note.to_dict())


@bp.route('/case-notes/<int:note_id>', methods=['DELETE'])
@jwt_required
@require_permission('case_files.update')
def delete_note(note_id):
    note = _note_or_404(note_id)
    if not note:
        return jsonify({'error': 'Note not found'}), 404
    db.session.delete(note)
    db.session.commit()
    return jsonify({'message': 'Note deleted'})
```

- [ ] **Step 4: Register the blueprint**

In `backend/app/main.py:12`, append `, case_notes` to the `from app.api import ...` line.
After line 88 (`app.register_blueprint(leads.bp, ...)`), add:

```python
    app.register_blueprint(case_notes.bp, url_prefix='/api/v1')
```

- [ ] **Step 5: Null note links when an event or document is deleted**

In `backend/app/api/case_events.py`, inside `delete_event` (after the existing `CaseDocument...update({'event_id': None})` line), add:

```python
    from app.models.case import CaseNote
    CaseNote.query.filter_by(event_id=event.id).update({'event_id': None})
```

In `backend/app/api/case_documents.py`, inside `delete_document` (before `db.session.delete(doc)`), add:

```python
    from app.models.case import CaseNote
    CaseNote.query.filter_by(document_id=doc.id).update({'document_id': None})
```

- [ ] **Step 6: Run the API test + full suite**

Run: `cd backend && python -m pytest tests/test_case_notes_api.py -q && python -m pytest -q`
Expected: PASS (268).

- [ ] **Step 7: Stage (do NOT commit)**

```bash
git add backend/app/api/case_notes.py backend/app/main.py backend/app/api/case_events.py backend/app/api/case_documents.py backend/tests/test_case_notes_api.py
```

---

### Task 3: Seed intake notes as the first (pinned) `CaseNote` on convert

**Files:**
- Modify: `backend/app/api/leads.py` (convert: create a `CaseNote` instead of a `CaseEvent`)
- Modify: `backend/tests/test_lead_convert.py` (assert the intake note now lives in `/notes`)

**Interfaces:**
- Consumes: `CaseNote` (`app.models.case`).
- Produces: on convert, when `intake_notes` is non-empty, a pinned `CaseNote(body=intake_notes)` is created on the new case.

- [ ] **Step 1: Update the convert test to expect a pinned note**

In `backend/tests/test_lead_convert.py`, in `test_convert_creates_case_client_and_intake_note`, replace the timeline-note assertion block:

```python
    # Intake notes landed as the first timeline note.
    events = client.get(f"/api/v1/case-files/{case['id']}/events", headers=headers).get_json()
    notes = [e for e in events if e['kind'] == 'note']
    assert any('Heard the facts' in (e['notes'] or '') for e in notes)
```
with:

```python
    # Intake notes landed as the first (pinned) case note.
    notes = client.get(f"/api/v1/case-files/{case['id']}/notes", headers=headers).get_json()
    assert any('Heard the facts' in n['body'] for n in notes)
    assert notes[0]['pinned'] is True
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd backend && python -m pytest tests/test_lead_convert.py::test_convert_creates_case_client_and_intake_note -v`
Expected: FAIL — `/notes` empty (convert still writes a `CaseEvent`).

- [ ] **Step 3: Switch convert to create a `CaseNote`**

In `backend/app/api/leads.py`:
- Change the case import to drop `CaseEvent` and add `CaseNote`:
  ```python
  from app.models.case import CaseFile, CaseNote
  ```
- Replace the intake-note block:
  ```python
      if (lead.intake_notes or '').strip():
          db.session.add(CaseEvent(
              firm_id=g.firm_id, case_file_id=case_file.id, created_by_user_id=g.user.id,
              event_date=date.today(), kind='note', title='Intake notes',
              notes=lead.intake_notes))
  ```
  with:
  ```python
      if (lead.intake_notes or '').strip():
          db.session.add(CaseNote(
              firm_id=g.firm_id, case_file_id=case_file.id, created_by_user_id=g.user.id,
              body=lead.intake_notes, pinned=True))
  ```
- The `date` import in `leads.py` may now be unused; leave the `from datetime import datetime, date` line as-is (harmless) to avoid churn.

- [ ] **Step 4: Run the convert tests + full suite**

Run: `cd backend && python -m pytest tests/test_lead_convert.py -q && python -m pytest -q`
Expected: PASS (268).

- [ ] **Step 5: Stage (do NOT commit)**

```bash
git add backend/app/api/leads.py backend/tests/test_lead_convert.py
```

---

### Task 4: Frontend — Notes panel in the case file

**Files:**
- Modify: `frontend/src/api.ts` (`CaseNote` type + methods)
- Create: `frontend/src/components/NotesPanel.tsx`
- Modify: `frontend/src/pages/CaseDetail.tsx` (mount the panel under the rail; show pinned notes on Overview)
- Gate: `npm run build` clean.

**Interfaces:**
- Produces: `api.getCaseNotes(caseId)`, `api.addCaseNote(caseId, body)`, `api.updateCaseNote(id, body)`, `api.deleteCaseNote(id)`, and a `CaseNote` interface. `NotesPanel` props `{ caseId: number; canUpdate: boolean }` (self-contained: owns its own query/mutations).

- [ ] **Step 1: Add the `CaseNote` type + API methods**

In `frontend/src/api.ts`, add the interface near the other case types:

```ts
export interface CaseNote {
  id: number;
  case_file_id: number;
  body: string;
  pinned: boolean;
  event_id: number | null;
  document_id: number | null;
  created_by_user_id: number | null;
  created_at: string | null;
  updated_at: string | null;
}
```

Add to the `api` object, after the leads methods:

```ts
  // ---- Case notes -------------------------------------------------------
  getCaseNotes: (caseId: number) =>
    fetchAPI<CaseNote[]>(`${API_BASE_URL}/case-files/${caseId}/notes`),

  addCaseNote: (caseId: number, data: { body: string; pinned?: boolean; event_id?: number; document_id?: number }) =>
    fetchAPI<CaseNote>(`${API_BASE_URL}/case-files/${caseId}/notes`, {
      method: 'POST', body: JSON.stringify(data),
    }),

  updateCaseNote: (id: number, data: Partial<CaseNote>) =>
    fetchAPI<CaseNote>(`${API_BASE_URL}/case-notes/${id}`, {
      method: 'PATCH', body: JSON.stringify(data),
    }),

  deleteCaseNote: (id: number) =>
    fetchAPI<{ message: string }>(`${API_BASE_URL}/case-notes/${id}`, { method: 'DELETE' }),
```

- [ ] **Step 2: Create the `NotesPanel` component**

Create `frontend/src/components/NotesPanel.tsx`:

```tsx
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../api';
import { useToast } from '../contexts/ToastContext';
import { Pin, PinOff, Trash2, Plus } from 'lucide-react';

const errMsg = (e: unknown) => (e instanceof Error ? e.message : 'Something went wrong');

export default function NotesPanel({ caseId, canUpdate }: { caseId: number; canUpdate: boolean }) {
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const [body, setBody] = useState('');

  const { data: notes = [] } = useQuery({
    queryKey: ['case-notes', caseId], queryFn: () => api.getCaseNotes(caseId),
  });
  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['case-notes', caseId] });

  const add = useMutation({
    mutationFn: () => api.addCaseNote(caseId, { body }),
    onSuccess: () => { invalidate(); setBody(''); },
    onError: (e) => showToast(errMsg(e), 'error'),
  });
  const togglePin = useMutation({
    mutationFn: ({ id, pinned }: { id: number; pinned: boolean }) => api.updateCaseNote(id, { pinned }),
    onSuccess: invalidate,
    onError: (e) => showToast(errMsg(e), 'error'),
  });
  const del = useMutation({
    mutationFn: (id: number) => api.deleteCaseNote(id),
    onSuccess: invalidate,
    onError: (e) => showToast(errMsg(e), 'error'),
  });

  return (
    <div className="card p-4">
      <div className="eyebrow mb-3">Notes</div>
      {canUpdate && (
        <form onSubmit={(e) => { e.preventDefault(); if (body.trim()) add.mutate(); }} className="mb-3">
          <textarea value={body} rows={2} placeholder="Jot a note…"
            onChange={(e) => setBody(e.target.value)} className="field-textarea text-sm" />
          <div className="flex justify-end mt-1.5">
            <button type="submit" disabled={!body.trim() || add.isPending} className="btn-primary text-2xs disabled:opacity-50">
              <Plus size={12} /> Add
            </button>
          </div>
        </form>
      )}
      <div className="space-y-2">
        {notes.map((n) => (
          <div key={n.id} className={`group text-sm border-l-2 pl-2.5 ${n.pinned ? 'border-oxblood' : 'border-rule'}`}>
            <p className="text-ink whitespace-pre-wrap">{n.body}</p>
            <div className="flex items-center gap-2 mt-0.5">
              <span className="text-2xs text-ink-faint">{n.created_at?.slice(0, 10)}</span>
              {canUpdate && (
                <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition">
                  <button onClick={() => togglePin.mutate({ id: n.id, pinned: !n.pinned })}
                    className="text-ink-muted hover:text-oxblood" title={n.pinned ? 'Unpin' : 'Pin to timeline'}>
                    {n.pinned ? <PinOff size={12} /> : <Pin size={12} />}
                  </button>
                  <button onClick={() => del.mutate(n.id)} className="text-ink-muted hover:text-oxblood" title="Delete">
                    <Trash2 size={12} />
                  </button>
                </div>
              )}
            </div>
          </div>
        ))}
        {notes.length === 0 && <p className="text-sm text-ink-muted">No notes yet.</p>}
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Mount the panel under the stage rail in `CaseDetail.tsx`**

Add the import at the top of `frontend/src/pages/CaseDetail.tsx`:

```tsx
import NotesPanel from '../components/NotesPanel';
```

In the right sidebar, render the notes panel below `StageRail`. Replace the rail mount:

```tsx
      <StageRail stage={caseFile.stage} meta={meta} canUpdate={canUpdate}
        onAction={railAction} onAdvance={(k) => stageMutation.mutate(k)}
        advancing={stageMutation.isPending} />
      </div>
```
with:

```tsx
      <div className="lg:w-72 shrink-0 space-y-4">
        <StageRail stage={caseFile.stage} meta={meta} canUpdate={canUpdate}
          onAction={railAction} onAdvance={(k) => stageMutation.mutate(k)}
          advancing={stageMutation.isPending} />
        <NotesPanel caseId={caseId} canUpdate={canUpdate} />
      </div>
      </div>
```

(`StageRail` already sets its own width; wrapping both in a `lg:w-72` column stacks them. The rail's `lg:w-72`/`lg:sticky` classes remain harmless inside the fixed-width column.)

- [ ] **Step 4: Show pinned notes on the Overview tab**

In `CaseDetail.tsx`, add a query for notes near the other queries (after the `expenses` query, around line 61):

```tsx
  const { data: notes = [] } = useQuery({
    queryKey: ['case-notes', caseId], queryFn: () => api.getCaseNotes(caseId),
  });
```

In the Overview panel, inside the `lg:col-span-2` column, after the Progression `<div>` block (before the closing `</div>` of `lg:col-span-2`), add a pinned-notes section:

```tsx
            {notes.some((n) => n.pinned) && (
              <div>
                <div className="eyebrow mb-3">Pinned notes</div>
                <ul className="space-y-2">
                  {notes.filter((n) => n.pinned).map((n) => (
                    <li key={n.id} className="text-sm text-ink border-l-2 border-oxblood pl-2.5 whitespace-pre-wrap">{n.body}</li>
                  ))}
                </ul>
              </div>
            )}
```

- [ ] **Step 5: Build the frontend**

Run: `cd frontend && npm run build`
Expected: build succeeds, no TypeScript errors (note: the `NotesPanel` owns its own notes query; the Overview `notes` query shares the same `['case-notes', caseId]` key, so they stay in sync).

- [ ] **Step 6: Stage (do NOT commit)**

```bash
git add frontend/src/api.ts frontend/src/components/NotesPanel.tsx frontend/src/pages/CaseDetail.tsx
```

---

## Self-Review

**Spec coverage (against `2026-06-25-case-system-ux-design.md` §D notes + §H):**
- `case_notes` table (body, pinned, event_id, document_id) + migration → Task 1. ✓
- Always-on notes panel across tabs (right sidebar persists regardless of active tab) → Task 4. ✓
- Pin to timeline (pinned flag; pinned notes surface on Overview) → Task 4 Steps 3-4. ✓
- Attach to event/document → model + API support (Task 2); UI attach deferred (noted in Global Constraints). ✓
- Intake notes seed the first note on convert → Task 3. ✓
- Note links survive event/document deletion → Task 2 Step 5. ✓

**Placeholder scan:** none.

**Type consistency:** `CaseNote` fields match between `case.py` `to_dict`, the API, and the FE interface (`body`, `pinned`, `event_id`, `document_id`). List ordering (`pinned desc, id desc`) matches the `test_notes_pinned_first` expectation. `NotesPanel` and the Overview query share the `['case-notes', caseId]` cache key.
