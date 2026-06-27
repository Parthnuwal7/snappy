# Firm Tenancy & RBAC Foundation (Design)

Date: 2026-06-23
Status: Draft (pending spec review)
First sub-project of the larger **Legal CRM** initiative (case/matter management,
proceedings, calendar, documents, templates, AI assist). This spec covers the
**tenancy + access-control floor** that every later CRM feature stands on.

## Problem

Snappy today is **single-user**. Every table is scoped to `user_id`, and
`FirmDetails` is one billing profile per user — a "firm" is really just one
counsel's settings. To become a practice-management product where a firm has a
partner, associates, and clerks who collaborate on the same clients and cases
with **different access levels**, the tenancy model itself must change: from
"this row's `user_id` is me" to **firm → members → role → permissions**.

Building Matters, Calendar, and Documents first on the single-user model and
bolting on access control later would mean re-plumbing every one of them. So the
access layer goes first; everything after inherits it for free.

## Scope

**In scope (this spec):**
- A real `Firm` tenant; `FirmDetails` becomes the firm's profile.
- Membership: `User` belongs to exactly one firm with exactly one role.
- Custom roles built from a **module × CRUD permission matrix**.
- Email-invite member onboarding.
- Re-scoping existing billing data from `user_id` to `firm_id` (+ creator attribution).
- A permission-enforcement layer (request middleware + endpoint decorator).
- A backfill migration so every existing user becomes the Owner of their own firm.
- Team page, Roles editor, and invite-accept UI on the frontend.

**Out of scope (each its own later spec):** Matters/cases, proceedings, calendar,
documents/files, document templates, AI assist, billing-from-time-tracking,
per-matter access grants, multi-firm membership.

## Key decisions (from brainstorming)

- **One firm, many users. One user → one firm → one role.** Strict 1:1 between a
  user and their firm (no firm switcher, no multi-firm membership ever planned).
- **Firm owns the data; creator is tracked.** Billing rows are re-scoped to
  `firm_id` and also carry `created_by_user_id` for attribution / "my records".
- **Fully custom roles via a module × CRUD matrix.** A role is a set of
  `module.action` permission keys. The Roles editor renders modules as rows and
  Create/Read/Update/Delete (plus a few non-CRUD capabilities) as togglable
  columns. "Can see" = the **Read** toggle.
