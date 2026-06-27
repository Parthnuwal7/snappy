# Legal Feed — Operations

## One-time setup
1. Set env vars in the Cloud Run service: `ADMIN_PASSWORD`, optionally
   `ADMIN_USERNAME`, and `LEGAL_FEED_INGEST_SECRET`.
2. Seed the source registry once: open `/admin`, authenticate, click
   **"Seed v1 sources"** (or run `cd backend && python -m app.services.legal_feed.seed`).
3. Verify the two news feed URLs (LiveLaw, Bar & Bench) return valid RSS; fix in
   the admin Sources table if needed.

## Scheduled ingestion (2×/day)
Create a Cloud Scheduler job (set the two times you want, e.g. 08:00 and 18:00 IST):

    Method:  POST
    URL:     https://<cloud-run-host>/api/v1/legal-feed/ingest
    Header:  X-Ingest-Secret: <LEGAL_FEED_INGEST_SECRET>
    Body:    (empty)

## Monitoring
- `/admin` → Legal Feed card shows recent runs (status, items ingested) and
  per-source results. Use "Run ingestion now" to test on demand.

## Tuning the feed
- Enable/disable sources and add new RSS feeds in the Sources table.
- Switch ordering between "Recency" and "Weighted" (uses per-source weight).
- The Sources table also shows per-source content counts: **24h** (items ingested
  in the last day) and **Last run** (items inserted by the most recent run).

## Enrichment & personalization
- **Enrichment runs automatically** during each ingest for newly-added items:
  news gets a punchy `headline`, a "why it matters" `tldr`, practice-area
  `topics`, an `importance` score, and an embedding; judgements keep their
  canonical case name and get only `topics` + `importance` + embedding (an LLM
  must never fabricate a holding). Set `OPENAI_API_KEY` (and optionally
  `LEGAL_FEED_ENRICH_MODEL`, `LEGAL_FEED_EMBED_MODEL`) to enable it.
- **Best-effort:** if enrichment fails for an item it still appears with its raw
  title/summary; the failure is counted as `enrich_failed` in the run results and
  retried automatically on a later run (only items with no enrichment yet).
- **Backlog:** after first enabling OpenAI, click **"Enrich backlog"** in `/admin`
  to enrich already-ingested items (batched; safe to click repeatedly — it only
  touches un-enriched items, so no double billing).
- **Personalization is per-user**, set via the in-app **Personalize** panel on the
  Legal Feed page (practice areas + courts + free-text interests). The feed shows
  a personalized "For you" shelf above the chronological "Latest" list. Users with
  no preferences set see a global importance-ranked "For you".

## Behavioral curation (news)
- The news feed **learns from engagement**: opening an article ("Read at source")
  is a positive signal; "Not interested" demotes that item for the user and, after
  **3+** rejections, steers the feed away from similar items. A single rejection
  only demotes — it never hides and never reshapes the feed.
- Updates are **instant** (online EMA). **"Recompute behavior"** in `/admin`
  re-grounds all users' vectors from the event log (`legal_feed_events`) — safe to
  run on a schedule.
- The News tab is a dense multi-column "For you" wall (30 items, load-more);
  judgements keep the simple list and are not part of behavioral learning.
