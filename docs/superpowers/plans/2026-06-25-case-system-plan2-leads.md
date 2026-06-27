# Case System UX — Plan 2: Leads / Enquiries + Convert Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a lightweight Lead/Enquiry entity that holds a prospective matter (contact + summary + intake notes + decision) and converts into a full case file on accept, carrying the intake notes in as the first timeline note.

**Architecture:** A new `Lead` model (firm-scoped) lives apart from `CaseFile`; no CF number is spent until conversion. A `leads` RBAC module gates a CRUD API plus a `/convert` action that creates (or reuses) a `Client`, opens a `CaseFile` at stage `engaged`, records the initial stage change, and writes the lead's `intake_notes` into a `CaseEvent` of kind `note`. The Enquiries section of the Case Vault lists leads and drives accept/decline.

**Tech Stack:** Flask + SQLAlchemy (SQLite in tests via `db.create_all`), pytest; React + TypeScript + Vite, React Router v6, TanStack Query, Tailwind tokens.

## Global Constraints

- Never run git commits/pushes — Parth does git. Stage only; run the test/build gate and report.
- Migrations are SQL files for Parth to apply manually. New file: `014_leads.sql` (009–013 already delivered).
- Intake notes carry into the converted case as a `CaseEvent(kind='note')` — the `case_notes` table arrives in Plan 4; this is the forward-compatible seam for now.
- Lead statuses (verbatim): `open, accepted, declined`; default `open`. Accept happens only via `/convert`.
- Backend stays green (`pytest`); frontend builds clean (`npm run build`).
- Firm-wide RBAC; every lead is firm-scoped + `created_by_user_id` attribution.

---

### Task 1: `Lead` model + `case_files.lead_id` + migration 014

**Files:**
- Create: `backend/app/models/lead.py`
- Modify: `backend/app/models/case.py:34-41` (add `lead_id` column), `:55-81` (add to `to_dict`)
- Modify: `backend/app/main.py:61` (import `Lead` so the table is created)
- Create: `backend/migrations/014_leads.sql`
- Test: `backend/tests/test_lead_models.py`

**Interfaces:**
- Produces: `Lead` model with `to_dict()`; `LEAD_STATUSES = {"open","accepted","declined"}`, `DEFAULT_LEAD_STATUS = "open"`; `CaseFile.lead_id` (nullable int) serialized in `to_dict`.

- [ ] **Step 1: Write the failing model test**

Create `backend/tests/test_lead_models.py`:

```python
from app.models.models import db
from app.models.lead import Lead, LEAD_STATUSES, DEFAULT_LEAD_STATUS
from app.models.auth import User
from app.models.firm import Firm


def _firm_user(app):
    with app.app_context():
        f = Firm(firm_name='F'); db.session.add(f); db.session.flush()
        u = User(supabase_id='sb', email='o@f.com', firm_id=f.id)
        db.session.add(u); db.session.commit()
        return f.id, u.id


def test_lead_defaults_and_to_dict(app):
    firm_id, uid = _firm_user(app)
    with app.app_context():
        lead = Lead(firm_id=firm_id, created_by_user_id=uid,
                    contact_name='Mehta', phone='99', email='m@x.com',
                    matter_summary='Property dispute', intake_notes='Heard him out')
        db.session.add(lead); db.session.commit()
        d = lead.to_dict()
        assert d['contact_name'] == 'Mehta'
        assert d['status'] == DEFAULT_LEAD_STATUS == 'open'
        assert d['converted_case_file_id'] is None
        assert d['intake_notes'] == 'Heard him out'
        assert LEAD_STATUSES == {'open', 'accepted', 'declined'}
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd backend && python -m pytest tests/test_lead_models.py -v`
Expected: FAIL — `app.models.lead` does not exist.

- [ ] **Step 3: Create the `Lead` model**

Create `backend/app/models/lead.py`:

