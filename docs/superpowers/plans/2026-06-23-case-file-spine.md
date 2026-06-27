# Case File Spine + Kanban Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the case-file spine of the Legal CRM — a firm-scoped `CaseFile` entity with parties and a timeline (`case_events`), surfaced as a kanban board and an "open the file" detail view, with the existing billing linkable per case.

**Architecture:** Mirror the existing billing stack exactly — `firm_id` access scope + `created_by_user_id` attribution, a code-defined catalog (`app/case/stages.py`, like `app/rbac/permissions.py`), models in a focused `app/models/case.py`, a numbering service, and a firm-scoped blueprint gated by a new `case_files` RBAC module. Frontend reuses the design system and React Query patterns from `pages/Items.tsx`.

**Tech Stack:** Flask, SQLAlchemy, Postgres (Supabase prod) / in-memory SQLite (tests), Supabase JWT, React + TypeScript (Vite), TanStack Query, lucide-react, Tailwind design tokens.

## Global Constraints

- Access is **firm-wide, RBAC-gated** by a new `case_files` module (CRUD). No per-matter visibility walls in this sub-project. Scope every query by `g.firm_id`; never `user_id`.
- Attribution via `created_by_user_id`; access scope via `firm_id` (both on `case_files` and `case_events`).
- Case numbering is **per-firm**, format `CF/{YYYY}/{NNNN}`, sequence = max-for-firm-this-year + 1, zero-padded to 4. Backstopped by `UNIQUE (firm_id, case_number)`.
- Stages (kanban columns) are code-defined, in order: `intake, drafting, filed, in_hearing, awaiting_order, closed`. A case is closed when `stage == "closed"` (no separate status field).
- Timeline step kinds are code-defined: `note, filing, hearing, order, step`.
- New models must compile on SQLite (`db.JSON`, no Postgres-only types). Tests build schema via `db.create_all()` on `sqlite:///:memory:`.
- The Supabase SQL migration (`009_case_files.sql`) is delivered as a file for Parth to apply manually; **no code path runs it.**
- **Do not run git commits** — Parth handles git. End each task at a green test run, not a commit. (The plan's "Step: verify green" is the task gate.)

---

### Task 1: Stage + event-kind catalog

**Files:**
- Create: `backend/app/case/__init__.py` (empty)
- Create: `backend/app/case/stages.py`
- Test: `backend/tests/test_case_stages.py`

**Interfaces:**
- Produces:
  - `STAGES: list[dict]` — `[{"key": "intake", "label": "Intake"}, ...]` in column order.
  - `STAGE_KEYS: set[str]`, `DEFAULT_STAGE: str = "intake"`.
  - `EVENT_KINDS: list[str]` — `["note","filing","hearing","order","step"]`.
  - `is_valid_stage(key: str) -> bool`, `is_valid_event_kind(kind: str) -> bool`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_case_stages.py
from app.case.stages import (
    STAGES, STAGE_KEYS, DEFAULT_STAGE, EVENT_KINDS,
    is_valid_stage, is_valid_event_kind,
)


def test_stages_are_ordered_columns():
    keys = [s["key"] for s in STAGES]
    assert keys == ["intake", "drafting", "filed", "in_hearing", "awaiting_order", "closed"]
    assert all("label" in s for s in STAGES)


def test_default_stage_is_intake():
    assert DEFAULT_STAGE == "intake"
    assert DEFAULT_STAGE in STAGE_KEYS


def test_stage_validation():
    assert is_valid_stage("filed")
    assert not is_valid_stage("teleported")


def test_event_kinds_and_validation():
    assert EVENT_KINDS == ["note", "filing", "hearing", "order", "step"]
    assert is_valid_event_kind("hearing")
    assert not is_valid_event_kind("smoke_signal")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_case_stages.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.case'`

- [ ] **Step 3: Create the package and catalog**

```python
# backend/app/case/__init__.py
```
(empty file)

```python
# backend/app/case/stages.py
"""Code-defined case workflow catalog: kanban stages + timeline step kinds.

Stages drive the kanban columns in display order. A case is closed when its
stage is "closed" — there is no separate status field. Kinds classify timeline
(case_events) steps. Both are extended here without a schema change.
"""

STAGES = [
    {"key": "intake",         "label": "Intake"},
    {"key": "drafting",       "label": "Drafting"},
    {"key": "filed",          "label": "Filed"},
    {"key": "in_hearing",     "label": "In Hearing"},
    {"key": "awaiting_order", "label": "Awaiting Order"},
    {"key": "closed",         "label": "Closed"},
]

STAGE_KEYS = {s["key"] for s in STAGES}
DEFAULT_STAGE = "intake"

EVENT_KINDS = ["note", "filing", "hearing", "order", "step"]


def is_valid_stage(key):
    return key in STAGE_KEYS


def is_valid_event_kind(kind):
    return kind in EVENT_KINDS
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_case_stages.py -q`
Expected: PASS (4 passed)

---

### Task 2: Case models (CaseFile, CaseParty, CaseEvent)

**Files:**
- Create: `backend/app/models/case.py`
- Modify: `backend/app/main.py` (import case models inside `create_app` so `create_all` builds the tables)
- Test: `backend/tests/test_case_models.py`

**Interfaces:**
- Consumes: `db` from `app.models.models`; `DEFAULT_STAGE` from `app.case.stages`.
- Produces:
  - `CaseFile` (`__tablename__='case_files'`): `id, firm_id, created_by_user_id, case_number, title, client_id, matter_type, court, court_case_number, stage, position, handling_advocate_user_id, next_hearing_date, open_date, description, created_at, updated_at`; relationships `client`, `parties` (cascade), `events` (cascade); `to_dict(include_parties=False)`.
  - `CaseParty` (`case_parties`): `id, case_file_id, name, role, created_at`; `to_dict()`.
  - `CaseEvent` (`case_events`): `id, case_file_id, firm_id, created_by_user_id, event_date, kind, title, notes, created_at, updated_at`; `to_dict()`.
  - Unique constraint `UNIQUE (firm_id, case_number)` named `case_files_firm_id_case_number_key`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_case_models.py
from datetime import date

from app.models.models import db, Client
from app.models.auth import User
from app.models.case import CaseFile, CaseParty, CaseEvent
from app.services.firm_service import provision_firm_for_user


def _firm_with_client(app):
    with app.app_context():
        user = User(supabase_id='sb-case', email='c@firm.com')
        db.session.add(user)
        db.session.commit()
        firm = provision_firm_for_user(user, 'Acme')
        client = Client(firm_id=firm.id, created_by_user_id=user.id, name='X Corp')
        db.session.add(client)
        db.session.commit()
        return firm.id, user.id, client.id


def test_case_file_defaults_and_to_dict(app):
    firm_id, user_id, client_id = _firm_with_client(app)
    with app.app_context():
        cf = CaseFile(firm_id=firm_id, created_by_user_id=user_id,
                      case_number='CF/2026/0001', title='X vs State',
                      client_id=client_id)
        db.session.add(cf)
        db.session.commit()
        d = cf.to_dict()
        assert d['case_number'] == 'CF/2026/0001'
        assert d['stage'] == 'intake'        # DEFAULT_STAGE
        assert d['client_name'] == 'X Corp'
        assert d['position'] == 0


def test_parties_and_events_cascade_on_delete(app):
    firm_id, user_id, client_id = _firm_with_client(app)
    with app.app_context():
        cf = CaseFile(firm_id=firm_id, created_by_user_id=user_id,
                      case_number='CF/2026/0002', title='Y matter', client_id=client_id)
        cf.parties.append(CaseParty(name='Petitioner Co', role='petitioner'))
        cf.events.append(CaseEvent(firm_id=firm_id, created_by_user_id=user_id,
                                   event_date=date(2026, 6, 1), kind='filing',
                                   title='Petition filed'))
        db.session.add(cf)
        db.session.commit()
        cf_id = cf.id

        assert CaseParty.query.filter_by(case_file_id=cf_id).count() == 1
        assert CaseEvent.query.filter_by(case_file_id=cf_id).count() == 1

        db.session.delete(cf)
        db.session.commit()
        assert CaseParty.query.filter_by(case_file_id=cf_id).count() == 0
        assert CaseEvent.query.filter_by(case_file_id=cf_id).count() == 0


def test_case_to_dict_includes_parties_when_requested(app):
    firm_id, user_id, client_id = _firm_with_client(app)
    with app.app_context():
        cf = CaseFile(firm_id=firm_id, created_by_user_id=user_id,
                      case_number='CF/2026/0003', title='Z matter', client_id=client_id)
        cf.parties.append(CaseParty(name='Resp Co', role='respondent'))
        db.session.add(cf)
        db.session.commit()
        d = cf.to_dict(include_parties=True)
        assert len(d['parties']) == 1
        assert d['parties'][0]['role'] == 'respondent'
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_case_models.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.models.case'`

- [ ] **Step 3: Create the models**

```python
# backend/app/models/case.py
"""Case file spine models: CaseFile + its parties and timeline (case_events).

Scope = firm_id (like clients/invoices); attribution = created_by_user_id.
case_events carries a denormalized firm_id so the later calendar can range-query
all of a firm's dated steps without a join.
"""
from datetime import datetime, date
from app.models.models import db
from app.case.stages import DEFAULT_STAGE


class CaseFile(db.Model):
    __tablename__ = 'case_files'
    __table_args__ = (
        db.UniqueConstraint('firm_id', 'case_number',
                            name='case_files_firm_id_case_number_key'),
    )

    id = db.Column(db.Integer, primary_key=True)
    firm_id = db.Column(db.Integer, db.ForeignKey('firms.id'), index=True)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
    case_number = db.Column(db.String(50), nullable=False, index=True)
    title = db.Column(db.String(300), nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    matter_type = db.Column(db.String(80))
    court = db.Column(db.String(200))
    court_case_number = db.Column(db.String(120))
    stage = db.Column(db.String(40), nullable=False, default=DEFAULT_STAGE)
    position = db.Column(db.Integer, nullable=False, default=0)
    handling_advocate_user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    next_hearing_date = db.Column(db.Date)
    open_date = db.Column(db.Date, default=date.today)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    client = db.relationship('Client')
    parties = db.relationship('CaseParty', back_populates='case_file',
                              cascade='all, delete-orphan')
    events = db.relationship('CaseEvent', back_populates='case_file',
                             cascade='all, delete-orphan')

    def to_dict(self, include_parties=False):
        d = {
            'id': self.id,
            'firm_id': self.firm_id,
            'created_by_user_id': self.created_by_user_id,
            'case_number': self.case_number,
            'title': self.title,
            'client_id': self.client_id,
            'client_name': self.client.name if self.client else None,
            'matter_type': self.matter_type,
            'court': self.court,
            'court_case_number': self.court_case_number,
            'stage': self.stage,
            'position': self.position,
            'handling_advocate_user_id': self.handling_advocate_user_id,
            'next_hearing_date': self.next_hearing_date.isoformat() if self.next_hearing_date else None,
            'open_date': self.open_date.isoformat() if self.open_date else None,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_parties:
            d['parties'] = [p.to_dict() for p in self.parties]
        return d


class CaseParty(db.Model):
    __tablename__ = 'case_parties'

    id = db.Column(db.Integer, primary_key=True)
    case_file_id = db.Column(db.Integer, db.ForeignKey('case_files.id'), index=True)
    name = db.Column(db.String(300), nullable=False)
    role = db.Column(db.String(60))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    case_file = db.relationship('CaseFile', back_populates='parties')

    def to_dict(self):
        return {
            'id': self.id,
            'case_file_id': self.case_file_id,
            'name': self.name,
            'role': self.role,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class CaseEvent(db.Model):
    __tablename__ = 'case_events'

    id = db.Column(db.Integer, primary_key=True)
    case_file_id = db.Column(db.Integer, db.ForeignKey('case_files.id'), index=True)
    firm_id = db.Column(db.Integer, db.ForeignKey('firms.id'), index=True)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    event_date = db.Column(db.Date, nullable=False, index=True)
    kind = db.Column(db.String(30), nullable=False, default='note')
    title = db.Column(db.String(300), nullable=False)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    case_file = db.relationship('CaseFile', back_populates='events')

    def to_dict(self):
        return {
            'id': self.id,
            'case_file_id': self.case_file_id,
            'firm_id': self.firm_id,
            'created_by_user_id': self.created_by_user_id,
            'event_date': self.event_date.isoformat() if self.event_date else None,
            'kind': self.kind,
            'title': self.title,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
```

- [ ] **Step 4: Wire the models into app startup**

In `backend/app/main.py`, inside `create_app`'s `with app.app_context():` block, add the case models import next to the other model imports (so `db.create_all()` builds the tables):

```python
        from app.models.case import CaseFile, CaseParty, CaseEvent  # ensure case tables are created
```
Place it immediately after the line:
```python
        from app.models.models import RecurringSchedule  # ensure table is created
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_case_models.py -q`
Expected: PASS (3 passed)

---

### Task 3: Case numbering service

**Files:**
- Create: `backend/app/services/case_service.py`
- Test: `backend/tests/test_case_numbering.py`

**Interfaces:**
- Consumes: `CaseFile` from `app.models.case`.
- Produces: `generate_case_number(firm_id: int) -> str` — returns `"CF/{YYYY}/{NNNN}"`, per-firm sequence for the current year.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_case_numbering.py
from datetime import date

from app.models.models import db, Client
from app.models.auth import User
from app.models.case import CaseFile
from app.services.firm_service import provision_firm_for_user
from app.services.case_service import generate_case_number


def _seed(app):
    with app.app_context():
        user = User(supabase_id='sb-num', email='n@firm.com')
        db.session.add(user)
        db.session.commit()
        firm = provision_firm_for_user(user, 'Acme')
        client = Client(firm_id=firm.id, created_by_user_id=user.id, name='X')
        db.session.add(client)
        db.session.commit()
        return firm.id, user.id, client.id


def test_first_case_number_for_year(app):
    firm_id, _, _ = _seed(app)
    with app.app_context():
        assert generate_case_number(firm_id) == f"CF/{date.today().year}/0001"


def test_sequence_increments_per_firm(app):
    firm_id, user_id, client_id = _seed(app)
    with app.app_context():
        year = date.today().year
        db.session.add(CaseFile(firm_id=firm_id, created_by_user_id=user_id,
                                case_number=f"CF/{year}/0001", title='A', client_id=client_id))
        db.session.commit()
        assert generate_case_number(firm_id) == f"CF/{year}/0002"


def test_numbering_is_isolated_between_firms(app):
    firm_a, user_a, client_a = _seed(app)
    with app.app_context():
        year = date.today().year
        db.session.add(CaseFile(firm_id=firm_a, created_by_user_id=user_a,
                                case_number=f"CF/{year}/0001", title='A', client_id=client_a))
        db.session.commit()
        # A second firm starts its own sequence at 0001.
        userb = User(supabase_id='sb-b', email='b@firm.com')
        db.session.add(userb)
        db.session.commit()
        firm_b = provision_firm_for_user(userb, 'Beta')
        assert generate_case_number(firm_b.id) == f"CF/{year}/0001"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_case_numbering.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.case_service'`

- [ ] **Step 3: Implement the service**

```python
# backend/app/services/case_service.py
"""Per-firm case number generation: CF/{YYYY}/{NNNN}.

Mirrors generate_invoice_number: scoped per firm, year-segmented, sequence is
the max existing for the firm this year + 1. The (firm_id, case_number) unique
constraint backstops races.
"""
from datetime import date
from app.models.case import CaseFile


def generate_case_number(firm_id):
    year = date.today().year
    prefix = f"CF/{year}/"
    last = (CaseFile.query
            .filter(CaseFile.firm_id == firm_id,
                    CaseFile.case_number.like(f"{prefix}%"))
            .order_by(CaseFile.id.desc())
            .first())
    if last:
        try:
            next_seq = int(last.case_number.split('/')[-1]) + 1
        except ValueError:
            next_seq = 1
    else:
        next_seq = 1
    return f"{prefix}{str(next_seq).zfill(4)}"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_case_numbering.py -q`
Expected: PASS (3 passed)

---

### Task 4: `case_files` RBAC module

**Files:**
- Modify: `backend/app/rbac/permissions.py`
- Test: `backend/tests/test_case_permissions.py`

**Interfaces:**
- Consumes/Produces: extends `MODULES`, `ALL_PERMISSIONS`, `DEFAULT_ROLES` with `case_files` keys (`case_files.create/read/update/delete`).

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_case_permissions.py
from app.rbac.permissions import MODULES, ALL_PERMISSIONS, DEFAULT_ROLES


def test_case_files_module_present_with_crud():
    mod = next((m for m in MODULES if m['key'] == 'case_files'), None)
    assert mod is not None
    assert mod['actions'] == ['create', 'read', 'update', 'delete']


def test_case_files_permissions_registered():
    for action in ('create', 'read', 'update', 'delete'):
        assert f'case_files.{action}' in ALL_PERMISSIONS


def test_default_roles_grant_case_files():
    assert 'case_files.read' in DEFAULT_ROLES['Staff']
    assert 'case_files.create' in DEFAULT_ROLES['Associate']
    assert set(DEFAULT_ROLES['Partner']) >= {
        'case_files.create', 'case_files.read', 'case_files.update', 'case_files.delete'}
    assert set(DEFAULT_ROLES['Owner']) == ALL_PERMISSIONS
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_case_permissions.py -q`
Expected: FAIL on `test_case_files_module_present_with_crud` (module is None)

- [ ] **Step 3: Add the module + default grants**

In `backend/app/rbac/permissions.py`, add to the `MODULES` list (after the `roles` entry):

```python
    {"key": "case_files", "label": "Case Files", "actions": CRUD},
```

In the same file, extend the non-Owner `DEFAULT_ROLES` specs. Add to the `Partner` `_perms(...)` call:
```python
        ("case_files", CRUD),
```
Add to the `Associate` `_perms(...)` call:
```python
        ("case_files", ["create", "read", "update"]),
```
Add to the `Staff` `_perms(...)` call:
```python
        ("case_files", ["read"]),
```
(`ALL_PERMISSIONS` and the `Owner` role recompute automatically from `MODULES`.)

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_case_permissions.py -q`
Expected: PASS (3 passed)

- [ ] **Step 5: Confirm no RBAC regressions**

Run: `cd backend && python -m pytest tests/test_rbac_permissions.py tests/test_roles_api.py -q`
Expected: PASS (existing RBAC tests still green — Owner picks up the new keys dynamically)

---

### Task 5: Case Files API (CRUD + move + meta + nested parties)

**Files:**
- Create: `backend/app/api/case_files.py`
- Modify: `backend/app/main.py` (import `case_files` into the `app.api` import line; register the blueprint at `/api/v1`)
- Test: `backend/tests/test_case_files_api.py`

**Interfaces:**
- Consumes: `generate_case_number` (Task 3); `require_permission`, `jwt_required`; `STAGES`, `EVENT_KINDS`, `is_valid_stage` (Task 1); `CaseFile`, `CaseParty` (Task 2); `make_owner` fixture (existing).
- Produces blueprint `bp` with routes under `/api/v1`:
  - `GET /case-files`, `POST /case-files`, `GET /case-files/<id>`, `PATCH /case-files/<id>`, `PATCH /case-files/<id>/move`, `DELETE /case-files/<id>`, `GET /case-files/meta`.
  - Helper `_set_parties(case_file, parties_data)` — replace-set of `CaseParty` rows.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_case_files_api.py
import pytest

from app.models.models import db, Client
from app.models.auth import User


def _client_id(app_client, firm_id):
    with app_client.application.app_context():
        c = Client(firm_id=firm_id, created_by_user_id=User.query.filter_by(
            email='owner@firm.com').first().id, name='X Corp')
        db.session.add(c)
        db.session.commit()
        return c.id


def test_meta_lists_stages_and_kinds(client, make_owner):
    headers, _ = make_owner()
    body = client.get('/api/v1/case-files/meta', headers=headers).get_json()
    assert [s['key'] for s in body['stages']][0] == 'intake'
    assert 'hearing' in body['event_kinds']


def test_create_case_autonumbers_and_adds_parties(client, make_owner):
    headers, firm_id = make_owner()
    cid = _client_id(client, firm_id)
    resp = client.post('/api/v1/case-files', headers=headers, json={
        'title': 'X vs State', 'client_id': cid, 'court': 'Delhi HC',
        'parties': [{'name': 'X', 'role': 'petitioner'},
                    {'name': 'State', 'role': 'respondent'}],
    })
    assert resp.status_code == 201
    body = resp.get_json()
    assert body['case_number'].startswith('CF/')
    assert body['stage'] == 'intake'
    assert len(body['parties']) == 2


def test_create_rejects_other_firms_client(client, make_owner):
    headers, _ = make_owner()
    headers_b, firm_b = make_owner(supabase_id='sb-b', email='b@firm.com', firm_name='B')
    cid_b = _client_id(client, firm_b)
    resp = client.post('/api/v1/case-files', headers=headers, json={
        'title': 'Bad', 'client_id': cid_b})
    assert resp.status_code == 404


def test_list_and_get_detail(client, make_owner):
    headers, firm_id = make_owner()
    cid = _client_id(client, firm_id)
    created = client.post('/api/v1/case-files', headers=headers, json={
        'title': 'Matter A', 'client_id': cid}).get_json()
    listing = client.get('/api/v1/case-files', headers=headers).get_json()
    assert any(c['id'] == created['id'] for c in listing)
    detail = client.get(f"/api/v1/case-files/{created['id']}", headers=headers).get_json()
    assert detail['title'] == 'Matter A'
    assert 'parties' in detail


def test_patch_updates_fields_and_replaces_parties(client, make_owner):
    headers, firm_id = make_owner()
    cid = _client_id(client, firm_id)
    created = client.post('/api/v1/case-files', headers=headers, json={
        'title': 'Matter A', 'client_id': cid,
        'parties': [{'name': 'Old', 'role': 'petitioner'}]}).get_json()
    resp = client.patch(f"/api/v1/case-files/{created['id']}", headers=headers, json={
        'title': 'Matter A (amended)',
        'parties': [{'name': 'New', 'role': 'appellant'}]})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body['title'] == 'Matter A (amended)'
    assert len(body['parties']) == 1
    assert body['parties'][0]['name'] == 'New'


def test_move_changes_stage(client, make_owner):
    headers, firm_id = make_owner()
    cid = _client_id(client, firm_id)
    created = client.post('/api/v1/case-files', headers=headers, json={
        'title': 'Matter A', 'client_id': cid}).get_json()
    resp = client.patch(f"/api/v1/case-files/{created['id']}/move", headers=headers,
                        json={'stage': 'filed', 'position': 2})
    assert resp.status_code == 200
    assert resp.get_json()['stage'] == 'filed'


def test_move_rejects_invalid_stage(client, make_owner):
    headers, firm_id = make_owner()
    cid = _client_id(client, firm_id)
    created = client.post('/api/v1/case-files', headers=headers, json={
        'title': 'M', 'client_id': cid}).get_json()
    resp = client.patch(f"/api/v1/case-files/{created['id']}/move", headers=headers,
                        json={'stage': 'nowhere'})
    assert resp.status_code == 400


def test_delete_case(client, make_owner):
    headers, firm_id = make_owner()
    cid = _client_id(client, firm_id)
    created = client.post('/api/v1/case-files', headers=headers, json={
        'title': 'M', 'client_id': cid}).get_json()
    assert client.delete(f"/api/v1/case-files/{created['id']}", headers=headers).status_code == 200
    assert client.get(f"/api/v1/case-files/{created['id']}", headers=headers).status_code == 404
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_case_files_api.py -q`
Expected: FAIL — 404s (blueprint not registered yet)

- [ ] **Step 3: Create the blueprint**

```python
# backend/app/api/case_files.py
"""Case File API — firm-scoped, gated by the case_files RBAC module."""
from datetime import datetime
from flask import Blueprint, request, jsonify, g
from app.models.models import db, Client
from app.models.case import CaseFile, CaseParty
from app.middleware.jwt_auth import jwt_required
from app.middleware.firm_context import require_permission
from app.services.case_service import generate_case_number
from app.case.stages import STAGES, EVENT_KINDS, is_valid_stage

bp = Blueprint('case_files', __name__)


def _parse_date(value):
    return datetime.fromisoformat(value).date() if value else None


def _set_parties(case_file, parties_data):
    """Replace the case's parties with the supplied list."""
    case_file.parties.clear()
    for p in parties_data or []:
        name = (p.get('name') or '').strip()
        if not name:
            continue
        case_file.parties.append(CaseParty(name=name, role=p.get('role')))


@bp.route('/case-files/meta', methods=['GET'])
@jwt_required
@require_permission('case_files.read')
def case_meta():
    return jsonify({'stages': STAGES, 'event_kinds': EVENT_KINDS})


@bp.route('/case-files', methods=['GET'])
@jwt_required
@require_permission('case_files.read')
def list_case_files():
    query = CaseFile.query.filter_by(firm_id=g.firm_id)
    stage = request.args.get('stage')
    client_id = request.args.get('client_id', type=int)
    assignee = request.args.get('assignee', type=int)
    search = (request.args.get('search') or '').strip()
    if stage:
        query = query.filter_by(stage=stage)
    if client_id:
        query = query.filter_by(client_id=client_id)
    if assignee:
        query = query.filter_by(handling_advocate_user_id=assignee)
    if search:
        like = f"%{search}%"
        query = query.filter(db.or_(
            CaseFile.title.ilike(like),
            CaseFile.case_number.ilike(like),
            CaseFile.court_case_number.ilike(like),
        ))
    cases = query.order_by(CaseFile.position, CaseFile.id.desc()).all()
    return jsonify([c.to_dict() for c in cases])


@bp.route('/case-files', methods=['POST'])
@jwt_required
@require_permission('case_files.create')
def create_case_file():
    data = request.get_json() or {}
    title = (data.get('title') or '').strip()
    if not title:
        return jsonify({'error': 'Title is required'}), 400
    client = Client.query.filter_by(id=data.get('client_id'), firm_id=g.firm_id).first()
    if not client:
        return jsonify({'error': 'Client not found'}), 404

    stage = data.get('stage')
    if stage and not is_valid_stage(stage):
        return jsonify({'error': 'Invalid stage'}), 400

    case_file = CaseFile(
        firm_id=g.firm_id,
        created_by_user_id=g.user.id,
        case_number=generate_case_number(g.firm_id),
        title=title,
        client_id=client.id,
        matter_type=data.get('matter_type'),
        court=data.get('court'),
        court_case_number=data.get('court_case_number'),
        handling_advocate_user_id=data.get('handling_advocate_user_id'),
        next_hearing_date=_parse_date(data.get('next_hearing_date')),
        open_date=_parse_date(data.get('open_date')),
        description=data.get('description'),
    )
    if stage:
        case_file.stage = stage
    _set_parties(case_file, data.get('parties'))
    db.session.add(case_file)
    db.session.commit()
    return jsonify(case_file.to_dict(include_parties=True)), 201


@bp.route('/case-files/<int:case_id>', methods=['GET'])
@jwt_required
@require_permission('case_files.read')
def get_case_file(case_id):
    case_file = CaseFile.query.filter_by(id=case_id, firm_id=g.firm_id).first()
    if not case_file:
        return jsonify({'error': 'Case not found'}), 404
    return jsonify(case_file.to_dict(include_parties=True))


@bp.route('/case-files/<int:case_id>', methods=['PATCH'])
@jwt_required
@require_permission('case_files.update')
def update_case_file(case_id):
    case_file = CaseFile.query.filter_by(id=case_id, firm_id=g.firm_id).first()
    if not case_file:
        return jsonify({'error': 'Case not found'}), 404
    data = request.get_json() or {}

    if 'client_id' in data:
        client = Client.query.filter_by(id=data['client_id'], firm_id=g.firm_id).first()
        if not client:
            return jsonify({'error': 'Client not found'}), 404
        case_file.client_id = client.id
    if 'stage' in data:
        if not is_valid_stage(data['stage']):
            return jsonify({'error': 'Invalid stage'}), 400
        case_file.stage = data['stage']
    for field in ('title', 'matter_type', 'court', 'court_case_number',
                  'description', 'handling_advocate_user_id'):
        if field in data:
            setattr(case_file, field, data[field])
    if 'next_hearing_date' in data:
        case_file.next_hearing_date = _parse_date(data['next_hearing_date'])
    if 'open_date' in data:
        case_file.open_date = _parse_date(data['open_date'])
    if 'parties' in data:
        _set_parties(case_file, data['parties'])

    db.session.commit()
    return jsonify(case_file.to_dict(include_parties=True))


@bp.route('/case-files/<int:case_id>/move', methods=['PATCH'])
@jwt_required
@require_permission('case_files.update')
def move_case_file(case_id):
    case_file = CaseFile.query.filter_by(id=case_id, firm_id=g.firm_id).first()
    if not case_file:
        return jsonify({'error': 'Case not found'}), 404
    data = request.get_json() or {}
    stage = data.get('stage')
    if not stage or not is_valid_stage(stage):
        return jsonify({'error': 'Invalid stage'}), 400
    case_file.stage = stage
    if 'position' in data:
        case_file.position = int(data['position'])
    db.session.commit()
    return jsonify(case_file.to_dict())


@bp.route('/case-files/<int:case_id>', methods=['DELETE'])
@jwt_required
@require_permission('case_files.delete')
def delete_case_file(case_id):
    case_file = CaseFile.query.filter_by(id=case_id, firm_id=g.firm_id).first()
    if not case_file:
        return jsonify({'error': 'Case not found'}), 404
    db.session.delete(case_file)
    db.session.commit()
    return jsonify({'message': 'Case deleted'})
```

- [ ] **Step 4: Register the blueprint**

In `backend/app/main.py`, add `case_files` to the `from app.api import ...` line, then register it next to the other `/api/v1` blueprints:

```python
    app.register_blueprint(case_files.bp, url_prefix='/api/v1')
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_case_files_api.py -q`
Expected: PASS (8 passed)

---

### Task 6: Case Events API (timeline / diary steps)

**Files:**
- Create: `backend/app/api/case_events.py`
- Modify: `backend/app/main.py` (import + register `case_events` blueprint at `/api/v1`)
- Test: `backend/tests/test_case_events_api.py`

**Interfaces:**
- Consumes: `CaseFile`, `CaseEvent` (Task 2); `is_valid_event_kind` (Task 1); `require_permission`, `jwt_required`.
- Produces routes: `GET /case-files/<case_id>/events`, `POST /case-files/<case_id>/events`, `PATCH /case-events/<event_id>`, `DELETE /case-events/<event_id>`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_case_events_api.py
from app.models.models import db, Client
from app.models.auth import User


def _case(client, headers, firm_id):
    with client.application.app_context():
        c = Client(firm_id=firm_id, created_by_user_id=User.query.filter_by(
            email='owner@firm.com').first().id, name='X')
        db.session.add(c)
        db.session.commit()
        cid = c.id
    return client.post('/api/v1/case-files', headers=headers,
                       json={'title': 'M', 'client_id': cid}).get_json()['id']


def test_add_and_list_events_ordered(client, make_owner):
    headers, firm_id = make_owner()
    case_id = _case(client, headers, firm_id)
    client.post(f'/api/v1/case-files/{case_id}/events', headers=headers,
                json={'event_date': '2026-06-10', 'kind': 'hearing', 'title': 'Second hearing'})
    client.post(f'/api/v1/case-files/{case_id}/events', headers=headers,
                json={'event_date': '2026-06-01', 'kind': 'filing', 'title': 'Petition filed'})
    events = client.get(f'/api/v1/case-files/{case_id}/events', headers=headers).get_json()
    assert [e['title'] for e in events] == ['Petition filed', 'Second hearing']  # by event_date


def test_add_event_rejects_invalid_kind(client, make_owner):
    headers, firm_id = make_owner()
    case_id = _case(client, headers, firm_id)
    resp = client.post(f'/api/v1/case-files/{case_id}/events', headers=headers,
                       json={'event_date': '2026-06-01', 'kind': 'bogus', 'title': 'X'})
    assert resp.status_code == 400


def test_edit_and_delete_event(client, make_owner):
    headers, firm_id = make_owner()
    case_id = _case(client, headers, firm_id)
    ev = client.post(f'/api/v1/case-files/{case_id}/events', headers=headers,
                     json={'event_date': '2026-06-01', 'kind': 'note', 'title': 'Note'}).get_json()
    upd = client.patch(f"/api/v1/case-events/{ev['id']}", headers=headers,
                       json={'title': 'Note (edited)', 'notes': 'detail'})
    assert upd.status_code == 200
    assert upd.get_json()['title'] == 'Note (edited)'
    assert client.delete(f"/api/v1/case-events/{ev['id']}", headers=headers).status_code == 200


def test_events_isolated_by_firm(client, make_owner):
    headers, firm_id = make_owner()
    headers_b, _ = make_owner(supabase_id='sb-b', email='b@firm.com', firm_name='B')
    case_id = _case(client, headers, firm_id)
    ev = client.post(f'/api/v1/case-files/{case_id}/events', headers=headers,
                     json={'event_date': '2026-06-01', 'kind': 'note', 'title': 'N'}).get_json()
    # Firm B cannot touch firm A's event or list firm A's case events.
    assert client.patch(f"/api/v1/case-events/{ev['id']}", headers=headers_b,
                        json={'title': 'hack'}).status_code == 404
    assert client.get(f'/api/v1/case-files/{case_id}/events', headers=headers_b).status_code == 404
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_case_events_api.py -q`
Expected: FAIL — 404s (blueprint not registered)

- [ ] **Step 3: Create the blueprint**

```python
# backend/app/api/case_events.py
"""Case timeline (case_events) API — the diary 'steps'. Firm-scoped."""
from datetime import datetime
from flask import Blueprint, request, jsonify, g
from app.models.models import db
from app.models.case import CaseFile, CaseEvent
from app.middleware.jwt_auth import jwt_required
from app.middleware.firm_context import require_permission
from app.case.stages import is_valid_event_kind

bp = Blueprint('case_events', __name__)


def _parse_date(value):
    return datetime.fromisoformat(value).date() if value else None


@bp.route('/case-files/<int:case_id>/events', methods=['GET'])
@jwt_required
@require_permission('case_files.read')
def list_events(case_id):
    case_file = CaseFile.query.filter_by(id=case_id, firm_id=g.firm_id).first()
    if not case_file:
        return jsonify({'error': 'Case not found'}), 404
    events = (CaseEvent.query
              .filter_by(case_file_id=case_id)
              .order_by(CaseEvent.event_date.asc(), CaseEvent.id.asc())
              .all())
    return jsonify([e.to_dict() for e in events])


@bp.route('/case-files/<int:case_id>/events', methods=['POST'])
@jwt_required
@require_permission('case_files.update')
def add_event(case_id):
    case_file = CaseFile.query.filter_by(id=case_id, firm_id=g.firm_id).first()
    if not case_file:
        return jsonify({'error': 'Case not found'}), 404
    data = request.get_json() or {}
    title = (data.get('title') or '').strip()
    if not title:
        return jsonify({'error': 'Title is required'}), 400
    event_date = _parse_date(data.get('event_date'))
    if not event_date:
        return jsonify({'error': 'event_date is required'}), 400
    kind = data.get('kind', 'note')
    if not is_valid_event_kind(kind):
        return jsonify({'error': 'Invalid kind'}), 400

    event = CaseEvent(
        case_file_id=case_id,
        firm_id=g.firm_id,
        created_by_user_id=g.user.id,
        event_date=event_date,
        kind=kind,
        title=title,
        notes=data.get('notes'),
    )
    db.session.add(event)
    db.session.commit()
    return jsonify(event.to_dict()), 201


@bp.route('/case-events/<int:event_id>', methods=['PATCH'])
@jwt_required
@require_permission('case_files.update')
def update_event(event_id):
    event = CaseEvent.query.filter_by(id=event_id, firm_id=g.firm_id).first()
    if not event:
        return jsonify({'error': 'Event not found'}), 404
    data = request.get_json() or {}
    if 'kind' in data:
        if not is_valid_event_kind(data['kind']):
            return jsonify({'error': 'Invalid kind'}), 400
        event.kind = data['kind']
    if 'title' in data:
        event.title = (data['title'] or '').strip() or event.title
    if 'notes' in data:
        event.notes = data['notes']
    if 'event_date' in data:
        parsed = _parse_date(data['event_date'])
        if parsed:
            event.event_date = parsed
    db.session.commit()
    return jsonify(event.to_dict())


@bp.route('/case-events/<int:event_id>', methods=['DELETE'])
@jwt_required
@require_permission('case_files.update')
def delete_event(event_id):
    event = CaseEvent.query.filter_by(id=event_id, firm_id=g.firm_id).first()
    if not event:
        return jsonify({'error': 'Event not found'}), 404
    db.session.delete(event)
    db.session.commit()
    return jsonify({'message': 'Event deleted'})
```

- [ ] **Step 4: Register the blueprint**

In `backend/app/main.py`, add `case_events` to the `from app.api import ...` line and register:

```python
    app.register_blueprint(case_events.bp, url_prefix='/api/v1')
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_case_events_api.py -q`
Expected: PASS (4 passed)

---

### Task 7: Link invoices to cases (`case_file_id`)

**Files:**
- Modify: `backend/app/models/models.py` (add `Invoice.case_file_id` + `to_dict` key)
- Modify: `backend/app/api/invoices.py` (accept/validate `case_file_id` on create + update; add `GET /case-files/<id>/invoices` is NOT here — case invoices are read via the invoices list filter)
- Test: `backend/tests/test_invoice_case_link.py`

**Interfaces:**
- Consumes: `CaseFile` (Task 2).
- Produces: `Invoice.case_file_id` column + dict key; invoice create/update honor `case_file_id`; `GET /invoices?case_file_id=<id>` filters by case.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_invoice_case_link.py
from app.models.models import db, Client
from app.models.auth import User


def _client_and_case(client, headers, firm_id):
    with client.application.app_context():
        c = Client(firm_id=firm_id, created_by_user_id=User.query.filter_by(
            email='owner@firm.com').first().id, name='X')
        db.session.add(c)
        db.session.commit()
        cid = c.id
    case_id = client.post('/api/v1/case-files', headers=headers,
                          json={'title': 'M', 'client_id': cid}).get_json()['id']
    return cid, case_id


def test_create_invoice_with_case_link(client, make_owner):
    headers, firm_id = make_owner()
    cid, case_id = _client_and_case(client, headers, firm_id)
    resp = client.post('/api/v1/invoices', headers=headers, json={
        'client_id': cid, 'case_file_id': case_id, 'invoice_date': '2026-06-01',
        'items': [{'description': 'Fee', 'quantity': 1, 'rate': 1000, 'amount': 1000}]})
    assert resp.status_code == 201
    assert resp.get_json()['case_file_id'] == case_id


def test_invoice_rejects_other_firms_case(client, make_owner):
    headers, firm_id = make_owner()
    headers_b, firm_b = make_owner(supabase_id='sb-b', email='b@firm.com', firm_name='B')
    cid, _ = _client_and_case(client, headers, firm_id)
    _, case_b = _client_and_case(client, headers_b, firm_b)
    resp = client.post('/api/v1/invoices', headers=headers, json={
        'client_id': cid, 'case_file_id': case_b, 'invoice_date': '2026-06-01',
        'items': [{'description': 'Fee', 'quantity': 1, 'rate': 1000, 'amount': 1000}]})
    assert resp.status_code == 404


def test_filter_invoices_by_case(client, make_owner):
    headers, firm_id = make_owner()
    cid, case_id = _client_and_case(client, headers, firm_id)
    client.post('/api/v1/invoices', headers=headers, json={
        'client_id': cid, 'case_file_id': case_id, 'invoice_date': '2026-06-01',
        'items': [{'description': 'Fee', 'quantity': 1, 'rate': 1000, 'amount': 1000}]})
    listing = client.get(f'/api/v1/invoices?case_file_id={case_id}', headers=headers).get_json()
    assert len(listing) == 1
    assert listing[0]['case_file_id'] == case_id
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_invoice_case_link.py -q`
Expected: FAIL — `case_file_id` not honored (KeyError/None or 201 without link)

- [ ] **Step 3a: Add the model column**

In `backend/app/models/models.py`, in the `Invoice` model, add this column after the `client_id` column (line ~105):

```python
    case_file_id = db.Column(db.Integer, db.ForeignKey('case_files.id'), index=True)
```

In `Invoice.to_dict`, add to the returned dict (after `'client_id': self.client_id,`):

```python
            'case_file_id': self.case_file_id,
```

- [ ] **Step 3b: Honor `case_file_id` in the API**

In `backend/app/api/invoices.py`, add this import near the top model imports:

```python
from app.models.case import CaseFile
```

In `create_invoice`, after the client check block (after `invoice_number = generate_invoice_number(g.firm_id)`), add case validation:

```python
        case_file_id = data.get('case_file_id')
        if case_file_id is not None:
            case_file = CaseFile.query.filter_by(id=case_file_id, firm_id=g.firm_id).first()
            if not case_file:
                return jsonify({'error': 'Case not found'}), 404
```

Then add `case_file_id=case_file_id,` to the `Invoice(...)` constructor kwargs.

In `get_invoices`, after the `client_id` filter block, add the case filter:

```python
    case_file_id = request.args.get('case_file_id', type=int)
    if case_file_id:
        query = query.filter_by(case_file_id=case_file_id)
```

In `update_invoice`, add (next to the other field updates):

```python
    if 'case_file_id' in data:
        if data['case_file_id'] is None:
            invoice.case_file_id = None
        else:
            case_file = CaseFile.query.filter_by(id=data['case_file_id'], firm_id=g.firm_id).first()
            if case_file:
                invoice.case_file_id = case_file.id
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_invoice_case_link.py -q`
Expected: PASS (3 passed)

- [ ] **Step 5: Confirm invoice regressions are green**

Run: `cd backend && python -m pytest tests/test_api.py tests/test_send_service.py tests/test_pagination.py -q`
Expected: PASS (existing invoice tests still pass)

---

### Task 8: Cross-firm isolation regression for cases

**Files:**
- Test: `backend/tests/test_case_isolation.py`

**Interfaces:**
- Consumes: the case API (Tasks 5–6) and `make_owner` fixture.

- [ ] **Step 1: Write the failing-then-passing regression test**

```python
# backend/tests/test_case_isolation.py
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

    # B cannot see A's case in its own listing
    listing_b = client.get('/api/v1/case-files', headers=headers_b).get_json()
    assert all(c['id'] != case_a for c in listing_b)

    # B cannot read / patch / move / delete A's case
    assert client.get(f'/api/v1/case-files/{case_a}', headers=headers_b).status_code == 404
    assert client.patch(f'/api/v1/case-files/{case_a}', headers=headers_b,
                        json={'title': 'hack'}).status_code == 404
    assert client.patch(f'/api/v1/case-files/{case_a}/move', headers=headers_b,
                        json={'stage': 'closed'}).status_code == 404
    assert client.delete(f'/api/v1/case-files/{case_a}', headers=headers_b).status_code == 404

    # A still sees its case intact
    assert client.get(f'/api/v1/case-files/{case_a}', headers=headers_a).status_code == 200
```

- [ ] **Step 2: Run the test**

Run: `cd backend && python -m pytest tests/test_case_isolation.py -q`
Expected: PASS (1 passed) — the API already filters by `firm_id`; this locks it in.

- [ ] **Step 3: Run the whole backend suite**

Run: `cd backend && python -m pytest -q`
Expected: PASS (all previously-green tests + the new case tests)

---

### Task 9: Supabase migration `009_case_files.sql`

**Files:**
- Create: `backend/migrations/009_case_files.sql`

**Interfaces:** none (delivered for Parth to apply manually).

- [ ] **Step 1: Write the migration**

```sql
-- 009_case_files.sql — Case File spine (sub-project 2).
-- Additive, non-destructive. Apply once in the Supabase SQL editor.
-- Creates case_files / case_parties / case_events and links invoices to a case.
BEGIN;

CREATE TABLE IF NOT EXISTS public.case_files (
  id SERIAL PRIMARY KEY,
  firm_id INTEGER REFERENCES public.firms(id),
  created_by_user_id INTEGER REFERENCES public.users(id),
  case_number VARCHAR(50) NOT NULL,
  title VARCHAR(300) NOT NULL,
  client_id INTEGER NOT NULL REFERENCES public.clients(id),
  matter_type VARCHAR(80),
  court VARCHAR(200),
  court_case_number VARCHAR(120),
  stage VARCHAR(40) NOT NULL DEFAULT 'intake',
  position INTEGER NOT NULL DEFAULT 0,
  handling_advocate_user_id INTEGER REFERENCES public.users(id),
  next_hearing_date DATE,
  open_date DATE,
  description TEXT,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  CONSTRAINT case_files_firm_id_case_number_key UNIQUE (firm_id, case_number)
);
CREATE INDEX IF NOT EXISTS ix_case_files_firm_id ON public.case_files (firm_id);
CREATE INDEX IF NOT EXISTS ix_case_files_created_by ON public.case_files (created_by_user_id);
CREATE INDEX IF NOT EXISTS ix_case_files_case_number ON public.case_files (case_number);

CREATE TABLE IF NOT EXISTS public.case_parties (
  id SERIAL PRIMARY KEY,
  case_file_id INTEGER REFERENCES public.case_files(id) ON DELETE CASCADE,
  name VARCHAR(300) NOT NULL,
  role VARCHAR(60),
  created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_case_parties_case_file_id ON public.case_parties (case_file_id);

CREATE TABLE IF NOT EXISTS public.case_events (
  id SERIAL PRIMARY KEY,
  case_file_id INTEGER REFERENCES public.case_files(id) ON DELETE CASCADE,
  firm_id INTEGER REFERENCES public.firms(id),
  created_by_user_id INTEGER REFERENCES public.users(id),
  event_date DATE NOT NULL,
  kind VARCHAR(30) NOT NULL DEFAULT 'note',
  title VARCHAR(300) NOT NULL,
  notes TEXT,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_case_events_case_file_id ON public.case_events (case_file_id);
CREATE INDEX IF NOT EXISTS ix_case_events_firm_id ON public.case_events (firm_id);
CREATE INDEX IF NOT EXISTS ix_case_events_event_date ON public.case_events (event_date);

ALTER TABLE public.invoices
  ADD COLUMN IF NOT EXISTS case_file_id INTEGER REFERENCES public.case_files(id);
CREATE INDEX IF NOT EXISTS ix_invoices_case_file_id ON public.invoices (case_file_id);

COMMIT;

-- Permissions need no migration: the Owner role resolves to ALL_PERMISSIONS
-- dynamically, so existing firm owners gain case_files.* automatically. Grant
-- case_files.* to other roles via the in-app Roles editor as needed.
```

- [ ] **Step 2: Sanity-check it parses (no DB write)**

This file is applied manually by Parth. No automated step. Confirm the SQL matches the model columns in `app/models/case.py` (names, types, the unique constraint, and the `invoices.case_file_id` FK).

---

### Task 10: Frontend API client + types

**Files:**
- Modify: `frontend/src/api.ts` (types + `api` methods)
- Test: build typecheck (`cd frontend && npm run build`)

**Interfaces:**
- Produces TS types `CaseFile`, `CaseParty`, `CaseEvent`, `CaseMeta`; `api` methods: `getCaseMeta`, `getCaseFiles`, `getCaseFile`, `createCaseFile`, `updateCaseFile`, `moveCaseFile`, `deleteCaseFile`, `getCaseEvents`, `addCaseEvent`, `updateCaseEvent`, `deleteCaseEvent`, `getCaseInvoices`.

- [ ] **Step 1: Add the types**

In `frontend/src/api.ts`, after the `AgingBuckets` interface, add:

```typescript
// ---- Case files (CRM spine) -----------------------------------------------

export interface CaseParty {
  id?: number;
  case_file_id?: number;
  name: string;
  role?: string;
}

export interface CaseFile {
  id: number;
  firm_id: number;
  created_by_user_id: number;
  case_number: string;
  title: string;
  client_id: number;
  client_name?: string;
  matter_type?: string;
  court?: string;
  court_case_number?: string;
  stage: string;
  position: number;
  handling_advocate_user_id?: number | null;
  next_hearing_date?: string | null;
  open_date?: string | null;
  description?: string;
  parties?: CaseParty[];
  created_at?: string;
  updated_at?: string;
}

export interface CaseEvent {
  id: number;
  case_file_id: number;
  firm_id: number;
  created_by_user_id: number;
  event_date: string;
  kind: string;
  title: string;
  notes?: string | null;
  created_at?: string;
  updated_at?: string;
}

export interface CaseMeta {
  stages: { key: string; label: string }[];
  event_kinds: string[];
}
```

- [ ] **Step 2: Add the API methods**

In `frontend/src/api.ts`, inside the `api` object (before `getSignedUrl`), add:

```typescript
  // ---- Case files -------------------------------------------------------
  getCaseMeta: () => fetchAPI<CaseMeta>(`${API_BASE_URL}/case-files/meta`),

  getCaseFiles: (params?: { stage?: string; client_id?: number; search?: string }) => {
    const q = new URLSearchParams();
    if (params?.stage) q.append('stage', params.stage);
    if (params?.client_id) q.append('client_id', String(params.client_id));
    if (params?.search) q.append('search', params.search);
    const qs = q.toString();
    return fetchAPI<CaseFile[]>(`${API_BASE_URL}/case-files${qs ? `?${qs}` : ''}`);
  },

  getCaseFile: (id: number) => fetchAPI<CaseFile>(`${API_BASE_URL}/case-files/${id}`),

  createCaseFile: (data: Partial<CaseFile>) =>
    fetchAPI<CaseFile>(`${API_BASE_URL}/case-files`, {
      method: 'POST', body: JSON.stringify(data),
    }),

  updateCaseFile: (id: number, data: Partial<CaseFile>) =>
    fetchAPI<CaseFile>(`${API_BASE_URL}/case-files/${id}`, {
      method: 'PATCH', body: JSON.stringify(data),
    }),

  moveCaseFile: (id: number, stage: string, position?: number) =>
    fetchAPI<CaseFile>(`${API_BASE_URL}/case-files/${id}/move`, {
      method: 'PATCH', body: JSON.stringify({ stage, position }),
    }),

  deleteCaseFile: (id: number) =>
    fetchAPI<{ message: string }>(`${API_BASE_URL}/case-files/${id}`, { method: 'DELETE' }),

  getCaseEvents: (caseId: number) =>
    fetchAPI<CaseEvent[]>(`${API_BASE_URL}/case-files/${caseId}/events`),

  addCaseEvent: (caseId: number, data: { event_date: string; kind: string; title: string; notes?: string }) =>
    fetchAPI<CaseEvent>(`${API_BASE_URL}/case-files/${caseId}/events`, {
      method: 'POST', body: JSON.stringify(data),
    }),

  updateCaseEvent: (eventId: number, data: Partial<CaseEvent>) =>
    fetchAPI<CaseEvent>(`${API_BASE_URL}/case-events/${eventId}`, {
      method: 'PATCH', body: JSON.stringify(data),
    }),

  deleteCaseEvent: (eventId: number) =>
    fetchAPI<{ message: string }>(`${API_BASE_URL}/case-events/${eventId}`, { method: 'DELETE' }),

  getCaseInvoices: (caseId: number) =>
    fetchAPI<Invoice[]>(`${API_BASE_URL}/invoices?case_file_id=${caseId}`),
```

- [ ] **Step 3: Typecheck**

Run: `cd frontend && npm run build`
Expected: `tsc` passes (no type errors), vite build completes.

---

### Task 11: Frontend Cases board (kanban + list) + route + nav

**Files:**
- Create: `frontend/src/pages/Cases.tsx`
- Modify: `frontend/src/App.tsx` (route `/cases`)
- Modify: `frontend/src/components/Layout.tsx` (nav link in Practice group, gated by `case_files.read`)

**Interfaces:**
- Consumes: `api.getCaseMeta/getCaseFiles/createCaseFile/moveCaseFile`, `api.getClients`, `usePermissions`, `useToast`, design-system classes.

- [ ] **Step 1: Create the page**

```tsx
// frontend/src/pages/Cases.tsx
import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api, CaseFile, CaseParty } from '../api';
import { usePermissions } from '../hooks/usePermissions';
import { useToast } from '../contexts/ToastContext';
import { Plus, X, LayoutGrid, List as ListIcon } from 'lucide-react';

const errMsg = (e: unknown) => (e instanceof Error ? e.message : 'Something went wrong');

const EMPTY = {
  title: '', client_id: 0, matter_type: '', court: '', court_case_number: '',
  parties: [] as CaseParty[],
};

export default function Cases() {
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const { has } = usePermissions();
  const canCreate = has('case_files.create');
  const canMove = has('case_files.update');

  const [view, setView] = useState<'board' | 'list'>('board');
  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState(EMPTY);

  const { data: meta } = useQuery({ queryKey: ['case-meta'], queryFn: api.getCaseMeta });
  const { data: cases = [], isLoading } = useQuery({
    queryKey: ['case-files'], queryFn: () => api.getCaseFiles(),
  });
  const { data: clients = [] } = useQuery({ queryKey: ['clients'], queryFn: () => api.getClients() });

  const stages = meta?.stages ?? [];
  const byStage = useMemo(() => {
    const map: Record<string, CaseFile[]> = {};
    stages.forEach((s) => { map[s.key] = []; });
    cases.forEach((c) => { (map[c.stage] = map[c.stage] || []).push(c); });
    return map;
  }, [cases, stages]);

  const createMutation = useMutation({
    mutationFn: () => api.createCaseFile({
      ...form,
      client_id: Number(form.client_id),
      parties: form.parties.filter((p) => p.name.trim()),
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['case-files'] });
      setModalOpen(false); setForm(EMPTY); showToast('Case file opened');
    },
    onError: (e) => showToast(errMsg(e), 'error'),
  });

  const moveMutation = useMutation({
    mutationFn: ({ id, stage }: { id: number; stage: string }) => api.moveCaseFile(id, stage),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['case-files'] }),
    onError: (e) => showToast(errMsg(e), 'error'),
  });

  const onDrop = (stage: string, e: React.DragEvent) => {
    e.preventDefault();
    const id = Number(e.dataTransfer.getData('text/case-id'));
    if (id && canMove) moveMutation.mutate({ id, stage });
  };

  return (
    <div className="max-w-page mx-auto px-8 lg:px-12 py-10">
      <header className="flex items-end justify-between flex-wrap gap-6 mb-8">
        <div>
          <div className="page-eyebrow">Folio V · Docket</div>
          <h1 className="page-title">Case files</h1>
          <p className="page-subtitle">Every matter your firm is running, on one board.</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex border border-rule rounded-DEFAULT overflow-hidden">
            <button onClick={() => setView('board')}
              className={`p-2 ${view === 'board' ? 'bg-paper-deep text-ink' : 'text-ink-muted'}`}
              title="Board"><LayoutGrid size={15} /></button>
            <button onClick={() => setView('list')}
              className={`p-2 ${view === 'list' ? 'bg-paper-deep text-ink' : 'text-ink-muted'}`}
              title="List"><ListIcon size={15} /></button>
          </div>
          {canCreate && (
            <button onClick={() => setModalOpen(true)} className="btn-primary">
              <Plus size={14} strokeWidth={2} /><span>New case</span>
            </button>
          )}
        </div>
      </header>

      {isLoading ? (
        <div className="card p-16 flex justify-center"><div className="spinner" /></div>
      ) : view === 'board' ? (
        <div className="flex gap-4 overflow-x-auto pb-4">
          {stages.map((s) => (
            <div key={s.key}
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => onDrop(s.key, e)}
              className="w-72 shrink-0">
              <div className="eyebrow mb-2 flex items-center justify-between">
                <span>{s.label}</span>
                <span className="text-ink-faint">{byStage[s.key]?.length ?? 0}</span>
              </div>
              <div className="space-y-2 min-h-[60px]">
                {(byStage[s.key] ?? []).map((c) => (
                  <Link key={c.id} to={`/cases/${c.id}`}
                    draggable={canMove}
                    onDragStart={(e) => e.dataTransfer.setData('text/case-id', String(c.id))}
                    className="block card p-3 hover:bg-paper-deep/40 transition-colors">
                    <div className="text-2xs font-mono text-oxblood">{c.case_number}</div>
                    <div className="text-sm text-ink font-medium leading-snug mt-0.5">{c.title}</div>
                    <div className="text-2xs text-ink-muted mt-1">{c.client_name}</div>
                    {c.court && <div className="text-2xs text-ink-faint mt-0.5">{c.court}</div>}
                    {c.next_hearing_date && (
                      <div className="text-2xs text-oxblood mt-1">Next: {c.next_hearing_date}</div>
                    )}
                  </Link>
                ))}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="border border-rule divide-y divide-rule">
          {cases.map((c) => (
            <Link key={c.id} to={`/cases/${c.id}`}
              className="bg-surface flex items-center gap-4 px-5 py-3 hover:bg-paper-deep/40">
              <span className="text-2xs font-mono text-oxblood w-28 shrink-0">{c.case_number}</span>
              <span className="text-sm text-ink flex-1 truncate">{c.title}</span>
              <span className="text-xs text-ink-muted w-40 truncate">{c.client_name}</span>
              <span className="text-2xs uppercase tracking-eyebrow text-ink-muted w-32 text-right">
                {stages.find((s) => s.key === c.stage)?.label ?? c.stage}
              </span>
            </Link>
          ))}
          {cases.length === 0 && (
            <div className="bg-surface p-10 text-center text-sm text-ink-muted">No case files yet.</div>
          )}
        </div>
      )}

      {modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 animate-fade-in">
          <div className="absolute inset-0 bg-ink/40 backdrop-blur-[2px]" onClick={() => setModalOpen(false)} />
          <div className="relative bg-surface border border-rule rounded-DEFAULT max-w-xl w-full
                          max-h-[90vh] overflow-y-auto shadow-modal animate-fade-up">
            <div className="h-[3px] bg-oxblood" />
            <div className="p-8">
              <button onClick={() => setModalOpen(false)}
                className="absolute top-5 right-5 text-ink-faint hover:text-ink-muted" aria-label="Close">
                <X size={20} strokeWidth={1.5} />
              </button>
              <div className="mb-6"><div className="page-eyebrow">New matter</div>
                <h2 className="page-title !text-2xl">Open a case file</h2></div>
              <form onSubmit={(e) => { e.preventDefault(); createMutation.mutate(); }} className="space-y-4">
                <div>
                  <label className="field-label">Title *</label>
                  <input required value={form.title} autoFocus
                    onChange={(e) => setForm({ ...form, title: e.target.value })}
                    className="field-input" placeholder="e.g., X Corp vs State of Delhi" />
                </div>
                <div>
                  <label className="field-label">Client *</label>
                  <select required value={form.client_id}
                    onChange={(e) => setForm({ ...form, client_id: Number(e.target.value) })}
                    className="field-select">
                    <option value={0} disabled>Select a client…</option>
                    {clients.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
                  </select>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="field-label">Court</label>
                    <input value={form.court}
                      onChange={(e) => setForm({ ...form, court: e.target.value })}
                      className="field-input" placeholder="Delhi High Court" />
                  </div>
                  <div>
                    <label className="field-label">Case / filing no.</label>
                    <input value={form.court_case_number}
                      onChange={(e) => setForm({ ...form, court_case_number: e.target.value })}
                      className="field-input font-mono" placeholder="W.P.(C) 1234/2026" />
                  </div>
                </div>
                <div>
                  <label className="field-label">Matter type</label>
                  <input value={form.matter_type}
                    onChange={(e) => setForm({ ...form, matter_type: e.target.value })}
                    className="field-input" placeholder="Constitutional / Civil / Tax…" />
                </div>
                <div className="flex gap-3 justify-end pt-4 border-t border-rule">
                  <button type="button" onClick={() => setModalOpen(false)} className="btn-ghost">Cancel</button>
                  <button type="submit" className="btn-primary" disabled={createMutation.isPending}>Open file</button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Add the route**

In `frontend/src/App.tsx`, import the page and the detail page (detail created in Task 12):

```tsx
import Cases from './pages/Cases';
import CaseDetail from './pages/CaseDetail';
```

Add these two routes inside the protected `Layout` route block (next to `clients`):

```tsx
            <Route path="cases" element={<Cases />} />
            <Route path="cases/:id" element={<CaseDetail />} />
```

- [ ] **Step 3: Add the nav link**

In `frontend/src/components/Layout.tsx`, import `Briefcase` from lucide-react (add to the existing import list), import `usePermissions`, and make the Practice nav permission-aware. Replace the static `NAV_PRIMARY` usage with a computed list inside the component:

```tsx
  const { has } = usePermissions();
  const navPrimary: Item[] = [
    { name: 'Dashboard', path: '/dashboard', Icon: LayoutDashboard },
    { name: 'Invoices', path: '/invoices', Icon: FileText },
    ...(has('case_files.read') ? [{ name: 'Cases', path: '/cases', Icon: Briefcase }] : []),
    { name: 'Clients', path: '/clients', Icon: Users },
    { name: 'Items', path: '/items', Icon: Package },
    { name: 'Legal Feed', path: '/legal-feed', Icon: Scale },
  ];
```

Then change `<NavGroup label="Practice" items={NAV_PRIMARY} />` to `items={navPrimary}` and delete the now-unused module-level `NAV_PRIMARY` constant.

- [ ] **Step 4: Typecheck**

Run: `cd frontend && npm run build`
Expected: `tsc` clean, vite build completes. (CaseDetail import resolves once Task 12 lands; do Task 12 before this build, or stub it. Run this build at the end of Task 12.)

---

### Task 12: Frontend Case detail — "open the file"

**Files:**
- Create: `frontend/src/pages/CaseDetail.tsx`
- (Route already added in Task 11.)

**Interfaces:**
- Consumes: `api.getCaseFile/updateCaseFile/getCaseEvents/addCaseEvent/deleteCaseEvent/getCaseInvoices/getCaseMeta`, `usePermissions`, `useToast`.

- [ ] **Step 1: Create the detail page**

```tsx
// frontend/src/pages/CaseDetail.tsx
import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../api';
import { usePermissions } from '../hooks/usePermissions';
import { useToast } from '../contexts/ToastContext';
import { ArrowLeft, Plus, Trash2, FileText } from 'lucide-react';

const errMsg = (e: unknown) => (e instanceof Error ? e.message : 'Something went wrong');
const today = () => new Date().toISOString().slice(0, 10);

export default function CaseDetail() {
  const { id } = useParams();
  const caseId = Number(id);
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const { has } = usePermissions();
  const canUpdate = has('case_files.update');

  const { data: meta } = useQuery({ queryKey: ['case-meta'], queryFn: api.getCaseMeta });
  const { data: caseFile, isLoading } = useQuery({
    queryKey: ['case-file', caseId], queryFn: () => api.getCaseFile(caseId),
  });
  const { data: events = [] } = useQuery({
    queryKey: ['case-events', caseId], queryFn: () => api.getCaseEvents(caseId),
  });
  const { data: invoices = [] } = useQuery({
    queryKey: ['case-invoices', caseId], queryFn: () => api.getCaseInvoices(caseId),
  });

  const [step, setStep] = useState({ event_date: today(), kind: 'note', title: '', notes: '' });

  const stageMutation = useMutation({
    mutationFn: (stage: string) => api.updateCaseFile(caseId, { stage }),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['case-file', caseId] }); showToast('Stage updated'); },
    onError: (e) => showToast(errMsg(e), 'error'),
  });

  const addStep = useMutation({
    mutationFn: () => api.addCaseEvent(caseId, step),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['case-events', caseId] });
      setStep({ event_date: today(), kind: 'note', title: '', notes: '' });
      showToast('Step added');
    },
    onError: (e) => showToast(errMsg(e), 'error'),
  });

  const delStep = useMutation({
    mutationFn: (eventId: number) => api.deleteCaseEvent(eventId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['case-events', caseId] }),
    onError: (e) => showToast(errMsg(e), 'error'),
  });

  if (isLoading || !caseFile) {
    return <div className="max-w-page mx-auto px-8 py-16 flex justify-center"><div className="spinner" /></div>;
  }

  return (
    <div className="max-w-page mx-auto px-8 lg:px-12 py-10">
      <Link to="/cases" className="inline-flex items-center gap-1.5 text-xs text-ink-muted hover:text-oxblood mb-6">
        <ArrowLeft size={13} /> Back to docket
      </Link>

      {/* Header */}
      <header className="mb-8">
        <div className="page-eyebrow font-mono">{caseFile.case_number}</div>
        <h1 className="page-title">{caseFile.title}</h1>
        <div className="flex flex-wrap gap-x-6 gap-y-1 text-sm text-ink-muted mt-2">
          <span>{caseFile.client_name}</span>
          {caseFile.court && <span>{caseFile.court}</span>}
          {caseFile.court_case_number && <span className="font-mono">{caseFile.court_case_number}</span>}
          {caseFile.next_hearing_date && <span className="text-oxblood">Next: {caseFile.next_hearing_date}</span>}
        </div>
        <div className="mt-3">
          <label className="field-label">Stage</label>
          <select value={caseFile.stage} disabled={!canUpdate}
            onChange={(e) => stageMutation.mutate(e.target.value)}
            className="field-select w-56">
            {(meta?.stages ?? []).map((s) => <option key={s.key} value={s.key}>{s.label}</option>)}
          </select>
        </div>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Timeline / diary */}
        <section className="lg:col-span-2">
          <div className="eyebrow mb-3">Case timeline</div>

          {canUpdate && (
            <form onSubmit={(e) => { e.preventDefault(); addStep.mutate(); }}
              className="card p-4 mb-5 space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="field-label">Date</label>
                  <input type="date" value={step.event_date}
                    onChange={(e) => setStep({ ...step, event_date: e.target.value })}
                    className="field-input" />
                </div>
                <div>
                  <label className="field-label">Kind</label>
                  <select value={step.kind} onChange={(e) => setStep({ ...step, kind: e.target.value })}
                    className="field-select">
                    {(meta?.event_kinds ?? []).map((k) => <option key={k} value={k}>{k}</option>)}
                  </select>
                </div>
              </div>
              <input required value={step.title} placeholder="What happened — e.g. Notice issued"
                onChange={(e) => setStep({ ...step, title: e.target.value })} className="field-input" />
              <textarea value={step.notes} rows={2} placeholder="Notes (optional)"
                onChange={(e) => setStep({ ...step, notes: e.target.value })} className="field-textarea" />
              <div className="flex justify-end">
                <button type="submit" className="btn-primary" disabled={addStep.isPending}>
                  <Plus size={14} strokeWidth={2} /><span>Add step</span>
                </button>
              </div>
            </form>
          )}

          <ol className="relative border-l border-rule ml-2 space-y-5">
            {events.map((ev) => (
              <li key={ev.id} className="ml-5">
                <span className="absolute -left-[5px] mt-1.5 h-2 w-2 rounded-full bg-oxblood" />
                <div className="flex items-start justify-between gap-3 group">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-2xs font-mono text-ink-muted">{ev.event_date}</span>
                      <span className="text-2xs uppercase tracking-eyebrow text-oxblood bg-oxblood-wash px-1.5 py-0.5 rounded-sm">{ev.kind}</span>
                    </div>
                    <div className="text-sm text-ink font-medium mt-1">{ev.title}</div>
                    {ev.notes && <div className="text-sm text-ink-muted mt-0.5 whitespace-pre-wrap">{ev.notes}</div>}
                  </div>
                  {canUpdate && (
                    <button onClick={() => delStep.mutate(ev.id)}
                      className="opacity-0 group-hover:opacity-100 p-1 text-ink-muted hover:text-oxblood transition">
                      <Trash2 size={13} />
                    </button>
                  )}
                </div>
              </li>
            ))}
            {events.length === 0 && <li className="ml-5 text-sm text-ink-muted">No steps recorded yet.</li>}
          </ol>
        </section>

        {/* Side: parties + invoices */}
        <aside className="space-y-8">
          <div>
            <div className="eyebrow mb-3">Parties</div>
            <div className="border border-rule divide-y divide-rule">
              {(caseFile.parties ?? []).map((p) => (
                <div key={p.id} className="bg-surface px-4 py-2.5">
                  <div className="text-sm text-ink">{p.name}</div>
                  <div className="text-2xs uppercase tracking-eyebrow text-ink-muted">{p.role}</div>
                </div>
              ))}
              {(caseFile.parties ?? []).length === 0 && (
                <div className="bg-surface px-4 py-3 text-sm text-ink-muted">No parties recorded.</div>
              )}
            </div>
          </div>

          <div>
            <div className="eyebrow mb-3">Billing</div>
            <div className="border border-rule divide-y divide-rule">
              {invoices.map((inv) => (
                <div key={inv.id} className="bg-surface flex items-center gap-2 px-4 py-2.5">
                  <FileText size={13} className="text-ink-faint" />
                  <span className="text-sm text-ink flex-1">{inv.invoice_number}</span>
                  <span className="text-sm tabular text-ink-muted">{inv.total}</span>
                </div>
              ))}
              {invoices.length === 0 && (
                <div className="bg-surface px-4 py-3 text-sm text-ink-muted">No invoices for this case.</div>
              )}
            </div>
            <Link to={`/invoices/new?case_file_id=${caseId}&client_id=${caseFile.client_id}`}
              className="btn-ghost mt-3 inline-flex"><Plus size={14} /> New invoice for this case</Link>
          </div>
        </aside>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Typecheck the whole frontend**

Run: `cd frontend && npm run build`
Expected: `tsc` clean, vite build completes (Cases + CaseDetail both resolve).

---

### Task 13: Invoice form — optional Case picker

**Files:**
- Modify: `frontend/src/pages/NewInvoice.tsx`

**Interfaces:**
- Consumes: `api.getCaseFiles`, the `case_file_id`/`client_id` query params produced by the CaseDetail "New invoice" link.

- [ ] **Step 1: Add a case picker to the invoice form**

In `frontend/src/pages/NewInvoice.tsx`:

1. Ensure `useSearchParams` is imported from `react-router-dom`.
2. Add a query for cases filtered by the selected client, and a `case_file_id` field in the invoice form state. Concretely: where the form holds `client_id`, add `case_file_id` (default from `useSearchParams().get('case_file_id')` or `null`). Add:

```tsx
  const { data: caseOptions = [] } = useQuery({
    queryKey: ['case-files', 'for-client', selectedClientId],
    queryFn: () => api.getCaseFiles({ client_id: selectedClientId }),
    enabled: !!selectedClientId,
  });
```

(`selectedClientId` is the form's current client id.)

3. Render the picker near the client selector:

```tsx
  {selectedClientId ? (
    <div>
      <label className="field-label">Case (optional)</label>
      <select value={form.case_file_id ?? ''}
        onChange={(e) => setForm({ ...form, case_file_id: e.target.value ? Number(e.target.value) : null })}
        className="field-select">
        <option value="">— No case —</option>
        {caseOptions.map((c) => (
          <option key={c.id} value={c.id}>{c.case_number} · {c.title}</option>
        ))}
      </select>
    </div>
  ) : null}
```

4. Include `case_file_id: form.case_file_id` in the payload passed to `api.createInvoice` / `api.updateInvoice`.

> Note: `NewInvoice.tsx` is an existing file with its own form-state shape. Read it first and adapt the exact variable names (the form-state object, the client-id field, the create/update call site). The behavior to implement is: a client is chosen → an optional case dropdown of that client's cases appears → the chosen id rides along on the invoice payload, pre-selected when arriving via the CaseDetail link.

- [ ] **Step 2: Typecheck**

Run: `cd frontend && npm run build`
Expected: `tsc` clean, vite build completes.

---

### Task 14: Full regression + smoke

- [ ] **Step 1: Backend suite green**

Run: `cd backend && python -m pytest -q`
Expected: all tests pass (existing + the new case tests).

- [ ] **Step 2: Frontend builds clean**

Run: `cd frontend && npm run build`
Expected: `tsc` clean, vite build completes.

- [ ] **Step 3: Manual smoke (solo Owner)**

Walk the flow as the solo advocate:
1. Open a case file (title + client + court) → it appears in the **Intake** column.
2. Drag the card to **Filed** → reload → it stays in Filed.
3. Open the file → add timeline steps (filing, hearing) → they show in date order.
4. From the case, click "New invoice for this case" → confirm the invoice form pre-selects the client + case, create it → it appears under the case's Billing panel.
5. Confirm the "Cases" nav link is present (Owner has `case_files.read`).

- [ ] **Step 4: Hand the migration to Parth**

`backend/migrations/009_case_files.sql` — apply in the Supabase SQL editor. No backfill; permissions are automatic for Owners.

---

## Self-Review notes

- **Spec coverage:** CaseFile (T2), parties (T2/T5), timeline `case_events` (T2/T6), per-firm numbering (T3), `case_files` RBAC module + default grants (T4), CRUD+move+meta API (T5), events API (T6), invoice link (T7), isolation (T8), migration (T9), frontend API (T10), kanban+list+nav (T11), open-the-file detail (T12), invoice case picker (T13), regression+smoke (T14). Every spec section maps to a task.
- **Out-of-scope held:** no document/evidence vault, no calendar view, no templates/AI, no per-matter access walls — all deferred per the spec.
- **Type consistency:** `case_file_id`, `firm_id`, `created_by_user_id`, `stage`, `position`, `event_date`, `kind`, `generate_case_number`, `is_valid_stage`, `is_valid_event_kind`, `_set_parties` used consistently across backend tasks; `CaseFile`/`CaseEvent`/`CaseMeta` and the `api.*` method names match between Tasks 10–13.
- **Git:** no commit steps — Parth handles git; each task gates on a green test/build run.
