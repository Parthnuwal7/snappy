-- 008_firm_tenancy.sql — Firm tenancy & RBAC foundation.
-- In-place, additive, NON-DESTRUCTIVE. Apply once in the Supabase SQL editor.
-- Nothing is dropped, moved, or copied: new tables + new columns + a column
-- rename (user_id -> created_by_user_id, which preserves all data) + backfill.
-- Safe to re-run (guards skip already-migrated rows).
BEGIN;

-- 1. New tables -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.firms (
  id SERIAL PRIMARY KEY,
  name VARCHAR(200) NOT NULL,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.roles (
  id SERIAL PRIMARY KEY,
  firm_id INTEGER NOT NULL REFERENCES public.firms(id) ON DELETE CASCADE,
  name VARCHAR(80) NOT NULL,
  description TEXT,
  permissions JSONB DEFAULT '[]'::jsonb,
  is_system BOOLEAN NOT NULL DEFAULT false,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  UNIQUE (firm_id, name)
);

CREATE TABLE IF NOT EXISTS public.firm_invites (
  id SERIAL PRIMARY KEY,
  firm_id INTEGER NOT NULL REFERENCES public.firms(id) ON DELETE CASCADE,
  email VARCHAR(200) NOT NULL,
  role_id INTEGER NOT NULL REFERENCES public.roles(id),
  token VARCHAR(64) NOT NULL UNIQUE,
  status VARCHAR(20) NOT NULL DEFAULT 'pending',
  invited_by INTEGER REFERENCES public.users(id),
  expires_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW(),
  accepted_at TIMESTAMP
);

-- 2. New columns (nullable -> non-blocking, breaks no existing query) --------
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS firm_id INTEGER REFERENCES public.firms(id);
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS role_id INTEGER REFERENCES public.roles(id);
ALTER TABLE public.firm_details ADD COLUMN IF NOT EXISTS firm_id INTEGER REFERENCES public.firms(id);
ALTER TABLE public.bank_accounts ADD COLUMN IF NOT EXISTS firm_id INTEGER REFERENCES public.firms(id);
ALTER TABLE public.bank_accounts ADD COLUMN IF NOT EXISTS created_by_user_id INTEGER REFERENCES public.users(id);

-- 3. Rename user_id -> created_by_user_id on the four billing tables.
--    Instant, metadata-only, preserves every value. Guarded so re-runs no-op.
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.columns
             WHERE table_name='clients' AND column_name='user_id') THEN
    ALTER TABLE public.clients RENAME COLUMN user_id TO created_by_user_id;
  END IF;
  IF EXISTS (SELECT 1 FROM information_schema.columns
             WHERE table_name='items' AND column_name='user_id') THEN
    ALTER TABLE public.items RENAME COLUMN user_id TO created_by_user_id;
  END IF;
  IF EXISTS (SELECT 1 FROM information_schema.columns
             WHERE table_name='invoices' AND column_name='user_id') THEN
    ALTER TABLE public.invoices RENAME COLUMN user_id TO created_by_user_id;
  END IF;
  IF EXISTS (SELECT 1 FROM information_schema.columns
             WHERE table_name='recurring_schedules' AND column_name='user_id') THEN
    ALTER TABLE public.recurring_schedules RENAME COLUMN user_id TO created_by_user_id;
  END IF;
END $$;

ALTER TABLE public.clients             ADD COLUMN IF NOT EXISTS firm_id INTEGER REFERENCES public.firms(id);
ALTER TABLE public.items               ADD COLUMN IF NOT EXISTS firm_id INTEGER REFERENCES public.firms(id);
ALTER TABLE public.invoices            ADD COLUMN IF NOT EXISTS firm_id INTEGER REFERENCES public.firms(id);
ALTER TABLE public.recurring_schedules ADD COLUMN IF NOT EXISTS firm_id INTEGER REFERENCES public.firms(id);

-- 4. One firm per existing user, made Owner. Owner.permissions MUST equal the
--    app's ALL_PERMISSIONS (regenerate this list if the catalog changes).
DO $$
DECLARE u RECORD; new_firm_id INTEGER; owner_role_id INTEGER;
BEGIN
  FOR u IN SELECT id, email FROM public.users WHERE firm_id IS NULL LOOP
    INSERT INTO public.firms(name)
      VALUES (COALESCE((SELECT firm_name FROM public.firm_details WHERE user_id = u.id LIMIT 1), u.email))
      RETURNING id INTO new_firm_id;

    INSERT INTO public.roles(firm_id, name, is_system, description, permissions)
      VALUES (new_firm_id, 'Owner', true, 'Default Owner role',
        '["bank_accounts.create","bank_accounts.delete","bank_accounts.read","bank_accounts.update","clients.create","clients.delete","clients.read","clients.update","firm_settings.read","firm_settings.update","invoices.create","invoices.delete","invoices.read","invoices.send","invoices.update","items.create","items.delete","items.read","items.update","members.invite","members.manage_roles","members.read","members.remove","recurring.create","recurring.delete","recurring.read","recurring.update","roles.manage","roles.read"]'::jsonb)
      RETURNING id INTO owner_role_id;
    INSERT INTO public.roles(firm_id, name, is_system, description, permissions) VALUES
      (new_firm_id, 'Partner',   false, 'Default Partner role',   '[]'::jsonb),
      (new_firm_id, 'Associate', false, 'Default Associate role', '[]'::jsonb),
      (new_firm_id, 'Staff',     false, 'Default Staff role',     '[]'::jsonb);

    UPDATE public.users          SET firm_id = new_firm_id, role_id = owner_role_id WHERE id = u.id;
    UPDATE public.firm_details   SET firm_id = new_firm_id WHERE user_id = u.id;
    UPDATE public.clients             SET firm_id = new_firm_id WHERE created_by_user_id = u.id;
    UPDATE public.items               SET firm_id = new_firm_id WHERE created_by_user_id = u.id;
    UPDATE public.invoices            SET firm_id = new_firm_id WHERE created_by_user_id = u.id;
    UPDATE public.recurring_schedules SET firm_id = new_firm_id WHERE created_by_user_id = u.id;
    UPDATE public.bank_accounts  SET firm_id = new_firm_id, created_by_user_id = u.id WHERE user_id = u.id;
  END LOOP;
END $$;

-- 5. Invoice numbering is now per-firm: swap the old per-user unique constraint.
ALTER TABLE public.invoices DROP CONSTRAINT IF EXISTS invoices_user_id_invoice_number_key;
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'invoices_firm_id_invoice_number_key') THEN
    ALTER TABLE public.invoices ADD CONSTRAINT invoices_firm_id_invoice_number_key UNIQUE (firm_id, invoice_number);
  END IF;
END $$;

COMMIT;

-- After applying: non-Owner default roles (Partner/Associate/Staff) ship with
-- empty permissions; set them via the in-app Roles editor (the module x CRUD grid).
