# Case System UX Redesign — Design Spec

**Date:** 2026-06-25
**Status:** Approved (design), pending spec review → implementation plans
**Builds on:** `2026-06-23-case-file-spine-design.md`, `2026-06-23-deeper-case-record-design.md`, `2026-06-23-documents-vault-design.md`

## Goal

Settle the UX of the case-file system before further phases. Restructure the "Cases" area into three tabs (Kanban / Case Vault / Calendar) and turn the open case file into a stage-adaptive "real case file" experience whose focus follows the advocate through the litigation lifecycle — intake notes → wakalatnama/notice drafting → file/evidence/date management → judgment & billing.

## Problem statement (from stakeholder)

A solo-advocate firm (~4 staff; assistant/viewer roles deferred). His flow:

1. **Intake** — hears the client's story, takes notes, decides to take the case or not.
2. **Engaged / pre-filing** — signs wakalatnama, drafts a legal notice (tweaks templates per case; AI-assisted later).
3. **Litigation** — files petition → show-cause → replies → evidence, cross-examination, hearings; after every appearance the court fixes the **next date** ("tareekh"). Heavy document/evidence/date management.
4. **Judgment** — final hearing, judgment reserved/delivered.
5. **Post-judgment** — billing, future course of action.

The **focus changes by stage**. Documents are in English **or** Hindi. **Notes are first-class and visible at every stage.** Guiding principle: **make his work easier, not more complicated.**

---

## Design decisions (settled in brainstorming)

| # | Decision | Choice |
|---|----------|--------|
| Stage focus | How the file expresses stage | **Fixed tabs + adaptive "This stage" action rail** |
| Intake | Where a prospective matter lives | **Lightweight Lead entity, separate; converts to a case file on accept** |
| Notes | How notes behave | **Always-on notes panel + any note pinnable to timeline / attachable to an event/document** |
| Evidence | Evidence vs Documents | **Exhibit register** (mark, party, status, file, hearing link) |
| Kanban scope | What appears on the board | **Auto by stage** — every case where stage ≠ Closed/Declined |
| Drafting | Scope this phase | **Stub the seam** — mock template → draft document; real editor/templates/AI later |
| Next date | Recurring court-date cycle | **"Record proceedings" combined action + inline header next-date control** |

---

## A. Stage taxonomy

Replaces the current `STAGES` (`intake→drafting→filed→in_hearing→awaiting_order→closed`). Leads are pre-case (not a stage). A case file moves through:

```
Engaged → Notice → Filed → Hearings & Evidence → Arguments → Judgment → Closed
```

- **Engaged** — wakalatnama signed, facts recorded.
- **Notice** — drafting/sending legal notice.
- **Filed** — petition filed, show-cause, replies.
- **Hearings & Evidence** — exhibits marked, cross-examination, hearing dates.
- **Arguments** — final hearing / arguments.
- **Judgment** — reserved/delivered.
- **Closed** — disposed (billing + future course).

`stages.py` keys: `engaged, notice, filed, hearings_evidence, arguments, judgment, closed`. `DEFAULT_STAGE='engaged'`. A separate **terminal label `declined`** applies only to Leads, not case files. Stage set is tunable; nothing in the model hard-codes the count.

**Migration note:** migrations 009–012 are now applied on Supabase, so `case_files` rows may already exist with the old stage keys. Plan 1's migration (013) therefore includes an idempotent **stage remap** (no-op if no rows): `intake→engaged`, `drafting→notice`, `filed→filed`, `in_hearing→hearings_evidence`, `awaiting_order→judgment`, `closed→closed`. `stage` is a plain `VARCHAR` (no DB enum), so this is a simple `UPDATE`. `record_stage_change` audit behaviour is unchanged.

## B. Three tabs ("Cases" area)

Nav entry "Cases" (gated by `case_files.read`) opens a tabbed area:

```
Cases ▸  [ Kanban ]  [ Case Vault ]  [ Calendar ]
```

- **Kanban** — every case where `stage ∉ {closed}` (declined never reaches a case file). Drag across the stage columns of section A. Cards show priority dot + next date.
- **Case Vault** — two stacked sections: **Enquiries** (leads) and **All Cases**. Both "New enquiry" and "New case" start here. Filters: Active / Prospective / Declined / Closed. Search by title/number/client.
- **Calendar** — month + agenda view of all hearing dates & deadlines across cases; click-through to the file.

Implemented as three routes under a shared `Cases` shell with a sub-tab bar; the existing single `Cases.tsx` becomes the Kanban view.

## C. Lead → Case conversion

