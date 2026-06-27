# Case File Spine + Kanban — Design Spec

**Status:** Approved (brainstorming) — ready for implementation planning
**Date:** 2026-06-23
**Sub-project:** 2 of the Snappy Legal CRM (foundation = Firm Tenancy & RBAC, complete)

## Purpose

Digitize the life of a legal case. The **case file** is the spine of the CRM:
the container that documents, hearings, evidence, calendar dates, notes, and
invoices all attach to. This sub-project builds that spine and its two primary
faces — a **kanban board** across all cases, and an **"open the file" detail
view** for working through one case step by step — plus the link that lets the
existing billing roll up per case.

Later sub-projects (documents/storage, calendar/hearings, drafting/AI) hang off
the two seams this one establishes: `case_file_id` and the **timeline step**
(`case_events`).

## Guiding constraints

- **Solo-first.** Build a flow that works end to end for a single advocate (the
  firm Owner). Multi-user nuance is deferred.
- **RBAC only, parked.** Access is firm-wide, gated by a new `case_files`
  permission module — exactly like clients/invoices today. No per-matter
  visibility walls, no assignment-based access in this sub-project. The Owner
  (the solo advocate) resolves to all permissions automatically, so the solo
  flow needs no permission setup.
- **Reuse existing patterns.** `firm_id` scope + `created_by_user_id`
  attribution; per-firm sequence numbering like invoices; Supabase JWT;
  React Query + the existing design system on the frontend.
- **Migration delivered as SQL** for Parth to apply manually on Supabase
  (migration `009`); no code path runs it. Tests build schema from models on
  in-memory SQLite.
- **Git:** Parth handles all commits. End each task at a green test run.

## Scope

### In scope (this sub-project)

1. **CaseFile** entity — firm-scoped, per-firm case numbering, core litigation
   fields, a workflow **stage** (kanban column), an optional handling advocate,
   and a next-hearing-date field.
2. **CaseParty** child rows — the cause-title parties `{name, role}`.
3. **CaseEvent** timeline/diary — chronological **steps** that form the
   "open the file" experience; the attach-point for documents/hearings later.
4. **Billing link** — nullable `case_file_id` on invoices + an optional case
   picker on the invoice form; the case detail lists its linked invoices.
5. **Kanban board** (cards grouped by stage, drag to change stage) and a
   **list view** across cases.
6. **Case detail view** — header + timeline + parties + linked invoices.
7. **`case_files` RBAC module** in the permission catalog (CRUD).

### Out of scope (later sub-projects)

- Document/evidence uploads and the per-case vault (sub-project 3).
- Structured hearing scheduling and the firm-wide calendar view (sub-project 3
  leads with this; CaseEvent already carries `event_date` to feed it).
- Templates + AI-assisted drafting (sub-project 4).
- Per-matter access walls (assignee/viewer visibility, `case_files.access_all`).
  The intent is recorded; enforcement comes when we scale past solo.

## Data model

All money/date/JSON conventions follow `app/models/models.py`. New tables live
in a new module `app/models/case.py` (imported in `main.py` so `create_all`
picks them up), keeping case concerns in one focused file.

### `case_files`

| Column | Type | Notes |
|---|---|---|
| `id` | Integer PK | |
| `firm_id` | FK `firms.id`, index | access scope |
| `created_by_user_id` | FK `users.id`, index | attribution |
| `case_number` | String(50), index | per-firm sequence, e.g. `CF/2026/0001` |
| `title` | String(300), not null | matter/case name |
| `client_id` | FK `clients.id`, not null | billed/instructing client |
| `matter_type` | String(80) | practice area; reuse the legal-feed list |
| `court` | String(200) | e.g. "Delhi High Court" |
| `court_case_number` | String(120) | official filing/registration no. (free text) |
| `stage` | String(40), not null, default `intake` | kanban column key |
| `position` | Integer, default 0 | intra-stage ordering for drag |
| `handling_advocate_user_id` | FK `users.id`, nullable | shown on the card |
| `next_hearing_date` | Date, nullable | surfaced on card + later calendar |
| `open_date` | Date, default today | |
| `description` | Text | |
| `created_at` / `updated_at` | DateTime | |

