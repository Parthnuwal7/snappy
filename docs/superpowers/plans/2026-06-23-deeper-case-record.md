# Deeper Case Record Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. Steps use checkbox (`- [ ]`).

**Goal:** Add stage-progression history, fee/expense tracking with a financial summary, and a tabbed case-detail layout.

**Architecture:** Two new firm-scoped tables (`case_stage_changes` audit log, `case_expenses` ledger) + an `agreed_fee` column on case files. Stage changes are auto-recorded on create/update/move. A financials endpoint aggregates expenses and linked invoices. Frontend reorganizes the case page into tabs.

**Tech Stack:** Flask, SQLAlchemy, React+TS, TanStack Query.

## Global Constraints

- Firm-scoped; stage history read-only (gated `case_files.read`); expense writes gate `case_files.update`. No new RBAC module.
- Money = `Numeric(12,2)`, serialized via `_money`.
- Migration `012` delivered for Parth; **no git commits** — end each task at green.

---

### Task 1: Expense catalog

**Files:** Create `backend/app/case/expenses.py`; Test `backend/tests/test_expense_catalog.py`

- [ ] **Step 1: Failing test**

```python
# backend/tests/test_expense_catalog.py
from app.case.expenses import (
    EXPENSE_CATEGORIES, EXPENSE_CATEGORY_KEYS, DEFAULT_EXPENSE_CATEGORY,
    is_valid_expense_category,
)

def test_categories():
    assert {"court_fee", "filing", "travel", "professional", "misc"} <= EXPENSE_CATEGORY_KEYS
    assert all("label" in c for c in EXPENSE_CATEGORIES)

def test_default_and_validation():
    assert DEFAULT_EXPENSE_CATEGORY == "misc"
    assert is_valid_expense_category("court_fee")
    assert not is_valid_expense_category("bribe")
```

- [ ] **Step 2:** `cd backend && python -m pytest tests/test_expense_catalog.py -q` → FAIL (no module)

- [ ] **Step 3: Implement**

```python
# backend/app/case/expenses.py
"""Case expense category catalog."""

EXPENSE_CATEGORIES = [
    {"key": "court_fee",    "label": "Court fee"},
    {"key": "filing",       "label": "Filing / registry"},
    {"key": "travel",       "label": "Travel"},
    {"key": "professional", "label": "Professional / counsel"},
    {"key": "misc",         "label": "Miscellaneous"},
]
EXPENSE_CATEGORY_KEYS = {c["key"] for c in EXPENSE_CATEGORIES}
DEFAULT_EXPENSE_CATEGORY = "misc"


def is_valid_expense_category(key):
    return key in EXPENSE_CATEGORY_KEYS
```

- [ ] **Step 4:** rerun → PASS (2 passed)

---

### Task 2: Models + `agreed_fee`

**Files:** Modify `backend/app/models/case.py`, `backend/app/main.py`; Test `backend/tests/test_case_record_models.py`

**Produces:** `CaseStageChange` (`case_stage_changes`), `CaseExpense` (`case_expenses`), `CaseFile.agreed_fee`; `CaseFile.to_dict` includes `agreed_fee` (via `_money`).

- [ ] **Step 1: Failing test**

```python
# backend/tests/test_case_record_models.py
from datetime import date
from app.models.models import db, Client
from app.models.auth import User
from app.models.case import CaseFile, CaseStageChange, CaseExpense
from app.services.firm_service import provision_firm_for_user


def _case(app):
    with app.app_context():
        u = User(supabase_id='sb-r', email='r@firm.com')
        db.session.add(u); db.session.commit()
        firm = provision_firm_for_user(u, 'Acme')
        c = Client(firm_id=firm.id, created_by_user_id=u.id, name='X')
        db.session.add(c); db.session.commit()
        cf = CaseFile(firm_id=firm.id, created_by_user_id=u.id,
                      case_number='CF/2026/0001', title='M', client_id=c.id,
                      agreed_fee=50000)
        db.session.add(cf); db.session.commit()
        return firm.id, u.id, cf.id


def test_agreed_fee_serialized_as_float(app):
    firm_id, uid, cf_id = _case(app)
    with app.app_context():
        assert CaseFile.query.get(cf_id).to_dict()['agreed_fee'] == 50000.0


def test_stage_change_and_expense_cascade(app):
    firm_id, uid, cf_id = _case(app)
    with app.app_context():
        db.session.add(CaseStageChange(firm_id=firm_id, case_file_id=cf_id,
                                       from_stage=None, to_stage='intake', changed_by_user_id=uid))
        db.session.add(CaseExpense(firm_id=firm_id, case_file_id=cf_id,
                                   expense_date=date(2026, 6, 1), description='Court fee',
                                   category='court_fee', amount=1500, created_by_user_id=uid))
        db.session.commit()
        assert CaseExpense.query.first().to_dict()['amount'] == 1500.0
        cf = CaseFile.query.get(cf_id)
        db.session.delete(cf); db.session.commit()
        assert CaseStageChange.query.filter_by(case_file_id=cf_id).count() == 0
        assert CaseExpense.query.filter_by(case_file_id=cf_id).count() == 0
```

