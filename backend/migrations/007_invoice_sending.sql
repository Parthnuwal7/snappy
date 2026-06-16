-- 007_invoice_sending.sql
-- Adds invoice delivery tracking and per-firm message templates for the
-- WhatsApp/email sending feature. Run in the Supabase SQL editor.
-- (db.create_all() handles fresh deploys but does NOT alter existing tables.)

ALTER TABLE public.invoices
  ADD COLUMN IF NOT EXISTS sent_at TIMESTAMP,
  ADD COLUMN IF NOT EXISTS sent_channel VARCHAR(20);

ALTER TABLE public.firm_details
  ADD COLUMN IF NOT EXISTS email_subject_template TEXT,
  ADD COLUMN IF NOT EXISTS email_body_template TEXT,
  ADD COLUMN IF NOT EXISTS whatsapp_template TEXT;
