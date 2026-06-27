# Legal Feed — Personalization & Enrichment (Design)

Date: 2026-06-22
Status: Approved (pending spec review)
Builds on: `2026-06-17-legal-feed-design.md` (ingestion pipeline + awareness feed, already shipped)

## Problem

The v1 feed ingests ~100 cards/day but is **not impactful**: items are unranked,
untailored, weakly titled, and force the counsel to click through and read the
whole article to learn what it's about. We need to deliver an *important,
tailored, personalized* feed so the lawyer doesn't waste time browsing — with
better titles, a "why it matters" summary, topic/practice-area awareness, and
images for memorability.

This design covers that (#3) plus three small adjacent items (#1, #2, #4).

## Scope

One coherent feature: enrichment + personalization for the feed. Plus:
- **#1** court-filter bug (legal feed)
- **#2** admin per-source content counts (legal feed)
- **#4** CC the sending user on invoice email — **independent** of the feed;
  specified here for convenience but can be built and committed on its own.

Out of scope (noted as future hooks, not built): behavioral/implicit learning
(Phase 2), near-duplicate news clustering, pgvector, cross-source story merging.

## Key decisions (from brainstorming)

- **Enrichment is content-type-aware.** News gets a rewritten `headline`, a
  `tldr` ("why it matters"), `topics`, `importance`. **Judgements keep their
  canonical case name** and get only `topics` + `importance` (no headline, no
  tldr — an LLM must never fabricate a holding from a one-line snippet).
- **Provider is OpenAI** (not Claude/Haiku), called via direct `requests` behind
  a pluggable `EnrichmentClient` interface (mirrors the existing `EmailTransport`
  pattern). Model is TBD → configured via env.
- **Two-tier personalization, server-synced:**
  - *Macro:* per-user taxonomy weights + preferred courts (coarse filter/boost).
  - *Micro:* embedding similarity within the user's interested topics, seeded in
    v1 from **free-text interest phrases**; behavioral centroid is the long-run
    direction (Phase 2).
- **Layout:** within each tab (Judgements / News), a **"For you"** section
  (personalized) above a **"Latest"** chronological section.
- **Embeddings stored as JSON floats; similarity ranked in Python** over the
  taxonomy/recency-filtered candidate set, behind a `rank_by_similarity()`
  function. Rationale: no new Postgres extension, stays testable on the existing
  in-memory SQLite harness, sub-millisecond at this scale. **pgvector is a
  drop-in upgrade** behind the same function if the pool grows.
- **Images:** hotlink the RSS image URL with a deterministic court/topic fallback
  for items without one (all judgements).

## Fixed practice-area taxonomy

The single source of truth shared by the LLM classifier and the user preference
UI (they MUST align):

```
Tax, Criminal, Civil, Constitutional, Corporate/Commercial, IP,
Environment, Labour/Service, Family, Property, Banking/Insolvency, Arbitration
```

The LLM may only emit topics from this list; anything else is rejected.

## Data model

### `LegalFeedItem` — new columns (all nullable; raw `title`/`summary` retained)
- `headline` — punchy rewrite, **news only**; display falls back to `title`.
- `tldr` — "why it matters", **news only**.
- `topics` — JSON list, subset of the taxonomy.
- `importance` — int 0–100.
- `image_url` — extracted from the RSS item.
- `embedding` — JSON list of floats.
- `embed_model` — string stamp (model + implied dimension) next to `embedding`.
- `enriched_at` — datetime; NULL means "not yet enriched" (drives idempotency).

### `LegalFeedPreference` — new table
- `user_id` (unique)
- `topic_weights` — JSON map `{topic: weight}` over the taxonomy
- `courts` — JSON list of preferred courts
- `interest_phrases` — JSON list of free-text strings
- `interest_embedding` — JSON list of floats (computed from phrases on save)
- `embed_model` — string stamp
- `updated_at`

### `LegalFeedRun` — new columns
- `enriched` — count enriched this run
- `enrich_failed` — count that failed enrichment (still ingested)

## Ingestion + enrichment pipeline

Two phases per run, so a flaky LLM never blocks content from appearing.

**Phase 1 — Ingest (reliable, unchanged behavior + image):**
fetch → parse → compute dedup_key → skip existing, else insert the raw item
including `image_url`. Per-source errors stay isolated and recorded. Collect the
ids of newly-inserted items.

**Phase 2 — Enrich (best-effort, idempotent):**
select new items where `enriched_at IS NULL`. For each (small thread pool, ~5):
1. One LLM call with a **content-type-aware** prompt → JSON.
2. One embedding call over the item's text (news: `headline`+`tldr`+`summary`;
   judgement: `title`+`summary`).