```python
"""Lead / Enquiry: a prospective matter before the firm commits to it.

Lives apart from CaseFile so no CF number is spent until conversion. On accept,
a Lead converts into a CaseFile (see app/api/leads.py:convert_lead).
"""
from datetime import datetime
from app.models.models import db

LEAD_STATUSES = {"open", "accepted", "declined"}
DEFAULT_LEAD_STATUS = "open"


class Lead(db.Model):
    __tablename__ = 'leads'

    id = db.Column(db.Integer, primary_key=True)
    firm_id = db.Column(db.Integer, db.ForeignKey('firms.id'), index=True)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
    contact_name = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(50))
    email = db.Column(db.String(200))
    matter_summary = db.Column(db.Text)
    intake_notes = db.Column(db.Text)
    status = db.Column(db.String(20), nullable=False, default=DEFAULT_LEAD_STATUS)
    decided_at = db.Column(db.DateTime)
    converted_case_file_id = db.Column(db.Integer, db.ForeignKey('case_files.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'firm_id': self.firm_id,
            'created_by_user_id': self.created_by_user_id,
            'contact_name': self.contact_name,
            'phone': self.phone,
            'email': self.email,
            'matter_summary': self.matter_summary,
            'intake_notes': self.intake_notes,
            'status': self.status,
            'decided_at': self.decided_at.isoformat() if self.decided_at else None,
            'converted_case_file_id': self.converted_case_file_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
```

- [ ] **Step 4: Add `lead_id` to `CaseFile`**

In `backend/app/models/case.py`, after line 39 (`description = db.Column(db.Text)`) add:

```python
    lead_id = db.Column(db.Integer, db.ForeignKey('leads.id'))
```

And in `CaseFile.to_dict` (after the `'description': self.description,` line) add:

```python
            'lead_id': self.lead_id,
```

- [ ] **Step 5: Register the model so the table is created**

In `backend/app/main.py:61`, change:

```python
        from app.models.case import CaseFile, CaseParty, CaseEvent, CaseDocument, CaseStageChange, CaseExpense  # ensure case tables are created
```
to also import the lead model right after it (new line):

```python
        from app.models.lead import Lead  # ensure leads table is created
```

- [ ] **Step 6: Run the model test to verify it passes**

Run: `cd backend && python -m pytest tests/test_lead_models.py -v`
Expected: PASS.

- [ ] **Step 7: Create migration 014**

Create `backend/migrations/014_leads.sql`:

```sql
-- 014_leads.sql — Lead/Enquiry entity + case_files.lead_id origin link.
-- Additive/non-destructive. Apply in the Supabase SQL editor.
BEGIN;

CREATE TABLE IF NOT EXISTS public.leads (
  id SERIAL PRIMARY KEY,
  firm_id INTEGER REFERENCES public.firms(id),
  created_by_user_id INTEGER REFERENCES public.users(id),
  contact_name VARCHAR(200) NOT NULL,
  phone VARCHAR(50),
  email VARCHAR(200),
  matter_summary TEXT,
  intake_notes TEXT,
  status VARCHAR(20) NOT NULL DEFAULT 'open',
  decided_at TIMESTAMP,
  converted_case_file_id INTEGER REFERENCES public.case_files(id),
  created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_leads_firm_id ON public.leads (firm_id);

ALTER TABLE public.case_files ADD COLUMN IF NOT EXISTS lead_id INTEGER REFERENCES public.leads(id);

COMMIT;
```

- [ ] **Step 8: Run the full suite + stage (do NOT commit)**

Run: `cd backend && python -m pytest -q`
Expected: PASS (248).

```bash
git add backend/app/models/lead.py backend/app/models/case.py backend/app/main.py backend/migrations/014_leads.sql backend/tests/test_lead_models.py
```

---

### Task 2: `leads` RBAC module + default role grants

**Files:**
- Modify: `backend/app/rbac/permissions.py:19-20` (add module), `:42-64` (grants)
- Test: `backend/tests/test_lead_permissions.py`

**Interfaces:**
- Produces: permission keys `leads.create|read|update|delete`. Owner auto (resolves `ALL_PERMISSIONS`); Partner CRUD; Associate create/read/update; Staff read.

- [ ] **Step 1: Write the failing permissions test**

Create `backend/tests/test_lead_permissions.py`:

```python
from app.rbac.permissions import ALL_PERMISSIONS, DEFAULT_ROLES


def test_leads_module_in_catalog():
    for action in ("create", "read", "update", "delete"):
        assert f"leads.{action}" in ALL_PERMISSIONS


def test_default_role_grants_for_leads():
    assert "leads.delete" in DEFAULT_ROLES["Owner"]
    assert {"leads.create", "leads.read", "leads.update", "leads.delete"} <= set(DEFAULT_ROLES["Partner"])
    assert "leads.update" in DEFAULT_ROLES["Associate"]
    assert "leads.delete" not in DEFAULT_ROLES["Associate"]
    assert DEFAULT_ROLES["Staff"].count("leads.read") == 1
    assert "leads.create" not in DEFAULT_ROLES["Staff"]
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd backend && python -m pytest tests/test_lead_permissions.py -v`
Expected: FAIL — `leads.*` not in catalog.

