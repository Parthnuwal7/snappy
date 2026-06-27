-- 022_slim_case_schema.sql — fold case_parties into case_files.parties (JSON) and
-- case_exhibits into case_documents. Keeps case_stage_changes (Progression strip).
-- Run on the backed-up DB. Apply in Supabase.
BEGIN;

-- ---- R2a: parties become an inline JSON list on case_files ----
ALTER TABLE public.case_files ADD COLUMN IF NOT EXISTS parties JSONB DEFAULT '[]'::jsonb;
UPDATE public.case_files cf SET parties = COALESCE((
    SELECT json_agg(json_build_object('name', p.name, 'role', p.role) ORDER BY p.id)
    FROM public.case_parties p WHERE p.case_file_id = cf.id), '[]'::json);
DROP TABLE IF EXISTS public.case_parties;

-- ---- R2b: exhibits fold into case_documents ----
ALTER TABLE public.case_documents ALTER COLUMN storage_path DROP NOT NULL;
ALTER TABLE public.case_documents ADD COLUMN IF NOT EXISTS is_exhibit BOOLEAN DEFAULT FALSE;
ALTER TABLE public.case_documents ADD COLUMN IF NOT EXISTS exhibit_mark VARCHAR(40);
ALTER TABLE public.case_documents ADD COLUMN IF NOT EXISTS party VARCHAR(40);
ALTER TABLE public.case_documents ADD COLUMN IF NOT EXISTS exhibit_status VARCHAR(20);
ALTER TABLE public.case_documents ADD COLUMN IF NOT EXISTS hearing_event_id INTEGER REFERENCES public.case_events(id);
ALTER TABLE public.case_documents ADD COLUMN IF NOT EXISTS linked_document_id INTEGER REFERENCES public.case_documents(id);

INSERT INTO public.case_documents
    (firm_id, case_file_id, uploaded_by_user_id, title, doc_type, description,
     is_exhibit, exhibit_mark, party, exhibit_status, hearing_event_id, linked_document_id, created_at)
  SELECT firm_id, case_file_id, created_by_user_id,
         COALESCE(description, exhibit_mark, 'Exhibit'), 'evidence', description,
         TRUE, exhibit_mark, party, status, hearing_event_id, document_id, created_at
  FROM public.case_exhibits;
DROP TABLE IF EXISTS public.case_exhibits;

COMMIT;
