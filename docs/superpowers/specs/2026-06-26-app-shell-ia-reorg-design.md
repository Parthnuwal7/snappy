# App Shell & IA Reorg + Quick Wins — Design Spec

**Date:** 2026-06-26
**Status:** Approved (design) → implementation
**Scope:** Sub-project A of the next wave. Sub-projects B (Day planner) and C (Writing/drafting editor) follow separately.

## Goal

Re-architect the navigation into a collapsible, grouped sidebar with a Home greeting landing, and land three quick wins (Case Vault server-side search, view-an-enquiry detail, Dashboard→Reports rehome). Almost entirely frontend; no backend schema or API changes.

## New information architecture

```
Home                    ← default landing (replaces redirect to /dashboard)
Cases  ▸ Kanban  ▸ Case Vault  ▸ Calendar
Billing ▸ Invoices  ▸ Items
Clients
Writing                 ← gated nav entry → "Coming soon" placeholder
Personalize ▸ News feed (Legal Feed)  ▸ Reports (= old Dashboard analytics)
Administration ▸ Team  ▸ Roles  ▸ Settings
```

- **Groups** (Cases, Billing, Personalize, Administration) render a section header + indented sub-links. **Standalone** items (Home, Clients, Writing) are direct links.
- Permission gating preserved: Cases→`case_files.read`, Team→`members.read`, Roles→`roles.read`. Writing/Billing/Personalize visible to all authenticated users (no new permissions).

## Components & decisions

**1. Collapsible sidebar.** A collapse toggle persisted in `localStorage` (`snappy.sidebar.collapsed`). Expanded = full grouped sidebar; collapsed = icon-only rail with `title` tooltips. Collapsed state hides sub-links and group labels (icons only); clicking the toggle re-expands. Flyout-on-hover for sub-links when collapsed is **deferred** (YAGNI).

**2. Home greeting landing.** New `pages/Home.tsx` at route index `/`. Renders `"{greeting}, {name}"`. Greeting by **IST** hour (compute via `Intl`/offset): morning 05–12, afternoon 12–17, evening 17–21, night 21–05. Name = a display name derived from the authenticated user (firm name or the local-part of the email, title-cased). Minimal by design — a seed for a richer home later.

**3. Reports rehome.** The current analytics **Dashboard** content moves under **Personalize → Reports** (`/reports`). The standalone "Dashboard" nav entry and its top-level role are removed; `/dashboard` redirects to `/reports` for any stale links. The pre-existing Reports page content (if distinct, e.g. billing reports) is preserved within the Reports page or merged — resolved at plan time by reading both pages.

**4. Case Vault server-side search.** Add a debounced search input to `pages/CaseVault.tsx` bound to `api.getCaseFiles({ search })`; the React Query key includes the term so results refetch server-side. Backend `/case-files?search=` (title/number/court ILIKE) already exists — no backend change.

**5. View-an-enquiry.** Each enquiry row in the Vault gets a **View** action opening a detail modal: contact, phone, email, matter summary, intake notes, status. From inside it: **Accept** (convert), **Decline** (status), and **Edit** (inline edit of the lead fields via `PATCH /leads/<id>`). Enquiries are no longer accept/decline-only.

**6. Writing placeholder.** `pages/Writing.tsx` — a gated nav entry rendering a "Coming soon" placeholder (the drafting editor is Sub-project C, brainstormed separately).

## Routing changes (`App.tsx`)

- `/` index → `Home` (was `Navigate to /dashboard`).
- Add `/writing` → `Writing`.
- `/dashboard` → `Navigate to /reports` (rehome).
- Keep `/cases` (+ `vault`/`calendar`), `/invoices`, `/items`, `/clients`, `/legal-feed`, `/reports`, `/team`, `/roles`, `/settings`.

## Out of scope

Day planner (Sub-project B), the Writing editor itself (Sub-project C), flyout-on-hover collapsed sub-links, any backend/API/schema change.

## Testing

Frontend `npm run build` clean. Backend unaffected — suite stays green (289). No new migrations.
