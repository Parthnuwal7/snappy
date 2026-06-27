-- 011_case_documents.sql — Case document vault (sub-project 3).
-- Additive, non-destructive. Apply in the Supabase SQL editor.
-- ALSO create a PRIVATE bucket named 'case-documents' in Storage (dashboard).
BEGIN;

CREATE TABLE IF NOT EXISTS public.case_documents (
  id SERIAL PRIMARY KEY,
  firm_id INTEGER REFERENCES public.firms(id),
  case_file_id INTEGER REFERENCES public.case_files(id) ON DELETE CASCADE,
  event_id INTEGER REFERENCES public.case_events(id) ON DELETE SET NULL,
  uploaded_by_user_id INTEGER REFERENCES public.users(id),
  title VARCHAR(300) NOT NULL,
  doc_type VARCHAR(40) NOT NULL DEFAULT 'other',
  file_name VARCHAR(300),
  mime_type VARCHAR(120),
  size_bytes INTEGER,
  storage_path VARCHAR(500) NOT NULL,
  description TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_case_documents_firm_id ON public.case_documents (firm_id);
CREATE INDEX IF NOT EXISTS ix_case_documents_case_file_id ON public.case_documents (case_file_id);
CREATE INDEX IF NOT EXISTS ix_case_documents_event_id ON public.case_documents (event_id);

COMMIT;

-- Manual: Supabase dashboard → Storage → New bucket → name 'case-documents',
-- Private. Permissions need no migration (Owners dynamic; others via Roles editor).
