# Case System UX — Plan 1: Three-Tab Shell + Stage Taxonomy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure the "Cases" area into three tabs (Kanban / Case Vault / Calendar) and replace the old stage taxonomy with the litigation-lifecycle stages, including an idempotent stage-remap migration.

**Architecture:** Backend swaps the `stages.py` catalog (the single source of truth that drives kanban columns, `/meta`, and validation) and adds a `LEGACY_STAGE_REMAP` dict mirrored by SQL migration `013`. Frontend introduces a `CasesLayout` shell with a sub-tab bar; the existing `Cases.tsx` board becomes the Kanban tab, a new `CaseVault` page owns the All-Cases list + create + an Enquiries placeholder, and a new `CaseCalendar` page shows an upcoming-hearings agenda placeholder.

**Tech Stack:** Flask + SQLAlchemy (SQLite in tests via `db.create_all`), pytest; React + TypeScript + Vite, React Router v6, TanStack Query, Tailwind design tokens.

## Global Constraints

- Never run git commits/pushes — Parth does git himself. (Steps below include `git` commands per the skill template; in this repo, **stop at staging/optional** — do NOT execute commits. Run the test/build gate instead and report.)
- Migrations are delivered as SQL files for Parth to apply manually; no code path runs them. Migrations 009–012 are already applied; new files number from **013**.
- Stage keys (verbatim): `engaged, notice, filed, hearings_evidence, arguments, judgment, closed`; `DEFAULT_STAGE = "engaged"`.
- Legacy remap (verbatim): `intake→engaged, drafting→notice, filed→filed, in_hearing→hearings_evidence, awaiting_order→judgment, closed→closed`.
- Backend must stay green (`pytest`); frontend must build clean (`npm run build`).
- Access is firm-wide RBAC only; solo-advocate-first.

---

### Task 1: New stage taxonomy in `stages.py`

**Files:**
- Modify: `backend/app/case/stages.py:8-18`
- Test: `backend/tests/test_case_stages.py`
- Test (fix fallout): `backend/tests/test_case_models.py:31`, `backend/tests/test_case_files_api.py:19,34`, `backend/tests/test_case_record_api.py:27,35,38`, `backend/tests/test_case_record_models.py:32`, `backend/tests/test_stage_recorder.py:18,21`

**Interfaces:**
- Produces: `STAGES` (list of `{"key","label"}`), `STAGE_KEYS` (set), `DEFAULT_STAGE="engaged"`, unchanged `is_valid_stage(key)`. Consumed by `app/api/case_files.py` (`/meta`, validation) and `frontend` via `/case-files/meta`.

- [ ] **Step 1: Update the stage-catalog test to the new taxonomy**

In `backend/tests/test_case_stages.py`, replace the keys/default assertions:

```python
def test_stage_keys_in_lifecycle_order():
    keys = [s["key"] for s in STAGES]
    assert keys == ["engaged", "notice", "filed",
                    "hearings_evidence", "arguments", "judgment", "closed"]


def test_default_stage_is_engaged():
    assert DEFAULT_STAGE == "engaged"
    assert DEFAULT_STAGE in STAGE_KEYS
```

(Keep the existing import line and any `EVENT_KINDS`/priority assertions; only the function above named `test_default_stage_is_intake` is renamed/retargeted.)

- [ ] **Step 2: Run it to verify it fails**

Run: `cd backend && python -m pytest tests/test_case_stages.py -v`
Expected: FAIL — current `STAGES` still begins with `intake`.

- [ ] **Step 3: Replace the catalog in `stages.py`**

In `backend/app/case/stages.py`, replace the `STAGES`/`DEFAULT_STAGE` block (lines 8-18) with:

```python
STAGES = [
    {"key": "engaged",           "label": "Engaged"},
    {"key": "notice",            "label": "Notice"},
    {"key": "filed",             "label": "Filed"},
    {"key": "hearings_evidence", "label": "Hearings & Evidence"},
    {"key": "arguments",         "label": "Arguments"},
    {"key": "judgment",          "label": "Judgment"},
    {"key": "closed",            "label": "Closed"},
]

STAGE_KEYS = {s["key"] for s in STAGES}
DEFAULT_STAGE = "engaged"
```

- [ ] **Step 4: Update the docstring's stage example**

