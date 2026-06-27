-- 009_case_files.sql — Case File spine (sub-project 2).
-- Additive, non-destructive. Apply once in the Supabase SQL editor.
-- Creates case_files / case_parties / case_events and links invoices to a case.
BEGIN;

CREATE TABLE IF NOT EXISTS public.case_files (
  id SERIAL PRIMARY KEY,
  firm_id INTEGER REFERENCES public.firms(id),
  created_by_user_id INTEGER REFERENCES public.users(id),
  case_number VARCHAR(50) NOT NULL,
  title VARCHAR(300) NOT NULL,
  client_id INTEGER NOT NULL REFERENCES public.clients(id),
  matter_type VARCHAR(80),
  court VARCHAR(200),
  court_case_number VARCHAR(120),
  stage VARCHAR(40) NOT NULL DEFAULT 'intake',
  position INTEGER NOT NULL DEFAULT 0,
  handling_advocate_user_id INTEGER REFERENCES public.users(id),
  next_hearing_date DATE,
  open_date DATE,
  description TEXT,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  CONSTRAINT case_files_firm_id_case_number_key UNIQUE (firm_id, case_number)
);
CREATE INDEX IF NOT EXISTS ix_case_files_firm_id ON public.case_files (firm_id);
CREATE INDEX IF NOT EXISTS ix_case_files_created_by ON public.case_files (created_by_user_id);
CREATE INDEX IF NOT EXISTS ix_case_files_case_number ON public.case_files (case_number);

CREATE TABLE IF NOT EXISTS public.case_parties (
  id SERIAL PRIMARY KEY,
  case_file_id INTEGER REFERENCES public.case_files(id) ON DELETE CASCADE,
  name VARCHAR(300) NOT NULL,
  role VARCHAR(60),
  created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_case_parties_case_file_id ON public.case_parties (case_file_id);

CREATE TABLE IF NOT EXISTS public.case_events (
  id SERIAL PRIMARY KEY,
  case_file_id INTEGER REFERENCES public.case_files(id) ON DELETE CASCADE,
  firm_id INTEGER REFERENCES public.firms(id),
  created_by_user_id INTEGER REFERENCES public.users(id),
  event_date DATE NOT NULL,
  kind VARCHAR(30) NOT NULL DEFAULT 'note',
  title VARCHAR(300) NOT NULL,
  notes TEXT,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_case_events_case_file_id ON public.case_events (case_file_id);
CREATE INDEX IF NOT EXISTS ix_case_events_firm_id ON public.case_events (firm_id);
CREATE INDEX IF NOT EXISTS ix_case_events_event_date ON public.case_events (event_date);

ALTER TABLE public.invoices
  ADD COLUMN IF NOT EXISTS case_file_id INTEGER REFERENCES public.case_files(id);
CREATE INDEX IF NOT EXISTS ix_invoices_case_file_id ON public.invoices (case_file_id);

COMMIT;

-- Permissions need no migration: the Owner role resolves to ALL_PERMISSIONS
-- dynamically, so existing firm owners gain case_files.* automatically. Grant
-- case_files.* to other roles via the in-app Roles editor as needed.
