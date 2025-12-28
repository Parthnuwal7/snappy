"""
Test Script: Generate a license key that expires in 2 minutes
For testing offline expiry detection
"""
import os
import sys
from datetime import datetime, timedelta, timezone
import secrets

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_KEY')

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    print("❌ Missing SUPABASE_URL or SUPABASE_SERVICE_KEY in .env")
    sys.exit(1)

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

def generate_license_key():
    """Generate a unique license key"""
    return f"TEST-{secrets.token_hex(8).upper()}"

def create_short_lived_license(duration_minutes=4):
    """Create a license that expires in specified minutes"""
    
    # Generate key
    license_key = generate_license_key()
    
    # Set expiry (4 minutes from now)
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=duration_minutes)
    
    # First, check if test user exists or create one
    test_email = 'test@example.com'
    
    try:
        # Try to find existing test user
        user_result = supabase.table('users').select('id').eq('email', test_email).execute()
        
        if user_result.data and len(user_result.data) > 0:
            user_id = user_result.data[0]['id']
            print(f"📧 Using existing test user: {test_email} (ID: {user_id})")
        else:
            # Create test user if doesn't exist
            print(f"📧 Creating test user: {test_email}")
            
            # Hash password '123456' using bcrypt
            import bcrypt
            hashed = bcrypt.hashpw('123456'.encode('utf-8'), bcrypt.gensalt())
            
            new_user = supabase.table('users').insert({
                'email': test_email,
                'name': 'Test User',
                'password': hashed.decode('utf-8'),  # Proper bcrypt hash for '123456'
                'phone': '1234567890',
                'profession': 'tester',
                'gender': 'other',
                'dob': '1990-01-01',
                'city': 'Test City'
            }).execute()
            user_id = new_user.data[0]['id']
            print(f"✅ Created test user (ID: {user_id})")
            print(f"📧 Email: {test_email}")
            print(f"🔑 Password: 123456")
    
    except Exception as e:
        print(f"❌ Error with test user: {e}")
        print("💡 You may need to create a user via the website first")
        sys.exit(1)
    
    # Create license in Supabase with VERIFIED status (ready to use)
    data = {
        'user_id': user_id,
        'license_key': license_key,
        'plan': 'test',
        'status': 'verified',  # IMPORTANT: Must be 'verified' for desktop registration
        'admin_verified': True,  # IMPORTANT: Must be admin verified
        'email_sent': True,  # Mark as email sent
        'invoked_at': now.isoformat(),  # Mark as invoked (admin verified)
        'expires_at': expires_at.isoformat(),
        'payment_method': 'manual-test',
        'amount': 0
    }
    
    try:
        result = supabase.table('licenses').insert(data).execute()
        
        print("=" * 60)
        print("✅ TEST LICENSE CREATED & VERIFIED")
        print("=" * 60)
        print(f"License Key:    {license_key}")
        print(f"Status:         verified ✅ (ready for desktop registration)")
        print(f"Admin Verified: True ✅")
        print(f"Email Sent:     True ✅")
        print(f"Invoked At:     {now.strftime('%Y-%m-%d %H:%M:%S')} UTC")
        print(f"Created At:     {now.strftime('%Y-%m-%d %H:%M:%S')} UTC")
        print(f"Expires At:     {expires_at.strftime('%Y-%m-%d %H:%M:%S')} UTC")
        print(f"Duration:       {duration_minutes} minutes ⏰")
        print("=" * 60)
        print("\n📋 TESTING STEPS:")
        print("1. Register user with this key (will work ✅)")
        print("2. Login immediately (will work ✅)")
        print("3. Wait 4+ minutes ⏰")
        print("4. Try to login again (should show 'License expired' ❌)")
        print("5. Call /api/v1/auth/check-license (should return 403 ❌)")
        print("\n💡 TIP: Login checks cached expiry in SQLite (works offline!)")
        print("=" * 60)
        
        return license_key, expires_at
        
    except Exception as e:
        print(f"❌ Error creating license: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Create a license that expires in 4 minutes
    key, expiry = create_short_lived_license(duration_minutes=4)
    
    print(f"\n🔑 Use this key to register: {key}")
    print(f"⏰ Expires at: {expiry.strftime('%H:%M:%S')} UTC")
    print(f"\n✅ This license is FULLY VERIFIED and ready for desktop app registration!")
