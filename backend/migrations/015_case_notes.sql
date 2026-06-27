-- 015_case_notes.sql — case notes stream (running commentary, pin/attach).
-- Additive/non-destructive. Apply in the Supabase SQL editor.
BEGIN;

CREATE TABLE IF NOT EXISTS public.case_notes (
  id SERIAL PRIMARY KEY,
  firm_id INTEGER REFERENCES public.firms(id),
  case_file_id INTEGER REFERENCES public.case_files(id) ON DELETE CASCADE,
  body TEXT NOT NULL,
  pinned BOOLEAN NOT NULL DEFAULT FALSE,
  event_id INTEGER REFERENCES public.case_events(id),
  document_id INTEGER REFERENCES public.case_documents(id),
  created_by_user_id INTEGER REFERENCES public.users(id),
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_case_notes_case_file_id ON public.case_notes (case_file_id);
CREATE INDEX IF NOT EXISTS ix_case_notes_firm_id ON public.case_notes (firm_id);

COMMIT;
