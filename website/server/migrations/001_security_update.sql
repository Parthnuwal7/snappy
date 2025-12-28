-- ========================================
-- SECURITY UPDATE: Add machine_id column and audit logging
-- ========================================

-- 1. Add machine_id column to licenses table
ALTER TABLE licenses 
ADD COLUMN IF NOT EXISTS machine_id TEXT,
ADD COLUMN IF NOT EXISTS registered_email TEXT,
ADD COLUMN IF NOT EXISTS registered_at TIMESTAMPTZ;

-- 2. Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_licenses_machine_id ON licenses(machine_id);
CREATE INDEX IF NOT EXISTS idx_licenses_status ON licenses(status);

-- 3. Add constraint to prevent duplicate machine registrations (optional - for strict mode)
-- ALTER TABLE licenses ADD CONSTRAINT unique_machine_per_license UNIQUE (license_key, machine_id);

-- 4. Create audit log table for security tracking
CREATE TABLE IF NOT EXISTS license_audit_log (
  id BIGSERIAL PRIMARY KEY,
  license_key TEXT NOT NULL,
  action TEXT NOT NULL,  -- 'validate', 'register_attempt', 'register_success', 'register_fail', 'void'
  status_before TEXT,
  status_after TEXT,
  ip_address TEXT,
  user_agent TEXT,
  machine_id TEXT,
  email TEXT,
  success BOOLEAN NOT NULL,
  error_message TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. Create index for audit log
CREATE INDEX IF NOT EXISTS idx_audit_license_key ON license_audit_log(license_key);
CREATE INDEX IF NOT EXISTS idx_audit_created_at ON license_audit_log(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_action ON license_audit_log(action);

-- 6. Update RLS policies for licenses (stricter security)
-- Drop existing policies
DROP POLICY IF EXISTS "Allow backend full access to licenses" ON licenses;
DROP POLICY IF EXISTS "block_anon" ON licenses;

-- Create new strict policies
-- Backend service role: full access
CREATE POLICY "service_role_full_access" ON licenses
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- Anon role: NO access (backend only)
CREATE POLICY "anon_no_access" ON licenses
FOR ALL
TO anon
USING (false)
WITH CHECK (false);

-- 7. RLS for audit log
ALTER TABLE license_audit_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY "service_role_audit_access" ON license_audit_log
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

CREATE POLICY "anon_no_audit_access" ON license_audit_log
FOR ALL
TO anon
USING (false)
WITH CHECK (false);

-- 8. Create PostgreSQL function for atomic license consumption (prevents race conditions)
CREATE OR REPLACE FUNCTION consume_license(
  p_license_key TEXT,
  p_machine_id TEXT,
  p_email TEXT
)
RETURNS JSON AS $$
DECLARE
  v_license licenses%ROWTYPE;
  v_result JSON;
BEGIN
  -- Lock the row for update (prevents race conditions)
  SELECT * INTO v_license 
  FROM licenses 
  WHERE license_key = p_license_key 
  FOR UPDATE;
  
  -- Check if license exists
  IF NOT FOUND THEN
    RETURN json_build_object(
      'success', false, 
      'error', 'Invalid license key'
    );
  END IF;
  
  -- Check if admin verified
  IF NOT v_license.admin_verified THEN
    RETURN json_build_object(
      'success', false, 
      'error', 'License not verified by admin yet'
    );
  END IF;
  
  -- Check status
  IF v_license.status = 'pending_verification' THEN
    RETURN json_build_object(
      'success', false, 
      'error', 'License pending verification'
    );
  END IF;
  
  IF v_license.status = 'rejected' THEN
    RETURN json_build_object(
      'success', false, 
      'error', 'License has been rejected'
    );
  END IF;
  
  IF v_license.status = 'void' THEN
    RETURN json_build_object(
      'success', false, 
      'error', 'License has been voided'
    );
  END IF;
  
  IF v_license.status = 'expired' THEN
    RETURN json_build_object(
      'success', false, 
      'error', 'License has expired'
    );
  END IF;
  
  IF v_license.status = 'active' THEN
    RETURN json_build_object(
      'success', false, 
      'error', 'License key already in use'
    );
  END IF;
  
  -- Only allow 'verified' status
  IF v_license.status != 'verified' THEN
    RETURN json_build_object(
      'success', false, 
      'error', 'License is not available for use'
    );
  END IF;
  
  -- Check expiration
  IF v_license.expires_at IS NOT NULL AND v_license.expires_at < NOW() THEN
    -- Auto-expire
    UPDATE licenses 
    SET status = 'expired'
    WHERE id = v_license.id;
    
    RETURN json_build_object(
      'success', false, 
      'error', 'License has expired'
    );
  END IF;
  
  -- All checks passed - consume the license atomically
  UPDATE licenses 
  SET 
    status = 'active',
    machine_id = p_machine_id,
    registered_email = p_email,
    registered_at = NOW(),
    admin_notes = COALESCE(admin_notes, '') || E'\nDesktop Registration: ' || p_machine_id || ' at ' || NOW()::TEXT
  WHERE id = v_license.id
  RETURNING * INTO v_license;
  
  RETURN json_build_object(
    'success', true,
    'license', row_to_json(v_license)
  );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Grant execute permission to service role
GRANT EXECUTE ON FUNCTION consume_license(TEXT, TEXT, TEXT) TO service_role;

-- 9. Add comment for documentation
COMMENT ON FUNCTION consume_license IS 'Atomically consume a license for desktop registration. Prevents race conditions with row-level locking.';
COMMENT ON TABLE license_audit_log IS 'Audit trail for all license operations for security monitoring.';
COMMENT ON COLUMN licenses.machine_id IS 'Unique hardware identifier of the device where license is registered.';
COMMENT ON COLUMN licenses.registered_email IS 'Email used during desktop registration (for tracking).';
COMMENT ON COLUMN licenses.registered_at IS 'Timestamp when desktop registration completed.';

-- 10. Create view for admin dashboard (easier querying)
CREATE OR REPLACE VIEW license_overview AS
SELECT 
  l.id,
  l.license_key,
  l.plan,
  l.status,
  l.admin_verified,
  l.email_sent,
  l.machine_id,
  l.registered_email,
  l.registered_at,
  l.created_at,
  l.expires_at,
  l.amount,
  u.name as user_name,
  u.email as payment_email,
  u.phone as user_phone,
  CASE 
    WHEN l.expires_at IS NOT NULL AND l.expires_at < NOW() THEN true
    ELSE false
  END as is_expired,
  CASE
    WHEN l.status = 'used' THEN 'Active User'
    WHEN l.status = 'verified' THEN 'Ready to Use'
    WHEN l.status = 'pending_verification' THEN 'Awaiting Admin'
    WHEN l.status = 'rejected' THEN 'Rejected'
    WHEN l.status = 'void' THEN 'Voided'
    ELSE 'Unknown'
  END as status_label
FROM licenses l
JOIN users u ON l.user_id = u.id
ORDER BY l.created_at DESC;

GRANT SELECT ON license_overview TO service_role;

-- Success message
DO $$
BEGIN
  RAISE NOTICE 'Security migration completed successfully!';
  RAISE NOTICE 'Added columns: machine_id, registered_email, registered_at';
  RAISE NOTICE 'Created table: license_audit_log';
  RAISE NOTICE 'Created function: consume_license()';
  RAISE NOTICE 'Created view: license_overview';
END $$;
