-- 004_drop_invoice_signature_path.sql
--
-- Drop invoices.signature_path. The signature image is sourced from the
-- firm's profile (firm_details.signature_path) across every active PDF
-- template; the per-invoice override column was accepted on the API
-- (POST/PUT /invoices) but never rendered anywhere, and the frontend never
-- set it. Removing the column eliminates a misleading data field and
-- simplifies the Invoice model.
--
-- The matching SQLAlchemy column has been removed from app/models/models.py
-- and the API create/update paths no longer accept `signature_path` from
-- request bodies. The Simple template (pdf_service.generate_pdf) now reads
-- firm.signature_path, matching the LAW_001 and HALF_PAGE templates.

ALTER TABLE invoices DROP COLUMN IF EXISTS signature_path;
