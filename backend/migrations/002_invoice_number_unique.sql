-- 002_invoice_number_unique.sql
-- Applied: 2026-05-20
--
-- Closes a race in generate_invoice_number(): the function reads the last
-- invoice for a user, derives the next number, and writes -- two concurrent
-- POSTs could derive the same number and both insert. The unique constraint
-- now rejects the duplicate; the API will surface an IntegrityError instead
-- of silently producing two invoices with the same number.
--
-- The SQLAlchemy model in app/models/models.py declares the matching
-- UniqueConstraint via __table_args__, so any future fresh deployment will
-- create this constraint automatically via db.create_all().

ALTER TABLE invoices
  ADD CONSTRAINT invoices_user_id_invoice_number_key
  UNIQUE (user_id, invoice_number);