- [ ] **Step 2:** run → FAIL (import error)

- [ ] **Step 3a:** In `backend/app/models/case.py`, add `agreed_fee` to `CaseFile` after `position`:

```python
    agreed_fee = db.Column(db.Numeric(12, 2))
```

Add `_money` to the import line at top: change `from app.models.models import db` to `from app.models.models import db, _money`.

In `CaseFile.to_dict`, after `'position': self.position,` add:

```python
            'agreed_fee': _money(self.agreed_fee),
```

Add cascade relationships on `CaseFile` (next to `documents`):

```python
    stage_changes = db.relationship('CaseStageChange', back_populates='case_file',
                                    cascade='all, delete-orphan')
    expenses = db.relationship('CaseExpense', back_populates='case_file',
                               cascade='all, delete-orphan')
```

At end of file add:

```python
class CaseStageChange(db.Model):
    __tablename__ = 'case_stage_changes'

    id = db.Column(db.Integer, primary_key=True)
    firm_id = db.Column(db.Integer, db.ForeignKey('firms.id'), index=True)
    case_file_id = db.Column(db.Integer, db.ForeignKey('case_files.id'), index=True)
    from_stage = db.Column(db.String(40))
    to_stage = db.Column(db.String(40))
    changed_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    changed_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    case_file = db.relationship('CaseFile', back_populates='stage_changes')

    def to_dict(self):
        return {
            'id': self.id,
            'case_file_id': self.case_file_id,
            'from_stage': self.from_stage,
            'to_stage': self.to_stage,
            'changed_by_user_id': self.changed_by_user_id,
            'changed_at': self.changed_at.isoformat() if self.changed_at else None,
        }


class CaseExpense(db.Model):
    __tablename__ = 'case_expenses'

    id = db.Column(db.Integer, primary_key=True)
    firm_id = db.Column(db.Integer, db.ForeignKey('firms.id'), index=True)
    case_file_id = db.Column(db.Integer, db.ForeignKey('case_files.id'), index=True)
    expense_date = db.Column(db.Date)
    description = db.Column(db.String(300), nullable=False)
    category = db.Column(db.String(40), default='misc')
    amount = db.Column(db.Numeric(12, 2))
    created_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    case_file = db.relationship('CaseFile', back_populates='expenses')

    def to_dict(self):
        return {
            'id': self.id,
            'firm_id': self.firm_id,
            'case_file_id': self.case_file_id,
            'expense_date': self.expense_date.isoformat() if self.expense_date else None,
            'description': self.description,
            'category': self.category,
            'amount': _money(self.amount),
            'created_by_user_id': self.created_by_user_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
```

- [ ] **Step 3b:** In `backend/app/main.py`, extend the case import:

```python
        from app.models.case import CaseFile, CaseParty, CaseEvent, CaseDocument, CaseStageChange, CaseExpense  # ensure case tables are created
```

- [ ] **Step 4:** run → PASS (2 passed)

---

### Task 3: Stage-change recorder

**Files:** Modify `backend/app/services/case_service.py`; Test `backend/tests/test_stage_recorder.py`

**Produces:** `record_stage_change(case_file, from_stage, to_stage, user_id) -> CaseStageChange` (adds to session, no commit).

- [ ] **Step 1: Failing test**

```python
# backend/tests/test_stage_recorder.py
from app.models.models import db, Client
from app.models.auth import User
from app.models.case import CaseFile, CaseStageChange
from app.services.firm_service import provision_firm_for_user
from app.services.case_service import record_stage_change


def test_record_stage_change_adds_row(app):
    with app.app_context():
        u = User(supabase_id='sb-s', email='s@firm.com')
        db.session.add(u); db.session.commit()
        firm = provision_firm_for_user(u, 'Acme')
        c = Client(firm_id=firm.id, created_by_user_id=u.id, name='X')
        db.session.add(c); db.session.commit()
        cf = CaseFile(firm_id=firm.id, created_by_user_id=u.id,
                      case_number='CF/2026/0001', title='M', client_id=c.id)
        db.session.add(cf); db.session.commit()
        record_stage_change(cf, 'intake', 'filed', u.id)
        db.session.commit()
        row = CaseStageChange.query.filter_by(case_file_id=cf.id).first()
        assert row.from_stage == 'intake' and row.to_stage == 'filed'
        assert row.firm_id == firm.id
```

- [ ] **Step 2:** run → FAIL (no attribute)

- [ ] **Step 3:** Append to `backend/app/services/case_service.py`:

```python
def record_stage_change(case_file, from_stage, to_stage, user_id):
    """Append a stage-change audit row for a case. Caller commits."""
    from app.models.case import CaseStageChange
    change = CaseStageChange(
        firm_id=case_file.firm_id, case_file_id=case_file.id,
        from_stage=from_stage, to_stage=to_stage, changed_by_user_id=user_id)
    db.session.add(change)
    return change
```

Add `from app.models.models import db` at the top if not present (it imports `CaseFile` already; ensure `db` is imported — add `from app.models.models import db`).

- [ ] **Step 4:** run → PASS

---

### Task 4: Wire recording + `agreed_fee` + meta into case API

**Files:** Modify `backend/app/api/case_files.py`; Test `backend/tests/test_case_record_api.py` (stage-history + agreed_fee + meta parts)

- [ ] **Step 1: Failing test**

```python
# backend/tests/test_case_record_api.py
from app.models.models import db, Client
from app.models.auth import User


def _cid(client, firm_id):
    with client.application.app_context():
        c = Client(firm_id=firm_id, created_by_user_id=User.query.filter_by(
            email='owner@firm.com').first().id, name='X')
        db.session.add(c); db.session.commit()
        return c.id


def test_meta_includes_expense_categories(client, make_owner):
    headers, _ = make_owner()
    body = client.get('/api/v1/case-files/meta', headers=headers).get_json()
    assert {c['key'] for c in body['expense_categories']} >= {'court_fee', 'travel', 'misc'}


def test_create_records_initial_stage_and_agreed_fee(client, make_owner):
    headers, firm_id = make_owner()
    cid = _cid(client, firm_id)
    created = client.post('/api/v1/case-files', headers=headers,
                          json={'title': 'M', 'client_id': cid, 'agreed_fee': 50000}).get_json()
    assert created['agreed_fee'] == 50000.0
    hist = client.get(f"/api/v1/case-files/{created['id']}/stage-history", headers=headers).get_json()
    assert len(hist) == 1
    assert hist[0]['from_stage'] is None and hist[0]['to_stage'] == 'intake'


def test_move_and_patch_record_stage_changes(client, make_owner):
    headers, firm_id = make_owner()
    cid = _cid(client, firm_id)
    cf = client.post('/api/v1/case-files', headers=headers, json={'title': 'M', 'client_id': cid}).get_json()
    client.patch(f"/api/v1/case-files/{cf['id']}/move", headers=headers, json={'stage': 'filed'})
    client.patch(f"/api/v1/case-files/{cf['id']}", headers=headers, json={'stage': 'in_hearing'})
    client.patch(f"/api/v1/case-files/{cf['id']}", headers=headers, json={'title': 'no stage change'})
    hist = client.get(f"/api/v1/case-files/{cf['id']}/stage-history", headers=headers).get_json()
    # initial + move + patch = 3 (the title-only patch records nothing)
    assert [h['to_stage'] for h in hist] == ['intake', 'filed', 'in_hearing']
```

- [ ] **Step 2:** run → FAIL (no expense_categories / no stage-history route)

- [ ] **Step 3a:** In `backend/app/api/case_files.py` imports, add:

```python
from app.case.expenses import EXPENSE_CATEGORIES
from app.models.case import CaseFile, CaseParty, CaseStageChange
from app.services.case_service import generate_case_number, record_stage_change
```
(Replace the existing `from app.models.case import CaseFile, CaseParty` and the existing `from app.services.case_service import generate_case_number` lines accordingly.)

- [ ] **Step 3b:** Add `expense_categories` to the meta return:

```python
    return jsonify({'stages': STAGES, 'event_kinds': EVENT_KINDS,
                    'priorities': PRIORITIES, 'doc_types': DOC_TYPES,
                    'expense_categories': EXPENSE_CATEGORIES})
```

- [ ] **Step 3c:** In `create_case_file`, accept `agreed_fee` — add to the `CaseFile(...)` kwargs:

```python
        agreed_fee=data.get('agreed_fee'),
```
After `db.session.add(case_file)` and before `db.session.commit()`, flush then record the initial stage:

```python
    db.session.add(case_file)
    db.session.flush()
    record_stage_change(case_file, None, case_file.stage, g.user.id)
    db.session.commit()
```
(Replace the existing `db.session.add(case_file)\n    db.session.commit()` block.)

- [ ] **Step 3d:** In `update_case_file`, capture the prior stage and record on change. Replace the `if 'stage' in data:` block with:

```python
    if 'stage' in data:
        if not is_valid_stage(data['stage']):
            return jsonify({'error': 'Invalid stage'}), 400
        if data['stage'] != case_file.stage:
            record_stage_change(case_file, case_file.stage, data['stage'], g.user.id)
            case_file.stage = data['stage']
```
Add `agreed_fee` to the simple-field loop list (so PATCH updates it):

