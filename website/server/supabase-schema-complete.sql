-- ============================================
-- SNAPPY COMPLETE SUPABASE SCHEMA
-- Includes Website + Desktop App Tables
-- ============================================

-- ==================== WEBSITE TABLES ====================

-- Users table (for website authentication)
CREATE TABLE IF NOT EXISTS users (
  id BIGSERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  email TEXT UNIQUE NOT NULL,
  phone TEXT NOT NULL,
  password TEXT NOT NULL,
  profession TEXT NOT NULL,
  gender TEXT NOT NULL,
  dob TEXT NOT NULL,
  city TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  last_login TIMESTAMPTZ
);

-- Licenses table (shared between website and desktop app)
CREATE TABLE IF NOT EXISTS licenses (
  id BIGSERIAL PRIMARY KEY,
  user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  license_key TEXT UNIQUE NOT NULL,
  plan TEXT NOT NULL,
  payment_method TEXT DEFAULT 'upi',
  upi_transaction_id TEXT UNIQUE,
  upi_screenshot_path TEXT,
  razorpay_order_id TEXT,
  razorpay_payment_id TEXT,
  amount INTEGER NOT NULL,
  status TEXT DEFAULT 'pending_payment',
  admin_verified BOOLEAN DEFAULT FALSE,
  email_sent BOOLEAN DEFAULT FALSE,
  admin_notes TEXT,
  invoked_at TIMESTAMPTZ,
  expires_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  verified_at TIMESTAMPTZ,
  -- Desktop app will update these fields when license is activated
  machine_id TEXT,
  last_activated_at TIMESTAMPTZ
);

