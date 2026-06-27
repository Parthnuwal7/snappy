-- 019_writing.sql — Writing module: templates + drafts. Additive. Apply in Supabase.
BEGIN;

CREATE TABLE IF NOT EXISTS public.templates (
  id SERIAL PRIMARY KEY,
  firm_id INTEGER REFERENCES public.firms(id),
  created_by_user_id INTEGER REFERENCES public.users(id),
  name VARCHAR(200) NOT NULL,
  category VARCHAR(40) DEFAULT 'other',
  body TEXT,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_templates_firm_id ON public.templates (firm_id);

CREATE TABLE IF NOT EXISTS public.drafts (
  id SERIAL PRIMARY KEY,
  firm_id INTEGER REFERENCES public.firms(id),
  created_by_user_id INTEGER REFERENCES public.users(id),
  title VARCHAR(300) NOT NULL,
  body TEXT,
  case_file_id INTEGER REFERENCES public.case_files(id),
  template_id INTEGER REFERENCES public.templates(id),
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_drafts_firm_id ON public.drafts (firm_id);

COMMIT;