In `backend/app/case/stages.py:1-6`, the module docstring mentions stages generically — no `intake` literal appears there, so no change is required. Confirm by reading lines 1-6; if an old stage key is present, update it to `engaged`.

- [ ] **Step 5: Fix the existing tests that hard-code old stage keys**

Apply these exact literal replacements:
- `backend/tests/test_case_models.py:31` — `d['stage'] == 'intake'` → `d['stage'] == 'engaged'`
- `backend/tests/test_case_files_api.py:19` — `[s['key'] for s in body['stages']][0] == 'intake'` → `== 'engaged'`
- `backend/tests/test_case_files_api.py:34` — `body['stage'] == 'intake'` → `body['stage'] == 'engaged'`
- `backend/tests/test_case_record_api.py:27` — `hist[0]['to_stage'] == 'intake'` → `== 'engaged'`
- `backend/tests/test_case_record_api.py:35` — `json={'stage': 'in_hearing'}` → `json={'stage': 'hearings_evidence'}`
- `backend/tests/test_case_record_api.py:38` — `== ['intake', 'filed', 'in_hearing']` → `== ['engaged', 'filed', 'hearings_evidence']`
- `backend/tests/test_case_record_models.py:32` — `to_stage='intake'` → `to_stage='engaged'`
- `backend/tests/test_stage_recorder.py:18` — `record_stage_change(cf, 'intake', 'filed', u.id)` → `record_stage_change(cf, 'engaged', 'filed', u.id)`
- `backend/tests/test_stage_recorder.py:21` — `row.from_stage == 'intake'` → `row.from_stage == 'engaged'`

Note `backend/tests/test_case_isolation.py:28` uses `'closed'`, which remains valid — leave it.

- [ ] **Step 6: Run the full backend suite**

Run: `cd backend && python -m pytest -q`
Expected: PASS (same count as before, 246, all green).

- [ ] **Step 7: Stage changes (do NOT commit — Parth handles git)**

```bash
git add backend/app/case/stages.py backend/tests/
```
Report green; do not run `git commit`.

---

### Task 2: `LEGACY_STAGE_REMAP` + migration `013`

**Files:**
- Modify: `backend/app/case/stages.py` (append remap dict)
- Create: `backend/migrations/013_stage_taxonomy_remap.sql`
- Test: `backend/tests/test_case_stages.py`

**Interfaces:**
- Produces: `LEGACY_STAGE_REMAP: dict[str, str]` mapping every old key to a current key. The SQL migration mirrors it exactly.

- [ ] **Step 1: Write the failing test for the remap guard**

Append to `backend/tests/test_case_stages.py` (and add `LEGACY_STAGE_REMAP` to the existing import from `app.case.stages`):

```python
def test_legacy_remap_targets_are_valid_stages():
    # Every legacy key must map to a key that exists in the new taxonomy.
    assert set(LEGACY_STAGE_REMAP) == {
        "intake", "drafting", "filed", "in_hearing", "awaiting_order", "closed"}
    for old, new in LEGACY_STAGE_REMAP.items():
        assert new in STAGE_KEYS
    assert LEGACY_STAGE_REMAP["intake"] == "engaged"
    assert LEGACY_STAGE_REMAP["in_hearing"] == "hearings_evidence"
    assert LEGACY_STAGE_REMAP["awaiting_order"] == "judgment"
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd backend && python -m pytest tests/test_case_stages.py::test_legacy_remap_targets_are_valid_stages -v`
Expected: FAIL — `LEGACY_STAGE_REMAP` does not exist / ImportError.

- [ ] **Step 3: Add the remap dict to `stages.py`**

Append to `backend/app/case/stages.py` (after `DEFAULT_PRIORITY`):

```python
# Maps the pre-2026-06-25 stage keys to the current taxonomy. Mirrored by
# migrations/013_stage_taxonomy_remap.sql. Keys that did not change still
# appear so the mapping is total.
LEGACY_STAGE_REMAP = {
    "intake":         "engaged",
    "drafting":       "notice",
    "filed":          "filed",
    "in_hearing":     "hearings_evidence",
    "awaiting_order": "judgment",
    "closed":         "closed",
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd backend && python -m pytest tests/test_case_stages.py -v`
Expected: PASS.

- [ ] **Step 5: Create the migration SQL (mirrors the remap; only changed keys emit an UPDATE)**

Create `backend/migrations/013_stage_taxonomy_remap.sql`:

```sql
-- 013_stage_taxonomy_remap.sql — remap legacy case stage keys to the
-- 2026-06-25 litigation taxonomy. Additive/idempotent: after it runs, no
-- rows carry the old keys, so re-running is a safe no-op. Apply in Supabase.
BEGIN;

UPDATE public.case_files SET stage = 'engaged'           WHERE stage = 'intake';
UPDATE public.case_files SET stage = 'notice'            WHERE stage = 'drafting';
UPDATE public.case_files SET stage = 'hearings_evidence' WHERE stage = 'in_hearing';
UPDATE public.case_files SET stage = 'judgment'          WHERE stage = 'awaiting_order';
-- 'filed' and 'closed' are unchanged; no UPDATE needed.

COMMIT;
```

- [ ] **Step 6: Run the full backend suite**

Run: `cd backend && python -m pytest -q`
Expected: PASS (247 tests — one new).

- [ ] **Step 7: Stage changes (do NOT commit)**

```bash
git add backend/app/case/stages.py backend/tests/test_case_stages.py backend/migrations/013_stage_taxonomy_remap.sql
```
Report green; do not commit.

---

### Task 3: Frontend three-tab shell (Kanban / Case Vault / Calendar)

**Files:**
- Create: `frontend/src/pages/CasesLayout.tsx`
- Create: `frontend/src/pages/CasesKanban.tsx`
- Create: `frontend/src/pages/CaseVault.tsx`
- Create: `frontend/src/pages/CaseCalendar.tsx`
- Delete: `frontend/src/pages/Cases.tsx`
- Modify: `frontend/src/App.tsx:25` (imports) and `:92` (routes)

**Interfaces:**
- Consumes: `api.getCaseMeta`, `api.getCaseFiles`, `api.getClients`, `api.createCaseFile`, `api.moveCaseFile` (all already in `frontend/src/api.ts`), `CaseFile`/`CaseParty` types.
- Produces: route tree `/cases` (layout) → index `CasesKanban`, `/cases/vault` `CaseVault`, `/cases/calendar` `CaseCalendar`; `/cases/:id` `CaseDetail` stays a sibling (no sub-tab chrome).
- Gate: no FE unit-test runner — the deliverable gate is `npm run build` clean.

- [ ] **Step 1: Create `CasesLayout.tsx` (shared header + sub-tab bar + Outlet)**

```tsx
import { NavLink, Outlet } from 'react-router-dom';

const tabClass = ({ isActive }: { isActive: boolean }) =>
  [
    'px-1 pb-2 -mb-px text-sm font-medium border-b-2 transition-colors',
    isActive
      ? 'border-oxblood text-ink'
      : 'border-transparent text-ink-muted hover:text-ink',
  ].join(' ');

export default function CasesLayout() {
  return (
    <div className="max-w-page mx-auto px-8 lg:px-12 py-10">
      <header className="mb-6">
        <div className="page-eyebrow">Folio V · Docket</div>
        <h1 className="page-title">Case files</h1>
      </header>
      <nav className="flex gap-6 border-b border-rule mb-8">
        <NavLink end to="/cases" className={tabClass}>Kanban</NavLink>
        <NavLink to="/cases/vault" className={tabClass}>Case Vault</NavLink>
        <NavLink to="/cases/calendar" className={tabClass}>Calendar</NavLink>
      </nav>
      <Outlet />
    </div>
  );
}
```

- [ ] **Step 2: Create `CasesKanban.tsx` (board only — extracted from `Cases.tsx`)**

```tsx
import { useMemo } from 'react';
import { Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api, CaseFile } from '../api';
import { usePermissions } from '../hooks/usePermissions';
import { useToast } from '../contexts/ToastContext';

const errMsg = (e: unknown) => (e instanceof Error ? e.message : 'Something went wrong');

const PRIORITY_DOT: Record<string, string> = {
  urgent: 'bg-oxblood', high: 'bg-oxblood/60', normal: 'bg-ink-faint', low: 'bg-rule',
};

export default function CasesKanban() {
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const { has } = usePermissions();
  const canMove = has('case_files.update');

  const { data: meta } = useQuery({ queryKey: ['case-meta'], queryFn: api.getCaseMeta });
  const { data: cases = [], isLoading } = useQuery({
    queryKey: ['case-files'], queryFn: () => api.getCaseFiles(),
  });

  const stages = (meta?.stages ?? []).filter((s) => s.key !== 'closed');
  const byStage = useMemo(() => {
    const map: Record<string, CaseFile[]> = {};
    stages.forEach((s) => { map[s.key] = []; });
    cases.forEach((c) => { if (map[c.stage]) map[c.stage].push(c); });
    return map;
  }, [cases, stages]);

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

  if (isLoading) return <div className="card p-16 flex justify-center"><div className="spinner" /></div>;

  return (
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
                <div className="flex items-center gap-1.5">
                  <span className={`h-1.5 w-1.5 rounded-full shrink-0 ${PRIORITY_DOT[c.priority] ?? PRIORITY_DOT.normal}`}
                    title={`Priority: ${c.priority}`} />
                  <div className="text-2xs font-mono text-oxblood">{c.case_number}</div>
                </div>
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
  );
}
```

