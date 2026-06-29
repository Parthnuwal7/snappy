-- backend/migrations/024_upi_qr.sql
-- Dynamic UPI QR: payee name + default note on bank_accounts; retire upi_qr_path.
-- The UPI QR is now generated per-invoice from the bank's UPI deep link, so the
-- uploaded-image column is no longer needed. Idempotent. Apply manually on Supabase.

ALTER TABLE bank_accounts ADD COLUMN IF NOT EXISTS upi_payee_name VARCHAR(200);
ALTER TABLE bank_accounts ADD COLUMN IF NOT EXISTS upi_note       VARCHAR(120);
ALTER TABLE bank_accounts DROP COLUMN IF EXISTS upi_qr_path;
