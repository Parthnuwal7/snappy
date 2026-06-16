# Snappy — Productivity Features Design

**Date:** 2026-06-16
**Author:** Brainstormed with Claude
**Status:** Draft for review

## Context

Snappy is a multi-tenant billing/invoicing SaaS for **solo freelancers in the Indian
market** (₹, GSTIN, default 18% GST). Stack: React + TypeScript frontend (Vercel),
Flask backend (Cloud Run), Supabase Postgres, ReportLab PDFs. Scheduled work runs via
**Cloud Scheduler → protected HTTP endpoints** (the existing `/keepalive` pattern);
Cloud Run scales to zero, so in-process schedulers are not viable.

This round targets **faster invoicing** and **stickiness**, scoped to three independent
features. They will be implemented in order — A → B → C — and recurring (C) may get its
own implementation plan since it is the largest.

Two relevant facts about the current code:
- `Invoice.status` already defaults to `'draft'`, so auto-creating drafts needs no new state.
- A **half-page PDF template** already exists whose content fits ~half an A4 page.

---

## Feature A — Recent-client chips

**Goal:** eliminate the cold-start in the invoice composer. A freelancer with a handful
of clients should bill a known client with zero typing.

### Backend
- New endpoint `GET /api/v1/clients/recent?limit=6`.
- Returns the user's clients ordered by their most recent invoice's `created_at`
  (distinct clients, capped at `limit`, default 6), scoped to `user_id`.

### Frontend (`NewInvoice.tsx`)
- When **no client is selected** and the **search box is empty**, render the recent
  clients as clickable chips/cards above the search field.
- Clicking a chip reuses the existing selection logic: set `selectedClient`, set
  `client_id`, set `tax_rate` from the client default, clear search.
- Search remains for the long tail.

### Edge cases
- New user with zero invoices → no chips; only the search box (current behavior).
- Fewer than 6 clients with invoices → show however many exist.

### Out of scope
- Pinning/favoriting clients. Ordering is purely recency-based.

---

## Feature B — Two-up print

**Goal:** print **two identical, upright copies** of an invoice on one A4 portrait page
(tear down the middle) — saves paper and manual effort. One copy for the freelancer, one
for the client.

### Approach
- Refactor the existing half-page generator in `pdf_templates.py` to expose a reusable
  `build_halfpage_flowables(invoice, firm) -> list[Flowable]` function.
- For two-up, build a single A4 canvas with **two stacked Frames**:
  - Top frame: region `[margin, H/2 .. H-margin]`
  - Bottom frame: region `[margin .. H/2]`
- Pour a **freshly built** copy of the flowables into each frame (ReportLab flowables
  cannot be reused across frames — build the list twice). Both copies upright, identical,
  each constrained to its half.
- This reuses all existing half-page layout code; no scaling or distortion.

### Trigger / UX
- Add a `layout=two_up` modifier to the existing PDF endpoint.
- Surface as a **"Download 2-up (2 copies/page)"** action alongside the normal download on
  the invoice list and/or preview.

### Guardrail
- If an invoice's half-page content would overflow its half-page frame (many line items),
  fall back to the standard one-per-page PDF and show a small notice. Rare for the
  freelancer use case, but we avoid silent clipping.

### Out of scope
- Rotated (head-to-head) layouts and Original/Duplicate labeling — explicitly declined.
- N-up beyond two.

---

## Feature C — Recurring invoices

**Goal:** "Bill Client X the usual every month." A **draft** invoice is created
automatically on schedule, and the freelancer gets a concrete, money-forward reminder to
review it.

### Data model — `RecurringSchedule`
| Field | Notes |
|-------|-------|
| `id` | PK |
| `user_id` | owner (multi-tenant isolation) |
| `client_id` | FK to client |
| `items` | JSON: line-item template (description, quantity, rate) |
| `tax_rate` | numeric |
| `short_desc` | optional |
| `notes` | optional |
| `frequency` | `weekly` \| `monthly` |
| `anchor` | day-of-month (monthly) or day-of-week (weekly) |
| `next_run_date` | date the next draft is due |
| `last_run_date` | nullable |
| `end_date` | nullable, **optional** — schedule stops after this date |
| `active` | bool (pause/resume) |
| `created_at` / `updated_at` | timestamps |

### Trigger
- New **Cloud Scheduler job (daily)** → `POST /api/v1/recurring/run`.
- Secured by a **shared-secret header** (same shape as the keepalive heartbeat; reject
  requests without the secret).
- The handler scans schedules where `active && next_run_date <= today`. For each:
  1. Create a **draft** invoice (`status='draft'`, `source='recurring'`) from the
     template: next invoice number, today's `invoice_date`, computed `due_date`.
  2. Advance `next_run_date` by the cadence; set `last_run_date = today`.
  3. If `end_date` is set and the new `next_run_date > end_date`, set `active = false`
     (schedule has run its course).
  4. The created draft *is* the reminder source (see below).
- Idempotency: a schedule advances its `next_run_date` only after the draft is committed,
  so a re-run on the same day does not double-create.

### Reminder (in-app, money-forward)
- **No separate notifications table.** Recurring-created drafts are marked with
  `source='recurring'`; the dashboard derives reminders directly from today's recurring
  drafts.
- Surfaced as a banner / notification list on the **Dashboard** plus a small badge in the
  header. Message format, per draft:

  > **"Acme Corp is due ₹45,000 today — draft invoice created."** → *Review*

- Each reminder links to its draft. Multiple drafts stack into a list. A reminder clears
  once its draft is opened or finalized (i.e. no longer a fresh recurring draft).
- Email/WhatsApp reminders are explicitly deferred — the in-app banner is the v1 reminder.

### UI
- A **"Set up recurring" button at the top of the Invoices list page**.
- Opens a form: pick client, define line items (reusing the composer's item pieces),
  choose cadence (weekly/monthly + anchor day), set start date, and an **optional end
  date** (leave blank to run until paused).
- A small management list (likely a `/recurring` page) to view, pause/resume, and delete
  schedules.

### Out of scope
- Auto-finalizing/auto-sending invoices (declined — drafts only, human stays in the loop).
- Arbitrary custom intervals beyond weekly/monthly.
- Occurrence counts (use the optional end date instead). Schedules without an end date run
  until paused.

---

## Implementation order & sequencing

1. **A — Recent-client chips** — quick win, frontend + one small endpoint.
2. **B — Two-up print** — isolated PDF/template change.
3. **C — Recurring invoices** — largest; new model + Cloud Scheduler endpoint + UI +
   dashboard reminders. May warrant its own implementation plan.

## Non-goals for this round
- Online payments / UPI pay links.
- WhatsApp/email delivery and reminders.
- AI line-item drafting.
- GST export tooling.

(These were brainstormed and parked for future rounds.)