3. **Validate hard:** topics ∈ taxonomy (drop unknowns), `importance` clamped
   0–100, judgements carry no `tldr`/`headline`. Bad/partial JSON ⇒ failure.
4. On success: write fields + `embedding` + `embed_model` + `enriched_at=now`.
   On failure: leave `enriched_at` NULL, increment `enrich_failed`; **the item is
   already live with raw fields.**

Because Phase 2 only touches `enriched_at IS NULL`, re-running a failed run fills
only the gaps — **no double billing**.

**Backlog backfill:** the ~199 already-ingested items have `enriched_at IS NULL`.
Enriching them is a **deliberate, separate admin action** ("Enrich backlog",
batched + rate-limit-aware), not a side effect of the next scheduled run.

**PII boundary:** only public feed content (RSS title/summary) is ever sent to
OpenAI. Client, firm, and invoice data are never sent.

## Personalization

### Preferences (API + UI)
A "Personalize" panel on the Legal Feed page: pick topics (macro weights) +
courts, optionally add free-text interest phrases. On save, the server embeds the
phrases into `interest_embedding` (stamped with `embed_model`) and stores the
preference row.

### "For you"
1. Candidate filter: items in the user's topics/courts within a recent window
   (≈14 days).
2. Rank by `rank_by_similarity()` — cosine of item `embedding` vs the user's
   `interest_embedding` — blended with `importance` × recency-decay.
3. Return top N (≈10).
4. **Cold start** (no prefs / no embedding): fall back to global importance ×
   recency and surface a "Personalize your feed" prompt.

### "Latest"
Chronological, paginated — current behavior preserved.

## Provider & configuration

`EnrichmentClient` interface with an `OpenAIEnrichment` implementation (direct
`requests`, no SDK). Env:
- `OPENAI_API_KEY`
- `LEGAL_FEED_ENRICH_MODEL` (TBD)
- `LEGAL_FEED_EMBED_MODEL` (default `text-embedding-3-small`)

If `OPENAI_API_KEY` is unset, ingestion still runs; enrichment is skipped and
items remain unenriched (graceful degradation).

## Small items

### #1 — Court filter (bug)
`LegalFeed.tsx` derives the dropdown from the currently-loaded page only, so only
courts present on page 1 appear. Fix: backend exposes the full distinct-court
list (from enabled sources); the dropdown reads that.

### #2 — Admin per-source counts
Add per-source item counts (last run + last 24h) to the admin Sources table,
reading from items + the latest run results.

### #4 — CC the sending user on invoice email (independent)
Thread a `cc` param through `send_invoice` → `EmailTransport.send` → the Resend
payload. **CC = the firm's `firm_email`** (already used as `reply_to`), keeping
the firm looped in on what it sent. Robustness: skip the CC if it is missing or
equals the `to` address, and never let a CC issue block the actual send.

## Error handling

- Per-source ingestion errors isolated and recorded (unchanged).
- Enrichment/embedding failures degrade gracefully: raw item survives, counted in
  `enrich_failed`, retried on a later run.
- Missing `OPENAI_API_KEY` ⇒ enrichment skipped, ingestion unaffected.
- Invoice CC problems never block the send.

## Testing (TDD)

- `EnrichmentClient` with mocked HTTP (success, bad JSON, non-taxonomy topic,
  judgement-must-not-have-tldr).
- Content-type-aware enrich logic + idempotency on `enriched_at`.
- `rank_by_similarity()` cosine ordering (pure function, Python).
- Preferences CRUD + embedding-on-save (mocked embed call).
- "For you" (filter + rank + cold-start fallback) and "Latest" queries.
- Court-list endpoint (#1), admin per-source counts (#2).
- Invoice CC threading + skip/dedupe rules (#4).
- Frontend: `npm run build` (tsc + vite) and `npm run lint --max-warnings 0`.

## Future hooks (not built)

- **Phase 2 personalization:** behavioral centroid nudging `interest_embedding`
  from clicks/saves.
- **Near-duplicate clustering:** embeddings make same-story merging across
  sources cheap later; v1 keeps exact dedup only.
- **pgvector:** swap in behind `rank_by_similarity()` when the candidate pool
  outgrows brute-force Python cosine.
