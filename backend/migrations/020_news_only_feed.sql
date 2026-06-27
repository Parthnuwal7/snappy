-- 020_news_only_feed.sql — news-only legal feed cleanup (2026-06-26).
-- Disables judgement sources and hides existing judgement items. No tables or
-- columns dropped (deferred). Re-running is a safe no-op.
BEGIN;

UPDATE public.legal_feed_sources SET enabled = FALSE WHERE content_type <> 'news';
UPDATE public.legal_feed_items   SET hidden  = TRUE  WHERE content_type <> 'news';

COMMIT;
