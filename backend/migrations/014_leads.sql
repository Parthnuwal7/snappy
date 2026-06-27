-- 014_leads.sql — Lead/Enquiry entity + case_files.lead_id origin link.
-- Additive/non-destructive. Apply in the Supabase SQL editor.
BEGIN;

CREATE TABLE IF NOT EXISTS public.leads (
  id SERIAL PRIMARY KEY,
  firm_id INTEGER REFERENCES public.firms(id),
  created_by_user_id INTEGER REFERENCES public.users(id),
  contact_name VARCHAR(200) NOT NULL,
  phone VARCHAR(50),
  email VARCHAR(200),
  matter_summary TEXT,
  intake_notes TEXT,
  status VARCHAR(20) NOT NULL DEFAULT 'open',
  decided_at TIMESTAMP,
  converted_case_file_id INTEGER REFERENCES public.case_files(id),
  created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_leads_firm_id ON public.leads (firm_id);

ALTER TABLE public.case_files ADD COLUMN IF NOT EXISTS lead_id INTEGER REFERENCES public.leads(id);

COMMIT;
