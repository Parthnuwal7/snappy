# Day Planner — Design Spec (Sub-project B)

**Date:** 2026-06-26
**Status:** Approved (design) → implementation
**Scope:** Tasks + Day/Week/Month planner + one-click printable cause-list. **No notifications/digest** (explicitly dropped).

## Goal

Let the advocate plan by day/week/month: schedule tasks against dates, open any day to see that day's activity (hearings + tasks), and print the day's cause-list in one click.

## Components

**1. Tasks (new entity).** Firm-scoped to-do with: `title`, `due_date` (Date), optional `case_file_id` link, `done` (bool), `priority` (reuse the case PRIORITIES catalog: low/normal/high/urgent, default normal). CRUD. A new `tasks` RBAC module (CRUD) — Owner auto; Partner/Associate/Staff all granted CRUD (everyone plans their own day).

**2. Planner = the Cases ▸ Calendar subtab, with a Day / Week / Month toggle.**
- **Month** — the existing month grid, now also marking days that have tasks (not just hearings). Click a day → Day view for that date.
- **Week** — a 7-day agenda (each day's hearings + tasks).
- **Day** — opens a date: that day's **hearings** (from `/calendar`) + **tasks** (from `/tasks`), an inline add-task form, done-toggle and delete, and a **Print cause-list** button.

**3. One-click printable cause-list.** A bare, print-optimized page at its own route `/print/cause-list?date=YYYY-MM-DD`, rendered **outside the sidebar Layout** (still auth-gated). Shows firm name + date + a clean table of the day's hearings (case no · title · court · purpose) and the day's tasks, and auto-triggers `window.print()`. A separate route avoids fighting the app shell's CSS and gives a true one-click→paper flow.

## Backend

- **Model** `app/models/task.py` — `Task(firm_id, created_by_user_id, title, due_date, case_file_id?, done, priority, created_at)` + `to_dict()` that includes `case_number`/`case_title` when linked (via a `case_file` relationship). FK to `case_files.id` (no cycle → no `use_alter`). Registered for table creation via the tasks blueprint import (loaded before `init_db`, same pattern as leads).
- **RBAC** — add `{"key": "tasks", "label": "Tasks", "actions": CRUD}` to the catalog; grant CRUD to Partner/Associate/Staff.
- **API** `app/api/tasks.py` (gated by `tasks` perms):
  - `GET /tasks?from=&to=&status=&case_file_id=` — firm tasks, optional due-date range, `status` ∈ {open, done} filter, optional case filter; ordered by `due_date, id`.
  - `POST /tasks` — `{title (req), due_date (req), case_file_id?, priority?}`.
  - `PATCH /tasks/<id>` — `title, due_date, done, priority, case_file_id`.
  - `DELETE /tasks/<id>`.
- **Migration** `018_tasks.sql` (additive).
- The day/week views reuse the existing `GET /calendar` for hearings — no duplicated hearing logic.

## Frontend

- `api.ts` — `Task` type + `getTasks(from, to, status?)`, `addTask`, `updateTask`, `deleteTask`.
- `pages/CaseCalendar.tsx` — rebuilt with a Day/Week/Month toggle (Month = current grid + task markers; Week = 7-day agenda; Day = day detail with tasks + print).
- `pages/CauseListPrint.tsx` — the printable page; route `/print/cause-list` added under `ProtectedRoute` but outside `Layout`.

## Out of scope

Notifications / morning digest (WhatsApp/email) — dropped. Recurring tasks, task assignment to other members, drag-reschedule — later. Google Calendar export — later/never per the earlier decision.

## Testing

Backend: pytest on SQLite — task model + to_dict, RBAC grants, tasks CRUD + date-range/status filters + firm isolation. Frontend: `npm run build` clean. New migration 018 for Parth.
