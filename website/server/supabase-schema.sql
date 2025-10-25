-- Create users table
CREATE TABLE users (
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

-- Create licenses table
CREATE TABLE licenses (
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
  verified_at TIMESTAMPTZ
);

-- Create payment_logs table
CREATE TABLE payment_logs (
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

-- Create indexes for better performance
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_licenses_user ON licenses(user_id);
CREATE INDEX idx_licenses_key ON licenses(license_key);
CREATE INDEX idx_licenses_upi_txn ON licenses(upi_transaction_id);
CREATE INDEX idx_payment_order ON payment_logs(razorpay_order_id);

-- Enable Row Level Security (RLS)
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE licenses ENABLE ROW LEVEL SECURITY;
ALTER TABLE payment_logs ENABLE ROW LEVEL SECURITY;

-- RLS Policies for users table
CREATE POLICY "Allow backend full access to users" ON users
  FOR ALL
  USING (true)
  WITH CHECK (true);

-- RLS Policies for licenses table
CREATE POLICY "Allow backend full access to licenses" ON licenses
  FOR ALL
  USING (true)
  WITH CHECK (true);

-- RLS Policies for payment_logs table
CREATE POLICY "Allow backend full access to payment_logs" ON payment_logs
  FOR ALL
  USING (true)
  WITH CHECK (true);
