# Case System UX — Plan 3: Adaptive "This Stage" Action Rail Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the open case file a persistent right-hand "This stage" rail that states the stage's focus, offers stage-specific shortcut actions, and hosts a one-click "Advance to <next stage>" button — without changing the fixed tab set.

**Architecture:** The per-stage guidance is a code-defined catalog in `stages.py` (`STAGE_GUIDES` + `next_stage`/`STAGE_FLOW`), exposed through `/case-files/meta` so the backend stays the single source of truth. A new `StageRail` React component renders `meta.stage_guides[currentStage]`; available actions map to existing behaviours (switch tab, open the edit modal, jump to billing), actions slated for later plans render muted. Advance reuses the existing `updateCaseFile({stage})` path, so the stage-change audit fires for free.

**Tech Stack:** Flask + SQLAlchemy (SQLite in tests via `db.create_all`), pytest; React + TypeScript + Vite, TanStack Query, Tailwind tokens.

## Global Constraints

- Never run git commits/pushes — Parth does git. Stage only; run the gate and report.
- No new migration in this plan (no schema change — `STAGE_GUIDES` is code-only).
- Stage keys (verbatim): `engaged, notice, filed, hearings_evidence, arguments, judgment, closed`.
- The rail is a *suggestion + shortcut*, never a gate — the header stage `<select>` stays for arbitrary/backward moves.
- Backend stays green (`pytest`); frontend builds clean (`npm run build`).

---

### Task 1: `STAGE_GUIDES` + `next_stage` + `/meta` exposure

**Files:**
- Modify: `backend/app/case/stages.py` (append catalog + helper)
- Modify: `backend/app/api/case_files.py:32-38` (`/meta` payload + import)
- Test: `backend/tests/test_case_stages.py`, `backend/tests/test_case_files_api.py`

**Interfaces:**
- Produces: `STAGE_GUIDES: dict[str, {"focus": str, "actions": list[{"key","label","available"}]}]` covering every stage key; `STAGE_FLOW: dict[str, str|None]`; `next_stage(key) -> str|None`. `/meta` JSON gains `"stage_guides"` and `"stage_flow"`.

- [ ] **Step 1: Write the failing catalog test**

Append to `backend/tests/test_case_stages.py` (extend the import from `app.case.stages` to include `STAGE_GUIDES, STAGE_FLOW, next_stage`):

```python
def test_stage_guides_cover_every_stage():
    assert set(STAGE_GUIDES) == STAGE_KEYS
    for key, guide in STAGE_GUIDES.items():
        assert isinstance(guide["focus"], str) and guide["focus"]
        assert guide["actions"], f"{key} has no actions"
        for a in guide["actions"]:
            assert set(a) == {"key", "label", "available"}
            assert isinstance(a["available"], bool)


def test_next_stage_walks_the_lifecycle_and_ends_at_closed():
    assert next_stage("engaged") == "notice"
    assert next_stage("hearings_evidence") == "arguments"
    assert next_stage("closed") is None
    assert STAGE_FLOW["judgment"] == "closed"
    assert STAGE_FLOW["closed"] is None
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd backend && python -m pytest tests/test_case_stages.py -v`
Expected: FAIL — ImportError on `STAGE_GUIDES`.

- [ ] **Step 3: Append the catalog + helper to `stages.py`**

Add to the end of `backend/app/case/stages.py`:

```python
# Per-stage guidance for the case-file "This stage" rail. `available` is False
# for actions whose feature ships in a later plan (record proceedings = Plan 6,
# mark exhibit = Plan 5, drafting = Plan 7); those render as muted hints.
STAGE_GUIDES = {
    "engaged": {
        "focus": "Record the facts and sign the wakalatnama.",
        "actions": [
            {"key": "note", "label": "Add facts / note", "available": True},
            {"key": "new_draft", "label": "Draft wakalatnama", "available": False},
        ],
    },
    "notice": {
        "focus": "Draft and send the legal notice.",
        "actions": [
            {"key": "new_draft", "label": "Draft legal notice", "available": False},
            {"key": "note", "label": "Record notice sent", "available": True},
        ],
    },
    "filed": {
        "focus": "Petition filed — track show-cause and replies.",
        "actions": [
            {"key": "record_proceedings", "label": "Record proceedings", "available": False},
            {"key": "add_party", "label": "Add a party", "available": True},
            {"key": "documents", "label": "File a document", "available": True},
        ],
    },
    "hearings_evidence": {
        "focus": "Mark evidence, log cross-examination, track dates.",
        "actions": [
            {"key": "record_proceedings", "label": "Record proceedings", "available": False},
            {"key": "mark_exhibit", "label": "Mark an exhibit", "available": False},
            {"key": "note", "label": "Log cross-examination", "available": True},
        ],
    },
    "arguments": {
        "focus": "Final hearing and arguments.",
        "actions": [
            {"key": "record_proceedings", "label": "Record proceedings", "available": False},
            {"key": "note", "label": "Add a note", "available": True},
        ],
    },
    "judgment": {
        "focus": "Judgment reserved or delivered.",
        "actions": [
            {"key": "note", "label": "Record judgment", "available": True},
            {"key": "documents", "label": "Upload the order", "available": True},
        ],
    },
    "closed": {
        "focus": "Disposed — raise the bill and plan the next course.",
        "actions": [
            {"key": "raise_bill", "label": "Raise a bill", "available": True},
            {"key": "note", "label": "Record future course", "available": True},
        ],
    },
}

_STAGE_ORDER = [s["key"] for s in STAGES]
STAGE_FLOW = {
    key: (_STAGE_ORDER[i + 1] if i + 1 < len(_STAGE_ORDER) else None)
    for i, key in enumerate(_STAGE_ORDER)
}


def next_stage(key):
    return STAGE_FLOW.get(key)
```