-- Payment logs table
CREATE TABLE IF NOT EXISTS payment_logs (
  id BIGSERIAL PRIMARY KEY,
  user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  license_id BIGINT REFERENCES licenses(id) ON DELETE CASCADE,
  payment_method TEXT DEFAULT 'upi',
  upi_transaction_id TEXT,
  razorpay_order_id TEXT,
  razorpay_payment_id TEXT,
  razorpay_signature TEXT,
  amount INTEGER NOT NULL,
  currency TEXT DEFAULT 'INR',
  status TEXT NOT NULL,
  admin_verified BOOLEAN DEFAULT FALSE,
  metadata TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ==================== DESKTOP APP TABLES ====================

-- Clients table (for desktop app customers)
CREATE TABLE IF NOT EXISTS clients (
  id BIGSERIAL PRIMARY KEY,
  license_id BIGINT NOT NULL REFERENCES licenses(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  email TEXT,
  phone TEXT,
  address TEXT,
  tax_id TEXT,
  default_tax_rate NUMERIC(5,2) DEFAULT 18.0,
  notes TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Invoices table (for desktop app billing)
CREATE TABLE IF NOT EXISTS invoices (
  id BIGSERIAL PRIMARY KEY,
  license_id BIGINT NOT NULL REFERENCES licenses(id) ON DELETE CASCADE,
  client_id BIGINT NOT NULL REFERENCES clients(id) ON DELETE RESTRICT,
  invoice_number TEXT NOT NULL,
  invoice_date DATE NOT NULL DEFAULT CURRENT_DATE,
  due_date DATE,
  short_desc TEXT,
  
  -- Amounts
  subtotal NUMERIC(12,2) DEFAULT 0.0,
  tax_rate NUMERIC(5,2) DEFAULT 18.0,
  tax_amount NUMERIC(12,2) DEFAULT 0.0,
  total NUMERIC(12,2) DEFAULT 0.0,
  
  -- Status
  status TEXT DEFAULT 'draft', -- draft, sent, paid, void
  paid_date DATE,
  
  -- Metadata
  notes TEXT,
  signature_path TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  
  -- Unique invoice number per license
  UNIQUE(license_id, invoice_number)
);

-- Invoice items table (line items)
CREATE TABLE IF NOT EXISTS invoice_items (
  id BIGSERIAL PRIMARY KEY,
  invoice_id BIGINT NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
  description TEXT NOT NULL,
  quantity NUMERIC(10,2) DEFAULT 1.0,
  rate NUMERIC(12,2) NOT NULL,
  amount NUMERIC(12,2) NOT NULL,
  sort_order INTEGER DEFAULT 0
);

-- Settings table (per-license settings for desktop app)
CREATE TABLE IF NOT EXISTS app_settings (
  id BIGSERIAL PRIMARY KEY,
  license_id BIGINT NOT NULL REFERENCES licenses(id) ON DELETE CASCADE,
  key TEXT NOT NULL,
  value TEXT,
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(license_id, key)
);

-- ==================== INDEXES ====================

-- Website indexes
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_licenses_user ON licenses(user_id);
CREATE INDEX IF NOT EXISTS idx_licenses_key ON licenses(license_key);
CREATE INDEX IF NOT EXISTS idx_licenses_status ON licenses(status);
CREATE INDEX IF NOT EXISTS idx_licenses_upi_txn ON licenses(upi_transaction_id);
CREATE INDEX IF NOT EXISTS idx_payment_order ON payment_logs(razorpay_order_id);
CREATE INDEX IF NOT EXISTS idx_payment_license ON payment_logs(license_id);

-- Desktop app indexes
CREATE INDEX IF NOT EXISTS idx_clients_license ON clients(license_id);
CREATE INDEX IF NOT EXISTS idx_clients_name ON clients(name);
CREATE INDEX IF NOT EXISTS idx_invoices_license ON invoices(license_id);
CREATE INDEX IF NOT EXISTS idx_invoices_client ON invoices(client_id);
CREATE INDEX IF NOT EXISTS idx_invoices_number ON invoices(invoice_number);
CREATE INDEX IF NOT EXISTS idx_invoices_date ON invoices(invoice_date);
CREATE INDEX IF NOT EXISTS idx_invoices_status ON invoices(status);
CREATE INDEX IF NOT EXISTS idx_invoice_items_invoice ON invoice_items(invoice_id);
CREATE INDEX IF NOT EXISTS idx_settings_license ON app_settings(license_id);

-- ==================== TRIGGERS ====================

-- Auto-update updated_at timestamp for clients
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_clients_updated_at BEFORE UPDATE ON clients
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_invoices_updated_at BEFORE UPDATE ON invoices
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_settings_updated_at BEFORE UPDATE ON app_settings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ==================== ROW LEVEL SECURITY ====================

-- Enable RLS on all tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE licenses ENABLE ROW LEVEL SECURITY;
ALTER TABLE payment_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE clients ENABLE ROW LEVEL SECURITY;
ALTER TABLE invoices ENABLE ROW LEVEL SECURITY;
ALTER TABLE invoice_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE app_settings ENABLE ROW LEVEL SECURITY;

-- Permissive policies for backend access
CREATE POLICY "Allow backend full access to users" ON users
  FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "Allow backend full access to licenses" ON licenses
  FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "Allow backend full access to payment_logs" ON payment_logs
  FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "Allow backend full access to clients" ON clients
  FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "Allow backend full access to invoices" ON invoices
  FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "Allow backend full access to invoice_items" ON invoice_items
  FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "Allow backend full access to app_settings" ON app_settings
  FOR ALL USING (true) WITH CHECK (true);

-- ==================== DEFAULT SETTINGS ====================

-- Insert default settings for each license (this will be done by desktop app on first run)
-- Example:
-- INSERT INTO app_settings (license_id, key, value) VALUES
-- (1, 'invoice_prefix', 'LAW'),
-- (1, 'invoice_year_format', 'YYYY'),
-- (1, 'invoice_padding', '4'),
-- (1, 'currency', 'INR'),
-- (1, 'default_tax_rate', '18'),
-- (1, 'auto_backup', 'false');

-- ==================== VIEWS (Optional but useful) ====================

-- View to see license with user details
CREATE OR REPLACE VIEW license_details AS
SELECT 
  l.*,
  u.name as user_name,
  u.email as user_email,
  u.phone as user_phone,
  u.profession as user_profession
FROM licenses l
JOIN users u ON l.user_id = u.id;

-- View to see invoice summary
CREATE OR REPLACE VIEW invoice_summary AS
SELECT 
  i.*,
  c.name as client_name,
  c.email as client_email,
  COUNT(ii.id) as item_count
FROM invoices i
JOIN clients c ON i.client_id = c.id
LEFT JOIN invoice_items ii ON i.id = ii.invoice_id
GROUP BY i.id, c.id;

-- ==================== NOTES ====================

/*
MIGRATION STRATEGY:

1. Run this SQL in Supabase SQL Editor
2. Update desktop app to use Supabase instead of DuckDB
3. For existing desktop app users:
   - On first launch with new version, detect if using old DuckDB
   - Migrate their data to Supabase under their license_id
   - Keep DuckDB backup for safety

KEY CHANGES FOR DESKTOP APP:
- Install supabase-py: pip install supabase
- Replace all database.py calls with Supabase client
- Use license_key to authenticate desktop app
- Store license_id in local config after first activation
- All CRUD operations go to Supabase

SECURITY:
- Desktop app should use Service Role key (stored securely)
- All data is scoped to license_id
- RLS policies can be tightened later to check license_id

BENEFITS:
✅ Single source of truth
✅ Real-time admin panel
✅ Cross-device sync capability
✅ Automatic backups
✅ No local database corruption issues
✅ Can add web portal for users to view their data
*/
