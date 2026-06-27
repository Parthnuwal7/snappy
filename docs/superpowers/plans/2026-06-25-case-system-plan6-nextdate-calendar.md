# Case System UX — Plan 6: Next-Date Mechanism + Calendar Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make hearings the single source of truth for dates — each hearing carries a purpose and an outcome, `next_hearing_date` becomes derived, "Record proceedings" captures today's outcome and the next date in one step, and the Calendar tab aggregates every case's hearings.

**Architecture:** `case_events` gains `purpose`/`outcome` (used by `kind='hearing'`). A `recompute_next_hearing_date(case_file)` service sets `next_hearing_date` to the soonest future hearing; it runs whenever hearing events change and after the new endpoints. `POST /case-files/<id>/proceedings` records the current hearing's outcome and creates the next hearing; `POST /case-files/<id>/next-date` upserts the soonest future hearing (the quick inline edit). `GET /calendar` ranges over all firm hearings. The frontend shows purpose/outcome on the timeline, an inline next-date control in the header, a Record-proceedings modal (the now-live rail action), and a month-grid + agenda Calendar page.

**Tech Stack:** Flask + SQLAlchemy (SQLite in tests via `db.create_all`), pytest; React + TypeScript + Vite, TanStack Query, Tailwind tokens.

## Global Constraints

- Never run git commits/pushes — Parth does git. Stage only; run the gate and report.
- Migrations are SQL files for Parth to apply. New file: `017_hearing_fields.sql`.
- `next_hearing_date` is **derived** — never set by manual case edit. Only `recompute_next_hearing_date` (driven by hearing events) writes it.
- Hearings are `case_events` with `kind='hearing'`. `purpose`/`outcome` are stored free-form; `purpose` has catalog suggestions (`hearing_purposes`) in `/meta`.
- Endpoints gated by `case_files` permissions (read = calendar/list; update = proceedings/next-date), consistent with the rest of the case API.
- Backend stays green (`pytest`); frontend builds clean (`npm run build`).

---

### Task 1: Hearing `purpose`/`outcome` + derived `next_hearing_date`

**Files:**
- Modify: `backend/app/models/case.py` (`CaseEvent`: add `purpose`, `outcome`; serialize)
- Modify: `backend/app/api/case_events.py` (accept/return the fields; recompute on add/update/delete)
- Modify: `backend/app/services/case_service.py` (add `recompute_next_hearing_date`)
- Create: `backend/migrations/017_hearing_fields.sql`
- Test: `backend/tests/test_next_hearing_date.py`

**Interfaces:**
- Produces: `CaseEvent.purpose` (str), `CaseEvent.outcome` (text) in `to_dict`; `recompute_next_hearing_date(case_file) -> date|None` (caller commits). Event add/update/delete keep `next_hearing_date` in sync.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_next_hearing_date.py`:

```python
from datetime import date, timedelta
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


def _d(offset):
    return (date.today() + timedelta(days=offset)).isoformat()


def test_hearing_sets_next_date_to_soonest_future(client, make_owner):
    headers, firm_id = make_owner()
    case_id = _case(client, headers, firm_id)
    client.post(f'/api/v1/case-files/{case_id}/events', headers=headers,
                json={'event_date': _d(20), 'kind': 'hearing', 'title': 'Hearing', 'purpose': 'evidence'})
    client.post(f'/api/v1/case-files/{case_id}/events', headers=headers,
                json={'event_date': _d(5), 'kind': 'hearing', 'title': 'Hearing'})
    cf = client.get(f'/api/v1/case-files/{case_id}', headers=headers).get_json()
    assert cf['next_hearing_date'] == _d(5)  # the soonest future hearing


def test_past_hearing_does_not_set_next_date(client, make_owner):
    headers, firm_id = make_owner()
    case_id = _case(client, headers, firm_id)
    client.post(f'/api/v1/case-files/{case_id}/events', headers=headers,
                json={'event_date': _d(-3), 'kind': 'hearing', 'title': 'Past hearing'})
    cf = client.get(f'/api/v1/case-files/{case_id}', headers=headers).get_json()
    assert cf['next_hearing_date'] is None


def test_event_carries_purpose_and_outcome(client, make_owner):
    headers, firm_id = make_owner()
    case_id = _case(client, headers, firm_id)
    ev = client.post(f'/api/v1/case-files/{case_id}/events', headers=headers,
                     json={'event_date': _d(7), 'kind': 'hearing', 'title': 'Hearing',
                           'purpose': 'arguments'}).get_json()
    assert ev['purpose'] == 'arguments'
    upd = client.patch(f"/api/v1/case-events/{ev['id']}", headers=headers,
                       json={'outcome': 'Adjourned for evidence'}).get_json()
    assert upd['outcome'] == 'Adjourned for evidence'


