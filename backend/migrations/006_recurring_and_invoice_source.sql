-- 006_recurring_and_invoice_source.sql
-- Adds recurring invoice schedules and a `source` marker on invoices so the
-- dashboard can distinguish recurring-generated drafts from manual ones.
-- Run in the Supabase SQL editor (db.create_all() handles fresh deploys, but
-- it does NOT add the `source` column to the existing invoices table).

ALTER TABLE public.invoices
  ADD COLUMN IF NOT EXISTS source VARCHAR(20) DEFAULT 'manual';

CREATE TABLE IF NOT EXISTS public.recurring_schedules (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  client_id INTEGER NOT NULL REFERENCES public.clients(id) ON DELETE CASCADE,
  title VARCHAR(200),
  items JSONB NOT NULL DEFAULT '[]'::jsonb,
  tax_rate NUMERIC(5,2) DEFAULT 18.0,
  short_desc TEXT,
  notes TEXT,
  frequency VARCHAR(20) NOT NULL,            -- 'weekly' | 'monthly'
  start_date DATE NOT NULL,
  next_run_date DATE NOT NULL,
  end_date DATE,                             -- optional; NULL = run until paused
  last_run_date DATE,
  active BOOLEAN DEFAULT true,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_recurring_user_id ON public.recurring_schedules(user_id);
CREATE INDEX IF NOT EXISTS idx_recurring_due ON public.recurring_schedules(active, next_run_date);