Constraint: `UNIQUE (firm_id, case_number)` (mirrors the invoice constraint).

### `case_parties`

| Column | Type | Notes |
|---|---|---|
| `id` | Integer PK | |
| `case_file_id` | FK `case_files.id`, index, cascade delete | |
| `name` | String(300), not null | |
| `role` | String(60) | petitioner / respondent / appellant / … (free text, suggested values in UI) |
| `created_at` | DateTime | |

### `case_events` (timeline / case diary — the "steps")

| Column | Type | Notes |
|---|---|---|
| `id` | Integer PK | |
| `case_file_id` | FK `case_files.id`, index, cascade delete | |
| `firm_id` | FK `firms.id`, index | denormalized so the future calendar can range-query all firm events without a join |
| `created_by_user_id` | FK `users.id` | who logged the step |
| `event_date` | Date, not null, index | when the step happened / is set for |
| `kind` | String(30), not null, default `note` | code-defined set (below) |
| `title` | String(300), not null | |
| `notes` | Text | |
| `created_at` / `updated_at` | DateTime | |

Documents (sub-project 3) will attach to a `case_event` via a future
`event_id` FK, so a step can carry its drafts/exhibits.

### `invoices` (modified)

Add `case_file_id` (FK `case_files.id`, nullable, index). Optional — a blank
value preserves today's behavior. Surfaced via an optional "Case" picker on the
invoice form (filtered to the chosen client's cases) and listed on the case
detail view.

## Code-defined enums

In `app/case/` (new package, mirrors `app/rbac/`):

```python
# stages drive the kanban columns, in display order
STAGES = [
    {"key": "intake",         "label": "Intake"},
    {"key": "drafting",       "label": "Drafting"},
    {"key": "filed",          "label": "Filed"},
    {"key": "in_hearing",     "label": "In Hearing"},
    {"key": "awaiting_order", "label": "Awaiting Order"},
    {"key": "closed",         "label": "Closed"},
]

# timeline step kinds (extensible; documents/hearings add more later)
EVENT_KINDS = ["note", "filing", "hearing", "order", "step"]
```

A case is considered closed when `stage == "closed"` (no separate status field).
Labels/columns are code-defined for v1; per-firm customization is a later
concern.

## Numbering

`generate_case_number(firm_id)` mirrors `generate_invoice_number`: per-firm,
year-segmented sequence with a constant prefix for v1 — `CF/{YYYY}/{NNNN}`,
where the sequence is `max(existing for firm this year) + 1`, zero-padded to 4.
Uniqueness is backstopped by the `(firm_id, case_number)` constraint. A
configurable prefix (a `case_prefix` on `FirmDetails`) is deferred.

## RBAC integration

Add to the `MODULES` catalog in `app/rbac/permissions.py`:

```python
{"key": "case_files", "label": "Case Files", "actions": CRUD},
```

- `ALL_PERMISSIONS` recomputes automatically, so the **Owner system role gains
  `case_files.*` with no migration** (the Owner is resolved to `ALL_PERMISSIONS`
  dynamically in `load_firm_context`). The solo advocate therefore has full
  access out of the box.
- `DEFAULT_ROLES` gains sensible case_files grants for Partner/Associate/Staff
  (Partner: CRUD; Associate: create/read/update; Staff: read). These only affect
  newly seeded firms; existing non-Owner roles get the new permission via the
  in-app Roles editor — consistent with how the catalog already works.
- Every case endpoint stacks `@jwt_required` + `@require_permission('case_files.X')`
  and scopes by `g.firm_id`, identical to the clients/invoices pattern.

## API (all under `/api/v1`, firm-scoped, permission-gated)

`app/api/case_files.py` (blueprint registered at `/api/v1`):

| Method & path | Permission | Purpose |
|---|---|---|
| `GET /case-files` | `case_files.read` | list; filters: `stage`, `client_id`, `assignee`, `search`; returns card-shaped dicts. Frontend groups by stage for the board. |
| `POST /case-files` | `case_files.create` | create; auto `case_number`; accepts nested `parties[]`. |
| `GET /case-files/<id>` | `case_files.read` | full detail: case + parties + linked-invoice summaries. |
| `PATCH /case-files/<id>` | `case_files.update` | edit fields; `parties[]` is a full replace-set when present. |
| `PATCH /case-files/<id>/move` | `case_files.update` | kanban drag: `{stage, position}`. |
| `DELETE /case-files/<id>` | `case_files.delete` | delete (cascades parties + events). |
| `GET /case-files/<id>/events` | `case_files.read` | timeline, ordered by `event_date` then `created_at`. |
| `POST /case-files/<id>/events` | `case_files.update` | add a step `{event_date, kind, title, notes}`. |
| `PATCH /case-events/<id>` | `case_files.update` | edit a step. |
| `DELETE /case-events/<id>` | `case_files.update` | remove a step. |
| `GET /case-files/meta` | `case_files.read` | returns `{stages: STAGES, event_kinds: EVENT_KINDS}` for the UI. |

Invoice endpoints accept an optional `case_file_id` on create/update (validated
to belong to the same firm). All `<id>` lookups filter by `firm_id`, returning
404 for another firm's records (cross-firm isolation, same as billing).

## Frontend

Design system + React Query patterns per existing pages (e.g. `Items.tsx`).

- **`pages/Cases.tsx`** — the **kanban board**: columns from `STAGES`, draggable
  cards (title, client, court, next date, handling advocate), and a list/table
  toggle for large caseloads. A "New case" action opens a create form
  (title, client picker, type, court, case no., parties, stage).
- **`pages/CaseDetail.tsx`** — **"open the file"**: header (cause-title from
  parties, court, case no., stage selector, client, advocate, next date) + the
  **timeline/diary** (chronological steps with add/edit/delete) + a parties
  panel + a linked-invoices panel (with a "New invoice for this case" shortcut).
- **Invoice form** (`NewInvoice.tsx`) — optional **Case** picker, filtered to
  the selected client's cases.
- **Nav** (`Layout.tsx`) — a "Cases" link in the **Practice** group, gated by
  `case_files.read`.
- **`api.ts`** — `caseFiles` methods + types (`CaseFile`, `CaseParty`,
  `CaseEvent`, stage/kind meta); `usePermissions` gates create/edit/delete/move
  controls.

## Testing

TDD throughout (failing test → implement → green), in-memory SQLite.

- **Models**: `generate_case_number` per-firm sequencing + year segmentation;
  parties/events cascade on case delete; stage default.
- **API**: CRUD; stage `move`; nested parties replace-set; events CRUD;
  invoice `case_file_id` link validation; `meta` payload.
- **Isolation**: a second firm cannot read/patch/delete/move another firm's case
  or its events (404), mirroring `test_firm_isolation.py`.
- **Permission gates**: a role lacking `case_files.read` gets 403.
- **Frontend**: `npm run build` typechecks clean.

## Migration (009, manual)

`backend/migrations/009_case_files.sql` — additive, non-destructive:

- `CREATE TABLE case_files`, `case_parties`, `case_events` (with FKs + the
  `(firm_id, case_number)` unique constraint and useful indexes).
- `ALTER TABLE invoices ADD COLUMN case_file_id INTEGER REFERENCES case_files(id)`.

No backfill required (these are new concepts). The `case_files.*` permissions
need no migration — Owners get them dynamically; other roles via the Roles
editor.

## The two seams later sub-projects build on

1. **`case_file_id`** — documents, evidence, calendar entries, and invoices all
   reference a case.
2. **`case_events` (the timeline step)** — documents/hearings attach to a step,
   so the "page through the file" view deepens without restructuring.