def test_deleting_only_hearing_clears_next_date(client, make_owner):
    headers, firm_id = make_owner()
    case_id = _case(client, headers, firm_id)
    ev = client.post(f'/api/v1/case-files/{case_id}/events', headers=headers,
                     json={'event_date': _d(9), 'kind': 'hearing', 'title': 'Hearing'}).get_json()
    client.delete(f"/api/v1/case-events/{ev['id']}", headers=headers)
    cf = client.get(f'/api/v1/case-files/{case_id}', headers=headers).get_json()
    assert cf['next_hearing_date'] is None
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd backend && python -m pytest tests/test_next_hearing_date.py -v`
Expected: FAIL — `purpose` not returned / `next_hearing_date` not derived.

- [ ] **Step 3: Add `purpose`/`outcome` to `CaseEvent`**

In `backend/app/models/case.py`, in `CaseEvent`, after `notes = db.Column(db.Text)` add:

```python
    purpose = db.Column(db.String(80))
    outcome = db.Column(db.Text)
```

In `CaseEvent.to_dict`, after the `'notes': self.notes,` line, add:

```python
            'purpose': self.purpose,
            'outcome': self.outcome,
```

- [ ] **Step 4: Add the recompute helper**

Append to `backend/app/services/case_service.py`:

```python
def recompute_next_hearing_date(case_file):
    """Derive next_hearing_date = the soonest hearing event dated today or later
    (None if there is none). Caller commits."""
    from datetime import date
    from app.models.case import CaseEvent
    soonest = (CaseEvent.query
               .filter(CaseEvent.case_file_id == case_file.id,
                       CaseEvent.kind == 'hearing',
                       CaseEvent.event_date >= date.today())
               .order_by(CaseEvent.event_date.asc())
               .first())
    case_file.next_hearing_date = soonest.event_date if soonest else None
    return case_file.next_hearing_date
```

- [ ] **Step 5: Accept the fields + recompute in `case_events.py`**

In `backend/app/api/case_events.py`:
- Add the import: `from app.services.case_service import recompute_next_hearing_date`.
- In `add_event`, set the new fields on the `CaseEvent(...)` constructor by adding:
  ```python
        purpose=data.get('purpose'),
        outcome=data.get('outcome'),
  ```
  and replace the trailing `db.session.add(event)` / `db.session.commit()` / `return` with:
  ```python
      db.session.add(event)
      db.session.flush()
      recompute_next_hearing_date(case_file)
      db.session.commit()
      return jsonify(event.to_dict()), 201
  ```
- In `update_event`, add handling after the `event_date` block:
  ```python
      if 'purpose' in data:
          event.purpose = data['purpose']
      if 'outcome' in data:
          event.outcome = data['outcome']
      recompute_next_hearing_date(event.case_file)
      db.session.commit()
      return jsonify(event.to_dict())
  ```
  (replace the existing `db.session.commit()` / `return jsonify(event.to_dict())` at the end of `update_event`).
- In `delete_event`, before `db.session.delete(event)` capture the case file, and recompute after delete:
  ```python
      case_file = event.case_file
      ...
      db.session.delete(event)
      db.session.flush()
      recompute_next_hearing_date(case_file)
      db.session.commit()
  ```
  (insert `case_file = event.case_file` right after the 404 check; insert the `flush()` + recompute between `db.session.delete(event)` and `db.session.commit()`.)

- [ ] **Step 6: Stop manual `next_hearing_date` edits (make it derived)**

In `backend/app/api/case_files.py` `update_case_file`, delete the block:

```python
    if 'next_hearing_date' in data:
        case_file.next_hearing_date = _parse_date(data['next_hearing_date'])
```

(Creation may still seed it; it is overwritten as soon as a hearing event exists. Leave `create_case_file` as-is.)

- [ ] **Step 7: Create migration 017**

Create `backend/migrations/017_hearing_fields.sql`:

```sql
-- 017_hearing_fields.sql — hearing purpose + outcome on case_events.
-- Additive/non-destructive. Apply in the Supabase SQL editor.
BEGIN;

ALTER TABLE public.case_events ADD COLUMN IF NOT EXISTS purpose VARCHAR(80);
ALTER TABLE public.case_events ADD COLUMN IF NOT EXISTS outcome TEXT;