```python
    for field in ('title', 'matter_type', 'court', 'court_case_number',
                  'jurisdiction', 'act_section', 'opposing_counsel',
                  'description', 'handling_advocate_user_id', 'agreed_fee'):
```

- [ ] **Step 3e:** In `move_case_file`, record on change. Replace `case_file.stage = stage` with:

```python
    if stage != case_file.stage:
        record_stage_change(case_file, case_file.stage, stage, g.user.id)
        case_file.stage = stage
```

- [ ] **Step 3f:** Add the stage-history route at the end of `case_files.py`:

```python
@bp.route('/case-files/<int:case_id>/stage-history', methods=['GET'])
@jwt_required
@require_permission('case_files.read')
def stage_history(case_id):
    case_file = CaseFile.query.filter_by(id=case_id, firm_id=g.firm_id).first()
    if not case_file:
        return jsonify({'error': 'Case not found'}), 404
    rows = (CaseStageChange.query.filter_by(case_file_id=case_id)
            .order_by(CaseStageChange.changed_at.asc(), CaseStageChange.id.asc()).all())
    return jsonify([r.to_dict() for r in rows])
```

- [ ] **Step 4:** run → PASS (3 passed)

---

### Task 5: Expenses + financials API

**Files:** Create `backend/app/api/case_expenses.py`; Modify `backend/app/main.py`; Test `backend/tests/test_case_financials_api.py`

**Produces routes:** `GET/POST /case-files/<id>/expenses`, `PATCH/DELETE /case-expenses/<id>`, `GET /case-files/<id>/financials`.

- [ ] **Step 1: Failing test**

```python
# backend/tests/test_case_financials_api.py
from app.models.models import db, Client
from app.models.auth import User


def _cid(client, firm_id):
    with client.application.app_context():
        c = Client(firm_id=firm_id, created_by_user_id=User.query.filter_by(
            email='owner@firm.com').first().id, name='X')
        db.session.add(c); db.session.commit()
        return c.id


def _case(client, headers, firm_id, fee=None):
    cid = _cid(client, firm_id)
    return client.post('/api/v1/case-files', headers=headers,
                       json={'title': 'M', 'client_id': cid, 'agreed_fee': fee}).get_json()['id'], cid


def test_expense_crud(client, make_owner):
    headers, firm_id = make_owner()
    case_id, _ = _case(client, headers, firm_id)
    e = client.post(f'/api/v1/case-files/{case_id}/expenses', headers=headers,
                    json={'expense_date': '2026-06-01', 'description': 'Court fee',
                          'category': 'court_fee', 'amount': 1500}).get_json()
    assert e['amount'] == 1500.0
    lst = client.get(f'/api/v1/case-files/{case_id}/expenses', headers=headers).get_json()
    assert len(lst) == 1
    client.patch(f"/api/v1/case-expenses/{e['id']}", headers=headers, json={'amount': 2000})
    assert client.get(f'/api/v1/case-files/{case_id}/expenses', headers=headers).get_json()[0]['amount'] == 2000.0
    assert client.delete(f"/api/v1/case-expenses/{e['id']}", headers=headers).status_code == 200


def test_financials_summary(client, make_owner):
    headers, firm_id = make_owner()
    case_id, cid = _case(client, headers, firm_id, fee=50000)
    client.post(f'/api/v1/case-files/{case_id}/expenses', headers=headers,
                json={'expense_date': '2026-06-01', 'description': 'fee', 'category': 'court_fee', 'amount': 1500})
    # one paid invoice (25000) + one draft (16000) linked to the case
    inv = client.post('/api/v1/invoices', headers=headers, json={
        'client_id': cid, 'case_file_id': case_id, 'invoice_date': '2026-06-01',
        'items': [{'description': 'x', 'quantity': 1, 'rate': 25000, 'amount': 25000}]}).get_json()
    client.put(f"/api/v1/invoices/{inv['id']}", headers=headers, json={'status': 'paid'})
    client.post('/api/v1/invoices', headers=headers, json={
        'client_id': cid, 'case_file_id': case_id, 'invoice_date': '2026-06-02',
        'items': [{'description': 'y', 'quantity': 1, 'rate': 16000, 'amount': 16000}]})
    fin = client.get(f'/api/v1/case-files/{case_id}/financials', headers=headers).get_json()
    assert fin['agreed_fee'] == 50000.0
    assert fin['total_expenses'] == 1500.0
    assert fin['total_invoiced'] == 41000.0
    assert fin['total_paid'] == 25000.0
    assert fin['outstanding'] == 16000.0


def test_expenses_isolated(client, make_owner):
    headers, firm_id = make_owner()
    headers_b, _ = make_owner(supabase_id='sb-b', email='b@firm.com', firm_name='B')
    case_id, _ = _case(client, headers, firm_id)
    e = client.post(f'/api/v1/case-files/{case_id}/expenses', headers=headers,
                    json={'expense_date': '2026-06-01', 'description': 'x', 'amount': 100}).get_json()
    assert client.patch(f"/api/v1/case-expenses/{e['id']}", headers=headers_b, json={'amount': 1}).status_code == 404
    assert client.get(f'/api/v1/case-files/{case_id}/financials', headers=headers_b).status_code == 404
```

