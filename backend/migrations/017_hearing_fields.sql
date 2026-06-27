-- 017_hearing_fields.sql — hearing purpose + outcome on case_events.
-- Additive/non-destructive. Apply in the Supabase SQL editor.
BEGIN;

ALTER TABLE public.case_events ADD COLUMN IF NOT EXISTS purpose VARCHAR(80);
ALTER TABLE public.case_events ADD COLUMN IF NOT EXISTS outcome TEXT;

COMMIT;
