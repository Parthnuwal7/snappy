import crypto from 'crypto';

// Generate license key in format: SNAPPY-1782085A3359751C
// Matches the desktop app format: SNAPPY- followed by 16 hex characters
export function generateLicenseKey() {
  // Generate 8 random bytes and convert to 16 hex characters (uppercase)
  const hexKey = crypto.randomBytes(8).toString('hex').toUpperCase();
  return `SNAPPY-${hexKey}`;
}

// Calculate expiry date based on plan (1 year from activation)
export function calculateExpiryDate(activationDate = new Date()) {
  const expiry = new Date(activationDate);
  expiry.setFullYear(expiry.getFullYear() + 1);
  return expiry;
}

// Calculate days remaining
export function calculateDaysRemaining(expiryDate) {
  const now = new Date();
  const expiry = new Date(expiryDate);
  const diffTime = expiry - now;
  const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
  return Math.max(0, diffDays);
}