- **Seeded default roles per firm.** Each firm starts with **Owner** (all
  permissions, `is_system`, undeletable, can't be demoted while last Owner) plus
  editable starters **Partner / Associate / Staff**. Admins edit these or add new.
- **Owner bypasses all checks**; cross-firm access is structurally impossible
  because every query is firm-scoped.
- **Feed personalization stays user-private** (preferences, events, device info) —
  it is genuinely personal, not firm data.
- **Firm Owner ≠ app super-admin.** The existing app-level admin (legal-feed
  ingestion control in `admin.py`) is unrelated and unchanged.

## Data model

### New tables

**`firms`** — the tenant.
- `id`, `name`, `created_at`.

**`roles`** — firm-owned, editable bundles of permissions.
- `id`, `firm_id` (FK), `name`, `description`,
  `permissions` (JSON list of `module.action` keys),
  `is_system` (bool — Owner is `True`, undeletable),
  `created_at`, `updated_at`.
- Unique `(firm_id, name)`.

**`firm_invites`** — pending member invitations.
- `id`, `firm_id` (FK), `email`, `role_id` (FK), `token` (unique, random),
  `status` (`pending` | `accepted` | `revoked` | `expired`),
  `invited_by` (user id), `expires_at`, `created_at`, `accepted_at`.

### Changed tables

**`users`** gains:
- `firm_id` (FK → firms, nullable until onboarded/joined),
- `role_id` (FK → roles, nullable until joined).

**`firm_details`** — re-pointed from a user to a firm: drop the per-user
uniqueness, add `firm_id` (FK, unique — one profile per firm). Kept as the firm's
billing/branding profile (logo, terms, templates, invoice prefix, currency…).

**`clients`, `items`, `invoices`, `recurring_schedules`, `bank_accounts`** each:
- **rename `user_id` → `created_by_user_id`** (FK → users) — the existing column
  *is* the attribution; "who owns this" becomes "who created this", no new
  duplicate column, and
- gain `firm_id` (FK → firms, indexed) — the **new access scope**.

End state per table is exactly two ownership columns — `firm_id` (scope) and
`created_by_user_id` (attribution) — with no redundant legacy column. Scoped
queries change from `filter_by(user_id=…)` to `filter_by(firm_id=…)`.
`invoice_items` is a child of `invoices` and needs no scope column.

**Unchanged scope:** `legal_feed_preferences`, `legal_feed_events` stay
user-scoped. `legal_feed_sources/items/runs/settings` remain global.

## Permission model

Permissions are a **fixed catalog defined in code** (not user-editable), exposed
to the Roles editor as a module × action grid. A permission key is
`"<module>.<action>"`.

**Modules (v1):** `clients`, `invoices`, `items`, `recurring`, `bank_accounts`,
`firm_settings`, `members`, `roles`. The catalog is structured so future CRM
modules (`matters`, `proceedings`, `calendar`, `documents`, `templates`) slot in
without schema change.

**CRUD actions (per data module):** `create`, `read`, `update`, `delete`.

**Members & Roles module actions** (not plain CRUD):
- `members.read` — view the team list.
- `members.invite`, `members.remove`, `members.manage_roles` — team management.

**Other non-CRUD capabilities (where CRUD doesn't fit):**
- `invoices.send` — send an invoice to a client.
- `roles.manage` — create/edit/delete custom roles (this is the "admin" toggle).
- `firm_settings.update` — edit firm profile/branding/billing settings.

**Resolution rules:**
- A user's effective permissions = their role's `permissions` list.
- **Owner** (`is_system` Owner role) implicitly has **all** permissions — its
  grid is fully ticked and locked; it bypasses checks.
- Last Owner cannot be demoted, removed, or have the Owner role deleted.

**Seeded default role grids (starting points, all editable except Owner):**
- **Owner** — everything.
- **Partner** — full CRUD on all billing modules, `invoices.send`,
  `firm_settings.update`, `members.invite`; no `roles.manage`.
- **Associate** — CRUD (no delete) on clients/invoices/items, `invoices.send`;
  read-only on bank accounts and firm settings; no member/role management.
- **Staff** — read on most modules, create/update on clients and invoices; no
  delete, no send, no admin.

## Enforcement

- **Request middleware** (extends the existing `jwt_required` flow): after
  resolving `g.user_id`, load the user's `firm_id` and role, set `g.firm_id` and
  `g.permissions`. Requests from a user with no firm (mid-onboarding) get a
  well-defined limited state.
- **`@require_permission('invoices.create')` decorator** on each endpoint: 403s
  unless the permission is in `g.permissions` (Owner bypasses). Applied across
  the re-scoped billing endpoints and the new member/role/invite endpoints.
- **Firm isolation:** every data query filters by `g.firm_id`, so a member of
  firm A can never read or mutate firm B's rows even by guessing ids.

## Invite flow

1. A user with `members.invite` POSTs `{email, role_id}` → server creates a
   `firm_invites` row with a random `token` and `expires_at`, and emails a
   tokenized accept link via the existing `email_service`.
2. Invitee opens the link → frontend invite-accept page → they sign up or log in
   via Supabase.
3. Accept endpoint validates the token (pending + not expired + email match),
   sets the user's `firm_id` + `role_id`, marks the invite `accepted`.
4. Works whether or not the invitee already had a Snappy account. Owners can
   **revoke** a pending invite (status → `revoked`). Expired/used tokens are rejected.

## Migration & backfill

The migration is **in-place and non-destructive** — no table is dropped, no data
is moved or copied, and no cutover window exists. It runs once and is idempotent
(safe to re-run; already-migrated rows are skipped). Steps:

1. **Create** the new tables `firms`, `roles`, `firm_invites`.
2. **`ADD COLUMN`** (nullable, non-blocking): `firm_id` + `role_id` on `users`;
   `firm_id` on `firm_details`; `firm_id` on each of `clients`, `items`,
   `invoices`, `recurring_schedules`, `bank_accounts`.
3. **`RENAME COLUMN user_id → created_by_user_id`** on the five billing tables.
   This is an instant metadata-only operation in Postgres that preserves all
   existing values, so attribution is correct with zero backfill.
4. **For each existing user:** create a `Firm` (named from their
   `FirmDetails.firm_name`, falling back to their email); seed the four default
   roles into it; point their `FirmDetails` at the firm; set the user's
   `firm_id` and `role_id = Owner`.
5. **`UPDATE`-backfill only `firm_id`** on every existing `clients` / `items` /
   `invoices` / `recurring_schedules` / `bank_accounts` row, derived from its
   `created_by_user_id` → that user's firm.

Nothing is destroyed, no column is left redundant, every current user ends up the
Owner of a one-person firm with all their data intact, and the running app keeps
working throughout because the rename preserves data and the new columns are
additive.

## Backend surface (new/changed endpoints)

- `GET /firm` / `PATCH /firm` — firm profile (guarded by `firm_settings.update`).
- `GET /firm/members` — list members + roles (`members.read`-ish via `members`).
- `PATCH /firm/members/:id` — change a member's role (`members.manage_roles`).
- `DELETE /firm/members/:id` — remove a member (`members.remove`).
- `GET/POST/DELETE /firm/invites` — create / list / revoke invites (`members.invite`).
- `POST /firm/invites/accept` — accept via token (auth required, no permission).
- `GET /firm/roles`, `POST /firm/roles`, `PATCH /firm/roles/:id`,
  `DELETE /firm/roles/:id` — custom roles (`roles.manage`).
- `GET /permissions/catalog` — the module × action catalog, to render the grid.
- Existing billing endpoints: re-scoped to `g.firm_id` + `@require_permission`.

## Frontend surface

- **Team page** (under Settings): member list with roles, invite form (email +
  role picker), pending invites with revoke, change-role, remove-member.
- **Roles editor:** list of roles; an editor rendering the module × CRUD grid of
  checkboxes (Owner shown locked/all-on); create/edit/delete custom roles.
- **Invite-accept page:** token landing → Supabase sign-up/login → joined.
- **Permission-aware UI:** the app fetches `g.permissions` (via `/me`) and hides
  or disables actions the user lacks (e.g. no "New Invoice" button without
  `invoices.create`).

## Testing (TDD throughout)

- **Permission resolution:** role → effective permissions; Owner-all; unknown keys.
- **`@require_permission` decorator:** allow / deny(403) / Owner-bypass.
- **Firm isolation:** firm A member cannot read or mutate firm B rows.
- **Invite lifecycle:** create → email → accept (new + existing user) → revoke →
  expire → reused-token rejection → email-mismatch rejection.
- **Role management:** create/edit/delete custom role; cannot delete Owner;
  cannot demote last Owner.
- **Migration/backfill:** existing user becomes Owner of a one-person firm; all
  billing rows get correct `firm_id` + `created_by`; idempotent re-run.
- **Re-scoped billing endpoints:** still work for the Owner post-migration.

## Risks & notes

- **Most invasive part is the re-scope**, touching every billing query. Mitigated
  by an in-place, non-destructive migration: `firm_id` is added and backfilled,
  `user_id` is renamed (not duplicated) to `created_by_user_id` preserving all
  data, and nothing is dropped, moved, or copied — so existing users' data and
  flow are never at risk and the end-state model has no redundant columns.
- Supabase auth still owns identity; this layer is authorization on top.
- `roles.manage` is effectively the "admin" capability the user asked for — the
  toggle that lets someone configure who can see/CRUD each module.