- [ ] **Step 2:** run → FAIL (404s)

- [ ] **Step 3a: Create the blueprint**

```python
# backend/app/api/case_expenses.py
"""Case expenses + financial summary — firm-scoped, gated by case_files perms."""
from datetime import datetime
from flask import Blueprint, request, jsonify, g
from sqlalchemy import func
from app.models.models import db, Invoice, _money
from app.models.case import CaseFile, CaseExpense
from app.middleware.jwt_auth import jwt_required
from app.middleware.firm_context import require_permission
from app.case.expenses import DEFAULT_EXPENSE_CATEGORY, is_valid_expense_category

bp = Blueprint('case_expenses', __name__)


def _parse_date(v):
    return datetime.fromisoformat(v).date() if v else None


def _case_or_404(case_id):
    return CaseFile.query.filter_by(id=case_id, firm_id=g.firm_id).first()


@bp.route('/case-files/<int:case_id>/expenses', methods=['GET'])
@jwt_required
@require_permission('case_files.read')
def list_expenses(case_id):
    if not _case_or_404(case_id):
        return jsonify({'error': 'Case not found'}), 404
    rows = (CaseExpense.query.filter_by(case_file_id=case_id)
            .order_by(CaseExpense.expense_date.desc(), CaseExpense.id.desc()).all())
    return jsonify([r.to_dict() for r in rows])


@bp.route('/case-files/<int:case_id>/expenses', methods=['POST'])
@jwt_required
@require_permission('case_files.update')
def add_expense(case_id):
    if not _case_or_404(case_id):
        return jsonify({'error': 'Case not found'}), 404
    data = request.get_json() or {}
    description = (data.get('description') or '').strip()
    if not description:
        return jsonify({'error': 'Description is required'}), 400
    category = data.get('category') or DEFAULT_EXPENSE_CATEGORY
    if not is_valid_expense_category(category):
        return jsonify({'error': 'Invalid category'}), 400
    exp = CaseExpense(
        firm_id=g.firm_id, case_file_id=case_id,
        expense_date=_parse_date(data.get('expense_date')),
        description=description, category=category,
        amount=data.get('amount') or 0, created_by_user_id=g.user.id)
    db.session.add(exp)
    db.session.commit()
    return jsonify(exp.to_dict()), 201


@bp.route('/case-expenses/<int:expense_id>', methods=['PATCH'])
@jwt_required
@require_permission('case_files.update')
def update_expense(expense_id):
    exp = CaseExpense.query.filter_by(id=expense_id, firm_id=g.firm_id).first()
    if not exp:
        return jsonify({'error': 'Expense not found'}), 404
    data = request.get_json() or {}
    if 'description' in data:
        exp.description = (data['description'] or '').strip() or exp.description
    if 'category' in data:
        if not is_valid_expense_category(data['category']):
            return jsonify({'error': 'Invalid category'}), 400
        exp.category = data['category']
    if 'amount' in data:
        exp.amount = data['amount'] or 0
    if 'expense_date' in data:
        exp.expense_date = _parse_date(data['expense_date'])
    db.session.commit()
    return jsonify(exp.to_dict())


@bp.route('/case-expenses/<int:expense_id>', methods=['DELETE'])
@jwt_required
@require_permission('case_files.update')
def delete_expense(expense_id):
    exp = CaseExpense.query.filter_by(id=expense_id, firm_id=g.firm_id).first()
    if not exp:
        return jsonify({'error': 'Expense not found'}), 404
    db.session.delete(exp)
    db.session.commit()
    return jsonify({'message': 'Expense deleted'})


@bp.route('/case-files/<int:case_id>/financials', methods=['GET'])
@jwt_required
@require_permission('case_files.read')
def financials(case_id):
    case_file = _case_or_404(case_id)
    if not case_file:
        return jsonify({'error': 'Case not found'}), 404
    total_expenses = db.session.query(func.coalesce(func.sum(CaseExpense.amount), 0)) \
        .filter(CaseExpense.case_file_id == case_id).scalar()
    total_invoiced = db.session.query(func.coalesce(func.sum(Invoice.total), 0)) \
        .filter(Invoice.case_file_id == case_id).scalar()
    total_paid = db.session.query(func.coalesce(func.sum(Invoice.total), 0)) \
        .filter(Invoice.case_file_id == case_id, Invoice.status == 'paid').scalar()
    return jsonify({
        'agreed_fee': _money(case_file.agreed_fee),
        'total_expenses': _money(total_expenses),
        'total_invoiced': _money(total_invoiced),
        'total_paid': _money(total_paid),
        'outstanding': _money(total_invoiced - total_paid),
    })
```

