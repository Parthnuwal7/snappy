-- Migration: Fix Foreign Key Constraint for License Deletion
-- This allows admins to delete licenses along with their payment logs

-- Step 1: Drop the existing foreign key constraint
ALTER TABLE payment_logs 
DROP CONSTRAINT IF EXISTS payment_logs_license_id_fkey;

-- Step 2: Re-add the constraint with CASCADE delete
ALTER TABLE payment_logs 
ADD CONSTRAINT payment_logs_license_id_fkey 
FOREIGN KEY (license_id) 
REFERENCES licenses(id) 
ON DELETE CASCADE;

-- Verify the change
SELECT 
    conname AS constraint_name,
    confdeltype AS delete_action
FROM pg_constraint
WHERE conname = 'payment_logs_license_id_fkey';

-- Result should show: confdeltype = 'c' (which means CASCADE)
