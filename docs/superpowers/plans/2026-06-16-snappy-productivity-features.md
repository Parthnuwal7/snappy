# Snappy Productivity Features Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add three productivity features to Snappy — recent-client chips in the composer, two-up (two-copies-per-page) PDF printing, and recurring invoices that auto-create drafts with in-app reminders.

**Architecture:** Backend is Flask + SQLAlchemy on Cloud Run, Postgres on Supabase, PDFs via ReportLab. Frontend is React + TypeScript + TanStack Query on Vercel. Recurring generation runs through a secret-gated HTTP endpoint hit by Cloud Scheduler (mirroring the existing `/keepalive` pattern) — never an in-process scheduler, because Cloud Run scales to zero. Pure logic (cadence math, two-up composition, the recurring run service) is unit-tested; thin JWT-gated HTTP handlers and React components are verified manually.

**Tech Stack:** Flask, SQLAlchemy, ReportLab (platypus + canvas), Postgres/Supabase, React 18, TypeScript, TanStack Query, Tailwind, lucide-react, pytest.

**Spec:** `docs/superpowers/specs/2026-06-16-snappy-productivity-features-design.md`

---

## Testing notes (read first)

- Run backend tests from `backend/`: `cd backend && python -m pytest tests/ -v`.
- `tests/conftest.py` provides `app`, `client`, and `db` fixtures against an in-memory SQLite DB. New tests for pure logic and services use the `app`/`db` app-context fixtures and construct ORM rows directly — they do **not** go through JWT-gated HTTP routes.
- New backend test files go in `backend/tests/`.
- Frontend has no test runner configured; frontend tasks are verified by `cd frontend && npm run build` (TypeScript compile) plus manual smoke notes.
- **Git:** the repo owner runs all git commits/pushes himself. Do **not** run `git commit`/`git push`. Where a step says "Commit", stage nothing and instead pause for the owner to commit, or simply leave the change in the working tree for review.

---

# Part A — Recent-client chips

**Goal:** When composing an invoice with no client selected and an empty search box, show the user's most-recently-billed clients as one-click chips.

## Task A1: Backend `/clients/recent` endpoint

**Files:**
- Modify: `backend/app/api/clients.py` (add route after `get_clients`, around line 53)
- Test: `backend/tests/test_clients_recent.py` (create)

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_clients_recent.py
"""Tests for the recent-clients query helper."""
from datetime import date
from app.models.models import db, Client, Invoice
from app.models.auth import User
from app.api.clients import recent_clients_for_user


def _make_user():
    user = User(supabase_id='sb-test-1', email='t@example.com')
    db.session.add(user)
    db.session.flush()
    return user


def test_recent_clients_orders_by_latest_invoice(app):
    with app.app_context():
        db.create_all()
        user = _make_user()
        a = Client(user_id=user.id, name='Alpha')
        b = Client(user_id=user.id, name='Beta')
        c = Client(user_id=user.id, name='Gamma (never billed)')
        db.session.add_all([a, b, c])
        db.session.flush()
        # Beta billed most recently, Alpha earlier. Gamma never billed.
        db.session.add(Invoice(user_id=user.id, invoice_number='INV/0001',
                               client_id=a.id, invoice_date=date(2026, 1, 1)))
        db.session.add(Invoice(user_id=user.id, invoice_number='INV/0002',
                               client_id=b.id, invoice_date=date(2026, 6, 1)))
        db.session.commit()

        result = recent_clients_for_user(user.id, limit=6)
        names = [c['name'] for c in result]
        assert names == ['Beta', 'Alpha']
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_clients_recent.py -v`
Expected: FAIL with `ImportError: cannot import name 'recent_clients_for_user'`

- [ ] **Step 3: Implement the helper and route**

Add to `backend/app/api/clients.py` (after the imports, the helper; after `get_clients`, the route):

```python
def recent_clients_for_user(user_id, limit=6):
    """Return the user's clients ordered by most recent invoice, capped at limit.

    Clients with no invoices are excluded. Returns a list of client dicts.
    """
    rows = (
        db.session.query(Client)
        .join(Invoice, Invoice.client_id == Client.id)
        .filter(Client.user_id == user_id)
        .group_by(Client.id)
        .order_by(func.max(Invoice.invoice_date).desc())
        .limit(limit)
        .all()
    )
    return [c.to_dict() for c in rows]
```

Add the imports at the top of the file:

```python
from app.models.models import db, Client, Invoice
from sqlalchemy import func
```

(Replace the existing `from app.models.models import db, Client` line.)

Add the route after `get_clients` (after line ~53):

```python
@bp.route('/clients/recent', methods=['GET'])
@jwt_required
def get_recent_clients():
    """Get the current user's most-recently-billed clients."""
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({'error': 'User not found'}), 401
    limit = request.args.get('limit', default=6, type=int)
    return jsonify(recent_clients_for_user(user_id, limit=limit))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_clients_recent.py -v`
Expected: PASS

> **Route-order note:** Flask matches `/clients/recent` against the `/clients/<int:client_id>` rule only if the converter matches; `recent` is not an int, so there is no collision. No reordering needed.

- [ ] **Step 5: Commit** (leave for owner — see Testing notes)

## Task A2: Frontend API method + types

**Files:**
- Modify: `frontend/src/api.ts`

- [ ] **Step 1: Add the API method**

In `frontend/src/api.ts`, inside the `api` object, after `getClient` (around line 161), add:

```typescript
  getRecentClients: (limit = 6) =>
    fetchAPI<Client[]>(`${API_ENDPOINTS.clients}/recent?limit=${limit}`),
```

- [ ] **Step 2: Verify compile**

Run: `cd frontend && npm run build`
Expected: build succeeds (no TypeScript errors).

- [ ] **Step 3: Commit** (leave for owner)

## Task A3: Render recent-client chips in the composer

**Files:**
- Modify: `frontend/src/pages/NewInvoice.tsx`

- [ ] **Step 1: Add the recent-clients query**

In `NewInvoice.tsx`, after the existing `clients` query (around line 80), add:

```typescript
  const { data: recentClients } = useQuery({
    queryKey: ['clients', 'recent'],
    queryFn: () => api.getRecentClients(6),
    enabled: !id,  // only when composing a brand-new invoice
  });