COMMIT;
```

- [ ] **Step 8: Run the test + full suite + stage (do NOT commit)**

Run: `cd backend && python -m pytest tests/test_next_hearing_date.py -q && python -m pytest -q`
Expected: PASS (280).

```bash
git add backend/app/models/case.py backend/app/api/case_events.py backend/app/api/case_files.py backend/app/services/case_service.py backend/migrations/017_hearing_fields.sql backend/tests/test_next_hearing_date.py
```

---

### Task 2: Record-proceedings + next-date endpoints + purposes + rail flip

**Files:**
- Modify: `backend/app/case/stages.py` (`HEARING_PURPOSES`; flip `record_proceedings` to available in 4 stages)
- Modify: `backend/app/api/case_files.py` (`/meta` adds `hearing_purposes`; import)
- Modify: `backend/app/api/case_events.py` (add `/proceedings` + `/next-date` routes)
- Test: `backend/tests/test_proceedings_api.py`, `backend/tests/test_case_files_api.py`, `backend/tests/test_case_stages.py`

**Interfaces:**
- Produces: `HEARING_PURPOSES` (list of `{key,label}`); `/meta` gains `hearing_purposes`. `POST /case-files/<id>/proceedings` body `{next_date (req), purpose, outcome, current_event_id}` → records `outcome` on `current_event_id` (when given & a hearing of this case), creates a new hearing for `next_date`+`purpose`, recomputes `next_hearing_date`; returns `{case_file, next_event}`. `POST /case-files/<id>/next-date` body `{next_date (req), purpose}` → updates the soonest future hearing's date (or creates one), recomputes; returns the case file. `STAGE_GUIDES` `record_proceedings` becomes available in `filed`, `hearings_evidence`, `arguments`, `judgment`.

- [ ] **Step 1: Write the failing API test**

Create `backend/tests/test_proceedings_api.py`:

```python
from datetime import date, timedelta
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


def _d(offset):
    return (date.today() + timedelta(days=offset)).isoformat()


def test_record_proceedings_sets_outcome_and_next_date(client, make_owner):
    headers, firm_id = make_owner()
    case_id = _case(client, headers, firm_id)
    cur = client.post(f'/api/v1/case-files/{case_id}/events', headers=headers,
                      json={'event_date': _d(0), 'kind': 'hearing', 'title': 'Hearing'}).get_json()
    resp = client.post(f'/api/v1/case-files/{case_id}/proceedings', headers=headers,
                       json={'current_event_id': cur['id'], 'outcome': 'Reply filed; adjourned',
                             'purpose': 'evidence', 'next_date': _d(10)}).get_json()
    assert resp['case_file']['next_hearing_date'] == _d(10)
    assert resp['next_event']['purpose'] == 'evidence'

    events = client.get(f'/api/v1/case-files/{case_id}/events', headers=headers).get_json()
    disposed = next(e for e in events if e['id'] == cur['id'])
    assert disposed['outcome'] == 'Reply filed; adjourned'
    assert len([e for e in events if e['kind'] == 'hearing']) == 2


def test_proceedings_requires_next_date(client, make_owner):
    headers, firm_id = make_owner()
    case_id = _case(client, headers, firm_id)
    assert client.post(f'/api/v1/case-files/{case_id}/proceedings', headers=headers,
                       json={'outcome': 'x'}).status_code == 400


def test_next_date_upserts_soonest_hearing(client, make_owner):
    headers, firm_id = make_owner()
    case_id = _case(client, headers, firm_id)
    # No hearings yet -> creates one.
    client.post(f'/api/v1/case-files/{case_id}/next-date', headers=headers, json={'next_date': _d(8)})
    cf = client.get(f'/api/v1/case-files/{case_id}', headers=headers).get_json()
    assert cf['next_hearing_date'] == _d(8)
    # Correcting it -> moves the same hearing, not a second one.
    client.post(f'/api/v1/case-files/{case_id}/next-date', headers=headers, json={'next_date': _d(12)})
    cf = client.get(f'/api/v1/case-files/{case_id}', headers=headers).get_json()
    assert cf['next_hearing_date'] == _d(12)
    hearings = [e for e in client.get(f'/api/v1/case-files/{case_id}/events', headers=headers).get_json()
                if e['kind'] == 'hearing']
    assert len(hearings) == 1


def test_proceedings_isolated(client, make_owner):
    headers, firm_id = make_owner()
    headers_b, _ = make_owner(supabase_id='sb-b', email='b@firm.com', firm_name='B')
    case_id = _case(client, headers, firm_id)
    assert client.post(f'/api/v1/case-files/{case_id}/proceedings', headers=headers_b,
                       json={'next_date': _d(3)}).status_code == 404
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd backend && python -m pytest tests/test_proceedings_api.py -v`
Expected: FAIL — routes 404.

- [ ] **Step 3: Add `HEARING_PURPOSES` + flip `record_proceedings`**

In `backend/app/case/stages.py`, append:

```python
HEARING_PURPOSES = [
    {"key": "framing",   "label": "Framing of issues"},
    {"key": "evidence",  "label": "Evidence"},
    {"key": "cross",     "label": "Cross-examination"},
    {"key": "arguments", "label": "Arguments"},
    {"key": "reply",     "label": "Reply / Rejoinder"},
    {"key": "orders",    "label": "Orders"},
    {"key": "misc",      "label": "Miscellaneous"},
]
```

In `STAGE_GUIDES`, change every `{"key": "record_proceedings", ... "available": False}` to `"available": True` (it appears in `filed`, `hearings_evidence`, `arguments`, `judgment`).

- [ ] **Step 4: Add `hearing_purposes` to `/meta` (+ test)**

Append to `backend/tests/test_case_files_api.py`:

```python
def test_meta_includes_hearing_purposes(client, make_owner):
    headers, _ = make_owner()
    body = client.get('/api/v1/case-files/meta', headers=headers).get_json()
    assert any(p['key'] == 'evidence' for p in body['hearing_purposes'])
