-- ====================================
-- SNAPPY - Supabase Database Schema (Web-First)
-- ====================================
-- This schema is for the Supabase PostgreSQL database
-- Run in Supabase SQL Editor to set up tables
-- ====================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ====================================
-- USER PROFILES TABLE
-- ====================================
-- Extends Supabase auth.users with additional profile data
CREATE TABLE IF NOT EXISTS user_profiles (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  device_id TEXT,
  device_info JSONB,  -- {browser, os, device_type, last_active}
  is_onboarded BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- ====================================
-- FIRMS TABLE
-- ====================================
-- Stores firm details (one-to-one with user_profiles)
CREATE TABLE IF NOT EXISTS firms (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  firm_name TEXT NOT NULL,
  firm_address TEXT,
  firm_email TEXT,
  firm_phone TEXT,
  firm_phone_2 TEXT,
  firm_website TEXT,
  firm_gstin TEXT,
  
  -- Banking details
  bank_name TEXT,
  account_number TEXT,
  account_holder_name TEXT,
  ifsc_code TEXT,
  upi_id TEXT,
  
  -- Preferences
  default_template TEXT DEFAULT 'LAW_001',
  invoice_prefix TEXT DEFAULT 'LAW',
  default_tax_rate DECIMAL(5,2) DEFAULT 18.00,
  currency TEXT DEFAULT 'INR',
  
  -- Terms & conditions
  billing_terms TEXT,
  terms_and_conditions TEXT,
  
  -- File paths (stored in Supabase Storage buckets)
  logo_path TEXT,
  signature_path TEXT,
  upi_qr_path TEXT,
  
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  
  UNIQUE(user_id)
);

-- ====================================
-- CLIENTS TABLE
-- ====================================
-- Multi-tenant clients (each user has their own clients)
CREATE TABLE IF NOT EXISTS clients (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  email TEXT,
  phone TEXT,
  address TEXT,
  tax_id TEXT,
  default_tax_rate DECIMAL(5,2) DEFAULT 18.00,
  notes TEXT,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_clients_user_id ON clients(user_id);
CREATE INDEX IF NOT EXISTS idx_clients_name ON clients(user_id, name);

-- ====================================
-- ITEMS TABLE
-- ====================================
-- Reusable service/product catalog (multi-tenant)
CREATE TABLE IF NOT EXISTS items (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  alias TEXT,
  description TEXT,
  default_rate DECIMAL(12,2) DEFAULT 0.00,
  unit TEXT DEFAULT 'hour',
  hsn_code TEXT,
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_items_user_id ON items(user_id);
CREATE INDEX IF NOT EXISTS idx_items_name ON items(user_id, name);
CREATE INDEX IF NOT EXISTS idx_items_alias ON items(user_id, alias);

-- ====================================
-- INVOICES TABLE
-- ====================================
-- Invoices with JSON line items for flexibility
CREATE TABLE IF NOT EXISTS invoices (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  client_id UUID NOT NULL REFERENCES clients(id) ON DELETE RESTRICT,
  invoice_number TEXT NOT NULL,
  invoice_date DATE NOT NULL DEFAULT CURRENT_DATE,
  due_date DATE,
  short_desc TEXT,
  
  -- Line items stored as JSON array for flexibility
  -- Structure: [{description, quantity, rate, amount, item_id?}]
  line_items JSONB NOT NULL DEFAULT '[]',
  
  -- Calculated totals (stored for query performance)
  subtotal DECIMAL(12,2) DEFAULT 0.00,
  tax_rate DECIMAL(5,2) DEFAULT 18.00,
  tax_amount DECIMAL(12,2) DEFAULT 0.00,
  total DECIMAL(12,2) DEFAULT 0.00,
  
  -- Status tracking
  status TEXT DEFAULT 'draft' CHECK (status IN ('draft', 'sent', 'paid', 'void')),
  paid_date DATE,
  
  -- Additional info
  notes TEXT,
  signature_path TEXT,
  
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  
  -- Unique invoice number per user
  UNIQUE(user_id, invoice_number)
);

CREATE INDEX IF NOT EXISTS idx_invoices_user_id ON invoices(user_id);
CREATE INDEX IF NOT EXISTS idx_invoices_client_id ON invoices(client_id);
CREATE INDEX IF NOT EXISTS idx_invoices_status ON invoices(user_id, status);
CREATE INDEX IF NOT EXISTS idx_invoices_date ON invoices(user_id, invoice_date);

-- ====================================
-- BACKUP METADATA TABLE
-- ====================================
-- Tracks daily backup files in storage
CREATE TABLE IF NOT EXISTS backup_metadata (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  backup_type TEXT NOT NULL DEFAULT 'daily',
  file_path TEXT NOT NULL,
  file_name TEXT NOT NULL,
  file_size_bytes BIGINT,
  invoice_count INTEGER,
  checksum_sha256 TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_backup_metadata_user_id ON backup_metadata(user_id);
CREATE INDEX IF NOT EXISTS idx_backup_metadata_created_at ON backup_metadata(created_at);

-- ====================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- ====================================
-- Enable RLS on all tables
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE firms ENABLE ROW LEVEL SECURITY;
ALTER TABLE clients ENABLE ROW LEVEL SECURITY;
ALTER TABLE items ENABLE ROW LEVEL SECURITY;
ALTER TABLE invoices ENABLE ROW LEVEL SECURITY;
ALTER TABLE backup_metadata ENABLE ROW LEVEL SECURITY;

-- User profiles: users can only access their own profile
CREATE POLICY "Users can manage own profile" ON user_profiles
  FOR ALL USING (id = auth.uid());

-- Firms: users can only access their own firm
CREATE POLICY "Users can manage own firm" ON firms
  FOR ALL USING (user_id = auth.uid());

-- Clients: users can only access their own clients
CREATE POLICY "Users can manage own clients" ON clients
  FOR ALL USING (user_id = auth.uid());

-- Items: users can only access their own items
CREATE POLICY "Users can manage own items" ON items
  FOR ALL USING (user_id = auth.uid());

-- Invoices: users can only access their own invoices
CREATE POLICY "Users can manage own invoices" ON invoices
  FOR ALL USING (user_id = auth.uid());

-- Backup metadata: users can only access their own backups
CREATE POLICY "Users can manage own backups" ON backup_metadata
  FOR ALL USING (user_id = auth.uid());

-- ====================================
-- FUNCTIONS & TRIGGERS
-- ====================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to tables with updated_at
CREATE TRIGGER update_user_profiles_updated_at 
  BEFORE UPDATE ON user_profiles
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_firms_updated_at 
  BEFORE UPDATE ON firms
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_clients_updated_at 
  BEFORE UPDATE ON clients
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_items_updated_at 
  BEFORE UPDATE ON items
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_invoices_updated_at 
  BEFORE UPDATE ON invoices
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to create user profile on signup
CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO user_profiles (id, is_onboarded, created_at, updated_at)
  VALUES (NEW.id, FALSE, NOW(), NOW());
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Trigger to create profile when user signs up
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION handle_new_user();

-- ====================================
-- STORAGE BUCKETS
-- ====================================
-- Run these in Supabase SQL Editor or create via Dashboard

-- Create 4 private buckets
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES 
  ('firm-logos', 'firm-logos', FALSE, 5242880, ARRAY['image/jpeg', 'image/png']),
  ('signatures', 'signatures', FALSE, 2097152, ARRAY['image/jpeg', 'image/png']),
  ('qr-codes', 'qr-codes', FALSE, 2097152, ARRAY['image/jpeg', 'image/png']),
  ('invoice-backups', 'invoice-backups', FALSE, 52428800, ARRAY['application/json'])
ON CONFLICT (id) DO NOTHING;

-- Storage policies: Users can only access their own files
-- File naming convention: {user_id}_filename.ext

CREATE POLICY "Users manage own logos" ON storage.objects FOR ALL
  USING (bucket_id = 'firm-logos' AND (storage.foldername(name))[1] = auth.uid()::text)
  WITH CHECK (bucket_id = 'firm-logos' AND (storage.foldername(name))[1] = auth.uid()::text);

CREATE POLICY "Users manage own signatures" ON storage.objects FOR ALL
  USING (bucket_id = 'signatures' AND (storage.foldername(name))[1] = auth.uid()::text)
  WITH CHECK (bucket_id = 'signatures' AND (storage.foldername(name))[1] = auth.uid()::text);

CREATE POLICY "Users manage own QR codes" ON storage.objects FOR ALL
  USING (bucket_id = 'qr-codes' AND (storage.foldername(name))[1] = auth.uid()::text)
  WITH CHECK (bucket_id = 'qr-codes' AND (storage.foldername(name))[1] = auth.uid()::text);

CREATE POLICY "Users manage own backups" ON storage.objects FOR ALL
  USING (bucket_id = 'invoice-backups' AND (storage.foldername(name))[1] = auth.uid()::text)
  WITH CHECK (bucket_id = 'invoice-backups' AND (storage.foldername(name))[1] = auth.uid()::text);

-- ====================================
-- HELPFUL VIEWS
-- ====================================

-- View: Invoice summary with client name
CREATE OR REPLACE VIEW invoice_summary AS
SELECT 
  i.id,
  i.user_id,
  i.invoice_number,
  i.invoice_date,
  i.due_date,
  i.short_desc,
  i.subtotal,
  i.tax_rate,
  i.tax_amount,
  i.total,
  i.status,
  i.paid_date,
  c.name as client_name,
  c.email as client_email,
  jsonb_array_length(i.line_items) as item_count,
  i.created_at,
  i.updated_at
FROM invoices i
JOIN clients c ON i.client_id = c.id;

-- ====================================
-- NOTES
-- ====================================
-- 1. After running this schema, configure Supabase Auth settings
-- 2. Set up email templates for password reset in Supabase Dashboard
-- 3. Configure storage bucket policies if needed
-- 4. Frontend uses VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY
-- 5. Backend uses SUPABASE_SERVICE_ROLE_KEY for admin operations