- [ ] **Step 3: Add the module to the catalog**

In `backend/app/rbac/permissions.py`, after line 20 (`{"key": "documents", ...}`) add inside `MODULES`:

```python
    {"key": "leads", "label": "Enquiries", "actions": CRUD},
```

- [ ] **Step 4: Add default role grants**

In the same file's `DEFAULT_ROLES`:
- Partner `_perms(...)` — append `("leads", CRUD),`
- Associate `_perms(...)` — append `("leads", ["create", "read", "update"]),`
- Staff `_perms(...)` — append `("leads", ["read"]),`

(Owner needs no change — it is `sorted(ALL_PERMISSIONS)`.)

- [ ] **Step 5: Run the test + full suite**

Run: `cd backend && python -m pytest tests/test_lead_permissions.py -q && python -m pytest -q`
Expected: PASS (249).

- [ ] **Step 6: Stage (do NOT commit)**

```bash
git add backend/app/rbac/permissions.py backend/tests/test_lead_permissions.py
```

---

### Task 3: Leads CRUD API

**Files:**
- Create: `backend/app/api/leads.py`
- Modify: `backend/app/main.py:12` (import), `:88` (register blueprint)
- Test: `backend/tests/test_leads_api.py`

**Interfaces:**
- Consumes: `Lead`, `LEAD_STATUSES`, `jwt_required`, `require_permission`.
- Produces: blueprint `leads` with `GET/POST /leads`, `GET/PATCH/DELETE /leads/<id>`. (`/convert` is added in Task 4 on the same blueprint.)

- [ ] **Step 1: Write the failing API test**

Create `backend/tests/test_leads_api.py`:

```python
def test_lead_crud_and_decline(client, make_owner):
    headers, firm_id = make_owner()
    created = client.post('/api/v1/leads', headers=headers, json={
        'contact_name': 'Mehta', 'phone': '99', 'email': 'm@x.com',
        'matter_summary': 'Property dispute', 'intake_notes': 'Heard the facts'}).get_json()
    assert created['status'] == 'open'
    lid = created['id']

    assert len(client.get('/api/v1/leads', headers=headers).get_json()) == 1
    assert client.get(f'/api/v1/leads/{lid}', headers=headers).get_json()['contact_name'] == 'Mehta'

    declined = client.patch(f'/api/v1/leads/{lid}', headers=headers,
                            json={'status': 'declined'}).get_json()
    assert declined['status'] == 'declined'
    assert declined['decided_at'] is not None

    assert client.delete(f'/api/v1/leads/{lid}', headers=headers).status_code == 200
    assert client.get('/api/v1/leads', headers=headers).get_json() == []


def test_lead_requires_contact_name(client, make_owner):
    headers, _ = make_owner()
    assert client.post('/api/v1/leads', headers=headers, json={'phone': '1'}).status_code == 400


def test_lead_status_filter(client, make_owner):
    headers, _ = make_owner()
    a = client.post('/api/v1/leads', headers=headers, json={'contact_name': 'A'}).get_json()
    client.post('/api/v1/leads', headers=headers, json={'contact_name': 'B'})
    client.patch(f"/api/v1/leads/{a['id']}", headers=headers, json={'status': 'declined'})
    assert len(client.get('/api/v1/leads?status=open', headers=headers).get_json()) == 1


def test_leads_firm_isolation(client, make_owner):
    headers, _ = make_owner()
    headers_b, _ = make_owner(supabase_id='sb-b', email='b@firm.com', firm_name='B')
    lid = client.post('/api/v1/leads', headers=headers, json={'contact_name': 'A'}).get_json()['id']
    assert client.get(f'/api/v1/leads/{lid}', headers=headers_b).status_code == 404
    assert client.patch(f'/api/v1/leads/{lid}', headers=headers_b, json={'phone': '1'}).status_code == 404
    assert client.get('/api/v1/leads', headers=headers_b).get_json() == []
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd backend && python -m pytest tests/test_leads_api.py -v`
Expected: FAIL — 404s (no `/leads` route registered).

- [ ] **Step 3: Create the leads blueprint**

Create `backend/app/api/leads.py`:

```python
"""Lead / Enquiry API — firm-scoped, gated by the leads RBAC module."""
from datetime import datetime
from flask import Blueprint, request, jsonify, g
from app.models.models import db
from app.models.lead import Lead, LEAD_STATUSES
from app.middleware.jwt_auth import jwt_required
from app.middleware.firm_context import require_permission

bp = Blueprint('leads', __name__)

EDITABLE = ('contact_name', 'phone', 'email', 'matter_summary', 'intake_notes')


def _get_owned(lead_id):
    return Lead.query.filter_by(id=lead_id, firm_id=g.firm_id).first()


@bp.route('/leads', methods=['GET'])
@jwt_required
@require_permission('leads.read')
def list_leads():
    query = Lead.query.filter_by(firm_id=g.firm_id)
    status = request.args.get('status')
    if status:
        query = query.filter_by(status=status)
    leads = query.order_by(Lead.id.desc()).all()
    return jsonify([l.to_dict() for l in leads])


@bp.route('/leads', methods=['POST'])
@jwt_required
@require_permission('leads.create')
def create_lead():
    data = request.get_json() or {}
    name = (data.get('contact_name') or '').strip()
    if not name:
        return jsonify({'error': 'Contact name is required'}), 400
    lead = Lead(firm_id=g.firm_id, created_by_user_id=g.user.id, contact_name=name,
                phone=data.get('phone'), email=data.get('email'),
                matter_summary=data.get('matter_summary'),
                intake_notes=data.get('intake_notes'))
    db.session.add(lead)
    db.session.commit()
    return jsonify(lead.to_dict()), 201


@bp.route('/leads/<int:lead_id>', methods=['GET'])
@jwt_required
@require_permission('leads.read')
def get_lead(lead_id):
    lead = _get_owned(lead_id)
    if not lead:
        return jsonify({'error': 'Lead not found'}), 404
    return jsonify(lead.to_dict())


@bp.route('/leads/<int:lead_id>', methods=['PATCH'])
@jwt_required
@require_permission('leads.update')
def update_lead(lead_id):
    lead = _get_owned(lead_id)
    if not lead:
        return jsonify({'error': 'Lead not found'}), 404
    data = request.get_json() or {}
    for field in EDITABLE:
        if field in data:
            setattr(lead, field, data[field])
    if 'status' in data:
        status = data['status']
        if status not in LEAD_STATUSES:
            return jsonify({'error': 'Invalid status'}), 400
        # Acceptance only happens through /convert.
        if status == 'accepted':
            return jsonify({'error': 'Accept a lead via /convert'}), 400
        lead.status = status
        lead.decided_at = datetime.utcnow() if status == 'declined' else None
    db.session.commit()
    return jsonify(lead.to_dict())


@bp.route('/leads/<int:lead_id>', methods=['DELETE'])
@jwt_required
@require_permission('leads.delete')
def delete_lead(lead_id):
    lead = _get_owned(lead_id)
    if not lead:
        return jsonify({'error': 'Lead not found'}), 404
    db.session.delete(lead)
    db.session.commit()
    return jsonify({'ok': True})
```

- [ ] **Step 4: Register the blueprint**

In `backend/app/main.py:12`, append `, leads` to the `from app.api import ...` line.
After line 88 (`app.register_blueprint(case_expenses.bp, ...)`) add:

```python
    app.register_blueprint(leads.bp, url_prefix='/api/v1')
```

- [ ] **Step 5: Run the API test + full suite**

Run: `cd backend && python -m pytest tests/test_leads_api.py -q && python -m pytest -q`
Expected: PASS (253).

- [ ] **Step 6: Stage (do NOT commit)**

```bash
git add backend/app/api/leads.py backend/app/main.py backend/tests/test_leads_api.py
```

---

### Task 4: Convert a lead → case file

**Files:**
- Modify: `backend/app/api/leads.py` (add `/convert` route + imports)
- Test: `backend/tests/test_lead_convert.py`

**Interfaces:**
- Consumes: `Client` (`app.models.models`), `CaseFile`/`CaseEvent` (`app.models.case`), `generate_case_number`, `record_stage_change` (`app.services.case_service`), `DEFAULT_STAGE` (`app.case.stages`).
- Produces: `POST /leads/<id>/convert` → 201 with the new case file `to_dict(include_parties=True)`. Body (all optional): `client_id` (reuse existing firm client) and `title` (case title). Creates a `Client` from the lead contact when `client_id` is absent. Copies `intake_notes` into a `CaseEvent(kind='note')`. Marks the lead `accepted` + links `converted_case_file_id`. Re-converting a non-`open` lead → 400.