```

In `backend/app/api/case_files.py`, add `HEARING_PURPOSES` to the stages import and the meta dict:

```python
from app.case.stages import (
    STAGES, EVENT_KINDS, PRIORITIES, STAGE_GUIDES, STAGE_FLOW, HEARING_PURPOSES,
    is_valid_stage, is_valid_priority,
)
```
and add to the `case_meta` return dict:

```python
                    'hearing_purposes': HEARING_PURPOSES,
```

- [ ] **Step 5: Add the rail-availability test**

Append to `backend/tests/test_case_stages.py`:

```python
def test_record_proceedings_available_in_court_stages():
    for stage in ("filed", "hearings_evidence", "arguments", "judgment"):
        actions = {a["key"]: a for a in STAGE_GUIDES[stage]["actions"]}
        assert actions["record_proceedings"]["available"] is True
```

- [ ] **Step 6: Add the `/proceedings` + `/next-date` routes**

In `backend/app/api/case_events.py`, append:

```python
def _hearing_or_create_next(case_id, next_date, purpose):
    """Return (or create) the soonest future hearing for the case, set to next_date."""
    from datetime import date
    upcoming = (CaseEvent.query
                .filter(CaseEvent.case_file_id == case_id, CaseEvent.kind == 'hearing',
                        CaseEvent.event_date >= date.today())
                .order_by(CaseEvent.event_date.asc()).first())
    if upcoming:
        upcoming.event_date = next_date
        if purpose is not None:
            upcoming.purpose = purpose
        return upcoming
    ev = CaseEvent(case_file_id=case_id, firm_id=g.firm_id, created_by_user_id=g.user.id,
                   event_date=next_date, kind='hearing', title='Hearing', purpose=purpose)
    db.session.add(ev)
    return ev


@bp.route('/case-files/<int:case_id>/proceedings', methods=['POST'])
@jwt_required
@require_permission('case_files.update')
def record_proceedings(case_id):
    case_file = CaseFile.query.filter_by(id=case_id, firm_id=g.firm_id).first()
    if not case_file:
        return jsonify({'error': 'Case not found'}), 404
    data = request.get_json() or {}
    next_date = _parse_date(data.get('next_date'))
    if not next_date:
        return jsonify({'error': 'next_date is required'}), 400

    current_event_id = data.get('current_event_id')
    if current_event_id:
        cur = CaseEvent.query.filter_by(id=current_event_id, case_file_id=case_id).first()
        if cur:
            cur.outcome = data.get('outcome')

    new_ev = CaseEvent(case_file_id=case_id, firm_id=g.firm_id, created_by_user_id=g.user.id,
                       event_date=next_date, kind='hearing',
                       title=(data.get('purpose') or 'Hearing'), purpose=data.get('purpose'))
    db.session.add(new_ev)
    db.session.flush()
    recompute_next_hearing_date(case_file)
    db.session.commit()
    return jsonify({'case_file': case_file.to_dict(), 'next_event': new_ev.to_dict()})


@bp.route('/case-files/<int:case_id>/next-date', methods=['POST'])
@jwt_required
@require_permission('case_files.update')
def set_next_date(case_id):
    case_file = CaseFile.query.filter_by(id=case_id, firm_id=g.firm_id).first()
    if not case_file:
        return jsonify({'error': 'Case not found'}), 404
    data = request.get_json() or {}
    next_date = _parse_date(data.get('next_date'))
    if not next_date:
        return jsonify({'error': 'next_date is required'}), 400
    _hearing_or_create_next(case_id, next_date, data.get('purpose'))
    db.session.flush()
    recompute_next_hearing_date(case_file)
    db.session.commit()
    return jsonify(case_file.to_dict())
```

- [ ] **Step 7: Run the new tests + full suite**

Run: `cd backend && python -m pytest tests/test_proceedings_api.py tests/test_case_files_api.py tests/test_case_stages.py -q && python -m pytest -q`
Expected: PASS (285).

- [ ] **Step 8: Stage (do NOT commit)**

```bash
git add backend/app/case/stages.py backend/app/api/case_files.py backend/app/api/case_events.py backend/tests/test_proceedings_api.py backend/tests/test_case_files_api.py backend/tests/test_case_stages.py
```

---

### Task 3: Calendar endpoint

**Files:**
- Create: `backend/app/api/calendar.py`
- Modify: `backend/app/main.py:12` (import), `:88` (register blueprint)
- Test: `backend/tests/test_calendar_api.py`

**Interfaces:**
- Produces: blueprint `calendar` with `GET /calendar?from=YYYY-MM-DD&to=YYYY-MM-DD` → list of `{event_id, case_file_id, case_number, case_title, client_name, event_date, title, purpose, outcome}` for all firm hearing events in `[from, to]` (defaults: from = today, to = today + 60 days), ordered by `event_date`.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_calendar_api.py`:

```python
from datetime import date, timedelta
from app.models.models import db, Client
from app.models.auth import User


def _case(client, headers, firm_id, title='M'):
    with client.application.app_context():
        c = Client(firm_id=firm_id, created_by_user_id=User.query.filter_by(
            email='owner@firm.com').first().id, name='Acme')
        db.session.add(c); db.session.commit()
        cid = c.id
    return client.post('/api/v1/case-files', headers=headers,
                       json={'title': title, 'client_id': cid}).get_json()['id']


def _d(offset):
    return (date.today() + timedelta(days=offset)).isoformat()


def test_calendar_lists_hearings_in_window(client, make_owner):
    headers, firm_id = make_owner()
    case_id = _case(client, headers, firm_id, title='Sharma v. State')
    client.post(f'/api/v1/case-files/{case_id}/events', headers=headers,
                json={'event_date': _d(5), 'kind': 'hearing', 'title': 'Hearing', 'purpose': 'evidence'})
    client.post(f'/api/v1/case-files/{case_id}/events', headers=headers,
                json={'event_date': _d(2), 'kind': 'note', 'title': 'A note'})
    rows = client.get(f'/api/v1/calendar?from={_d(0)}&to={_d(30)}', headers=headers).get_json()
    assert len(rows) == 1  # only the hearing
    assert rows[0]['case_title'] == 'Sharma v. State'
    assert rows[0]['client_name'] == 'Acme'
    assert rows[0]['purpose'] == 'evidence'


def test_calendar_window_excludes_outside(client, make_owner):
    headers, firm_id = make_owner()
    case_id = _case(client, headers, firm_id)
    client.post(f'/api/v1/case-files/{case_id}/events', headers=headers,
                json={'event_date': _d(90), 'kind': 'hearing', 'title': 'Far hearing'})
    rows = client.get(f'/api/v1/calendar?from={_d(0)}&to={_d(30)}', headers=headers).get_json()
    assert rows == []


def test_calendar_firm_isolation(client, make_owner):
    headers, firm_id = make_owner()
    headers_b, _ = make_owner(supabase_id='sb-b', email='b@firm.com', firm_name='B')
    case_id = _case(client, headers, firm_id)
    client.post(f'/api/v1/case-files/{case_id}/events', headers=headers,
                json={'event_date': _d(5), 'kind': 'hearing', 'title': 'Hearing'})
    assert client.get(f'/api/v1/calendar?from={_d(0)}&to={_d(30)}', headers=headers_b).get_json() == []
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd backend && python -m pytest tests/test_calendar_api.py -v`
Expected: FAIL — `/calendar` 404.

- [ ] **Step 3: Create the calendar blueprint**

Create `backend/app/api/calendar.py`:

```python
"""Firm-wide hearing calendar — aggregates case_events of kind 'hearing'."""
from datetime import date, timedelta, datetime
from flask import Blueprint, request, jsonify, g
from app.models.models import db
from app.models.case import CaseEvent, CaseFile
from app.middleware.jwt_auth import jwt_required
from app.middleware.firm_context import require_permission

bp = Blueprint('calendar', __name__)


def _parse(value, fallback):
    try:
        return datetime.fromisoformat(value).date() if value else fallback
    except ValueError:
        return fallback


@bp.route('/calendar', methods=['GET'])
@jwt_required
@require_permission('case_files.read')
def calendar():
    today = date.today()
    start = _parse(request.args.get('from'), today)
    end = _parse(request.args.get('to'), today + timedelta(days=60))
    rows = (db.session.query(CaseEvent, CaseFile)
            .join(CaseFile, CaseEvent.case_file_id == CaseFile.id)
            .filter(CaseEvent.firm_id == g.firm_id, CaseEvent.kind == 'hearing',
                    CaseEvent.event_date >= start, CaseEvent.event_date <= end)
            .order_by(CaseEvent.event_date.asc(), CaseEvent.id.asc())
            .all())
    out = []
    for ev, cf in rows:
        out.append({
            'event_id': ev.id,
            'case_file_id': cf.id,
            'case_number': cf.case_number,
            'case_title': cf.title,
            'client_name': cf.client.name if cf.client else None,
            'event_date': ev.event_date.isoformat() if ev.event_date else None,
            'title': ev.title,
            'purpose': ev.purpose,
            'outcome': ev.outcome,
        })
    return jsonify(out)
```

- [ ] **Step 4: Register the blueprint**

In `backend/app/main.py:12`, append `, calendar` to the `from app.api import ...` line.
After the `case_exhibits` blueprint registration (line ~89), add:

```python
    app.register_blueprint(calendar.bp, url_prefix='/api/v1')
```

- [ ] **Step 5: Run the test + full suite + stage (do NOT commit)**

Run: `cd backend && python -m pytest tests/test_calendar_api.py -q && python -m pytest -q`
Expected: PASS (288).

```bash
git add backend/app/api/calendar.py backend/app/main.py backend/tests/test_calendar_api.py
```

---

### Task 4: Frontend — proceedings, inline next-date, timeline purpose/outcome

**Files:**
- Modify: `frontend/src/api.ts` (`CaseEvent` fields; `CaseMeta.hearing_purposes`; methods)
- Modify: `frontend/src/pages/CaseDetail.tsx` (timeline purpose/outcome; header next-date; proceedings modal; rail action; drop manual next_hearing_date from edit modal)
- Gate: `npm run build` clean.

**Interfaces:**
- Produces: `api.recordProceedings(caseId, body)`, `api.setNextDate(caseId, body)`; `CaseEvent.purpose`/`outcome`; `CaseMeta.hearing_purposes`.

- [ ] **Step 1: Extend types + add methods in `api.ts`**

Add to the `CaseEvent` interface (wherever it is defined): `purpose: string | null;` and `outcome: string | null;`.

Add to `CaseMeta`: `hearing_purposes: { key: string; label: string }[];`.

Add to the `api` object (after the exhibit methods):

```ts
  // ---- Hearings / proceedings -------------------------------------------
  recordProceedings: (caseId: number, data: { next_date: string; purpose?: string; outcome?: string; current_event_id?: number }) =>
    fetchAPI<{ case_file: CaseFile; next_event: CaseEvent }>(`${API_BASE_URL}/case-files/${caseId}/proceedings`, {
      method: 'POST', body: JSON.stringify(data),
    }),

  setNextDate: (caseId: number, data: { next_date: string; purpose?: string }) =>
    fetchAPI<CaseFile>(`${API_BASE_URL}/case-files/${caseId}/next-date`, {
      method: 'POST', body: JSON.stringify(data),
    }),
```

- [ ] **Step 2: Drop the manual next-hearing field from the edit modal**

In `frontend/src/pages/CaseDetail.tsx`:
- In `saveCase`'s mutation payload, remove `next_hearing_date: draft.next_hearing_date || null,`.
- In the edit-modal date grid, delete the `<div>` containing the `Next hearing` `<input>` (the one bound to `draft.next_hearing_date`). Leave Filed / Opened.

- [ ] **Step 3: Add proceedings + next-date state/mutations**

In `CaseDetail.tsx`, after the exhibit mutations (added in Plan 5), add:

```tsx
  const invalidateHearing = () => {
    queryClient.invalidateQueries({ queryKey: ['case-file', caseId] });
    queryClient.invalidateQueries({ queryKey: ['case-files'] });
    queryClient.invalidateQueries({ queryKey: ['case-events', caseId] });
  };
  const [procOpen, setProcOpen] = useState(false);
  const [proc, setProc] = useState({ outcome: '', purpose: '', next_date: today() });
  const currentHearing = events.find((ev) => ev.kind === 'hearing' && ev.event_date === caseFile?.next_hearing_date);
  const recordProc = useMutation({
    mutationFn: () => api.recordProceedings(caseId, {
      next_date: proc.next_date, purpose: proc.purpose || undefined,
      outcome: proc.outcome || undefined, current_event_id: currentHearing?.id,
    }),
    onSuccess: () => { invalidateHearing(); setProcOpen(false); setProc({ outcome: '', purpose: '', next_date: today() }); showToast('Proceedings recorded'); },
    onError: (e) => showToast(errMsg(e), 'error'),
  });
  const nextDateMut = useMutation({
    mutationFn: (next_date: string) => api.setNextDate(caseId, { next_date }),
    onSuccess: () => { invalidateHearing(); showToast('Next date updated'); },
    onError: (e) => showToast(errMsg(e), 'error'),
  });
```

In `railAction`, add: `case 'record_proceedings': setProcOpen(true); break;`.

- [ ] **Step 4: Inline next-date control in the header**

In `CaseDetail.tsx` header, the facts `<dl>` renders Next hearing via `fact('Next hearing', caseFile.next_hearing_date)`. Replace that single `{fact('Next hearing', caseFile.next_hearing_date)}` line with an editable control:

```tsx
          <div>
            <dt className="text-2xs uppercase tracking-eyebrow text-ink-faint">Next hearing</dt>
            <dd className="text-sm text-ink mt-0.5">
              {canUpdate ? (
                <input type="date" value={caseFile.next_hearing_date ?? ''}
                  onChange={(e) => e.target.value && nextDateMut.mutate(e.target.value)}
                  className="field-input !py-0.5 !text-sm w-40" />
              ) : (caseFile.next_hearing_date ?? '—')}
            </dd>
          </div>
```