- [ ] **Step 3b:** Register in `backend/app/main.py`: add `case_expenses` to the `from app.api import ...` line and:

```python
    app.register_blueprint(case_expenses.bp, url_prefix='/api/v1')
```

- [ ] **Step 4:** run → PASS (3 passed)

---

### Task 6: Migration `012`

**Files:** Create `backend/migrations/012_case_record_depth.sql`

- [ ] **Step 1:** Write:

```sql
-- 012_case_record_depth.sql — agreed_fee + stage history + expense ledger.
-- Additive, non-destructive. Apply in the Supabase SQL editor.
BEGIN;

ALTER TABLE public.case_files ADD COLUMN IF NOT EXISTS agreed_fee NUMERIC(12,2);

CREATE TABLE IF NOT EXISTS public.case_stage_changes (
  id SERIAL PRIMARY KEY,
  firm_id INTEGER REFERENCES public.firms(id),
  case_file_id INTEGER REFERENCES public.case_files(id) ON DELETE CASCADE,
  from_stage VARCHAR(40),
  to_stage VARCHAR(40),
  changed_by_user_id INTEGER REFERENCES public.users(id),
  changed_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_case_stage_changes_case_file_id ON public.case_stage_changes (case_file_id);
CREATE INDEX IF NOT EXISTS ix_case_stage_changes_firm_id ON public.case_stage_changes (firm_id);

CREATE TABLE IF NOT EXISTS public.case_expenses (
  id SERIAL PRIMARY KEY,
  firm_id INTEGER REFERENCES public.firms(id),
  case_file_id INTEGER REFERENCES public.case_files(id) ON DELETE CASCADE,
  expense_date DATE,
  description VARCHAR(300) NOT NULL,
  category VARCHAR(40) DEFAULT 'misc',
  amount NUMERIC(12,2),
  created_by_user_id INTEGER REFERENCES public.users(id),
  created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_case_expenses_case_file_id ON public.case_expenses (case_file_id);
CREATE INDEX IF NOT EXISTS ix_case_expenses_firm_id ON public.case_expenses (firm_id);

COMMIT;
```

- [ ] **Step 2:** Confirm columns match `app/models/case.py`.

---

### Task 7: Frontend API client

**Files:** Modify `frontend/src/api.ts`

- [ ] **Step 1:** After `CaseDocument` add:

```typescript
export interface CaseStageChange {
  id: number;
  case_file_id: number;
  from_stage?: string | null;
  to_stage: string;
  changed_by_user_id?: number;
  changed_at?: string;
}

export interface CaseExpense {
  id: number;
  firm_id: number;
  case_file_id: number;
  expense_date?: string | null;
  description: string;
  category: string;
  amount: number;
  created_by_user_id?: number;
  created_at?: string;
}

export interface CaseFinancials {
  agreed_fee: number | null;
  total_expenses: number;
  total_invoiced: number;
  total_paid: number;
  outstanding: number;
}
```

Add `agreed_fee?: number | null;` to the `CaseFile` interface (after `description`).
Add `expense_categories: { key: string; label: string }[];` to `CaseMeta`.

- [ ] **Step 2:** In the `api` object, after `deleteCaseDocument`, add:

```typescript
  getStageHistory: (caseId: number) =>
    fetchAPI<CaseStageChange[]>(`${API_BASE_URL}/case-files/${caseId}/stage-history`),

  getCaseFinancials: (caseId: number) =>
    fetchAPI<CaseFinancials>(`${API_BASE_URL}/case-files/${caseId}/financials`),

  getCaseExpenses: (caseId: number) =>
    fetchAPI<CaseExpense[]>(`${API_BASE_URL}/case-files/${caseId}/expenses`),

  addCaseExpense: (caseId: number, data: { expense_date?: string; description: string; category: string; amount: number }) =>
    fetchAPI<CaseExpense>(`${API_BASE_URL}/case-files/${caseId}/expenses`, {
      method: 'POST', body: JSON.stringify(data),
    }),

  updateCaseExpense: (expenseId: number, data: Partial<CaseExpense>) =>
    fetchAPI<CaseExpense>(`${API_BASE_URL}/case-expenses/${expenseId}`, {
      method: 'PATCH', body: JSON.stringify(data),
    }),

  deleteCaseExpense: (expenseId: number) =>
    fetchAPI<{ message: string }>(`${API_BASE_URL}/case-expenses/${expenseId}`, { method: 'DELETE' }),
```

- [ ] **Step 3:** `cd frontend && npm run build` → clean.

---

### Task 8: Tabbed case detail + Fees & Billing

**Files:** Modify `frontend/src/pages/CaseDetail.tsx`

