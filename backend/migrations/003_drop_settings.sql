-- 003_drop_settings.sql
--
-- Drop the unused `settings` key-value table. The original intent was a
-- generic per-user key-value store, but every setting the app actually uses
-- ended up on firm_details (invoice_prefix, default_tax_rate, currency,
-- default_template, use_invoice_prefix, show_due_date) or bank_accounts.
-- No API route reads or writes the settings table; in production it has
-- zero rows. Removing it to eliminate a confusing parallel structure.
--
-- The matching SQLAlchemy model (Settings in app/models/models.py) has been
-- removed alongside this migration.

DROP TABLE IF EXISTS settings;
