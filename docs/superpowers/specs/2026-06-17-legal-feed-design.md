# Legal Feed — Judgements & Readings for Advocates

**Date:** 2026-06-17
**Status:** Design approved, pending spec review
**Sub-project:** 1 of 3 (Ingestion pipeline + Awareness feed); search deferred

## Background & Motive

Snappy's customer base is lawyers. This feature adds a content/updates surface
(distinct from Snappy's transactional invoicing data) that keeps advocates
informed: daily judgements and orders from the Supreme Court / High Courts /
tribunals, legal news, and official notices. The motive is to deliver timely,
relevant legal updates inside the product the lawyer already uses daily.

## Overall Vision (3 sub-projects + deferred search)

The feature is a legal content platform built in sequenced phases, each with
its own spec → plan → build cycle. They share one backbone: a content ingestion
pipeline (sources → cleaned, tagged, stored content). The emphasis is on making
the **feed** genuinely good — curated and personalized — rather than on
case-law search.

1. **Ingestion pipeline + Awareness feed** ← this spec. Foundation everything
   else reads from; delivers a live "what's new" feed on its own.
2. **Curated digest** — practice-area tagging + per-item summaries (likely an
   LLM step), so the feed is filtered to what's relevant to each lawyer.
3. **Personalized + saved** — bookmarks, filters, daily email/notification
   digest (reuses Snappy's existing email service).

**Deferred (no committed timeline): Searchable judgement library.** Searching a
particular judgement is explicitly out of scope for this effort. Rationale: the
gov portals (`judgments.ecourts.gov.in`, eCourts services, `sci.gov.in`) expose
**no official public API** — only undocumented, session-bound, CAPTCHA-gated
internal AJAX endpoints. Automating them requires OCR CAPTCHA solving (~75%
accuracy), rotating-token session management, and per-court bespoke handling,
which is fragile and a ToS/legal grey area for a commercial product. When
revisited, search should be built on the **Indian Kanoon paid API** (clean
full-text search, ~₹0.50/search, ~₹0.20/document), not gov scraping.

## Scope of This Spec (Sub-project 1)

In scope:
- A scheduled ingestion pipeline that polls sources and stores normalized items.
- A config-driven **source registry** (feeds defined as data, not hardcoded), so
  adding/removing a source is a data change, not a code rewrite.
- Exact (idempotent) deduplication.
- A read API with type tabs + a court/category filter dropdown + pagination.
- A frontend feed page with nav entry.
- An **operator-only admin panel** (extends the existing `/admin` panel) for
  monitoring ingestion, manual triggering, source management, and item
  moderation — plus a "Feed Algorithm" section seeded with the v1 ordering knob.

Out of scope (deferred to later sub-projects):
- Storing or republishing full judgement/article text or PDFs. We store only
  headline + summary + link-out, for copyright/ToS safety and storage economy.
- Near-duplicate / semantic dedup across sources.
- Bookmarks, email digests, practice-area tagging, search.
- Full personalization / ranking logic beyond the v1 ordering knob (`recency` |
  `weighted`). The admin "Feed Algorithm" section is built as the seam these
  later phases extend.

## Content Sourcing Decisions

- **No full text.** Each item stores headline + short summary/abstract + a link
  to the source. The user reads full text at the source. This avoids copyright/
  ToS risk and keeps storage light.
- **Sources for v1** (mapped to tabs). v1 launches with **two** populated tabs
  — Judgements and News — both from stable RSS feeds:
  - **Judgements:** Indian Kanoon RSS feeds (free, no API key, stable), one feed
    per court:
    - Supreme Court
    - High Courts: Delhi, Bombay, Madras, Calcutta, Karnataka, Rajasthan
      (Rajasthan included for a known client based there)
    - Tribunals: ITAT (tax), NGT (environment)

    ~9 feeds total, each becoming an option in the court filter dropdown.
  - **News:** LiveLaw + Bar & Bench RSS. Already summarized for lawyers.

- **Deferred to a fast-follow (not v1): Notices tab.** Official notices/circulars
  have no RSS or API and would require an HTML scraper against gov listing pages
  (brittle; the useful ones sit behind the CAPTCHA-gated search portal we've
  ruled out). Rather than ship a known-fragile source on day one, v1 omits it.
  The tabs UI and `content_type` enum already accommodate it, so adding it later
  is just one more isolated fetcher module — no structural change. When added,
  it is constrained to **public, non-CAPTCHA listing pages only**.
- **Indian Kanoon paid API** (₹0.20/document, ₹500 free dev credit) is NOT used
  in v1. Reserved for the Searchable library sub-project.

## Architecture

**Approach A — Scheduler → existing backend endpoint.** Reuses the current
stack (Cloud Run Flask backend + Supabase + Cloud Scheduler). No new infra.

```
Cloud Scheduler (2x/day, cron times set by operator)
        │  POST /api/legal-feed/ingest   (protected by secret header)
        ▼
Flask ingest handler ──reads── legal_feed_sources (enabled feeds)
        │  for each enabled source: fetch → normalize → compute dedup_key
        │  log the run ──────────► legal_feed_runs
        ▼
Upsert into Supabase legal_feed_items (skip existing rows)

Users:    GET /api/legal-feed?type=&court=&page=  → reads (hidden excluded)
Operator: /admin  (Basic Auth) → status, run-now, sources, moderation, ordering
```

### Data Model

Three shared Supabase tables. Content is global (identical for all users,
read-only to users); the source registry and run log are operator-facing only.
Data access goes through the existing Supabase client service
(`backend/app/services/supabase_client.py`), consistent with the current API.

**`legal_feed_items`** — the feed content:

| Column | Type | Notes |
|---|---|---|
| `id` | uuid (pk) | |
| `source_id` | uuid, FK → `legal_feed_sources` | which source produced it |
| `content_type` | enum: `judgement` \| `news` \| `notice` | drives the tabs; v1 populates `judgement` + `news`, `notice` reserved for fast-follow |
| `title` | text | headline |
| `summary` | text | abstract/snippet |
| `source_url` | text | link out; full text lives at source |
| `source_name` | text | denormalized for display, e.g. "LiveLaw" |
| `court` / `category` | text, nullable | filter tag, e.g. "Supreme Court", "Delhi HC", "ITAT" |
| `published_at` | timestamptz | item's own date |
| `ingested_at` | timestamptz | default now() |
| `hidden` | boolean | default false; set true by admin moderation, excluded from the read API |
| `dedup_key` | text, **unique** | enforces exact dedup. Derivation: SHA-256 of normalized `source_url` when present; if a source omits a stable URL, fall back to SHA-256 of `source_name` + normalized `title`. |

Indexes: unique on `dedup_key`; composite on `(content_type, published_at desc)`
for the default feed query; index on `court` for the filter.

**`legal_feed_sources`** — config-driven source registry (the feeds the pipeline
polls; powers admin "source management"):

| Column | Type | Notes |
|---|---|---|
| `id` | uuid (pk) | |
| `name` | text | display name, e.g. "Indian Kanoon — Delhi HC" |
| `content_type` | enum | tab this source feeds |
| `court` / `category` | text, nullable | tag applied to its items |
| `kind` | enum: `rss` \| `scrape` | fetcher type (v1: all `rss`) |
| `feed_url` | text | the URL polled |
| `enabled` | boolean | default true; disabled sources are skipped |
| `weight` | int | default 0; per-source priority for the "Feed Algorithm" ordering knob (see below) |
| `created_at` | timestamptz | |

v1 is seeded with the 9 judgement feeds + 2 news feeds described above.

**`legal_feed_runs`** — ingestion run log (powers admin "ingestion status"):

| Column | Type | Notes |
|---|---|---|
| `id` | uuid (pk) | |
| `started_at` / `finished_at` | timestamptz | |
| `trigger` | enum: `scheduled` \| `manual` | manual = admin button |
| `status` | enum: `success` \| `partial` \| `failed` | partial = some sources errored |
| `total_ingested` | int | new rows inserted this run |
| `results` | jsonb | per-source `{source_id, fetched, inserted, error}` |

### Ingestion Flow

1. Scheduler triggers `POST /api/legal-feed/ingest` with a secret header
   (`trigger=scheduled`). The admin "Run now" button hits the same handler
   (`trigger=manual`).
2. Open a `legal_feed_runs` row (`started_at`, trigger).
3. Load all **enabled** rows from `legal_feed_sources`. For each, dispatch to the
   fetcher for its `kind` (v1: the RSS fetcher). Each fetcher returns normalized
   items `{title, summary, source_url, published_at}`; `content_type`, `court`,
   and `source_name` come from the source record.
4. Compute `dedup_key` per item.
5. Upsert into `legal_feed_items` on conflict of `dedup_key` → do nothing
   (idempotent; safe to re-run).
6. Close the run: write `finished_at`, `status`, `total_ingested`, and the
   per-source `results` jsonb.

Fetchers are keyed by `kind`, so each fetcher type is one small module with a
single responsibility — independently testable, and adding a new source is a
registry row (same `kind`) or, for a new `kind`, one new fetcher module.

### Read API

`GET /api/legal-feed?type=judgement&court=Delhi%20HC&page=2`
- Optional `type` filter (tab), optional `court` filter (dropdown).
- Excludes `hidden = true` items.
- Ordering follows the active "Feed Algorithm" mode (see Admin Panel):
  - `recency` (v1 default) — newest first by `published_at`.
  - `weighted` — orders by source `weight` then recency, so an operator can
    float Supreme Court above a tribunal. This is the deliberate seam the later
    curated/personalized work extends; v1 ships only these two modes.
- Uses Snappy's existing pagination utility (`backend/app/utils/pagination.py`).
- Read access requires an authenticated user (same JWT middleware as the rest of
  the app); content itself is global.

### Frontend

- New page `frontend/src/pages/LegalFeed.tsx` + a nav entry in `Layout.tsx` +
  a route in `App.tsx`.
- **Tabs** for content type. v1 launches two populated tabs: Judgements /
  Legal News. (The Notices tab is deferred; the component supports adding it.)
- **Dropdown** to filter by court/category within the active tab.
- **Cards**: title, summary, source badge (`source_name`), date, and a
  "Read at source ↗" link that opens `source_url` in a new tab.
- Paginated using the existing `Pagination` component.

### Admin Panel (operator-only)

Extends the **existing** server-rendered admin panel at `/admin`
(`backend/app/api/admin.py`) — it is intentionally not part of the React app or
its nav; an operator reaches it by typing the URL and authenticating. Reuses the
existing HTTP Basic Auth pattern (`requires_admin_auth`), which enforces a
server-side credential check on every request.

**Security fix folded in (touching this file anyway):** the panel currently has
**hardcoded** credentials (`ADMIN_USERNAME='admin'`,
`ADMIN_PASSWORD='SnappyAdmin@2025'`). Move these to environment variables —
`ADMIN_PASSWORD` (required; app refuses to expose `/admin` if unset) and
`ADMIN_USERNAME` (optional, defaults to `admin`). Compare with a constant-time
check. Add basic rate-limiting on failed auth. Served over HTTPS (Cloud Run).

A new "Legal Feed" area in the panel provides the four agreed capabilities, all
via `/admin/api/legal-feed/*` endpoints guarded by `requires_admin_auth`:

1. **Ingestion status & monitoring** — recent `legal_feed_runs`: last run time,
   trigger, status, total ingested, and the per-source `results` (fetched /
   inserted / error). The "is it working?" view.
2. **Manual trigger** — "Run ingestion now" button → calls the ingest handler
   with `trigger=manual`. Lets the operator test without waiting for the cron.
3. **Source management** — list/add/edit `legal_feed_sources`: toggle `enabled`,
   add a new `feed_url` (the self-serve "more news sources" lever), set `court`/
   `content_type`.
4. **Item moderation** — view recent `legal_feed_items`; toggle `hidden` to pull
   a broken or bad item from the feed.

**Feed Algorithm section** — exposes the v1 ordering control: choose the global
ordering mode (`recency` | `weighted`) and edit per-source `weight`. This is the
explicit seam for the deferred curated/personalized work — those phases add
their controls (practice-area rules, personalization) into this same section
rather than a new surface. v1 intentionally ships only the ordering knob; richer
logic is updated here as it's built.

## Error Handling

- A failing source logs the error (captured in `legal_feed_runs.results`) and is
  skipped — it never aborts the whole run. One broken source must not starve the
  rest of the feed; the run is marked `partial` rather than `failed`.
- Ingestion is idempotent (dedup_key conflict → no-op), so retries and overlap
  between the 2 daily runs are safe.
- The ingest endpoint is protected by a shared secret header; unauthenticated
  calls are rejected. The admin endpoints are protected by `requires_admin_auth`.
- `/admin` refuses to serve if `ADMIN_PASSWORD` is unset (no insecure default).

## Testing

- Unit-test the RSS fetcher against a saved sample feed fixture: parse →
  expected normalized items.
- Dedup test: ingest the same item twice → exactly one row.
- Run-logging test: a run with one failing source → status `partial`, error
  recorded in `results`, other sources still ingested.
- Read endpoint: filters (`type`, `court`), `hidden` exclusion, both ordering
  modes, and pagination return correct results.
- Ingest endpoint: rejects calls without the secret header.
- Admin: endpoints reject missing/wrong credentials; `/admin` refuses to serve
  when `ADMIN_PASSWORD` is unset; manual-trigger creates a `manual` run.

## Operational Notes

- Frequency: 2×/day. Exact times are configured by the operator in Cloud
  Scheduler (cron) — no code change required to retime.
- Adding a new source = a row in `legal_feed_sources` (via the admin panel) when
  it's an RSS feed; a new `kind` needs one new fetcher module.
- New env vars: `ADMIN_PASSWORD` (required), `ADMIN_USERNAME` (optional), and the
  ingest endpoint's shared secret.
