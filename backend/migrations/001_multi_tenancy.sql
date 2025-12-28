-- =============================================
-- SNAPPY DATABASE MIGRATION SCRIPT
-- Run this in Supabase SQL Editor
-- =============================================

-- 1. FIRM DETAILS TABLE
CREATE TABLE public.firm_details (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  firm_name VARCHAR(200) NOT NULL,
  firm_address TEXT NOT NULL,
  firm_email VARCHAR(120),
  firm_phone VARCHAR(50),
  firm_phone_2 VARCHAR(50),
  firm_website VARCHAR(200),
  logo_path TEXT,
  signature_path TEXT,
  terms_and_conditions TEXT,
  billing_terms TEXT,
  default_template VARCHAR(50) DEFAULT 'Simple',
  invoice_prefix VARCHAR(20) DEFAULT 'INV',
  default_tax_rate NUMERIC(5,2) DEFAULT 18.0,
  currency VARCHAR(10) DEFAULT 'INR',
  show_due_date BOOLEAN DEFAULT true,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(user_id)
);

-- 2. BANK ACCOUNTS TABLE
CREATE TABLE public.bank_accounts (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  bank_name VARCHAR(200),
  account_number VARCHAR(100),
  account_holder_name VARCHAR(200),
  ifsc_code VARCHAR(50),
  upi_id VARCHAR(100),
  upi_qr_path TEXT,
  is_default BOOLEAN DEFAULT true,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- 3. CLIENTS TABLE (with user_id for multi-tenancy)
CREATE TABLE public.clients (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  name VARCHAR(200) NOT NULL,
  email VARCHAR(200),
  phone VARCHAR(50),
  address TEXT,
  tax_id VARCHAR(100),
  default_tax_rate NUMERIC(5,2) DEFAULT 18.0,
  notes TEXT,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- 4. ITEMS TABLE (with user_id for multi-tenancy)
CREATE TABLE public.items (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  name VARCHAR(200) NOT NULL,
  alias VARCHAR(100),
  description TEXT,
  default_rate NUMERIC(12,2) DEFAULT 0.0,
  unit VARCHAR(50),
  hsn_code VARCHAR(50),
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- 5. INVOICES TABLE (with user_id for multi-tenancy)
CREATE TABLE public.invoices (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  client_id INTEGER NOT NULL REFERENCES public.clients(id) ON DELETE RESTRICT,
  invoice_number VARCHAR(50) NOT NULL,
  invoice_date DATE NOT NULL,
  due_date DATE,
  short_desc TEXT,
  subtotal NUMERIC(12,2) DEFAULT 0,
  tax_rate NUMERIC(5,2) DEFAULT 18.0,
  tax_amount NUMERIC(12,2) DEFAULT 0,
  total NUMERIC(12,2) DEFAULT 0,
  status VARCHAR(20) DEFAULT 'draft',
  paid_date DATE,
  notes TEXT,
  signature_path TEXT,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- 6. INVOICE ITEMS TABLE
CREATE TABLE public.invoice_items (
  id SERIAL PRIMARY KEY,
  invoice_id INTEGER NOT NULL REFERENCES public.invoices(id) ON DELETE CASCADE,
  description TEXT NOT NULL,
  quantity NUMERIC(10,2) DEFAULT 1,
  rate NUMERIC(12,2) DEFAULT 0,
  amount NUMERIC(12,2) DEFAULT 0
);

-- 7. SETTINGS TABLE (with user_id for multi-tenancy)
CREATE TABLE public.settings (
  id SERIAL PRIMARY KEY,
  user_id INTEGER REFERENCES public.users(id) ON DELETE CASCADE,
  key VARCHAR(100) NOT NULL,
  value TEXT,
  updated_at TIMESTAMP DEFAULT NOW(),
  UNIQUE(user_id, key)
);

-- Create indexes for performance
CREATE INDEX idx_firm_details_user_id ON public.firm_details(user_id);
CREATE INDEX idx_bank_accounts_user_id ON public.bank_accounts(user_id);
CREATE INDEX idx_clients_user_id ON public.clients(user_id);
CREATE INDEX idx_items_user_id ON public.items(user_id);
CREATE INDEX idx_invoices_user_id ON public.invoices(user_id);
CREATE INDEX idx_invoices_client_id ON public.invoices(client_id);
CREATE INDEX idx_invoice_items_invoice_id ON public.invoice_items(invoice_id);
CREATE INDEX idx_settings_user_id ON public.settings(user_id);