- [ ] **Step 1: Write the failing convert test**

Create `backend/tests/test_lead_convert.py`:

```python
from datetime import date
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

    # Intake notes landed as the first timeline note.
    events = client.get(f"/api/v1/case-files/{case['id']}/events", headers=headers).get_json()
    notes = [e for e in events if e['kind'] == 'note']
    assert any('Heard the facts' in (e['notes'] or '') for e in notes)

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
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd backend && python -m pytest tests/test_lead_convert.py -v`
Expected: FAIL — `/convert` returns 404 / 405.

- [ ] **Step 3: Add imports to `leads.py`**

At the top of `backend/app/api/leads.py`, extend imports:

```python
from datetime import datetime, date
from app.models.models import db, Client
from app.models.case import CaseFile, CaseEvent
from app.services.case_service import generate_case_number, record_stage_change
from app.case.stages import DEFAULT_STAGE
```

(Keep the existing `Lead, LEAD_STATUSES`, `jwt_required`, `require_permission`, `Blueprint/request/jsonify/g` imports; just merge the `datetime`/`models` lines.)

- [ ] **Step 4: Add the convert route**

Append to `backend/app/api/leads.py`:

```python
@bp.route('/leads/<int:lead_id>/convert', methods=['POST'])
@jwt_required
@require_permission('leads.update')
def convert_lead(lead_id):
    lead = _get_owned(lead_id)
    if not lead:
        return jsonify({'error': 'Lead not found'}), 404
    if lead.status != 'open':
        return jsonify({'error': 'Lead already decided'}), 400
    data = request.get_json() or {}

    # Resolve the client: reuse an existing firm client or create one from contact.
    client_id = data.get('client_id')
    if client_id:
        client_row = Client.query.filter_by(id=client_id, firm_id=g.firm_id).first()
        if not client_row:
            return jsonify({'error': 'Client not found'}), 404
    else:
        client_row = Client(firm_id=g.firm_id, created_by_user_id=g.user.id,
                            name=lead.contact_name, email=lead.email, phone=lead.phone)
        db.session.add(client_row)
        db.session.flush()

    title = (data.get('title') or lead.matter_summary or lead.contact_name or 'Untitled matter').strip()[:300]
    case_file = CaseFile(
        firm_id=g.firm_id, created_by_user_id=g.user.id,
        case_number=generate_case_number(g.firm_id), title=title,
        client_id=client_row.id, stage=DEFAULT_STAGE, lead_id=lead.id)
    db.session.add(case_file)
    db.session.flush()
    record_stage_change(case_file, None, case_file.stage, g.user.id)

    if (lead.intake_notes or '').strip():
        db.session.add(CaseEvent(
            firm_id=g.firm_id, case_file_id=case_file.id, created_by_user_id=g.user.id,
            event_date=date.today(), kind='note', title='Intake notes',
            notes=lead.intake_notes))

    lead.status = 'accepted'
    lead.decided_at = datetime.utcnow()
    lead.converted_case_file_id = case_file.id
    db.session.commit()
    return jsonify(case_file.to_dict(include_parties=True)), 201
```

- [ ] **Step 5: Run the convert test + full suite**

Run: `cd backend && python -m pytest tests/test_lead_convert.py -q && python -m pytest -q`
Expected: PASS (257).

- [ ] **Step 6: Stage (do NOT commit)**

```bash
git add backend/app/api/leads.py backend/tests/test_lead_convert.py
```

---

### Task 5: Frontend — Enquiries wired into the Case Vault

**Files:**
- Modify: `frontend/src/api.ts` (Lead type + methods)
- Modify: `frontend/src/pages/CaseVault.tsx` (replace the Enquiries placeholder with a live list + new-enquiry modal + accept/decline)
- Gate: `npm run build` clean.

**Interfaces:**
- Consumes: existing `api` request helper. Produces `api.getLeads(status?)`, `api.createLead(body)`, `api.updateLead(id, body)`, `api.deleteLead(id)`, `api.convertLead(id, body)` and a `Lead` interface.

- [ ] **Step 1: Add the `Lead` type + API methods**

In `frontend/src/api.ts`, add the interface near the other case types:

```ts
export interface Lead {
  id: number;
  contact_name: string;
  phone: string | null;
  email: string | null;
  matter_summary: string | null;
  intake_notes: string | null;
  status: 'open' | 'accepted' | 'declined';
  decided_at: string | null;
  converted_case_file_id: number | null;
  created_at: string | null;
}
```

And add these methods to the exported `api` object (mirror the existing `request`/`get`/`post` style already used by `getCaseFiles`/`createCaseFile`):

```ts
  getLeads: (status?: string): Promise<Lead[]> =>
    request(`/leads${status ? `?status=${status}` : ''}`),
  createLead: (body: Partial<Lead>): Promise<Lead> =>
    request('/leads', { method: 'POST', body: JSON.stringify(body) }),
  updateLead: (id: number, body: Partial<Lead>): Promise<Lead> =>
    request(`/leads/${id}`, { method: 'PATCH', body: JSON.stringify(body) }),
  deleteLead: (id: number): Promise<{ ok: boolean }> =>
    request(`/leads/${id}`, { method: 'DELETE' }),
  convertLead: (id: number, body: { title?: string; client_id?: number }): Promise<CaseFile> =>
    request(`/leads/${id}/convert`, { method: 'POST', body: JSON.stringify(body) }),
```

(If `api.ts` uses a different transport signature, match `getCaseFiles`/`moveCaseFile` exactly — read those two methods first and copy their call shape.)

- [ ] **Step 2: Wire the Enquiries section in `CaseVault.tsx`**

Replace the Enquiries placeholder `<section>` (the dashed-border block) with a live list, and add a "New enquiry" modal + accept/decline handlers. Add these imports/hooks at the top of the component (alongside the existing ones):

```tsx
import { useNavigate } from 'react-router-dom';
import { Lead } from '../api';
```

Inside the component, after the existing `createMutation`:

```tsx
  const navigate = useNavigate();
  const [leadModalOpen, setLeadModalOpen] = useState(false);
  const [leadForm, setLeadForm] = useState({ contact_name: '', phone: '', email: '', matter_summary: '', intake_notes: '' });

  const { data: leads = [] } = useQuery({
    queryKey: ['leads', 'open'], queryFn: () => api.getLeads('open'),
  });

  const createLead = useMutation({
    mutationFn: () => api.createLead(leadForm),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['leads'] });
      setLeadModalOpen(false);
      setLeadForm({ contact_name: '', phone: '', email: '', matter_summary: '', intake_notes: '' });
      showToast('Enquiry logged');
    },
    onError: (e) => showToast(errMsg(e), 'error'),
  });

  const declineLead = useMutation({
    mutationFn: (id: number) => api.updateLead(id, { status: 'declined' }),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['leads'] }); showToast('Enquiry declined'); },
    onError: (e) => showToast(errMsg(e), 'error'),
  });

  const acceptLead = useMutation({
    mutationFn: (lead: Lead) => api.convertLead(lead.id, { title: lead.matter_summary || lead.contact_name }),
    onSuccess: (caseFile) => {
      queryClient.invalidateQueries({ queryKey: ['leads'] });
      queryClient.invalidateQueries({ queryKey: ['case-files'] });
      showToast('Case file opened');
      navigate(`/cases/${caseFile.id}`);
    },
    onError: (e) => showToast(errMsg(e), 'error'),
  });
```

Replace the Enquiries `<section>` body with:

```tsx
      <section>
        <div className="flex items-center justify-between mb-3">
          <h2 className="eyebrow">Enquiries</h2>
          {canCreate && (
            <button onClick={() => setLeadModalOpen(true)} className="btn-ghost">
              <Plus size={14} strokeWidth={2} /><span>New enquiry</span>
            </button>
          )}
        </div>
        {leads.length === 0 ? (
          <div className="border border-dashed border-rule bg-surface p-8 text-center text-sm text-ink-muted">
            No open enquiries. Log a prospective matter before you decide to take it on.
          </div>
        ) : (
          <div className="border border-rule divide-y divide-rule">
            {leads.map((l) => (
              <div key={l.id} className="bg-surface flex items-center gap-4 px-5 py-3">
                <div className="flex-1 min-w-0">
                  <div className="text-sm text-ink font-medium truncate">{l.contact_name}</div>
                  <div className="text-2xs text-ink-muted truncate">{l.matter_summary}</div>
                </div>
                <button onClick={() => declineLead.mutate(l.id)} className="btn-ghost text-2xs">Decline</button>
                <button onClick={() => acceptLead.mutate(l)} className="btn-primary text-2xs">Accept → open file</button>
              </div>
            ))}
          </div>
        )}
      </section>
```