- [ ] **Step 3: Create `CaseVault.tsx` (All Cases list + create modal + Enquiries placeholder)**

```tsx
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api, CaseParty } from '../api';
import { usePermissions } from '../hooks/usePermissions';
import { useToast } from '../contexts/ToastContext';
import { Plus, X } from 'lucide-react';

const errMsg = (e: unknown) => (e instanceof Error ? e.message : 'Something went wrong');

const EMPTY = {
  title: '', client_id: 0, matter_type: '', court: '', court_case_number: '',
  priority: 'normal', parties: [] as CaseParty[],
};

export default function CaseVault() {
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const { has } = usePermissions();
  const canCreate = has('case_files.create');

  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState(EMPTY);

  const { data: meta } = useQuery({ queryKey: ['case-meta'], queryFn: api.getCaseMeta });
  const { data: cases = [], isLoading } = useQuery({
    queryKey: ['case-files'], queryFn: () => api.getCaseFiles(),
  });
  const { data: clients = [] } = useQuery({ queryKey: ['clients'], queryFn: () => api.getClients() });

  const stages = meta?.stages ?? [];

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

  return (
    <div className="space-y-10">
      {/* Enquiries — leads land here in Plan 2 */}
      <section>
        <div className="flex items-center justify-between mb-3">
          <h2 className="eyebrow">Enquiries</h2>
        </div>
        <div className="border border-dashed border-rule bg-surface p-8 text-center text-sm text-ink-muted">
          Prospective matters (leads) will appear here.
        </div>
      </section>

      {/* All cases */}
      <section>
        <div className="flex items-center justify-between mb-3">
          <h2 className="eyebrow">All cases</h2>
          {canCreate && (
            <button onClick={() => setModalOpen(true)} className="btn-primary">
              <Plus size={14} strokeWidth={2} /><span>New case</span>
            </button>
          )}
        </div>
        {isLoading ? (
          <div className="card p-16 flex justify-center"><div className="spinner" /></div>
        ) : (
          <div className="border border-rule divide-y divide-rule">
            {cases.map((c) => (
              <Link key={c.id} to={`/cases/${c.id}`}
                className="bg-surface flex items-center gap-4 px-5 py-3 hover:bg-paper-deep/40">
                <span className="text-2xs font-mono text-oxblood w-28 shrink-0">{c.case_number}</span>
                <span className="text-sm text-ink flex-1 truncate">{c.title}</span>
                <span className="text-xs text-ink-muted w-40 truncate">{c.client_name}</span>
                <span className="text-2xs uppercase tracking-eyebrow text-ink-muted w-36 text-right">
                  {stages.find((s) => s.key === c.stage)?.label ?? c.stage}
                </span>
              </Link>
            ))}
            {cases.length === 0 && (
              <div className="bg-surface p-10 text-center text-sm text-ink-muted">No case files yet.</div>
            )}
          </div>
        )}
      </section>

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
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="field-label">Matter type</label>
                    <input value={form.matter_type}
                      onChange={(e) => setForm({ ...form, matter_type: e.target.value })}
                      className="field-input" placeholder="Constitutional / Civil / Tax…" />
                  </div>
                  <div>
                    <label className="field-label">Priority</label>
                    <select value={form.priority}
                      onChange={(e) => setForm({ ...form, priority: e.target.value })}
                      className="field-select">
                      {(meta?.priorities ?? [{ key: 'normal', label: 'Normal' }]).map((p) => (
                        <option key={p.key} value={p.key}>{p.label}</option>
                      ))}
                    </select>
                  </div>
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

- [ ] **Step 4: Create `CaseCalendar.tsx` (upcoming-hearings agenda placeholder)**

```tsx
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { api } from '../api';