A **Lead** (`leads` table) is light: contact name, phone/email, matter summary, free-form intake notes, status (`open`/`accepted`/`declined`), decision timestamp, optional `converted_case_file_id`. **No CF number is allocated for a lead.**

- **Accept** → create a `CaseFile` at stage `engaged`, copy the lead's intake notes in as the first `case_note`, set `case_files.lead_id` and `leads.converted_case_file_id`/`status='accepted'`.
- **Decline** → `status='declined'`; remains searchable in the Enquiries section, never on the Kanban.

## D. The open case file — fixed tabs + adaptive rail + notes panel

```
┌─ CF/2026/0042 · Sharma v. State ─────── Stage: Hearings & Evidence ▼  Next date: 5 Jul 2026 ✎ ┐
│  Overview │ Documents │ Evidence │ Fees                                                        │
├──────────────────────────────────────┬───────────────────────┬───────────────────────────────┤
│  TIMELINE (roznama)                   │ THIS STAGE            │ NOTES  + jot…                 │
│  ● 25 Jun [hearing] adjourned → 5 Jul │ ▸ Record proceedings  │ · carry original docs (5 Jul) │
│     └ 📌 carry original docs          │ ▸ Mark exhibit        │ · limitation angle weak       │
│  ● 20 Jun [filing] reply filed        │ ▸ Log cross-exam      │                               │
│  (click an entry → opens its detail)  │ ▸ → Arguments         │                               │
└──────────────────────────────────────┴───────────────────────┴───────────────────────────────┘
```

- **Tabs are fixed** (Overview / Documents / Evidence / Fees) — predictable across stages.
- **"This stage" action rail** shows stage-typical shortcut actions and hosts the **→ advance stage** button. The rail is *suggestion + shortcut*, never a gate — he can do anything at any stage.
- **Notes panel** is present across all tabs (docked). A note can be **pinned to the timeline** (shows as a standalone marker) or **attached to a hearing/filing/document** (`event_id`/`document_id`).
- **Overview timeline** is the chronological `case_events` stream; clicking an entry expands its detail.

### Per-stage rail content (initial)

| Stage | Rail actions |
|-------|--------------|
| Engaged | Add facts/notes · New draft from template (wakalatnama) · → Notice |
| Notice | New draft from template (legal notice) · Record notice sent · → Filed |
| Filed | Record proceedings · Add party · File reply · → Hearings & Evidence |
| Hearings & Evidence | Record proceedings · Mark exhibit · Log cross-exam · → Arguments |
| Arguments | Record proceedings · → Judgment |
| Judgment | Record proceedings · Record judgment · → Closed |
| Closed | Raise bill · Record future course |

## E. Evidence — exhibit register

`case_exhibits` table. Each exhibit:

- **mark** — e.g. `Ex. P-1`, `Ex. D-1` (free text; suggested next mark per party).
- **description**.
- **producing party** — plaintiff/petitioner/defendant/respondent (text; or `case_party_id` link).
- **status** — `marked` / `admitted` / `objected` / `denied`.
- **file** — `document_id` link to a `case_documents` row.
- **hearing** — optional `hearing_event_id` (the date it came in through).

The Evidence tab renders the register table with add/edit; uploading an exhibit's file reuses the documents upload path.

## F. Drafting — seam only this phase

