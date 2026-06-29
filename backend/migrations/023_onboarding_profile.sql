-- backend/migrations/023_onboarding_profile.sql
-- Onboarding redesign: personal-profile layer on users + relax firm_address.
-- Idempotent (safe to re-run). Apply manually on Supabase.

ALTER TABLE users ADD COLUMN IF NOT EXISTS full_name           VARCHAR(200);
ALTER TABLE users ADD COLUMN IF NOT EXISTS designation         VARCHAR(120);
ALTER TABLE users ADD COLUMN IF NOT EXISTS bar_council_number  VARCHAR(120);
ALTER TABLE users ADD COLUMN IF NOT EXISTS personal_phone      VARCHAR(50);
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_solo             BOOLEAN;
ALTER TABLE users ADD COLUMN IF NOT EXISTS checklist_dismissed BOOLEAN DEFAULT FALSE;

-- The minimal gate creates a firm profile with no address yet.
ALTER TABLE firm_details ALTER COLUMN firm_address DROP NOT NULL;
