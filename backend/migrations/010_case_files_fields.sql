-- 010_case_files_fields.sql — richer litigation fields on case_files.
-- Additive, non-destructive. Apply after 009 in the Supabase SQL editor.
BEGIN;

ALTER TABLE public.case_files ADD COLUMN IF NOT EXISTS jurisdiction VARCHAR(120);
ALTER TABLE public.case_files ADD COLUMN IF NOT EXISTS act_section VARCHAR(200);
ALTER TABLE public.case_files ADD COLUMN IF NOT EXISTS opposing_counsel VARCHAR(200);
ALTER TABLE public.case_files ADD COLUMN IF NOT EXISTS priority VARCHAR(20) NOT NULL DEFAULT 'normal';
ALTER TABLE public.case_files ADD COLUMN IF NOT EXISTS filing_date DATE;

COMMIT;
