# Onboarding Redesign — Design

**Date:** 2026-06-29
**Status:** Approved, proceeding to implementation plan.

## Goal

Redesign Snappy's onboarding end-to-end for two entry paths — a brand-new firm
owner, and a user joining an existing firm via invite — converging on a shared
personal-profile capture step. Replace the front-loaded firm-setup wizard with a
minimal gate plus a progressive "Finish setting up" checklist on Home.

## Decisions (from brainstorming)

- **Driver:** redesign the experience (not just patch gaps).
- **Persona:** mixed — adapt to both solo advocates and small-firm owners via an
  early Solo/Firm fork (a first-run *nudge* only; no schema/permission change).
- **Personal profile captured for every user:** full name, designation, Bar
  Council / enrollment number, personal phone.
- **Owner flow shape:** minimal gate (name + firm name + solo/firm) → land in app;
  banking / branding / billing / team deferred to a Home checklist.
- **Invite reconciliation:** a direct signup whose email matches a pending invite
  is **auto-routed** into that firm (no duplicate firm), then sees only the
  profile step.
- **Checklist state:** derive each item live from real data; persist only a single
  `checklist_dismissed` flag.

## 1. Data model (migration `023_onboarding_profile.sql`)

**`users`** — add personal-profile layer + checklist flag (all nullable except
the boolean default):
- `full_name` (text)
- `designation` (text)
- `bar_council_number` (text)
- `personal_phone` (text)
- `checklist_dismissed` (boolean, default false)

**`firm_details`** — relax `firm_address` to **nullable** (the minimal gate only
collects `firm_name`; the checklist fills the address later). `firm_name` stays
`NOT NULL`.

No change to `firm_invites` — reconciliation matches on the existing `email`
column.

> R3 (`firm_details → firms` merge) is out of scope and takes a later migration
> number; this onboarding migration is 023.

## 2. Two entry paths, one convergence point

Everyone lands on a router (`OnboardingGate`) that reads `GET /auth/me`. The
backend returns a `pending_invite` block (`{firm_name, role_name}`) when a
firm-less user's email matches a pending invite. That splits the path:

**A. Owner (no pending invite)** — minimal gate, one screen:
- *You:* full name, designation, bar council no., personal phone
- *Your firm:* firm name + **Solo / Firm** toggle
- Submit → `POST /auth/onboard` (redesigned): writes profile fields to `users`,
  provisions `Firm` + roles + Owner, creates minimal
  `FirmDetails(firm_name, address=null)`, sets `is_onboarded=true` → land in app.
- Solo/Firm toggle only affects first-run nudges: **Firm** surfaces the "Invite
  your team" checklist item prominently; **Solo** de-emphasizes it. No schema or
  permission difference.

**B. Invitee (pending invite exists, OR arrived via `/accept-invite/<token>`)** —
profile-only screen titled *"Join {firm_name} as {role}"*:
- Same personal fields, **no** firm fields.
- Submit → accept the invite + `PATCH /auth/profile` → land in app.
- Token path calls `POST /invites/accept` (token); direct-signup path calls the
  new `POST /invites/accept-pending` (no token — accepts the newest matching
  pending invite for the authenticated email). This is the auto-route behavior.

## 3. Backend API changes

- `POST /auth/onboard` — slimmed to the gate (profile + firm_name + is_solo).
  Drops required banking/branding/billing fields. Keeps the "already onboarded"
  guard and the provision-firm-once guard.
- `PATCH /auth/profile` — **new**; updates the four personal fields. Used by the
  invitee step and later profile edits.
- `POST /invites/accept-pending` — **new**; firm-less user, no token, accepts the
  newest matching pending invite by email (raises if none). Shares the
  email-match + attach logic with the token path.
- `GET /auth/me` — extend `profile` with the four personal fields +
  `checklist_dismissed`; add a `pending_invite` block; add a `setup` block with
  four **derived** booleans (bank / branding / billing / team).
- `POST /auth/dismiss-checklist` — **new**; sets `checklist_dismissed=true`.
- `PUT /auth/firm` & `/auth/bank` — unchanged; the checklist items call them.

### Derived `setup` booleans (computed live in `/auth/me`)

- `bank` = a `BankAccount` row exists for the firm
- `branding` = `firm_details.logo_path` or `signature_path` set
- `billing` = `firm_details.billing_terms` set
- `team` = ≥1 `FirmInvite` sent for the firm

## 4. Frontend changes

- `Onboarding.tsx` — rewritten as the **minimal owner gate** (single screen,
  profile + firm + solo/firm). Old banking/branding/billing steps removed (they
  already exist in `Settings.tsx`).
- New `InviteeProfile` step component — shared by `AcceptInvite.tsx` (post-token)
  and the direct-signup reconciliation path.
- `AcceptInvite.tsx` — after a successful token accept, route to `InviteeProfile`
  instead of straight to dashboard.
- `Home.tsx` — add a **"Finish setting up"** checklist card: derives item states
  from the `/auth/me` `setup` block, each row deep-links to the relevant
  Settings/Team section, dismiss (×) calls `POST /auth/dismiss-checklist`. Hidden
  when dismissed or all-complete.

## 5. Testing (TDD, pytest — backend currently 312 green)

- `onboard` writes profile fields + provisions firm with null address; rejects
  double-onboard.
- `accept-pending` attaches a direct-signup user to the matching firm/role and
  does **not** create a second firm; raises when no pending invite.
- Email-mismatch still blocked on both accept paths.
- `/auth/me` returns correct derived `setup` booleans as bank/branding/billing/
  team data appears, and surfaces `pending_invite` for a firm-less invited email.
- `dismiss-checklist` flips the flag.
- Frontend `npm run build` clean.

## 6. Out of scope

- `firm_details → firms` R3 merge.
- Email-template / branding redesign.
- Any RBAC/permission change — Solo vs Firm is purely a first-run nudge.
