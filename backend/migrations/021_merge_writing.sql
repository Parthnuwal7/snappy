-- 021_merge_writing.sql — collapse templates + drafts into one writing_documents
-- table (distinguished by kind). Run on the backed-up DB. Apply in Supabase.
BEGIN;

CREATE TABLE IF NOT EXISTS public.writing_documents (
  id SERIAL PRIMARY KEY,
  firm_id INTEGER REFERENCES public.firms(id),
  created_by_user_id INTEGER REFERENCES public.users(id),
  kind VARCHAR(20) NOT NULL,
  title VARCHAR(300) NOT NULL,
  category VARCHAR(40),
  body TEXT,
  case_file_id INTEGER REFERENCES public.case_files(id),
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_writing_documents_firm_id ON public.writing_documents (firm_id);

-- Carry existing rows over (no-op if the old tables are already gone).
INSERT INTO public.writing_documents (firm_id, created_by_user_id, kind, title, category, body, created_at, updated_at)
  SELECT firm_id, created_by_user_id, 'template', name, category, body, created_at, updated_at
  FROM public.templates;
INSERT INTO public.writing_documents (firm_id, created_by_user_id, kind, title, category, body, case_file_id, created_at, updated_at)
  SELECT firm_id, created_by_user_id, 'draft', title, NULL, body, case_file_id, created_at, updated_at
  FROM public.drafts;

DROP TABLE IF EXISTS public.drafts;     -- drafts references templates, drop first
DROP TABLE IF EXISTS public.templates;

COMMIT;