- [ ] **Step 5: Show purpose/outcome on hearing timeline entries**

In `CaseDetail.tsx`, in the Timeline panel's read-only event render (the block showing `ev.title` and `ev.notes`), after the `{ev.notes && ...}` line add:

```tsx
                      {ev.purpose && <div className="text-2xs text-ink-muted mt-0.5">Purpose: {ev.purpose}</div>}
                      {ev.outcome && <div className="text-sm text-ink-muted mt-0.5 italic whitespace-pre-wrap">{ev.outcome}</div>}
```

- [ ] **Step 6: Add the Record-proceedings modal**

In `CaseDetail.tsx`, before the closing `{/* Edit modal */}` block (i.e., alongside the other modals), add:

```tsx
      {procOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 animate-fade-in">
          <div className="absolute inset-0 bg-ink/40 backdrop-blur-[2px]" onClick={() => setProcOpen(false)} />
          <div className="relative bg-surface border border-rule rounded-DEFAULT max-w-lg w-full shadow-modal animate-fade-up">
            <div className="h-[3px] bg-oxblood" />
            <div className="p-8">
              <button onClick={() => setProcOpen(false)} className="absolute top-5 right-5 text-ink-faint hover:text-ink-muted"><X size={20} strokeWidth={1.5} /></button>
              <div className="mb-6"><div className="page-eyebrow">Order sheet</div><h2 className="page-title !text-2xl">Record proceedings</h2></div>
              <form onSubmit={(e) => { e.preventDefault(); recordProc.mutate(); }} className="space-y-4">
                {currentHearing && (
                  <p className="text-2xs text-ink-muted">Disposing hearing dated <span className="font-mono">{currentHearing.event_date}</span>.</p>
                )}
                <div>
                  <label className="field-label">What happened today</label>
                  <textarea value={proc.outcome} rows={2} placeholder="e.g. Reply filed; matter adjourned for evidence"
                    onChange={(e) => setProc({ ...proc, outcome: e.target.value })} className="field-textarea" />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="field-label">Purpose of next date</label>
                    <select value={proc.purpose} onChange={(e) => setProc({ ...proc, purpose: e.target.value })} className="field-select">
                      <option value="">—</option>
                      {(meta?.hearing_purposes ?? []).map((p) => <option key={p.key} value={p.key}>{p.label}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="field-label">Next date *</label>
                    <input required type="date" value={proc.next_date}
                      onChange={(e) => setProc({ ...proc, next_date: e.target.value })} className="field-input" />
                  </div>
                </div>
                <div className="flex gap-3 justify-end pt-4 border-t border-rule">
                  <button type="button" onClick={() => setProcOpen(false)} className="btn-ghost">Cancel</button>
                  <button type="submit" className="btn-primary" disabled={recordProc.isPending}>Save</button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
```

- [ ] **Step 7: Build**

Run: `cd frontend && npm run build`
Expected: build succeeds, no TypeScript errors.

- [ ] **Step 8: Stage (do NOT commit)**

```bash
git add frontend/src/api.ts frontend/src/pages/CaseDetail.tsx
```

---

### Task 5: Frontend — Calendar page (month grid + agenda)

**Files:**
- Modify: `frontend/src/api.ts` (`CalendarItem` type + `getCalendar`)
- Modify: `frontend/src/pages/CaseCalendar.tsx` (replace the placeholder with a month grid + agenda)
- Gate: `npm run build` clean.

**Interfaces:**
- Produces: `api.getCalendar(from, to)`; `CalendarItem` interface.

- [ ] **Step 1: Add the type + method in `api.ts`**

```ts
export interface CalendarItem {
  event_id: number;
  case_file_id: number;
  case_number: string;
  case_title: string;
  client_name: string | null;
  event_date: string;
  title: string;
  purpose: string | null;
  outcome: string | null;
}
```

In the `api` object:

```ts
  getCalendar: (from: string, to: string) =>
    fetchAPI<CalendarItem[]>(`${API_BASE_URL}/calendar?from=${from}&to=${to}`),
```

- [ ] **Step 2: Rebuild `CaseCalendar.tsx` as a month grid + agenda**

Replace the entire contents of `frontend/src/pages/CaseCalendar.tsx` with:

```tsx
import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { api } from '../api';
import { ChevronLeft, ChevronRight } from 'lucide-react';

const iso = (d: Date) => d.toISOString().slice(0, 10);
const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December'];

export default function CaseCalendar() {
  const [cursor, setCursor] = useState(() => { const d = new Date(); return new Date(d.getFullYear(), d.getMonth(), 1); });
  const year = cursor.getFullYear();
  const month = cursor.getMonth();

  const from = iso(new Date(year, month, 1));
  const to = iso(new Date(year, month + 1, 0));

  const { data: items = [], isLoading } = useQuery({
    queryKey: ['calendar', from, to], queryFn: () => api.getCalendar(from, to),
  });

  const byDay = useMemo(() => {
    const map: Record<string, typeof items> = {};
    items.forEach((it) => { (map[it.event_date] = map[it.event_date] || []).push(it); });
    return map;
  }, [items]);

  // Build the month grid (weeks of Date|null), Monday-first.
  const cells = useMemo(() => {
    const first = new Date(year, month, 1);
    const lead = (first.getDay() + 6) % 7; // Mon=0
    const days = new Date(year, month + 1, 0).getDate();
    const out: (Date | null)[] = [];
    for (let i = 0; i < lead; i++) out.push(null);
    for (let d = 1; d <= days; d++) out.push(new Date(year, month, d));
    while (out.length % 7 !== 0) out.push(null);
    return out;
  }, [year, month]);

  const shift = (delta: number) => setCursor(new Date(year, month + delta, 1));

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="font-display text-xl text-ink">{MONTHS[month]} {year}</h2>
        <div className="flex gap-1">
          <button onClick={() => shift(-1)} className="btn-ghost p-2"><ChevronLeft size={15} /></button>
          <button onClick={() => shift(1)} className="btn-ghost p-2"><ChevronRight size={15} /></button>
        </div>
      </div>

      {isLoading ? (
        <div className="card p-16 flex justify-center"><div className="spinner" /></div>
      ) : (
        <>
          <div className="grid grid-cols-7 border-l border-t border-rule">
            {['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].map((d) => (
              <div key={d} className="eyebrow text-center py-1.5 border-r border-b border-rule bg-paper-deep">{d}</div>
            ))}
            {cells.map((d, i) => {
              const key = d ? iso(d) : `e${i}`;
              const hits = d ? (byDay[iso(d)] ?? []) : [];
              return (
                <div key={key} className="min-h-[84px] border-r border-b border-rule p-1.5 bg-surface">
                  {d && <div className="text-2xs text-ink-faint">{d.getDate()}</div>}
                  <div className="space-y-1 mt-1">
                    {hits.map((it) => (
                      <Link key={it.event_id} to={`/cases/${it.case_file_id}`}
                        className="block text-2xs px-1 py-0.5 bg-oxblood-wash text-oxblood rounded-sm truncate"
                        title={`${it.case_title}${it.purpose ? ' · ' + it.purpose : ''}`}>
                        {it.case_title}
                      </Link>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>

          <div>
            <div className="eyebrow mb-3">Agenda</div>
            <div className="border border-rule divide-y divide-rule">
              {items.map((it) => (
                <Link key={it.event_id} to={`/cases/${it.case_file_id}`}
                  className="bg-surface flex items-center gap-4 px-5 py-3 hover:bg-paper-deep/40">
                  <span className="text-sm font-medium text-oxblood w-28 shrink-0">{it.event_date}</span>
                  <span className="text-sm text-ink flex-1 truncate">{it.case_title}</span>
                  <span className="text-2xs uppercase tracking-eyebrow text-ink-muted">{it.purpose}</span>
                  <span className="text-xs text-ink-muted w-32 truncate text-right">{it.client_name}</span>
                </Link>
              ))}
              {items.length === 0 && <div className="bg-surface p-10 text-center text-sm text-ink-muted">No hearings this month.</div>}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
```

- [ ] **Step 3: Build**

Run: `cd frontend && npm run build`
Expected: build succeeds, no TypeScript errors.

- [ ] **Step 4: Stage (do NOT commit)**

```bash
git add frontend/src/api.ts frontend/src/pages/CaseCalendar.tsx
```

---

## Self-Review

**Spec coverage (against `2026-06-25-case-system-ux-design.md` §G + §D next-date):**
- Hearings are the source of truth; `purpose`/`outcome` on hearing events → Task 1. ✓
- `next_hearing_date` derived (soonest future hearing), kept in sync on event add/update/delete + endpoints → Task 1. ✓
- Inline header next-date control → Task 4 Step 4 (`set_next_date`). ✓
- "Record proceedings" = current outcome + new next hearing in one step → Tasks 2 + 4; rail action live → Task 2 Step 3 + Task 4 Step 3. ✓
- Calendar = month + agenda over hearings, click-through → Tasks 3 + 5. ✓
- `/meta` `hearing_purposes` → Task 2 Step 4. ✓

**Deferred-by-design:** reminders/notifications (a later phase). The proceedings modal disposes the hearing matching the current `next_hearing_date` (passes `current_event_id`); if none exists it just schedules the next date.

**Placeholder scan:** none.

**Type consistency:** `CaseEvent.purpose/outcome` align across model `to_dict`, events API, FE interface, calendar payload, and proceedings response. `recordProceedings` returns `{case_file, next_event}` matching the backend. `CalendarItem` matches the calendar endpoint dict. `set_next_date`/`recompute_next_hearing_date` keep `next_hearing_date` derived everywhere.
