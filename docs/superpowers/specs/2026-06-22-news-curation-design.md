# Behavior-Curated News Feed + Dense Layout (Design)

Date: 2026-06-22
Status: Approved (pending spec review)
Builds on: `2026-06-22-legal-feed-personalization-design.md` (enrichment + explicit-preference personalization, shipped)

## Goal

Make the **news** feed feel curated and "pushed" like X: it should learn from
what the counsel actually engages with, surface more relevant volume, and present
it in a dense, scannable, multi-column layout. Judgements are out of scope here
(currently not enriched; handled later).

## Decisions (from brainstorming)

- **Primary driver: learn from behavior** (bring the deferred behavioral layer
  forward), on top of the existing explicit preferences.
- **Signals: clicks (positive) + "Not interested" (negative).**
- **Update: online EMA (instant) + periodic batch recompute** from the event log
  (the log is the source of truth).
- **Negative guardrail:** a single rejection only **demotes that one item**
  (pushed to the bottom of the user's ranking, not hidden); negative *learning*
  activates only after **N = 3 total** rejections. Clicks have no threshold.
- **Volume:** "For you" becomes the primary news surface — initial **30**,
  load-more **+30**.
- **Layout:** dense, text-first **3-column** news wall (responsive). Judgements
  tab keeps its current simple list.

## Data model

### `LegalFeedEvent` (new)
- `id`
- `user_id` (indexed)
- `item_id` (FK → legal_feed_items)
- `kind` — `'click'` | `'not_interested'`
- `created_at`
- Index on `(user_id, kind)` for counting/recompute.

### `LegalFeedPreference` (extend)
- `behavior_embedding` — JSON float array (the learned vector)
- `behavior_updated_at` — datetime

## Behavioral engine

All vector math is pure Python in a new `behavior.py`, testable in isolation.

### Constants
- `EMA_ALPHA = 0.2` (click pull), `EMA_BETA = 0.2` (rejection push)
- `NEGATIVE_MIN_EVENTS = 3` (negative-learning threshold)
- `BEHAVIOR_DOMINATES_AT = 5` (events after which behavior outweighs phrases)
- `RECOMPUTE_DECAY_DAYS = 30` (half-life for batch recompute weighting)

### Online update (`apply_event`)
Given the current `behavior_embedding`, an item embedding, the event kind, and
the user's running `not_interested` count:
- **click:** `v = normalize((1-α)·v + α·e)` (if `v` is None → `e`).
- **not_interested:** record always (the item is demoted via ranking, not
  hidden); **only if** `not_interested_count ≥ NEGATIVE_MIN_EVENTS` do
  `v = normalize(v − β·e)`. Otherwise leave `v` unchanged.

Returns the new vector (or None if nothing to do yet, e.g. no embedding on item).

### Batch recompute (`recompute_behavior_embedding(user_id)`)
Rebuild from the event log (source of truth):
1. Pull this user's events joined to item embeddings, within a recent window.
2. Weight each by recency decay (`0.5 ** (age_days / RECOMPUTE_DECAY_DAYS)`).
3. Positive contribution from clicks (always). Negative contribution from
   rejections **only if** the user's total `not_interested` count ≥
   `NEGATIVE_MIN_EVENTS`.
4. `behavior_embedding = normalize(Σ w·e_click − Σ w·e_reject)`; stamp
   `behavior_updated_at`. Store on the preference row (create if absent).

Exposed for a scheduler/admin trigger; not required for the online path to work.

## Ranking & suppression (`query_for_you` changes)

- **Blended interest vector:** combine the explicit `interest_embedding` (typed
  phrases) and the learned `behavior_embedding`:
  - both present → `bw = min(1.0, event_count / BEHAVIOR_DOMINATES_AT)`;
    `blended = normalize((1 − bw)·interest + bw·behavior)`. So behavior grows from
    0 weight to full weight over the first 5 events.
  - only one present → use it. Neither → cold start (importance × recency).
- **Macro filter unchanged:** topic-weight keys + courts still filter candidates;
  fall back to all recent candidates if nothing matches.
- **Demotion (not suppression):** items the user marked `not_interested`
  (by `item_id`) get a heavy score penalty (`REJECT_PENALTY`, e.g. ×0.05) so they
  sink to the bottom of "For you" and "Latest" rather than being removed. The
  frontend optimistically drops the card from the current view for immediate
  feedback.
- **Volume/paging:** `query_for_you` gains `offset`; the endpoint supports
  `limit` + `offset` for load-more.

## Events API

`POST /api/v1/legal-feed/events` (`@jwt_required`), body `{item_id, kind}`:
1. Validate `kind ∈ {click, not_interested}` and that the item exists.
2. Insert a `LegalFeedEvent`.
3. Apply the online update (`apply_event`) to the user's preference row, using the
   user's current `not_interested` count for the threshold.
4. Return `{ok: true}`.

Frontend fires `click` fire-and-forget when "Read at source" is opened, and
`not_interested` when the ✕ control is used.

## Frontend

### News tab — dense 3-column wall
- Wider container (e.g. `max-w-6xl`); responsive grid `1 → 2 → 3` columns.
- Card = punchy `headline` (fallback `title`), `tldr` (fallback `summary`),
  a small `source · court · date` line, "Read at source ↗", and a quiet
  "Not interested" ✕.
- Minimal/no imagery for density.
- **"For you" is the primary section**: 30 items, "Load more" (+30) via `offset`.
  "Latest" remains available as a secondary section/toggle.
- Opening an article calls the events API (`click`); the ✕ calls it
  (`not_interested`) and removes the card locally.

### Judgements tab
Unchanged simple list (not enriched).

## Error handling
- Events are best-effort: a failed event POST never blocks opening the article or
  the UI; log and move on.
- Items without an embedding contribute nothing to learning (skipped safely).
- Missing preference row is created on first event.

## Testing (TDD)
- `behavior.normalize` / `apply_event`: click pull, rejection ignored below
  threshold, rejection applied at/above threshold, cold-start init, item without
  embedding is a no-op.
- `recompute_behavior_embedding`: recency weighting, negatives excluded below
  threshold and included at/above it.
- `query_for_you`: blend of phrases + behavior, not-interested demotion (rejected
  items rank last, not removed), `offset` paging.
- Events endpoint: validation, event row created, online update applied, auth
  required.
- Frontend: `npm run build` + `npm run lint`.

## Out of scope / future
- Behavioral signals for judgements (judgements aren't enriched yet).
- Dwell/impression signals (noisy, heavy instrumentation).
- Saved/bookmarks view.
- pgvector (still Python cosine at this scale).