This restructures the page into tabs. Full replacement of the page body's main grid with a tab switcher; the existing header + edit modal stay. See the detailed wiring below.

- [ ] **Step 1:** Add a tab state near the other `useState`s:

```tsx
  const [tab, setTab] = useState<'overview' | 'timeline' | 'documents' | 'fees'>('overview');
```

- [ ] **Step 2:** Add the fees data + expense form state + mutations (near the document mutations):

```tsx
  const { data: financials } = useQuery({
    queryKey: ['case-financials', caseId], queryFn: () => api.getCaseFinancials(caseId),
  });
  const { data: stageHistory = [] } = useQuery({
    queryKey: ['case-stage-history', caseId], queryFn: () => api.getStageHistory(caseId),
  });
  const { data: expenses = [] } = useQuery({
    queryKey: ['case-expenses', caseId], queryFn: () => api.getCaseExpenses(caseId),
  });

  const [exp, setExp] = useState({ expense_date: today(), description: '', category: 'misc', amount: 0 });
  const addExpense = useMutation({
    mutationFn: () => api.addCaseExpense(caseId, exp),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['case-expenses', caseId] });
      queryClient.invalidateQueries({ queryKey: ['case-financials', caseId] });
      setExp({ expense_date: today(), description: '', category: 'misc', amount: 0 });
      showToast('Expense added');
    },
    onError: (e) => showToast(errMsg(e), 'error'),
  });
  const deleteExpense = useMutation({
    mutationFn: (id: number) => api.deleteCaseExpense(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['case-expenses', caseId] });
      queryClient.invalidateQueries({ queryKey: ['case-financials', caseId] });
    },
    onError: (e) => showToast(errMsg(e), 'error'),
  });
  const money = (n?: number | null) => n == null ? '—' : '₹' + n.toLocaleString('en-IN');
```

- [ ] **Step 3:** Replace the existing `<div className="grid grid-cols-1 lg:grid-cols-3 gap-8">...</div>` main block with a tab bar + per-tab content. Tab bar:

```tsx
      <div className="flex gap-1 border-b border-rule mb-6">
        {(['overview', 'timeline', 'documents', 'fees'] as const).map((t) => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm capitalize border-b-2 -mb-px transition-colors ${
              tab === t ? 'border-oxblood text-ink' : 'border-transparent text-ink-muted hover:text-ink'}`}>
            {t === 'fees' ? 'Fees & billing' : t}
          </button>
        ))}
      </div>
```

Then render each tab. **Overview** = the facts grid (move the existing `<dl>` here if not in the header) + description + parties + a progression list:

```tsx
      {tab === 'overview' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div className="lg:col-span-2 space-y-6">
            {caseFile.description && <p className="text-sm text-ink-muted whitespace-pre-wrap">{caseFile.description}</p>}
            <div>
              <div className="eyebrow mb-3">Progression</div>
              <ol className="space-y-2">
                {stageHistory.map((h) => (
                  <li key={h.id} className="text-sm text-ink-muted">
                    <span className="font-mono text-2xs text-ink-faint">{h.changed_at?.slice(0, 10)}</span>{' '}
                    {h.from_stage ? `${h.from_stage} → ` : 'opened at '}<span className="text-ink">{h.to_stage}</span>
                  </li>
                ))}
                {stageHistory.length === 0 && <li className="text-sm text-ink-muted">No history.</li>}
              </ol>
            </div>
          </div>
          <aside>
            <div className="eyebrow mb-3">Parties</div>
            <div className="border border-rule divide-y divide-rule">
              {(caseFile.parties ?? []).map((p) => (
                <div key={p.id} className="bg-surface px-4 py-2.5">
                  <div className="text-sm text-ink">{p.name}</div>
                  <div className="text-2xs uppercase tracking-eyebrow text-ink-muted">{p.role}</div>
                </div>
              ))}
              {(caseFile.parties ?? []).length === 0 && <div className="bg-surface px-4 py-3 text-sm text-ink-muted">No parties.</div>}
            </div>
          </aside>
        </div>
      )}
