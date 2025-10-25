-- ====================================
-- SNAPPY - Supabase Database Schema
-- ====================================
-- This schema is for the cloud PostgreSQL database
-- Local desktop app continues to use SQLite
-- ====================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ====================================
-- USERS TABLE
-- ====================================
-- Stores user accounts for web and desktop app
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  email TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  is_active BOOLEAN DEFAULT TRUE,
  is_onboarded BOOLEAN DEFAULT FALSE,
  last_login TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Index for faster email lookups
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_active ON users(is_active);

-- ====================================
-- FIRMS TABLE
-- ====================================
-- Stores firm details (one-to-one with users)
CREATE TABLE firms (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
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
  
  -- File paths (stored in Supabase Storage)
  logo_path TEXT,
  signature_path TEXT,
  upi_qr_path TEXT,
  
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  
  UNIQUE(user_id)
);

-- Index for faster user lookups
CREATE INDEX idx_firms_user_id ON firms(user_id);

-- ====================================
-- SUBSCRIPTION PLANS TABLE
-- ====================================
-- Defines available subscription tiers
CREATE TABLE subscription_plans (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name TEXT NOT NULL UNIQUE, -- 'trial', 'starter', 'pro', 'enterprise'
  display_name TEXT NOT NULL,
  description TEXT,
  price_monthly INTEGER NOT NULL, -- in rupees
  price_yearly INTEGER NOT NULL, -- in rupees
  features JSONB, -- JSON array of features
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Insert default plans
INSERT INTO subscription_plans (name, display_name, description, price_monthly, price_yearly, features) VALUES
('trial', 'Free Trial', '7-day trial with all features', 0, 0, 
  '["Unlimited invoices", "All templates", "Cloud backup", "Advanced analytics", "Email support"]'::jsonb),
('starter', 'Starter', 'Basic billing for individuals', 400, 4000,
  '["Unlimited invoices", "Basic templates", "Local backup only", "Basic analytics", "Email support"]'::jsonb),
('pro', 'Professional', 'Full-featured for professionals', 1000, 10000,
  '["Everything in Starter", "Cloud backup (1GB)", "Advanced analytics", "Premium templates", "Priority support", "3 users"]'::jsonb),
('enterprise', 'Enterprise', 'Complete solution for firms', 1500, 15000,
  '["Everything in Pro", "Unlimited cloud backup", "Custom templates", "Multi-device sync", "Unlimited users", "Dedicated support", "API access"]'::jsonb);

-- ====================================
-- SUBSCRIPTIONS TABLE
-- ====================================
-- Stores user subscription status
CREATE TABLE subscriptions (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  plan_id UUID NOT NULL REFERENCES subscription_plans(id),
  
  status TEXT NOT NULL DEFAULT 'active', -- 'active', 'expired', 'cancelled', 'trial'
  billing_cycle TEXT NOT NULL DEFAULT 'monthly', -- 'monthly', 'yearly'
  
  started_at TIMESTAMP DEFAULT NOW(),
  expires_at TIMESTAMP NOT NULL,
  cancelled_at TIMESTAMP,
  
  -- Payment gateway integration
  razorpay_subscription_id TEXT,
  razorpay_customer_id TEXT,
  
  auto_renew BOOLEAN DEFAULT TRUE,
  
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_subscriptions_user_id ON subscriptions(user_id);
CREATE INDEX idx_subscriptions_status ON subscriptions(status);
CREATE INDEX idx_subscriptions_expires_at ON subscriptions(expires_at);

-- ====================================
-- LICENSE KEYS TABLE
-- ====================================
-- Stores license keys for desktop app activation
-- Keys are generated via separate payment system (website)
-- and sent to users via email
CREATE TABLE license_keys (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  
  key TEXT UNIQUE NOT NULL, -- Format: SNAPPY-XXXX-XXXX-XXXX-XXXX
  
  user_id UUID REFERENCES users(id) ON DELETE SET NULL, -- Linked when activated
  subscription_id UUID REFERENCES subscriptions(id) ON DELETE SET NULL,
  
  -- Desktop app binding
  device_id TEXT, -- Unique device identifier
  device_name TEXT, -- e.g., "Parth's Laptop"
  
  is_active BOOLEAN DEFAULT TRUE,
  is_used BOOLEAN DEFAULT FALSE,
  
  activated_at TIMESTAMP,
  last_validated TIMESTAMP,
  expires_at TIMESTAMP, -- Same as subscription expiry
  
  -- Offline grace period tracking
  last_online_validation TIMESTAMP,
  offline_grace_expires_at TIMESTAMP,
  
  created_at TIMESTAMP DEFAULT NOW(),
  
  -- Purchase information (from payment system)
  purchased_email TEXT, -- Email used during purchase
  purchase_order_id TEXT, -- Razorpay order ID
  purchase_amount INTEGER -- Amount paid in rupees
);

-- Indexes
CREATE INDEX idx_license_keys_key ON license_keys(key);
CREATE INDEX idx_license_keys_user_id ON license_keys(user_id);
CREATE INDEX idx_license_keys_device_id ON license_keys(device_id);
CREATE INDEX idx_license_keys_is_active ON license_keys(is_active);

-- ====================================
-- BACKUP METADATA TABLE
-- ====================================
-- Tracks cloud backups for users
CREATE TABLE backup_metadata (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  
  backup_type TEXT NOT NULL, -- 'daily', 'weekly', 'monthly', 'manual'
  
  -- Supabase Storage path
  file_path TEXT NOT NULL, -- e.g., 'user-backups/{user_id}/backup-2025-10-25.db.enc'
  file_name TEXT NOT NULL,
  file_size_bytes BIGINT,
  
  encrypted BOOLEAN DEFAULT TRUE,
  compressed BOOLEAN DEFAULT TRUE,
  
  -- Metadata
  database_version TEXT,
  app_version TEXT,
  
  -- Checksums for integrity
  checksum_sha256 TEXT,
  
  created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_backup_metadata_user_id ON backup_metadata(user_id);
CREATE INDEX idx_backup_metadata_created_at ON backup_metadata(created_at);
CREATE INDEX idx_backup_metadata_backup_type ON backup_metadata(backup_type);

-- ====================================
-- PAYMENT HISTORY TABLE
-- ====================================
-- Tracks all payment transactions
CREATE TABLE payment_history (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  subscription_id UUID REFERENCES subscriptions(id),
  
  -- Razorpay details
  razorpay_payment_id TEXT UNIQUE,
  razorpay_order_id TEXT,
  razorpay_signature TEXT,
  
  amount INTEGER NOT NULL, -- in rupees (paise * 100)
  currency TEXT DEFAULT 'INR',
  
  status TEXT NOT NULL, -- 'success', 'failed', 'pending', 'refunded'
  
  payment_method TEXT, -- 'card', 'upi', 'netbanking', 'wallet'
  
  -- GST invoice
  invoice_number TEXT,
  invoice_url TEXT, -- PDF stored in Supabase Storage
  
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_payment_history_user_id ON payment_history(user_id);
CREATE INDEX idx_payment_history_razorpay_payment_id ON payment_history(razorpay_payment_id);
CREATE INDEX idx_payment_history_status ON payment_history(status);

-- ====================================
-- AUDIT LOG TABLE
-- ====================================
-- Tracks important user actions for security
CREATE TABLE audit_log (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES users(id) ON DELETE SET NULL,
  
  action TEXT NOT NULL, -- 'login', 'logout', 'password_change', 'subscription_update', etc.
  entity_type TEXT, -- 'user', 'subscription', 'license', 'backup'
  entity_id UUID,
  
  ip_address TEXT,
  user_agent TEXT,
  
  metadata JSONB, -- Additional context
  
  created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_audit_log_user_id ON audit_log(user_id);
CREATE INDEX idx_audit_log_action ON audit_log(action);
CREATE INDEX idx_audit_log_created_at ON audit_log(created_at);

-- ====================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- ====================================
-- Enable RLS on all tables

ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE firms ENABLE ROW LEVEL SECURITY;
ALTER TABLE subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE license_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE backup_metadata ENABLE ROW LEVEL SECURITY;
ALTER TABLE payment_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;

-- Users can only read/update their own data
CREATE POLICY "Users can view own data" ON users
  FOR SELECT USING (auth.uid() = id);

CREATE POLICY "Users can update own data" ON users
  FOR UPDATE USING (auth.uid() = id);

-- Firms policies
CREATE POLICY "Users can view own firm" ON firms
  FOR SELECT USING (user_id = auth.uid());

CREATE POLICY "Users can update own firm" ON firms
  FOR UPDATE USING (user_id = auth.uid());

CREATE POLICY "Users can insert own firm" ON firms
  FOR INSERT WITH CHECK (user_id = auth.uid());

-- Subscriptions policies
CREATE POLICY "Users can view own subscriptions" ON subscriptions
  FOR SELECT USING (user_id = auth.uid());

-- License keys policies
CREATE POLICY "Users can view own license keys" ON license_keys
  FOR SELECT USING (user_id = auth.uid());

-- Backup metadata policies
CREATE POLICY "Users can view own backups" ON backup_metadata
  FOR SELECT USING (user_id = auth.uid());

CREATE POLICY "Users can insert own backups" ON backup_metadata
  FOR INSERT WITH CHECK (user_id = auth.uid());

CREATE POLICY "Users can delete own backups" ON backup_metadata
  FOR DELETE USING (user_id = auth.uid());

-- Payment history policies
CREATE POLICY "Users can view own payments" ON payment_history
  FOR SELECT USING (user_id = auth.uid());

-- Audit log policies (read-only for users)
CREATE POLICY "Users can view own audit log" ON audit_log
  FOR SELECT USING (user_id = auth.uid());

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
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_firms_updated_at BEFORE UPDATE ON firms
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_subscriptions_updated_at BEFORE UPDATE ON subscriptions
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to check subscription expiry
CREATE OR REPLACE FUNCTION check_subscription_expiry()
RETURNS void AS $$
BEGIN
  UPDATE subscriptions
  SET status = 'expired'
  WHERE status = 'active'
    AND expires_at < NOW()
    AND auto_renew = FALSE;
END;
$$ LANGUAGE plpgsql;

-- Function to clean up old backups (keep only per retention policy)
CREATE OR REPLACE FUNCTION cleanup_old_backups()
RETURNS void AS $$
BEGIN
  -- Delete daily backups older than 7 days
  DELETE FROM backup_metadata
  WHERE backup_type = 'daily'
    AND created_at < NOW() - INTERVAL '7 days';
  
  -- Delete weekly backups older than 4 weeks
  DELETE FROM backup_metadata
  WHERE backup_type = 'weekly'
    AND created_at < NOW() - INTERVAL '28 days';
  
  -- Delete monthly backups older than 12 months
  DELETE FROM backup_metadata
  WHERE backup_type = 'monthly'
    AND created_at < NOW() - INTERVAL '365 days';
END;
$$ LANGUAGE plpgsql;

-- ====================================
-- VIEWS FOR CONVENIENCE
-- ====================================

-- View: Active subscriptions with user details
CREATE VIEW active_subscriptions_view AS
SELECT 
  s.id as subscription_id,
  u.id as user_id,
  u.email,
  f.firm_name,
  sp.name as plan_name,
  sp.display_name as plan_display_name,
  s.status,
  s.billing_cycle,
  s.started_at,
  s.expires_at,
  s.auto_renew,
  CASE 
    WHEN s.expires_at > NOW() THEN TRUE
    ELSE FALSE
  END as is_valid
FROM subscriptions s
JOIN users u ON s.user_id = u.id
LEFT JOIN firms f ON u.id = f.user_id
JOIN subscription_plans sp ON s.plan_id = sp.id
WHERE s.status IN ('active', 'trial');

-- View: License usage statistics
CREATE VIEW license_usage_stats AS
SELECT 
  COUNT(*) as total_keys,
  COUNT(*) FILTER (WHERE is_used = TRUE) as used_keys,
  COUNT(*) FILTER (WHERE is_active = TRUE) as active_keys,
  COUNT(*) FILTER (WHERE expires_at > NOW()) as valid_keys,
  COUNT(*) FILTER (WHERE last_online_validation > NOW() - INTERVAL '7 days') as recently_validated
FROM license_keys;

-- ====================================
-- STORAGE BUCKETS (Run in Supabase Dashboard)
-- ====================================
-- Create storage buckets via Supabase Dashboard or SQL:
-- 
-- 1. user-backups (private)
--    - For encrypted database backups
--    - Only accessible by owner
-- 
-- 2. user-uploads (private)
--    - For firm logos, signatures, QR codes
--    - Only accessible by owner
-- 
-- 3. invoice-pdfs (private, optional)
--    - For storing generated invoices (premium feature)
--    - Only accessible by owner

-- ====================================
-- NOTES
-- ====================================
-- 1. After running this schema, update your .env with Supabase credentials
-- 2. Product key generation system will be separate (website payment flow)
-- 3. Desktop app will validate licenses with grace period for offline use
-- 4. Web app will use real-time subscription checks
-- 5. Backup encryption keys are derived from: license_key + user_password
