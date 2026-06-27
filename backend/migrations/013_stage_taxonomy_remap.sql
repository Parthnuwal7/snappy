-- 013_stage_taxonomy_remap.sql — remap legacy case stage keys to the
-- 2026-06-25 litigation taxonomy. Additive/idempotent: after it runs, no
-- rows carry the old keys, so re-running is a safe no-op. Apply in Supabase.
BEGIN;

UPDATE public.case_files SET stage = 'engaged'           WHERE stage = 'intake';
UPDATE public.case_files SET stage = 'notice'            WHERE stage = 'drafting';
UPDATE public.case_files SET stage = 'hearings_evidence' WHERE stage = 'in_hearing';
UPDATE public.case_files SET stage = 'judgment'          WHERE stage = 'awaiting_order';
-- 'filed' and 'closed' are unchanged; no UPDATE needed.

COMMIT;
