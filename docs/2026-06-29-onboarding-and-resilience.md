# Implementation Summary — Onboarding Redesign + Resilience Hardening

**Date:** 2026-06-29
**Branch:** `feature/legal-feed` (all changes currently uncommitted in the working tree)
**Backend tests:** 312 → **330 green** · **Frontend:** `npm run build` clean

This document records two related pieces of work shipped together: a redesign of
the first-run onboarding experience, and a defense-in-depth fix for orphaned
`idle in transaction` database connections observed in production.

Design + step-by-step plan live alongside this file:
- Spec: `docs/superpowers/specs/2026-06-29-onboarding-redesign-design.md`
- Plan: `docs/superpowers/plans/2026-06-29-onboarding-redesign.md`

---

## 1. Onboarding redesign

### Goal
Replace the front-loaded firm-setup wizard (which demanded firm name + address +
banking + branding before a user could do anything) with a **minimal first-run
gate** plus a **derived "finish setting up" checklist** on Home. Add a personal
profile layer, and converge the firm-owner path and the invitee path so a person
invited by email lands in the right firm without creating a duplicate.

### Data model — `migration 023_onboarding_profile.sql`
Additive and idempotent. **Must be applied on Supabase before the new backend is
deployed** (the `User` model now selects these columns on every query).

New columns on `users`:

| Column | Type | Purpose |
|---|---|---|
| `full_name` | VARCHAR(200) | Personal name (now required at the gate) |
| `designation` | VARCHAR(120) | e.g. Advocate / Senior Partner |
| `bar_council_number` | VARCHAR(120) | Bar Council enrolment no. |
| `personal_phone` | VARCHAR(50) | Personal contact |
| `is_solo` | BOOLEAN | Solo practitioner vs firm with a team |
| `checklist_dismissed` | BOOLEAN (default FALSE) | One flag to hide the Home checklist |

Plus: `firm_details.firm_address` relaxed to **NULLABLE** — the minimal gate
creates a firm profile with no address yet (filled in later via Settings).

`User.to_dict()` was extended to surface all six fields (with `is_solo` and
`checklist_dismissed` coerced to bool).

### Backend API changes

**`POST /api/v1/auth/onboard`** — *slimmed*. Now requires only `full_name` +
`firm_name` (previously firm_name + firm_address). Writes the profile fields and
`is_solo`, and creates a minimal `FirmDetails` with `firm_address` left null.

**`PATCH /api/v1/auth/profile`** *(new — `update_profile`)* — update any of the
personal-profile fields after the gate.

**`POST /api/v1/auth/dismiss-checklist`** *(new — `dismiss_checklist`)* — sets
`checklist_dismissed = true`.

**`POST /api/v1/invites/accept-pending`** *(new — `accept_pending`)* — for a user
who signed up directly (not via an invite link) but whose email matches a pending
invite: auto-creates the local user, attaches them to the inviting firm/role, and
returns `{firm_id, role_id, invite}` (or 400 if no valid pending invite).

**`GET /api/v1/auth/me`** — extended response. In addition to the profile fields,
it now returns:
- `pending_invite`: `{firm_name, role_name}` when a firm-less user has a matching
  unexpired invite (drives the invitee branch of the gate), else `null`.
- `setup`: a **derived** checklist state computed from real data —
  `{bank, branding, billing, team, dismissed, complete}` — built from the
  BankAccount count, `FirmDetails.logo_path`/`signature_path`,
  `FirmDetails.billing_terms`, and the FirmInvite count. Nothing about checklist
  *progress* is stored except the single `dismissed` flag.

**`invite_service.py`** *(new module)* — refactored invite logic into small
units: `_attach(user, invite)` (validates status/expiry/email match, sets
firm/role, marks onboarded + accepted), `accept_invite(token, user)`,
`pending_invite_for(email)` (newest unexpired pending invite, or None), and
`accept_pending_invite(user)`.

### Connection-pool note
`app/main.py` `create_app()` gained `SQLALCHEMY_ENGINE_OPTIONS` (see §2).

### Frontend changes

- **`pages/Onboarding.tsx`** — rewritten as a single minimal gate. If
  `pendingInvite` is set it renders the invitee "Join {firm} as {role}" form
  (calls `acceptPendingInvite()` then `updateProfile()`); otherwise the owner gate
  (profile + firm name + Solo/Firm toggle, calls `onboard({...profile, firm_name,
  is_solo})`). Navigates to `/` on success.
- **`pages/InviteeProfile.tsx`** *(new)* — profile form at `/invitee-profile` for
  users who accepted an invite via the email link; calls `updateProfile()` then
  navigates to `/`.
- **`pages/AcceptInvite.tsx`** — after a successful token accept it now reroutes to
  `/invitee-profile` instead of straight to Home, so invited users still set up
  their personal profile.