```

**Timeline** tab = the existing timeline `<section>` (the add-step form + `<ol>`), wrapped in `{tab === 'timeline' && ( ... )}`.

**Documents** tab = the existing Documents panel block, wrapped in `{tab === 'documents' && ( ... )}`.

**Fees** tab = financial summary + expense ledger + invoices:

```tsx
      {tab === 'fees' && (
        <div className="space-y-8">
          <div className="grid grid-cols-2 md:grid-cols-5 gap-px bg-rule border border-rule">
            {[['Agreed fee', financials?.agreed_fee], ['Expenses', financials?.total_expenses],
              ['Invoiced', financials?.total_invoiced], ['Paid', financials?.total_paid],
              ['Outstanding', financials?.outstanding]].map(([label, val]) => (
              <div key={label as string} className="bg-surface p-4">
                <div className="text-2xs uppercase tracking-eyebrow text-ink-faint">{label as string}</div>
                <div className="font-display text-xl text-ink mt-1 tabular">{money(val as number)}</div>
              </div>
            ))}
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            <div className="lg:col-span-2">
              <div className="eyebrow mb-3">Expenses</div>
              {canUpdate && (
                <form onSubmit={(e) => { e.preventDefault(); addExpense.mutate(); }} className="card p-3 mb-3 flex flex-wrap gap-2 items-end">
                  <input type="date" value={exp.expense_date} onChange={(e) => setExp({ ...exp, expense_date: e.target.value })} className="field-input w-36" />
                  <input value={exp.description} placeholder="Description" onChange={(e) => setExp({ ...exp, description: e.target.value })} className="field-input flex-1 min-w-[140px]" />
                  <select value={exp.category} onChange={(e) => setExp({ ...exp, category: e.target.value })} className="field-select w-36">
                    {(meta?.expense_categories ?? []).map((c) => <option key={c.key} value={c.key}>{c.label}</option>)}
                  </select>
                  <input type="number" value={exp.amount} onChange={(e) => setExp({ ...exp, amount: Number(e.target.value) })} className="field-input w-28 tabular" placeholder="₹" />
                  <button type="submit" className="btn-primary" disabled={!exp.description || addExpense.isPending}>Add</button>
                </form>
              )}
              <div className="border border-rule divide-y divide-rule">
                {expenses.map((x) => (
                  <div key={x.id} className="bg-surface flex items-center gap-3 px-4 py-2.5 group">
                    <span className="text-2xs font-mono text-ink-faint w-20">{x.expense_date}</span>
                    <span className="text-sm text-ink flex-1">{x.description}</span>
                    <span className="text-2xs uppercase tracking-eyebrow text-ink-muted">{x.category}</span>
                    <span className="text-sm tabular text-ink">{money(x.amount)}</span>
                    {canUpdate && <button onClick={() => deleteExpense.mutate(x.id)} className="p-1 text-ink-muted hover:text-oxblood opacity-0 group-hover:opacity-100"><Trash2 size={13} /></button>}
                  </div>
                ))}
                {expenses.length === 0 && <div className="bg-surface px-4 py-3 text-sm text-ink-muted">No expenses logged.</div>}
              </div>
            </div>
            <aside>
              <div className="eyebrow mb-3">Invoices</div>
              <div className="border border-rule divide-y divide-rule">
                {invoices.map((inv) => (
                  <div key={inv.id} className="bg-surface flex items-center gap-2 px-4 py-2.5">
                    <FileText size={13} className="text-ink-faint" />
                    <span className="text-sm text-ink flex-1">{inv.invoice_number}</span>
                    <span className="text-sm tabular text-ink-muted">{money(inv.total)}</span>
                  </div>
                ))}
                {invoices.length === 0 && <div className="bg-surface px-4 py-3 text-sm text-ink-muted">No invoices.</div>}
              </div>
              <Link to={`/invoices/new?case_file_id=${caseId}&client_id=${caseFile.client_id}`} className="btn-ghost mt-3 inline-flex"><Plus size={14} /> New invoice</Link>
            </aside>
          </div>
        </div>
      )}
```

- [ ] **Step 4:** Add an **Agreed fee** input to the edit modal (next to Priority), and include `agreed_fee` in `saveCase`'s payload:

```tsx
                  <div>
                    <label className="field-label">Agreed fee (₹)</label>
                    <input type="number" value={draft.agreed_fee ?? ''} onChange={(e) => setField('agreed_fee', e.target.value ? Number(e.target.value) : null)} className="field-input tabular" />
                  </div>
```
And in `saveCase.mutationFn`'s object add `agreed_fee: draft.agreed_fee ?? null,`.

- [ ] **Step 5:** Remove the now-duplicated parties/billing blocks that moved into tabs (the old `<aside>` Parties + Billing in the previous single-column layout) to avoid double render. Keep the header facts `<dl>` in the header.

- [ ] **Step 6:** `cd frontend && npm run build` → clean.

---

### Task 9: Full regression

- [ ] `cd backend && python -m pytest -q` → all green.
- [ ] `cd frontend && npm run build` → clean.
- [ ] Hand `012_case_record_depth.sql` to Parth.

## Self-Review

- Spec coverage: catalog (T1), models+agreed_fee (T2), recorder (T3), recording+meta+agreed_fee+stage-history route (T4), expenses+financials (T5), migration (T6), FE client (T7), tabbed UI + fees (T8), regression (T9). All mapped.
- Type consistency: `record_stage_change`, `CaseStageChange`, `CaseExpense`, `agreed_fee`, `expense_categories`, `getCaseFinancials`, `total_invoiced/total_paid/outstanding` consistent across tasks.
- Git: no commits; each task gates on green.