```

- [ ] **Step 2: Render chips above the search box**

In the `!selectedClient` branch, immediately inside the `<div>` that wraps the search label (around line 163, before the `<label className="field-label">`), insert:

```tsx
              {clientSearch.length === 0 && recentClients && recentClients.length > 0 && (
                <div className="mb-4">
                  <div className="eyebrow mb-2">Recent clients</div>
                  <div className="flex flex-wrap gap-2">
                    {recentClients.map((c) => (
                      <button
                        key={c.id}
                        type="button"
                        onClick={() => {
                          setSelectedClient(c);
                          setValue('client_id', c.id);
                          setValue('tax_rate', c.default_tax_rate);
                          setClientSearch('');
                        }}
                        className="px-3 py-1.5 text-sm border border-rule rounded-DEFAULT
                                   text-ink-soft hover:border-oxblood hover:text-oxblood
                                   bg-surface transition-colors"
                      >
                        {c.name}
                      </button>
                    ))}
                  </div>
                </div>
              )}
```

- [ ] **Step 3: Verify compile**

Run: `cd frontend && npm run build`
Expected: build succeeds.

- [ ] **Step 4: Manual smoke**

Start the app, open "New invoice". With at least one prior invoice in the DB, the recent-client chips appear above the search box; clicking one selects the client and hides the chips. Typing in search hides the chips. Editing an existing invoice (`/invoices/:id/edit`) shows no chips.

- [ ] **Step 5: Commit** (leave for owner)

---

# Part B — Two-up print (two copies per page)

**Goal:** Produce a single A4 page with two identical, upright copies of the half-page invoice, stacked top and bottom.

## Task B1: Extract the half-page element builder

**Files:**
- Modify: `backend/app/services/pdf_templates.py` (lines ~392-721)

This is a mechanical refactor: move the body that builds the `elements` list out of `generate_pdf_half_page` into a reusable function, so two-up can build the same elements twice.

- [ ] **Step 1: Create `build_halfpage_elements`**

In `pdf_templates.py`, define a new function directly above `generate_pdf_half_page` (line 392). Move the body of `generate_pdf_half_page` that constructs `elements` — that is, everything from `elements = []` (line ~410) through the final `elements.append(footer_table)` (line ~713) — into this new function. Keep the `from datetime import datetime` import inside it. The function signature and ending:

```python
def build_halfpage_elements(invoice, firm, user_id=None, bank=None, shell_data=None):
    """Build the ReportLab flowables for the HALF_PAGE invoice layout.

    Returns a fresh list of flowables each call (flowables cannot be reused
    across frames/documents, so callers needing two copies call this twice).
    """
    from datetime import datetime

    elements = []
    styles = getSampleStyleSheet()
    # ... (moved body: all the existing element-building code) ...
    elements.append(footer_table)
    return elements