- [ ] **Step 4: Run the catalog test to verify it passes**

Run: `cd backend && python -m pytest tests/test_case_stages.py -v`
Expected: PASS.

- [ ] **Step 5: Write the failing meta test**

Append to `backend/tests/test_case_files_api.py`:

```python
def test_meta_includes_stage_guides_and_flow(client, make_owner):
    headers, _ = make_owner()
    body = client.get('/api/v1/case-files/meta', headers=headers).get_json()
    assert 'stage_guides' in body and 'engaged' in body['stage_guides']
    assert body['stage_guides']['engaged']['actions'][0]['key'] == 'note'
    assert body['stage_flow']['engaged'] == 'notice'
    assert body['stage_flow']['closed'] is None
```

- [ ] **Step 6: Run it to verify it fails**

Run: `cd backend && python -m pytest tests/test_case_files_api.py::test_meta_includes_stage_guides_and_flow -v`
Expected: FAIL — keys absent from `/meta`.

- [ ] **Step 7: Add the keys to `/meta`**

In `backend/app/api/case_files.py`, extend the stages import (line 9-11) to add `STAGE_GUIDES, STAGE_FLOW`:

```python
from app.case.stages import (
    STAGES, EVENT_KINDS, PRIORITIES, STAGE_GUIDES, STAGE_FLOW,
    is_valid_stage, is_valid_priority,
)
```

Replace the `case_meta` return (lines 36-38) with:

```python
    return jsonify({'stages': STAGES, 'event_kinds': EVENT_KINDS,
                    'priorities': PRIORITIES, 'doc_types': DOC_TYPES,
                    'expense_categories': EXPENSE_CATEGORIES,
                    'stage_guides': STAGE_GUIDES, 'stage_flow': STAGE_FLOW})
```

- [ ] **Step 8: Run the meta test + full suite**

Run: `cd backend && python -m pytest tests/test_case_files_api.py -q && python -m pytest -q`
Expected: PASS (261).

- [ ] **Step 9: Stage (do NOT commit)**

```bash
git add backend/app/case/stages.py backend/app/api/case_files.py backend/tests/test_case_stages.py backend/tests/test_case_files_api.py
```

---

### Task 2: `StageRail` component + CaseDetail integration

**Files:**
- Create: `frontend/src/components/StageRail.tsx`
- Modify: `frontend/src/api.ts:351-357` (`CaseMeta` type)
- Modify: `frontend/src/pages/CaseDetail.tsx` (render the rail beside the tabs; wire actions/advance)
- Gate: `npm run build` clean.

**Interfaces:**
- Consumes: `CaseMeta.stage_guides`, `CaseMeta.stage_flow`, `CaseMeta.stages`.
- Produces: `StageRail` component with props `{ stage: string; meta?: CaseMeta; canUpdate: boolean; onAction: (key: string) => void; onAdvance: (nextKey: string) => void; advancing: boolean }`.

- [ ] **Step 1: Extend the `CaseMeta` type**

In `frontend/src/api.ts`, replace the `CaseMeta` interface (lines 351-357) with:

```ts
export interface StageAction { key: string; label: string; available: boolean }
export interface StageGuide { focus: string; actions: StageAction[] }

export interface CaseMeta {
  stages: { key: string; label: string }[];
  event_kinds: string[];
  priorities: { key: string; label: string }[];
  doc_types: { key: string; label: string }[];
  expense_categories: { key: string; label: string }[];
  stage_guides: Record<string, StageGuide>;
  stage_flow: Record<string, string | null>;
}
```

- [ ] **Step 2: Create the `StageRail` component**

Create `frontend/src/components/StageRail.tsx`:

```tsx
import { CaseMeta } from '../api';
import { ArrowRight, ChevronRight, Lock } from 'lucide-react';

interface Props {
  stage: string;
  meta?: CaseMeta;
  canUpdate: boolean;
  onAction: (key: string) => void;
  onAdvance: (nextKey: string) => void;
  advancing: boolean;
}

export default function StageRail({ stage, meta, canUpdate, onAction, onAdvance, advancing }: Props) {
  const guide = meta?.stage_guides?.[stage];
  const nextKey = meta?.stage_flow?.[stage] ?? null;
  const nextLabel = nextKey ? (meta?.stages.find((s) => s.key === nextKey)?.label ?? nextKey) : null;
  if (!guide) return null;

  return (
    <aside className="lg:w-72 shrink-0 lg:sticky lg:top-6 self-start space-y-4">
      <div className="card p-4">
        <div className="eyebrow mb-1">This stage</div>
        <p className="text-sm text-ink-muted leading-snug mb-4">{guide.focus}</p>
        <div className="space-y-1.5">
          {guide.actions.map((a) =>
            a.available ? (
              <button key={a.key} onClick={() => onAction(a.key)}
                className="w-full flex items-center justify-between text-left text-sm text-ink
                           px-3 py-2 border border-rule hover:border-oxblood hover:text-oxblood transition-colors rounded-sm">
                <span>{a.label}</span><ChevronRight size={14} />
              </button>
            ) : (
              <div key={a.key}
                className="w-full flex items-center justify-between text-left text-sm text-ink-faint
                           px-3 py-2 border border-dashed border-rule rounded-sm"
                title="Arrives in a later phase">
                <span>{a.label}</span><Lock size={12} />
              </div>
            ),
          )}
        </div>
      </div>

      {canUpdate && nextKey && (
        <button onClick={() => onAdvance(nextKey)} disabled={advancing}
          className="btn-primary w-full justify-center disabled:opacity-50">
          <span>Advance to {nextLabel}</span><ArrowRight size={14} />
        </button>
      )}
      {!nextKey && (
        <div className="text-2xs uppercase tracking-eyebrow text-ink-faint text-center">Final stage</div>
      )}
    </aside>
  );
}
```

- [ ] **Step 3: Import the rail in `CaseDetail.tsx`**

Add to the imports at the top of `frontend/src/pages/CaseDetail.tsx`:

```tsx
import StageRail from '../components/StageRail';
```

- [ ] **Step 4: Add the rail's action handler (next to the other handlers, e.g. after `stageMutation`)**

In `CaseDetail.tsx`, after the `stageMutation` definition (around line 112), add:

```tsx
  const railAction = (key: string) => {
    switch (key) {
      case 'note': setTab('timeline'); break;
      case 'add_party': openEdit(); break;
      case 'documents': setTab('documents'); break;
      case 'raise_bill': setTab('fees'); break;
      default: break;
    }
  };
```

- [ ] **Step 5: Wrap the tabbed body and mount the rail**

In `CaseDetail.tsx`, the tabbed content currently sits directly after `</header>` as: the `{/* Tabs */}` `<div>` followed by the four `{tab === '...' && (...)}` panels, ending right before `{/* Edit modal */}`.

Wrap that whole block (from `{/* Tabs */}` through the end of the `{tab === 'fees' && (...)}` panel) in a two-column flex, and add the rail as the second column. Concretely, replace the opening line:

```tsx
      {/* Tabs */}
      <div className="flex gap-1 border-b border-rule mb-6">
```
with:

```tsx
      <div className="flex flex-col lg:flex-row gap-8">
      <div className="flex-1 min-w-0">
      {/* Tabs */}
      <div className="flex gap-1 border-b border-rule mb-6">
```

and replace the closing of the fees panel + the start of the edit modal:

```tsx
        </div>
      )}

      {/* Edit modal */}
```
with:

```tsx
        </div>
      )}
      </div>

      <StageRail stage={caseFile.stage} meta={meta} canUpdate={canUpdate}
        onAction={railAction} onAdvance={(k) => stageMutation.mutate(k)}
        advancing={stageMutation.isPending} />
      </div>

      {/* Edit modal */}
```

(The first `</div>` closes the `flex-1` main column; the second closes the `flex flex-row` row after the rail.)

- [ ] **Step 6: Build the frontend**

Run: `cd frontend && npm run build`
Expected: build succeeds, no TypeScript errors, balanced JSX.

- [ ] **Step 7: Stage (do NOT commit)**

```bash
git add frontend/src/api.ts frontend/src/components/StageRail.tsx frontend/src/pages/CaseDetail.tsx
```

---

## Self-Review

**Spec coverage (against `2026-06-25-case-system-ux-design.md` §D + per-stage rail table):**
- Fixed tabs unchanged; adaptive "This stage" rail beside them → Task 2. ✓
- Rail hosts the advance-stage button; stage-change audit reused → Task 2 Step 5 (`stageMutation`). ✓
- Per-stage action list (Engaged…Closed) with later-plan actions deferred → Task 1 `STAGE_GUIDES` (`available:false`). ✓
- Backend single source of truth via `/meta` → Task 1. ✓

**Deferred-by-design:** `record_proceedings`, `mark_exhibit`, `new_draft` render muted (locked) — wired live in Plans 6/5/7. The header stage `<select>` remains for backward/arbitrary moves.

**Placeholder scan:** none. Locked actions are intentional UI with a tooltip, not stubs.

**Type consistency:** `StageGuide`/`StageAction` shape matches `STAGE_GUIDES` JSON (`focus`, `actions[].{key,label,available}`); `stage_flow` values `string|null` match `next_stage`. `StageRail` props match the call site in `CaseDetail`.