At **Engaged**/**Notice**, the rail offers **"New draft from template"** → a small in-code mock catalog (`wakalatnama`, `legal_notice`) of boilerplate text. Selecting one generates a `draft`-type document (a `.txt`/`.docx` produced from the boilerplate, stored via the existing document-storage path) that he downloads, edits offline, and re-uploads. **Out of scope this phase:** in-app rich-text editor, template CRUD/variables, AI generation, Hindi/English templating — a dedicated later phase.

## G. Calendar + hearing source of truth + next-date mechanism

**Source of truth:** hearings are `case_events` of kind `hearing`. **`case_files.next_hearing_date` becomes derived** = the soonest future hearing event, recomputed whenever hearing events change. Header, Kanban card, and Calendar always agree.

**`case_events` (kind=`hearing`) gains:** `purpose` (what the date is *for*) and `outcome` (what happened, filled after the appearance).

**Next-date mechanism (the tareekh cycle):**

1. **Inline header control** — `Next date: <date> ✎` lets him correct/advance the next date in one click at any in-court stage.
2. **"Record proceedings"** rail action (Filed → Judgment) captures both halves of a court date in one step:
   ```
   RECORD PROCEEDINGS — 25 Jun 2026
     What happened today:  [ … ]            → outcome on the current hearing event
     Purpose of next date: [ Evidence ▾ ]   → purpose on the new hearing event
     Next date:            [ 05 Jul 2026 ]  → new hearing event
   ```
   Effect: the current hearing event's `outcome` is recorded; a new hearing event is created for the next date+purpose; `next_hearing_date` is recomputed. The timeline thus becomes the **order-sheet / roznama** — a running ledger of every date, what happened, what's next.

**Calendar view:** month grid + agenda list over hearing events (and case `next_hearing_date`); click-through to the file. **Reminders/notifications: later phase.**

## H. Data model deltas (migrations — Parth applies manually)

- **`leads`** — `id, firm_id, created_by_user_id, contact_name, phone, email, matter_summary, intake_notes, status('open'|'accepted'|'declined'), decided_at, converted_case_file_id (FK case_files, nullable), created_at`.
- **`case_files`** — add `lead_id` (FK leads, nullable). Stage values updated per section A. `next_hearing_date` becomes derived (no schema change; recompute in service).
- **`case_notes`** — `id, firm_id, case_file_id, body, pinned(bool default false), event_id (FK case_events, nullable), document_id (FK case_documents, nullable), created_by_user_id, created_at`.
- **`case_exhibits`** — `id, firm_id, case_file_id, exhibit_mark, description, party, status('marked'|'admitted'|'objected'|'denied'), document_id (FK case_documents, nullable), hearing_event_id (FK case_events, nullable), created_by_user_id, created_at`.
- **`case_events`** — add `purpose VARCHAR`, `outcome TEXT` (used by kind=`hearing`).

All additive/non-destructive; one migration file per plan (numbers continue from **013**, since 009–012 are now applied). Plan 1's `013` also carries the idempotent stage remap from section A. RBAC: `case_files` and `documents` modules already exist; Owner auto-resolves new behaviour. A new `leads` permission module (CRUD) is added to the catalog — Owner automatic; defaults granted to Partner/Associate; Staff read.

## I. API surface (additions)

- `Leads`: `GET/POST /leads`, `GET/PATCH/DELETE /leads/<id>`, `POST /leads/<id>/convert` → returns the new case file.
- `Notes`: `GET/POST /case-files/<id>/notes`, `PATCH/DELETE /case-notes/<id>` (incl. `pinned`, `event_id`, `document_id`).
- `Exhibits`: `GET/POST /case-files/<id>/exhibits`, `PATCH/DELETE /case-exhibits/<id>`.
- `Proceedings`: `POST /case-files/<id>/proceedings` (records current outcome + creates next hearing event + recomputes `next_hearing_date`).
- `Drafts`: `GET /draft-templates` (mock catalog), `POST /case-files/<id>/drafts` (`{template_key}` → creates a draft document).
- `Calendar`: `GET /calendar?from=&to=` → hearing events + case next dates across the firm.
- `/case-files/meta` extended: new `stages`, `event_purposes`, `exhibit_statuses`, `draft_templates`.

## J. Frontend components

- `pages/Cases.tsx` → becomes the **Kanban** view inside a `CasesLayout` shell with sub-tabs.
- `pages/CaseVault.tsx` — Enquiries + All Cases, filters/search, create.
- `pages/CaseCalendar.tsx` — month + agenda.
- `pages/CaseDetail.tsx` — keep tabs; add the **action rail** (per-stage), the **notes panel** (pin/attach), the **Evidence** register tab, the **next-date** header control, and the **Record proceedings** + **New draft from template** modals.
- `api.ts` — types/methods for leads, notes, exhibits, proceedings, drafts, calendar.

## K. Testing

Backend: pytest on SQLite (`create_all`), `make_owner` fixture, monkeypatched storage. Cover: lead CRUD + convert (notes carried, CF allocated, statuses), notes CRUD + pin/attach + firm isolation, exhibit CRUD + isolation, proceedings (outcome recorded + next event created + `next_hearing_date` recomputed), derived next-date correctness, draft creation from template, calendar aggregation window + isolation. Frontend: `npm run build` clean per plan.

## L. Build sequence (one spec, phased plans — each shippable & green)

1. **Nav → 3 tabs** + Vault/Kanban/Calendar skeleton + new stage taxonomy.
2. **Leads / Enquiries** entity + convert flow.
3. **Case-file shell**: adaptive action rail + stage advance.
4. **Notes** (panel + pin/attach).
5. **Evidence** exhibit register.
6. **Next-date mechanism** (hearing `purpose`/`outcome`, derived `next_hearing_date`, Record proceedings) + **Calendar**.
7. **Drafting stub** (template → draft document).

Each plan ends backend-green and frontend-build-clean before the next starts.

## Out of scope (explicit)

Real drafting editor / template CRUD / AI; reminders & notifications; per-matter access walls (firm-wide RBAC only); document versioning; reusable contacts registry. All deferred to later, separately brainstormed phases.
