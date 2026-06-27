-- 012_case_record_depth.sql — agreed_fee + stage history + expense ledger.
-- Additive, non-destructive. Apply in the Supabase SQL editor.
BEGIN;

ALTER TABLE public.case_files ADD COLUMN IF NOT EXISTS agreed_fee NUMERIC(12,2);

CREATE TABLE IF NOT EXISTS public.case_stage_changes (
  id SERIAL PRIMARY KEY,
  firm_id INTEGER REFERENCES public.firms(id),
  case_file_id INTEGER REFERENCES public.case_files(id) ON DELETE CASCADE,
  from_stage VARCHAR(40),
  to_stage VARCHAR(40),
  changed_by_user_id INTEGER REFERENCES public.users(id),
  changed_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_case_stage_changes_case_file_id ON public.case_stage_changes (case_file_id);
CREATE INDEX IF NOT EXISTS ix_case_stage_changes_firm_id ON public.case_stage_changes (firm_id);

CREATE TABLE IF NOT EXISTS public.case_expenses (
  id SERIAL PRIMARY KEY,
  firm_id INTEGER REFERENCES public.firms(id),
  case_file_id INTEGER REFERENCES public.case_files(id) ON DELETE CASCADE,
  expense_date DATE,
  description VARCHAR(300) NOT NULL,
  category VARCHAR(40) DEFAULT 'misc',
  amount NUMERIC(12,2),
  created_by_user_id INTEGER REFERENCES public.users(id),
  created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_case_expenses_case_file_id ON public.case_expenses (case_file_id);
CREATE INDEX IF NOT EXISTS ix_case_expenses_firm_id ON public.case_expenses (firm_id);

COMMIT;