Add the new-enquiry modal at the end of the component (next to the existing case modal), inside the same fragment:

```tsx
      {leadModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 animate-fade-in">
          <div className="absolute inset-0 bg-ink/40 backdrop-blur-[2px]" onClick={() => setLeadModalOpen(false)} />
          <div className="relative bg-surface border border-rule rounded-DEFAULT max-w-lg w-full
                          max-h-[90vh] overflow-y-auto shadow-modal animate-fade-up">
            <div className="h-[3px] bg-oxblood" />
            <div className="p-8">
              <button onClick={() => setLeadModalOpen(false)}
                className="absolute top-5 right-5 text-ink-faint hover:text-ink-muted" aria-label="Close">
                <X size={20} strokeWidth={1.5} />
              </button>
              <div className="mb-6"><div className="page-eyebrow">Intake</div>
                <h2 className="page-title !text-2xl">Log an enquiry</h2></div>
              <form onSubmit={(e) => { e.preventDefault(); createLead.mutate(); }} className="space-y-4">
                <div>
                  <label className="field-label">Contact name *</label>
                  <input required autoFocus value={leadForm.contact_name}
                    onChange={(e) => setLeadForm({ ...leadForm, contact_name: e.target.value })}
                    className="field-input" placeholder="Who approached you?" />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="field-label">Phone</label>
                    <input value={leadForm.phone}
                      onChange={(e) => setLeadForm({ ...leadForm, phone: e.target.value })}
                      className="field-input" />
                  </div>
                  <div>
                    <label className="field-label">Email</label>
                    <input value={leadForm.email}
                      onChange={(e) => setLeadForm({ ...leadForm, email: e.target.value })}
                      className="field-input" />
                  </div>
                </div>
                <div>
                  <label className="field-label">Matter summary</label>
                  <input value={leadForm.matter_summary}
                    onChange={(e) => setLeadForm({ ...leadForm, matter_summary: e.target.value })}
                    className="field-input" placeholder="e.g., Property dispute" />
                </div>
                <div>
                  <label className="field-label">Intake notes</label>
                  <textarea value={leadForm.intake_notes} rows={4}
                    onChange={(e) => setLeadForm({ ...leadForm, intake_notes: e.target.value })}
                    className="field-input" placeholder="His story, the facts, your first read…" />
                </div>
                <div className="flex gap-3 justify-end pt-4 border-t border-rule">
                  <button type="button" onClick={() => setLeadModalOpen(false)} className="btn-ghost">Cancel</button>
                  <button type="submit" className="btn-primary" disabled={createLead.isPending}>Save enquiry</button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
```

- [ ] **Step 3: Build the frontend**

Run: `cd frontend && npm run build`
Expected: build succeeds, no TypeScript errors.

- [ ] **Step 4: Stage (do NOT commit)**

```bash
git add frontend/src/api.ts frontend/src/pages/CaseVault.tsx
```

---

## Self-Review

**Spec coverage (against `2026-06-25-case-system-ux-design.md`):**
- §C Lead entity (contact, summary, intake notes, status) → Task 1. ✓
- §C convert → case at `engaged`, carries intake notes, sets `lead_id`/`converted_case_file_id`/status → Task 4. ✓
- §H `leads` table + `case_files.lead_id` (migration 014) → Task 1. ✓
- §H new `leads` RBAC module (Owner auto, Partner/Associate granted, Staff read) → Task 2. ✓
- §I Leads API incl. `/convert` → Tasks 3–4. ✓
- §B/§J Enquiries section in the Vault (create + accept/decline) → Task 5. ✓
- Decline path + decided_at → Task 3 (`update_lead`). ✓

**Deviation noted:** intake notes carry into a `CaseEvent(kind='note')`, not `case_notes` (which arrives in Plan 4). Documented in Global Constraints. When Plan 4 lands, the intake note can optionally also seed a `case_note`; no rework required.

**Placeholder scan:** none. The Enquiries empty-state is concrete copy, not a stub.

**Type consistency:** `Lead` fields match between `lead.py` `to_dict`, the API, and the FE `Lead` interface. `convertLead` returns `CaseFile` (FE) ↔ `case_file.to_dict()` (BE). `LEAD_STATUSES`/`status` values consistent across model, API validation, and FE union type.