export default function CaseCalendar() {
  const { data: cases = [], isLoading } = useQuery({
    queryKey: ['case-files'], queryFn: () => api.getCaseFiles(),
  });

  const upcoming = cases
    .filter((c) => c.next_hearing_date)
    .sort((a, b) => (a.next_hearing_date! < b.next_hearing_date! ? -1 : 1));

  if (isLoading) return <div className="card p-16 flex justify-center"><div className="spinner" /></div>;

  return (
    <div className="space-y-4">
      <p className="text-sm text-ink-muted">
        Upcoming hearing dates across every case. A full month view arrives with the calendar phase.
      </p>
      <div className="border border-rule divide-y divide-rule">
        {upcoming.map((c) => (
          <Link key={c.id} to={`/cases/${c.id}`}
            className="bg-surface flex items-center gap-4 px-5 py-3 hover:bg-paper-deep/40">
            <span className="text-sm font-medium text-oxblood w-32 shrink-0">{c.next_hearing_date}</span>
            <span className="text-sm text-ink flex-1 truncate">{c.title}</span>
            <span className="text-xs text-ink-muted w-40 truncate">{c.client_name}</span>
          </Link>
        ))}
        {upcoming.length === 0 && (
          <div className="bg-surface p-10 text-center text-sm text-ink-muted">No upcoming hearing dates.</div>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 5: Rewire routes in `App.tsx`**

Replace the import on `frontend/src/App.tsx:25` (`import Cases from './pages/Cases';`) with:

```tsx
import CasesLayout from './pages/CasesLayout';
import CasesKanban from './pages/CasesKanban';
import CaseVault from './pages/CaseVault';
import CaseCalendar from './pages/CaseCalendar';
```

Replace the single `cases` route line `frontend/src/App.tsx:92` (`<Route path="cases" element={<Cases />} />`) with:

```tsx
<Route path="cases" element={<CasesLayout />}>
  <Route index element={<CasesKanban />} />
  <Route path="vault" element={<CaseVault />} />
  <Route path="calendar" element={<CaseCalendar />} />
</Route>
```

Leave `<Route path="cases/:id" element={<CaseDetail />} />` (line 93) unchanged — React Router ranks the static `vault`/`calendar` segments above `:id`, so there is no collision.

- [ ] **Step 6: Delete the obsolete `Cases.tsx`**

Remove `frontend/src/pages/Cases.tsx` (its board moved to `CasesKanban`, its list + create moved to `CaseVault`).

- [ ] **Step 7: Build the frontend**

Run: `cd frontend && npm run build`
Expected: build succeeds, no TypeScript errors, no unresolved import of `./pages/Cases`.

- [ ] **Step 8: Stage changes (do NOT commit)**

```bash
git add frontend/src/App.tsx frontend/src/pages/CasesLayout.tsx frontend/src/pages/CasesKanban.tsx frontend/src/pages/CaseVault.tsx frontend/src/pages/CaseCalendar.tsx
git rm frontend/src/pages/Cases.tsx
```
Report build-clean; do not commit.

---

## Self-Review

**Spec coverage (against `2026-06-25-case-system-ux-design.md`):**
- §B three tabs → Task 3 (`CasesLayout` + routes). ✓
- §A stage taxonomy → Task 1. ✓
- §A/§H idempotent stage remap + migration 013 → Task 2. ✓
- Kanban auto = `stage ≠ closed` → Task 3 Step 2 filters out `closed`. ✓
- Vault = Enquiries placeholder + All Cases + create → Task 3 Step 3. ✓
- Calendar placeholder agenda → Task 3 Step 4. ✓
- Leads/notes/exhibits/next-date/drafting → **out of scope for Plan 1** (Plans 2–7); not expected here. ✓

**Placeholder scan:** No "TBD"/"handle edge cases"/etc. The Enquiries/Calendar "placeholders" are intentional skeleton UI with concrete copy, not plan placeholders. ✓

**Type consistency:** `STAGES`/`STAGE_KEYS`/`DEFAULT_STAGE`/`LEGACY_STAGE_REMAP` names match between `stages.py` and tests; FE uses existing `api.*` method names and `CaseFile`/`CaseParty` types verbatim from `api.ts`. ✓