- **`components/SetupChecklist.tsx`** *(new)* — renders nothing if there is no
  `setup`, or it is dismissed, or it is complete. Otherwise shows rows for bank /
  branding / billing / team; for solo users the team row is muted and ordered last.
  The × calls `dismissChecklist()` then refreshes the profile.
- **`pages/Home.tsx`** — renders `<SetupChecklist />` under the greeting.
- **`contexts/AuthContext.tsx`** — `UserProfile` gained the six fields; new
  exported `SetupState` + `PendingInvite` interfaces; `setup` and `pendingInvite`
  are populated from `/auth/me` and cleared on 404 / sign-out / logout.
- **`api.ts`** — new client methods `updateProfile`, `dismissChecklist`,
  `acceptPendingInvite`.
- **`App.tsx`** — new `/invitee-profile` route (protected, does **not** require
  onboarding to be complete).

### Tests added (all green)
`test_onboarding_profile_model.py`, `test_onboard_gate.py`,
`test_profile_endpoint.py`, `test_dismiss_checklist.py`,
`test_accept_pending_api.py`, `test_me_setup_block.py`, plus new cases appended to
`test_invite_service.py` (accept_pending / pending_invite_for).

---

## 2. Resilience hardening — orphaned `idle in transaction` connections

### Symptom
Production showed 5 connections stuck `idle in transaction` for 2+ days, holding
an `ACCESS SHARE` lock on `users` and blocking the `ALTER TABLE` for migration 023
(the migration apply timed out on Supabase).

### Root cause
The legal-feed ingestion ran synchronously on the request path and committed only
once at the end of the whole enrichment loop. A slow run could exceed the Gunicorn
worker timeout (120s) → the worker was SIGKILLed mid-transaction → its connection
was orphaned in the pool with the transaction still open, and there was no DB-side
reaper to close it.

### Fixes (defense in depth)

**Code — `app/main.py`:** added SQLAlchemy engine options so the pool sheds
dead/stale connections:
```python
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,   # drop dead connections on checkout
    'pool_recycle': 280,     # cap connection lifetime (seconds)
}
```

**Code — `app/services/legal_feed/ingest.py`:** `_enrich_ids()` now
`db.session.commit()`s **after each item** instead of once at the end. A worker
killed mid-run can now orphan at most one short transaction, and every item
enriched so far is already durable.

**Database (for Parth to apply, live change, safe):**
```sql
ALTER ROLE <role> SET idle_in_transaction_session_timeout = '120s';
```
120s sits comfortably above the worst-case single enrichment item, so it reaps
genuinely-stranded transactions without killing legitimate work.

**One-time cleanup** of the 5 stranded sessions:
```sql
SELECT pg_terminate_backend(pid) FROM pg_stat_activity
WHERE state = 'idle in transaction' AND query_start < now() - interval '5 minutes';
```

### Tests added
`test_engine_hardening.py` (asserts pool_pre_ping/pool_recycle are configured),
plus `test_enrich_ids_commits_per_item` appended to `test_legal_feed_ingest.py`.

### Known follow-up (not done)
The durable architectural fix is to move legal-feed ingestion off the request path
entirely (e.g. a Cloud Run Job triggered by Cloud Scheduler) so a long run can
never collide with the HTTP worker timeout.

---

## 3. Docs / housekeeping (no prod impact)
- **`README.md`** — full rewrite to reflect reality: Legal CRM on Cloud Run +
  Supabase + Vercel (not "billing app on Render with DuckDB"), accurate stack,
  migrations, storage buckets, deploy command, RBAC, ~330 tests.
- **`suggestions.md`** — Cloud Run deploy guidance (`--source backend` controls
  what is uploaded, independent of cwd).

---

## 4. Deployment checklist for Parth

> Standing rule: Parth runs all git + migrations. None of the above is committed
> or deployed yet.

1. **Apply `migration 023` on Supabase first** — it is additive and
   backward-compatible with the currently-running old backend, but the *new*
   backend will `UndefinedColumn`-crash on every authenticated request if deployed
   before the columns exist.
2. **Apply** `ALTER ROLE <role> SET idle_in_transaction_session_timeout = '120s';`
   (find the role via `SELECT current_user;`). Terminate any leftover stranded
   sessions with the cleanup query above.
3. **Deploy backend + frontend together** — `/auth/onboard` now requires
   `full_name`, so a new backend with a stale old frontend would 400 brand-new
   signups during the window. (Existing onboarded users are unaffected — onboard
   400s "already onboarded" for them.)
4. **Verify** the private `case-documents` Supabase Storage bucket exists.

### Behavioural changes to expect post-deploy
- New signups go through the minimal gate, not the old wizard.
- **Existing users** will see a new "finish setting up" card on Home until they
  dismiss it (cosmetic; derived from their real bank/branding/billing/team state).
- New minimal-gate firms can have a null `firm_address`. Worth confirming the
  invoice PDF path (`pdf_templates.py`) renders a null address gracefully, since
  address is no longer collected upfront and isn't a checklist item.
