-- 018_tasks.sql — firm-scoped, date-scheduled tasks (day planner).
-- Additive/non-destructive. Apply in the Supabase SQL editor.
BEGIN;

CREATE TABLE IF NOT EXISTS public.tasks (
  id SERIAL PRIMARY KEY,
  firm_id INTEGER REFERENCES public.firms(id),
  created_by_user_id INTEGER REFERENCES public.users(id),
  title VARCHAR(300) NOT NULL,
  due_date DATE,
  case_file_id INTEGER REFERENCES public.case_files(id),
  done BOOLEAN NOT NULL DEFAULT FALSE,
  priority VARCHAR(20) NOT NULL DEFAULT 'normal',
  created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_tasks_firm_id ON public.tasks (firm_id);
CREATE INDEX IF NOT EXISTS ix_tasks_due_date ON public.tasks (due_date);

COMMIT;
