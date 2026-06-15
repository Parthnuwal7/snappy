-- 005_create_keepalive.sql
--
-- Heartbeat table. Cloud Scheduler hits POST/GET /keepalive every 3 days;
-- the endpoint inserts a row here so Supabase sees DB write activity and
-- doesn't auto-pause the project (free tier pauses after 7 days idle).
--
-- One ping every 3 days = ~120 rows/year. Negligible. No pruning needed
-- in the foreseeable future.

CREATE TABLE IF NOT EXISTS keepalive (
  id          BIGSERIAL PRIMARY KEY,
  pinged_at   TIMESTAMP NOT NULL DEFAULT NOW(),
  source      VARCHAR(50)
);

CREATE INDEX IF NOT EXISTS idx_keepalive_pinged_at
  ON keepalive (pinged_at DESC);
