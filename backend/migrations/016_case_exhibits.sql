-- 016_case_exhibits.sql — evidence exhibit register (Ex. P-1/D-1 marks).
-- Additive/non-destructive. Apply in the Supabase SQL editor.
BEGIN;

CREATE TABLE IF NOT EXISTS public.case_exhibits (
  id SERIAL PRIMARY KEY,
  firm_id INTEGER REFERENCES public.firms(id),
  case_file_id INTEGER REFERENCES public.case_files(id) ON DELETE CASCADE,
  exhibit_mark VARCHAR(40),
  description VARCHAR(300),
  party VARCHAR(40),
  status VARCHAR(20) NOT NULL DEFAULT 'marked',
  document_id INTEGER REFERENCES public.case_documents(id),
  hearing_event_id INTEGER REFERENCES public.case_events(id),
  created_by_user_id INTEGER REFERENCES public.users(id),
  created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_case_exhibits_case_file_id ON public.case_exhibits (case_file_id);
CREATE INDEX IF NOT EXISTS ix_case_exhibits_firm_id ON public.case_exhibits (firm_id);

COMMIT;