```

- [ ] **Step 2: Reduce `generate_pdf_half_page` to use it**

Replace the body of `generate_pdf_half_page` (which previously built `elements` inline) with:

```python
def generate_pdf_half_page(invoice, firm, user_id=None, bank=None, shell_data=None):
    """Generate HALF_PAGE template PDF - Compact horizontal layout (A5-like on A4)."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=20, leftMargin=20,
                            topMargin=20, bottomMargin=20)
    elements = build_halfpage_elements(invoice, firm, user_id=user_id, bank=bank,
                                       shell_data=shell_data)
    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
```

- [ ] **Step 3: Verify nothing broke — existing half-page still generates**

Run: `cd backend && python -m pytest tests/ -v`
Expected: existing tests still pass (no new failures from the refactor).

Then sanity-check generation directly:

Run:
```bash
cd backend && python -c "from app.services.pdf_templates import build_halfpage_elements; print('import ok')"
```
Expected: `import ok`

- [ ] **Step 4: Commit** (leave for owner)

## Task B2: Two-up generator

**Files:**
- Modify: `backend/app/services/pdf_templates.py`
- Test: `backend/tests/test_two_up_pdf.py` (create)

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_two_up_pdf.py
"""Two-up half-page PDF generation."""
from datetime import date
from types import SimpleNamespace
from app.services.pdf_templates import generate_pdf_half_page_two_up


def _fake_firm():
    return SimpleNamespace(
        firm_name='Test Firm', firm_address='123 St', firm_phone='999',
        firm_phone_2=None, firm_email='f@x.com', default_template='HALF_PAGE',
    )


def _fake_invoice():
    item = SimpleNamespace(description='Design work', quantity=1, rate=1000, amount=1000)
    return SimpleNamespace(
        invoice_number='INV/0001', invoice_date=date(2026, 6, 1),
        due_date=date(2026, 6, 30), short_desc='Work', tax_rate=18,
        subtotal=1000, tax_amount=180, total=1180, notes='Thanks',
        items=[item], client=SimpleNamespace(name='Acme', address='X', tax_id=None),
    )


def test_two_up_returns_single_page_pdf():
    pdf = generate_pdf_half_page_two_up(_fake_invoice(), _fake_firm())
    assert isinstance(pdf, (bytes, bytearray))
    assert pdf[:4] == b'%PDF'
    # One physical page (two copies composited onto it).
    try:
        from pypdf import PdfReader
        from io import BytesIO
        assert len(PdfReader(BytesIO(pdf)).pages) == 1
    except ImportError:
        pass  # pypdf optional; header check above is the minimum guarantee
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_two_up_pdf.py -v`
Expected: FAIL with `ImportError: cannot import name 'generate_pdf_half_page_two_up'`

- [ ] **Step 3: Implement the two-up generator**

Add to `pdf_templates.py`. Add these imports near the top of the file (after the existing `reportlab` imports):

```python
from reportlab.pdfgen import canvas
from reportlab.platypus import Frame, KeepInFrame
```

Then add the function below `generate_pdf_half_page`:

```python
def generate_pdf_half_page_two_up(invoice, firm, user_id=None, bank=None, shell_data=None):
    """Two identical upright copies of the half-page invoice on one A4 page.

    Top copy occupies the upper half, bottom copy the lower half. Each copy is
    wrapped in a shrink-to-fit frame so a slightly tall invoice scales down
    rather than clipping at the tear line.
    """
    buffer = BytesIO()
    width, height = A4
    c = canvas.Canvas(buffer, pagesize=A4)
    margin = 20
    half = height / 2.0
    gutter = 10  # breathing room either side of the tear line

    frames = [
        Frame(margin, half + gutter / 2.0, width - 2 * margin, half - margin - gutter / 2.0,
              leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0, showBoundary=0),
        Frame(margin, margin, width - 2 * margin, half - margin - gutter / 2.0,
              leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0, showBoundary=0),
    ]
    for fr in frames:
        elements = build_halfpage_elements(invoice, firm, user_id=user_id, bank=bank,
                                           shell_data=shell_data)
        story = KeepInFrame(fr._width, fr._height, elements, mode='shrink')
        fr.addFromList([story], c)

    c.showPage()
    c.save()
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_two_up_pdf.py -v`
Expected: PASS

- [ ] **Step 5: Commit** (leave for owner)

## Task B3: Wire two-up through the dispatcher and endpoint

**Files:**
- Modify: `backend/app/services/pdf_templates.py` (`generate_pdf_with_template`, lines ~732-753)
- Modify: `backend/app/api/invoices.py` (`generate_invoice_pdf`, lines ~301-335)

- [ ] **Step 1: Add a `layout` param to the dispatcher**

Read the current tail of `generate_pdf_with_template` (lines ~732 to end) first, then replace the function with:

```python
def generate_pdf_with_template(invoice, firm, template_name=None, user_id=None, bank=None,
                               layout='single'):
    """Generate PDF using specified template with cached static elements.

    layout='two_up' forces the half-page layout rendered twice on one A4 page,
    regardless of template_name (two-up only makes sense for the compact layout).
    """
    if layout == 'two_up':
        shell_data = get_template_shell(user_id, 'HALF_PAGE', firm, bank) if user_id else None
        return generate_pdf_half_page_two_up(invoice, firm, user_id=user_id, bank=bank,
                                             shell_data=shell_data)

    if not template_name:
        template_name = firm.default_template if firm else 'Simple'

    generator = TEMPLATES.get(template_name, generate_pdf_simple)

    if template_name == 'HALF_PAGE' and user_id:
        shell_data = get_template_shell(user_id, template_name, firm, bank)
        return generator(invoice, firm, user_id=user_id, bank=bank, shell_data=shell_data)
    else:
        return generator(invoice, firm)
```

> Verify against the real lines 742-753 when editing — preserve the existing non-HALF_PAGE `else` branch exactly (it may call `generator(invoice, firm)` or pass extra args; match what is already there).

- [ ] **Step 2: Pass the query param through the endpoint**

In `backend/app/api/invoices.py`, in `generate_invoice_pdf` (line ~301), after loading `firm, bank` and `template_name` (line ~320), change the generation call to read the `layout` query param:

```python
        firm, bank = get_cached_firm_bank(user)
        template_name = firm.default_template if firm else 'Simple'
        layout = request.args.get('layout', 'single')

        pdf_bytes = generate_pdf_with_template(
            invoice, firm, template_name, user_id=user.supabase_id, bank=bank, layout=layout
        )

        suffix = '_2up' if layout == 'two_up' else ''
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f"SNAPPY_INV_{invoice.invoice_number.replace('/', '_')}{suffix}.pdf"
        )
```

- [ ] **Step 3: Verify import + dispatcher**

Run:
```bash
cd backend && python -c "from app.services.pdf_templates import generate_pdf_with_template; print('ok')"
```
Expected: `ok`

- [ ] **Step 4: Commit** (leave for owner)

## Task B4: Frontend two-up download action

**Files:**
- Modify: `frontend/src/api.ts` (`generatePDF`)
- Modify: `frontend/src/pages/InvoiceList.tsx`

- [ ] **Step 1: Add a `layout` argument to `generatePDF`**

In `frontend/src/api.ts`, replace the `generatePDF` method (lines ~248-266) with:

```typescript
  generatePDF: async (id: number, layout: 'single' | 'two_up' = 'single'): Promise<Blob> => {
    const { supabase } = await import('./lib/supabase');
    const { data: { session } } = await supabase.auth.getSession();

    const headers: Record<string, string> = {};
    if (session?.access_token) {
      headers['Authorization'] = `Bearer ${session.access_token}`;
    }

    const qs = layout === 'two_up' ? '?layout=two_up' : '';
    const response = await fetch(`${API_ENDPOINTS.invoices}/${id}/generate_pdf${qs}`, {
      method: 'POST',
      headers,
    });
    if (!response.ok) {
      throw new Error('Failed to generate PDF');
    }
    return await response.blob();
  },
```

- [ ] **Step 2: Add a two-up download button to the actions cell**

In `frontend/src/pages/InvoiceList.tsx`, update `handleGeneratePDF` to accept a layout (replace the function, lines ~106-119):

```tsx
  const handleGeneratePDF = async (id: number, invoiceNumber: string, layout: 'single' | 'two_up' = 'single') => {
    try {
      const blob = await api.generatePDF(id, layout);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      const suffix = layout === 'two_up' ? '_2up' : '';
      a.href = url;
      a.download = `SNAPPY_INV_${invoiceNumber.replace(/\//g, '_')}${suffix}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      console.error(e);
      alert('Failed to generate PDF');
    }
  };
```

Add `Copy as `Files` icon` — import the `Files` icon by adding it to the existing lucide import (line 6-9):

```tsx
import {
  Plus, Search, ChevronDown, ChevronUp, ChevronsUpDown,
  Eye, Pencil, Copy, Download, X, Files,
} from 'lucide-react';
```

Then, in the actions cell, immediately after the existing Download button (after line ~325, before closing `</div>`), add:

```tsx
                        <button
                          onClick={() => handleGeneratePDF(invoice.id, invoice.invoice_number, 'two_up')}
                          className="p-1.5 text-ink-muted hover:text-oxblood hover:bg-oxblood-wash rounded-sm transition-colors"
                          title="Download 2-up (2 copies / page)"
                        >
                          <Files size={14} strokeWidth={1.5} />
                        </button>
```

- [ ] **Step 3: Verify compile**

Run: `cd frontend && npm run build`
Expected: build succeeds.

- [ ] **Step 4: Manual smoke**

Open the invoice register, click the new "Download 2-up" icon on a row. The downloaded PDF filename ends `_2up.pdf` and shows two identical upright copies stacked on one page.

- [ ] **Step 5: Commit** (leave for owner)

---

# Part C — Recurring invoices

**Goal:** Users define recurring schedules; a daily Cloud Scheduler ping creates a draft invoice per due schedule; the dashboard shows money-forward reminders for those drafts.

## Task C1: Database migration

**Files:**
- Create: `backend/migrations/006_recurring_and_invoice_source.sql`

- [ ] **Step 1: Write the migration**

```sql
-- 006_recurring_and_invoice_source.sql
-- Adds recurring invoice schedules and a `source` marker on invoices so the
-- dashboard can distinguish recurring-generated drafts from manual ones.
-- Run in the Supabase SQL editor (db.create_all() handles fresh deploys, but
-- it does NOT add the `source` column to the existing invoices table).

ALTER TABLE public.invoices
  ADD COLUMN IF NOT EXISTS source VARCHAR(20) DEFAULT 'manual';

CREATE TABLE IF NOT EXISTS public.recurring_schedules (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  client_id INTEGER NOT NULL REFERENCES public.clients(id) ON DELETE CASCADE,
  title VARCHAR(200),
  items JSONB NOT NULL DEFAULT '[]'::jsonb,
  tax_rate NUMERIC(5,2) DEFAULT 18.0,
  short_desc TEXT,
  notes TEXT,
  frequency VARCHAR(20) NOT NULL,            -- 'weekly' | 'monthly'
  start_date DATE NOT NULL,
  next_run_date DATE NOT NULL,
  end_date DATE,                             -- optional; NULL = run until paused
  last_run_date DATE,
  active BOOLEAN DEFAULT true,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_recurring_user_id ON public.recurring_schedules(user_id);
CREATE INDEX IF NOT EXISTS idx_recurring_due ON public.recurring_schedules(active, next_run_date);
```

- [ ] **Step 2: Note for owner**

This migration must be run manually in the Supabase SQL editor before the recurring feature is deployed. Flag it in the handoff. No automated test for this step.

- [ ] **Step 3: Commit** (leave for owner)

## Task C2: Models — `source` column + `RecurringSchedule`

**Files:**
- Modify: `backend/app/models/models.py`

- [ ] **Step 1: Add `source` to the Invoice model**

In `backend/app/models/models.py`, in the `Invoice` class after the `status` block (after line ~111 `paid_date = ...`), add:

```python
    # Provenance: 'manual' (default) or 'recurring' (created by a schedule)
    source = db.Column(db.String(20), default='manual')
```

And add `'source': self.source,` to `Invoice.to_dict()` (after the `'status'` line ~148):

```python
            'status': self.status,
            'source': self.source,
```

- [ ] **Step 2: Add the `RecurringSchedule` model**

Add a new class after `InvoiceItem` (before the `Keepalive` class, ~line 183):

```python
class RecurringSchedule(db.Model):
    """A recurring invoice template that auto-creates draft invoices on a cadence."""
    __tablename__ = 'recurring_schedules'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    title = db.Column(db.String(200))
    items = db.Column(db.JSON, nullable=False, default=list)
    tax_rate = db.Column(db.Numeric(5, 2), default=18.0)
    short_desc = db.Column(db.Text)
    notes = db.Column(db.Text)
    frequency = db.Column(db.String(20), nullable=False)  # 'weekly' | 'monthly'
    start_date = db.Column(db.Date, nullable=False)
    next_run_date = db.Column(db.Date, nullable=False, index=True)
    end_date = db.Column(db.Date)            # optional; None = until paused
    last_run_date = db.Column(db.Date)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    client = db.relationship('Client')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'client_id': self.client_id,
            'client_name': self.client.name if self.client else None,
            'title': self.title,
            'items': self.items or [],
            'tax_rate': _money(self.tax_rate),
            'short_desc': self.short_desc,
            'notes': self.notes,
            'frequency': self.frequency,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'next_run_date': self.next_run_date.isoformat() if self.next_run_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'last_run_date': self.last_run_date.isoformat() if self.last_run_date else None,
            'active': self.active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
```

- [ ] **Step 3: Verify import**

Run: `cd backend && python -c "from app.models.models import RecurringSchedule; print('ok')"`
Expected: `ok`

- [ ] **Step 4: Commit** (leave for owner)

## Task C3: Cadence math (pure, TDD)

**Files:**
- Create: `backend/app/services/recurring_service.py`
- Test: `backend/tests/test_recurring_cadence.py` (create)

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_recurring_cadence.py
from datetime import date
from app.services.recurring_service import compute_next_run


def test_weekly_adds_seven_days():
    assert compute_next_run(date(2026, 6, 1), 'weekly') == date(2026, 6, 8)


def test_monthly_keeps_day_of_month():
    assert compute_next_run(date(2026, 6, 15), 'monthly') == date(2026, 7, 15)


def test_monthly_clamps_to_end_of_short_month():
    # Jan 31 -> Feb 28 (2026 is not a leap year)
    assert compute_next_run(date(2026, 1, 31), 'monthly') == date(2026, 2, 28)


def test_monthly_rolls_over_year():
    assert compute_next_run(date(2026, 12, 10), 'monthly') == date(2027, 1, 10)


def test_unknown_frequency_raises():
    import pytest
    with pytest.raises(ValueError):
        compute_next_run(date(2026, 6, 1), 'yearly')
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_recurring_cadence.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.recurring_service'`

- [ ] **Step 3: Implement `compute_next_run`**

```python
# backend/app/services/recurring_service.py
"""Recurring invoice cadence math and draft-generation service."""
from calendar import monthrange
from datetime import date, timedelta


def compute_next_run(from_date, frequency):
    """Return the next run date after `from_date` for the given frequency.

    weekly  -> from_date + 7 days
    monthly -> same day next month, clamped to the month's last day
    """
    if frequency == 'weekly':
        return from_date + timedelta(days=7)
    if frequency == 'monthly':
        year = from_date.year + (1 if from_date.month == 12 else 0)
        month = 1 if from_date.month == 12 else from_date.month + 1
        last_day = monthrange(year, month)[1]
        return date(year, month, min(from_date.day, last_day))
    raise ValueError(f"Unknown frequency: {frequency}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_recurring_cadence.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit** (leave for owner)

## Task C4: Draft-generation service (TDD)

**Files:**
- Modify: `backend/app/services/recurring_service.py`
- Test: `backend/tests/test_recurring_run.py` (create)

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_recurring_run.py
from datetime import date
from app.models.models import db, Client, Invoice, RecurringSchedule
from app.models.auth import User
from app.services.recurring_service import run_due_schedules


def _seed(app, next_run, end_date=None, frequency='monthly'):
    with app.app_context():
        db.create_all()
        user = User(supabase_id='sb-rec', email='r@example.com')
        db.session.add(user)
        db.session.flush()
        client = Client(user_id=user.id, name='Acme')
        db.session.add(client)
        db.session.flush()
        sched = RecurringSchedule(
            user_id=user.id, client_id=client.id, items=[
                {'description': 'Retainer', 'quantity': 1, 'rate': 5000},
            ], tax_rate=18, short_desc='Monthly retainer', frequency=frequency,
            start_date=next_run, next_run_date=next_run, end_date=end_date, active=True,
        )
        db.session.add(sched)
        db.session.commit()
        return user.id, sched.id


def test_due_schedule_creates_one_draft_and_advances(app):
    user_id, sched_id = _seed(app, next_run=date(2026, 6, 1))
    with app.app_context():
        created = run_due_schedules(db.session, today=date(2026, 6, 1))
        assert len(created) == 1
        inv = Invoice.query.filter_by(user_id=user_id).one()
        assert inv.status == 'draft'
        assert inv.source == 'recurring'
        assert float(inv.total) == 5900.0  # 5000 + 18%
        sched = RecurringSchedule.query.get(sched_id)
        assert sched.next_run_date == date(2026, 7, 1)
        assert sched.last_run_date == date(2026, 6, 1)
        assert sched.active is True


def test_not_yet_due_schedule_is_skipped(app):
    user_id, _ = _seed(app, next_run=date(2026, 7, 1))
    with app.app_context():
        created = run_due_schedules(db.session, today=date(2026, 6, 1))
        assert created == []
        assert Invoice.query.count() == 0


def test_end_date_deactivates_after_final_run(app):
    user_id, sched_id = _seed(app, next_run=date(2026, 6, 1), end_date=date(2026, 6, 15))
    with app.app_context():
        run_due_schedules(db.session, today=date(2026, 6, 1))
        sched = RecurringSchedule.query.get(sched_id)
        # next would be 2026-07-01 which is past end_date -> deactivated
        assert sched.active is False


def test_only_one_invoice_per_run_even_if_overdue(app):
    user_id, _ = _seed(app, next_run=date(2026, 6, 1))
    with app.app_context():
        # today is far past the due date; still only one draft this run
        run_due_schedules(db.session, today=date(2026, 9, 1))
        assert Invoice.query.count() == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_recurring_run.py -v`
Expected: FAIL with `ImportError: cannot import name 'run_due_schedules'`

- [ ] **Step 3: Implement `run_due_schedules`**

Append to `backend/app/services/recurring_service.py`:

```python
def run_due_schedules(session, today=None):
    """Create one draft invoice per due, active schedule. Returns created invoices.

    Idempotent per period: each schedule advances exactly one period per call, so
    a schedule that is several periods overdue catches up one draft per daily run.
    """
    from app.models.models import Invoice, InvoiceItem, RecurringSchedule
    from app.api.invoices import generate_invoice_number

    today = today or date.today()
    created = []

    due = (
        RecurringSchedule.query
        .filter(RecurringSchedule.active.is_(True))
        .filter(RecurringSchedule.next_run_date <= today)
        .all()
    )

    for sched in due:
        if sched.end_date and sched.next_run_date > sched.end_date:
            sched.active = False
            continue

        invoice = Invoice(
            user_id=sched.user_id,
            invoice_number=generate_invoice_number(sched.user_id),
            client_id=sched.client_id,
            invoice_date=today,
            due_date=None,
            short_desc=sched.short_desc,
            tax_rate=sched.tax_rate,
            status='draft',
            source='recurring',
            notes=sched.notes,
        )
        for line in (sched.items or []):
            qty = float(line.get('quantity', 1))
            rate = float(line.get('rate', 0))
            invoice.items.append(InvoiceItem(
                description=line.get('description', ''),
                quantity=qty, rate=rate, amount=qty * rate,
            ))
        invoice.calculate_totals()
        session.add(invoice)

        sched.last_run_date = today
        sched.next_run_date = compute_next_run(sched.next_run_date, sched.frequency)
        if sched.end_date and sched.next_run_date > sched.end_date:
            sched.active = False

        created.append(invoice)

    session.commit()
    return created
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_recurring_run.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit** (leave for owner)

## Task C5: Recurring API blueprint (CRUD + secret-gated run)

**Files:**
- Create: `backend/app/api/recurring.py`
- Modify: `backend/app/main.py` (register blueprint, import model)

- [ ] **Step 1: Create the blueprint**

```python
# backend/app/api/recurring.py
"""Recurring invoice schedule endpoints (CRUD) + secret-gated run endpoint."""
import os
from datetime import datetime, date
from flask import Blueprint, request, jsonify, g
from app.models.models import db, RecurringSchedule, Client
from app.models.auth import User
from app.middleware.jwt_auth import jwt_required
from app.services.recurring_service import run_due_schedules

bp = Blueprint('recurring', __name__)


def _current_user_id():
    supabase_id = getattr(g, 'user_id', None)
    if not supabase_id:
        return None
    user = User.query.filter_by(supabase_id=supabase_id).first()
    return user.id if user else None


def _parse_date(value):
    return datetime.fromisoformat(value).date() if value else None


@bp.route('/recurring', methods=['GET'])
@jwt_required
def list_schedules():
    user_id = _current_user_id()
    if not user_id:
        return jsonify({'error': 'User not found'}), 401
    rows = (RecurringSchedule.query
            .filter_by(user_id=user_id)
            .order_by(RecurringSchedule.next_run_date.asc())
            .all())
    return jsonify([s.to_dict() for s in rows])


@bp.route('/recurring', methods=['POST'])
@jwt_required
def create_schedule():
    user_id = _current_user_id()
    if not user_id:
        return jsonify({'error': 'User not found'}), 401
    data = request.get_json() or {}

    if not data.get('client_id'):
        return jsonify({'error': 'client_id is required'}), 400
    client = Client.query.filter_by(id=data['client_id'], user_id=user_id).first()
    if not client:
        return jsonify({'error': 'Client not found'}), 404
    if data.get('frequency') not in ('weekly', 'monthly'):
        return jsonify({'error': 'frequency must be weekly or monthly'}), 400
    start = _parse_date(data.get('start_date'))
    if not start:
        return jsonify({'error': 'start_date is required'}), 400

    sched = RecurringSchedule(
        user_id=user_id,
        client_id=data['client_id'],
        title=data.get('title'),
        items=data.get('items', []),
        tax_rate=float(data.get('tax_rate', client.default_tax_rate)),
        short_desc=data.get('short_desc'),
        notes=data.get('notes'),
        frequency=data['frequency'],
        start_date=start,
        next_run_date=start,           # first draft is created on the start date
        end_date=_parse_date(data.get('end_date')),
        active=data.get('active', True),
    )
    db.session.add(sched)
    db.session.commit()
    return jsonify(sched.to_dict()), 201


@bp.route('/recurring/<int:schedule_id>', methods=['PUT'])
@jwt_required
def update_schedule(schedule_id):
    user_id = _current_user_id()
    if not user_id:
        return jsonify({'error': 'User not found'}), 401
    sched = RecurringSchedule.query.filter_by(id=schedule_id, user_id=user_id).first()
    if not sched:
        return jsonify({'error': 'Schedule not found'}), 404
    data = request.get_json() or {}

    if 'title' in data:
        sched.title = data['title']
    if 'items' in data:
        sched.items = data['items']
    if 'tax_rate' in data:
        sched.tax_rate = float(data['tax_rate'])
    if 'short_desc' in data:
        sched.short_desc = data['short_desc']
    if 'notes' in data:
        sched.notes = data['notes']
    if data.get('frequency') in ('weekly', 'monthly'):
        sched.frequency = data['frequency']
    if 'start_date' in data:
        sched.start_date = _parse_date(data['start_date'])
    if 'next_run_date' in data:
        sched.next_run_date = _parse_date(data['next_run_date'])
    if 'end_date' in data:
        sched.end_date = _parse_date(data['end_date'])
    if 'active' in data:
        sched.active = bool(data['active'])
    db.session.commit()
    return jsonify(sched.to_dict())


@bp.route('/recurring/<int:schedule_id>', methods=['DELETE'])
@jwt_required
def delete_schedule(schedule_id):
    user_id = _current_user_id()
    if not user_id:
        return jsonify({'error': 'User not found'}), 401
    sched = RecurringSchedule.query.filter_by(id=schedule_id, user_id=user_id).first()
    if not sched:
        return jsonify({'error': 'Schedule not found'}), 404
    db.session.delete(sched)
    db.session.commit()
    return jsonify({'message': 'Schedule deleted'})


@bp.route('/recurring/reminders', methods=['GET'])
@jwt_required
def reminders():
    """Recurring-generated drafts awaiting review — the in-app reminder feed."""
    from app.models.models import Invoice
    user_id = _current_user_id()
    if not user_id:
        return jsonify({'error': 'User not found'}), 401
    drafts = (Invoice.query
              .filter_by(user_id=user_id, status='draft', source='recurring')
              .order_by(Invoice.created_at.desc())
              .all())
    return jsonify([inv.to_dict() for inv in drafts])


@bp.route('/recurring/run', methods=['POST'])
def run():
    """Secret-gated endpoint hit daily by Cloud Scheduler. No JWT — uses a shared secret."""
    expected = os.getenv('CRON_SECRET')
    provided = request.headers.get('X-Cron-Secret')
    if not expected or provided != expected:
        return jsonify({'error': 'Unauthorized'}), 401
    created = run_due_schedules(db.session, today=date.today())
    return jsonify({'created': len(created)}), 200
```

- [ ] **Step 2: Register the blueprint and import the model in `main.py`**

In `backend/app/main.py`, add `recurring` to the API import (line 12):

```python
from app.api import invoices, clients, analytics, import_csv, backup, auth, admin, items, storage, recurring
```

Register it alongside the other `/api/v1` blueprints (after line 71 `app.register_blueprint(items.bp, ...)`):

```python
    app.register_blueprint(recurring.bp, url_prefix='/api/v1')
```

Ensure the new table is created on fresh deploys — in the `with app.app_context():` block (after line 59 `from app.models.models import Item`), add:

```python
        from app.models.models import RecurringSchedule  # ensure table is created
```

- [ ] **Step 3: Verify app boots and routes register**

Run:
```bash
cd backend && python -c "from app.main import create_app; app = create_app(); print([r.rule for r in app.url_map.iter_rules() if 'recurring' in r.rule])"
```
Expected: prints the recurring routes including `/api/v1/recurring/run`.

> Requires `DATABASE_URL` set in the environment (the app refuses to boot without it). Use the local `.env`/dev database.

- [ ] **Step 4: Commit** (leave for owner)

## Task C6: Frontend API methods + types

**Files:**
- Modify: `frontend/src/api.ts`

- [ ] **Step 1: Add the `RecurringSchedule` type**

After the `Invoice` interface (line ~93), add:

```typescript
export interface RecurringSchedule {
  id: number;
  client_id: number;
  client_name?: string;
  title?: string;
  items: { description: string; quantity: number; rate: number }[];
  tax_rate: number;
  short_desc?: string;
  notes?: string;
  frequency: 'weekly' | 'monthly';
  start_date: string;
  next_run_date: string;
  end_date?: string;
  last_run_date?: string;
  active: boolean;
  created_at?: string;
  updated_at?: string;
}
```

- [ ] **Step 2: Add the endpoint constant and API methods**

In `API_ENDPOINTS` (after `items:` line ~36) add:

```typescript
  recurring: `${API_BASE_URL}/recurring`,
```

In the `api` object (after `duplicateInvoice`, line ~271), add:

```typescript
  getRecurring: () => fetchAPI<RecurringSchedule[]>(API_ENDPOINTS.recurring),

  createRecurring: (data: Partial<RecurringSchedule>) =>
    fetchAPI<RecurringSchedule>(API_ENDPOINTS.recurring, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  updateRecurring: (id: number, data: Partial<RecurringSchedule>) =>
    fetchAPI<RecurringSchedule>(`${API_ENDPOINTS.recurring}/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),

  deleteRecurring: (id: number) =>
    fetchAPI<{ message: string }>(`${API_ENDPOINTS.recurring}/${id}`, {
      method: 'DELETE',
    }),

  getRecurringReminders: () =>
    fetchAPI<Invoice[]>(`${API_ENDPOINTS.recurring}/reminders`),
```

- [ ] **Step 3: Verify compile**

Run: `cd frontend && npm run build`
Expected: build succeeds.

- [ ] **Step 4: Commit** (leave for owner)

## Task C7: Recurring management page

**Files:**
- Create: `frontend/src/pages/Recurring.tsx`
- Modify: `frontend/src/App.tsx` (route)

- [ ] **Step 1: Create the page**

```tsx
// frontend/src/pages/Recurring.tsx
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { api, Client, RecurringSchedule } from '../api';
import { ArrowLeft, Plus, Trash2, Pause, Play } from 'lucide-react';

const formatINR = (v: number) =>
  '₹' + v.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

const lineTotal = (items: RecurringSchedule['items']) =>
  items.reduce((s, i) => s + (Number(i.quantity) || 0) * (Number(i.rate) || 0), 0);

export default function Recurring() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [clientId, setClientId] = useState<number | 0>(0);
  const [frequency, setFrequency] = useState<'weekly' | 'monthly'>('monthly');
  const [startDate, setStartDate] = useState(new Date().toISOString().split('T')[0]);
  const [endDate, setEndDate] = useState('');
  const [shortDesc, setShortDesc] = useState('');
  const [items, setItems] = useState([{ description: '', quantity: 1, rate: 0 }]);

  const { data: schedules } = useQuery({
    queryKey: ['recurring'],
    queryFn: () => api.getRecurring(),
  });
  const { data: clients } = useQuery({
    queryKey: ['clients'],
    queryFn: () => api.getClients(),
  });

  const createMutation = useMutation({
    mutationFn: () => api.createRecurring({
      client_id: clientId as number,
      frequency,
      start_date: startDate,
      end_date: endDate || undefined,
      short_desc: shortDesc,
      items,
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recurring'] });
      setShowForm(false);
      setItems([{ description: '', quantity: 1, rate: 0 }]);
      setClientId(0); setShortDesc(''); setEndDate('');
    },
  });

  const toggleMutation = useMutation({
    mutationFn: (s: RecurringSchedule) => api.updateRecurring(s.id, { active: !s.active }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['recurring'] }),
  });
  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.deleteRecurring(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['recurring'] }),
  });

  const canSave = clientId !== 0 && items.some((i) => i.description && i.rate > 0);

  return (
    <div className="max-w-page mx-auto px-8 lg:px-12 py-10">
      <button onClick={() => navigate('/invoices')}
              className="inline-flex items-center gap-1.5 text-sm text-ink-muted hover:text-oxblood mb-3">
        <ArrowLeft size={14} strokeWidth={2} /><span>Back to invoices</span>
      </button>

      <header className="flex items-end justify-between flex-wrap gap-6 mb-8">
        <div>
          <div className="page-eyebrow">Automation</div>
          <h1 className="page-title">Recurring invoices</h1>
          <p className="page-subtitle">Auto-create a draft on a schedule. Review it before it goes out.</p>
        </div>
        <button onClick={() => setShowForm((v) => !v)} className="btn-primary">
          <Plus size={14} strokeWidth={2} /><span>Set up recurring</span>
        </button>
      </header>

      {showForm && (
        <section className="card p-8 mb-8 space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="field-label">Client *</label>
              <select className="field-select" value={clientId}
                      onChange={(e) => setClientId(Number(e.target.value))}>
                <option value={0}>Select a client…</option>
                {clients?.map((c: Client) => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </div>
            <div>
              <label className="field-label">Frequency *</label>
              <select className="field-select" value={frequency}
                      onChange={(e) => setFrequency(e.target.value as 'weekly' | 'monthly')}>
                <option value="monthly">Monthly</option>
                <option value="weekly">Weekly</option>
              </select>
            </div>
            <div>
              <label className="field-label">Start date *</label>
              <input type="date" className="field-input font-mono" value={startDate}
                     onChange={(e) => setStartDate(e.target.value)} />
            </div>
            <div>
              <label className="field-label">End date (optional)</label>
              <input type="date" className="field-input font-mono" value={endDate}
                     onChange={(e) => setEndDate(e.target.value)} />
            </div>
          </div>

          <div>
            <label className="field-label">Short description</label>
            <input className="field-input" value={shortDesc}
                   onChange={(e) => setShortDesc(e.target.value)} placeholder="e.g. Monthly retainer" />
          </div>

          <div>
            <label className="field-label">Line items *</label>
            {items.map((it, idx) => (
              <div key={idx} className="grid grid-cols-[1fr_5rem_8rem_2rem] gap-3 mb-2 items-center">
                <input className="field-input" placeholder="Description" value={it.description}
                       onChange={(e) => setItems(items.map((x, i) => i === idx ? { ...x, description: e.target.value } : x))} />
                <input type="number" className="field-input text-center font-mono" value={it.quantity}
                       onChange={(e) => setItems(items.map((x, i) => i === idx ? { ...x, quantity: Number(e.target.value) } : x))} />
                <input type="number" className="field-input text-right font-mono" value={it.rate}
                       onChange={(e) => setItems(items.map((x, i) => i === idx ? { ...x, rate: Number(e.target.value) } : x))} />
                <button type="button" className="text-ink-muted hover:text-oxblood disabled:opacity-30"
                        disabled={items.length === 1}
                        onClick={() => setItems(items.filter((_, i) => i !== idx))}>
                  <Trash2 size={14} strokeWidth={1.5} />
                </button>
              </div>
            ))}
            <button type="button" className="btn-secondary mt-2"
                    onClick={() => setItems([...items, { description: '', quantity: 1, rate: 0 }])}>
              <Plus size={14} strokeWidth={2} /><span>Add line</span>
            </button>
          </div>

          <div className="flex justify-end gap-3 pt-2">
            <button className="btn-ghost" onClick={() => setShowForm(false)}>Cancel</button>
            <button className="btn-primary" disabled={!canSave || createMutation.isPending}
                    onClick={() => createMutation.mutate()}>
              {createMutation.isPending ? 'Saving…' : 'Create schedule'}
            </button>
          </div>
        </section>
      )}

      <div className="card overflow-hidden">
        {schedules && schedules.length > 0 ? (
          <table className="table-editorial">
            <thead>
              <tr>
                <th>Client</th><th>Every</th><th>Next draft</th>
                <th className="!text-right">Amount</th><th>Status</th><th className="!text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {schedules.map((s) => (
                <tr key={s.id}>
                  <td className="text-ink">{s.client_name}</td>
                  <td className="text-ink-muted capitalize">{s.frequency}</td>
                  <td className="font-mono text-ink-muted tabular">{s.next_run_date}</td>
                  <td className="text-right font-mono text-ink tabular">{formatINR(lineTotal(s.items))}</td>
                  <td><span className={s.active ? 'pill-paid' : 'pill-draft'}>{s.active ? 'active' : 'paused'}</span></td>
                  <td>
                    <div className="flex items-center justify-end gap-0.5">
                      <button onClick={() => toggleMutation.mutate(s)} title={s.active ? 'Pause' : 'Resume'}
                              className="p-1.5 text-ink-muted hover:text-ink hover:bg-paper-deep rounded-sm">
                        {s.active ? <Pause size={14} strokeWidth={1.5} /> : <Play size={14} strokeWidth={1.5} />}
                      </button>
                      <button onClick={() => { if (confirm('Delete this recurring schedule?')) deleteMutation.mutate(s.id); }}
                              title="Delete"
                              className="p-1.5 text-ink-muted hover:text-oxblood hover:bg-oxblood-wash rounded-sm">
                        <Trash2 size={14} strokeWidth={1.5} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div className="p-16 text-center">
            <div className="page-eyebrow">Nothing scheduled</div>
            <h2 className="section-title mt-2">No recurring invoices yet</h2>
            <p className="text-base text-ink-muted mt-3">Set one up to auto-draft repeat bills.</p>
          </div>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Add the route**

In `frontend/src/App.tsx`, import the page (after line 17 `import Items ...`):

```tsx
import Recurring from './pages/Recurring';
```

Add the route inside the protected `Layout` block (after line 68 `invoices/new`):

```tsx
            <Route path="recurring" element={<Recurring />} />
```

- [ ] **Step 3: Verify compile**

Run: `cd frontend && npm run build`
Expected: build succeeds.

- [ ] **Step 4: Commit** (leave for owner)

## Task C8: "Set up recurring" button on the invoice register

**Files:**
- Modify: `frontend/src/pages/InvoiceList.tsx`

- [ ] **Step 1: Add the button to the header**

In `frontend/src/pages/InvoiceList.tsx`, in the header (around line 139), wrap the existing "New invoice" link and a new recurring link together. Replace the single `<Link to="/invoices/new" ...>` block with:

```tsx
        <div className="flex items-center gap-3">
          <Link to="/recurring" className="btn-secondary">
            <RefreshCw size={14} strokeWidth={2} />
            <span>Set up recurring</span>
          </Link>
          <Link to="/invoices/new" className="btn-primary">
            <Plus size={14} strokeWidth={2} />
            <span>New invoice</span>
          </Link>
        </div>
```

Add `RefreshCw` to the lucide import block (the one already edited in Task B4):

```tsx
import {
  Plus, Search, ChevronDown, ChevronUp, ChevronsUpDown,
  Eye, Pencil, Copy, Download, X, Files, RefreshCw,
} from 'lucide-react';
```

- [ ] **Step 2: Verify compile**

Run: `cd frontend && npm run build`
Expected: build succeeds.

- [ ] **Step 3: Commit** (leave for owner)

## Task C9: Dashboard reminder banner

**Files:**
- Modify: `frontend/src/pages/Dashboard.tsx`

- [ ] **Step 1: Query reminders and render a banner**

In `Dashboard.tsx`, add the import (line ~10, extend the lucide import):

```tsx
import { TrendingUp, FileText, IndianRupee, Bell } from 'lucide-react';
```

Add `Link` import at the top:

```tsx
import { Link } from 'react-router-dom';
```

Inside the `Dashboard` component, add the query (near the other `useQuery` calls):

```tsx
  const { data: reminders } = useQuery({
    queryKey: ['recurring', 'reminders'],
    queryFn: () => api.getRecurringReminders(),
  });
```

Then, at the top of the dashboard's returned JSX (just inside the outer wrapper, before the metric tiles), insert:

```tsx
      {reminders && reminders.length > 0 && (
        <div className="card p-5 mb-6 border-l-2 border-oxblood">
          <div className="flex items-start gap-3">
            <Bell size={18} strokeWidth={1.5} className="text-oxblood mt-0.5" />
            <div className="flex-1">
              <div className="eyebrow mb-2">Recurring drafts to review</div>
              <ul className="space-y-1.5">
                {reminders.map((inv) => (
                  <li key={inv.id} className="text-sm text-ink-soft flex items-center justify-between gap-4">
                    <span>
                      <span className="font-medium text-ink">{inv.client_name}</span>{' '}
                      is due {formatINR(inv.total)} today — draft invoice created.
                    </span>
                    <Link to={`/invoices/${inv.id}/edit`}
                          className="text-xs uppercase tracking-eyebrow text-oxblood hover:text-oxblood-deep whitespace-nowrap">
                      Review →
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}
```

> `formatINR` already exists at the top of `Dashboard.tsx`; reuse it. If the dashboard's outer wrapper is a fragment or specific element, place the banner as the first child of the main content container so it sits above the metric tiles.

- [ ] **Step 2: Verify compile**

Run: `cd frontend && npm run build`
Expected: build succeeds.

- [ ] **Step 3: Manual smoke**

With at least one recurring-generated draft in the DB (run the cadence flow or insert one with `status='draft', source='recurring'`), the dashboard shows the banner: "Acme is due ₹X today — draft invoice created." Clicking "Review →" opens the draft. Finalizing the draft (status changes away from draft) removes it from the banner on refresh.

- [ ] **Step 4: Commit** (leave for owner)

## Task C10: Cloud Scheduler + env setup (ops, manual)

**Files:**
- Modify: `.env.example` (document `CRON_SECRET`)

- [ ] **Step 1: Document the env var**

Add to `.env.example`:

```
# Shared secret for the recurring-invoice cron endpoint (POST /api/v1/recurring/run).
# Cloud Scheduler must send this as the X-Cron-Secret header.
CRON_SECRET=change-me-to-a-long-random-string
```

- [ ] **Step 2: Owner action — set the secret and create the scheduler job**

This step is performed by the repo owner (requires GCP access). Document in the handoff:

1. Set `CRON_SECRET` in the Cloud Run service env vars (a long random string).
2. Create a daily Cloud Scheduler HTTP job:

```bash
gcloud scheduler jobs create http snappy-recurring-run \
  --schedule="0 6 * * *" \
  --uri="https://<CLOUD_RUN_URL>/api/v1/recurring/run" \
  --http-method=POST \
  --headers="X-Cron-Secret=<the-same-secret>" \
  --time-zone="Asia/Kolkata"
```

3. Run migration `006_recurring_and_invoice_source.sql` in the Supabase SQL editor.

- [ ] **Step 3: Commit** (leave for owner)

---

## Final verification

- [ ] Backend: `cd backend && python -m pytest tests/ -v` — all new tests pass (recent clients, two-up, cadence, run service).
- [ ] Frontend: `cd frontend && npm run build` — compiles cleanly.
- [ ] App boots: `cd backend && python -c "from app.main import create_app; create_app(); print('boot ok')"` (with `DATABASE_URL` set).
- [ ] Manual smoke of all three features per the per-task smoke notes.

---

## Self-review against spec

- **A — Recent-client chips:** Task A1 (endpoint, ordered by latest invoice, excludes unbilled), A2 (API method), A3 (chips shown only when composing + empty search; selecting reuses client tax rate). ✅
- **B — Two-up:** B1 (extract builder), B2 (two upright copies, one A4 page, shrink-to-fit guardrail against overflow), B3 (dispatcher `layout` param + endpoint query param + `_2up` filename), B4 (UI action). Both upright, identical — matches the declined-rotation/labels decisions. ✅
- **C — Recurring:** C1 (migration incl. `source` column + optional `end_date`), C2 (models), C3 (cadence weekly/monthly + clamp), C4 (draft creation, `source='recurring'`, one-per-run idempotency, end-date deactivation), C5 (CRUD + secret-gated run + reminders feed), C6 (frontend API), C7 (management page with optional end date), C8 ("Set up recurring" button at top of invoice register), C9 (dashboard reminder "Client X is due ₹Y today — draft invoice created"), C10 (Cloud Scheduler + `CRON_SECRET`). ✅
- **Reminder is in-app**, derived from recurring drafts (no notifications table) — matches spec. ✅
- **Optional end date** — present in model, migration, run logic, create form. ✅
- Type consistency: `generate_pdf_half_page_two_up`, `build_halfpage_elements`, `compute_next_run`, `run_due_schedules`, `recent_clients_for_user`, `api.getRecentClients`, `api.getRecurring*`, `RecurringSchedule` used consistently across tasks. ✅
