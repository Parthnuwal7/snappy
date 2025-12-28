"""
List all valid licenses in Supabase
"""
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_KEY')

if not SUPABASE_URL or SUPABASE_SERVICE_KEY == 'your-service-role-key':
    print("❌ Missing or invalid SUPABASE_SERVICE_KEY in .env")
    sys.exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

def list_licenses():
    """List all licenses"""
    try:
        result = supabase.table('licenses').select('*').order('created_at', desc=True).execute()
        
        if not result.data:
            print("📭 No licenses found in Supabase")
            return
        
        print("=" * 80)
        print("📋 ALL LICENSES IN SUPABASE")
        print("=" * 80)
        
        for license in result.data:
            key = license.get('license_key', 'N/A')
            status = license.get('status', 'N/A')
            verified = '✅' if license.get('admin_verified') else '❌'
            expires = license.get('expires_at', 'Never')
            
            # Check if expired
            if expires and expires != 'Never':
                try:
                    exp_date = datetime.fromisoformat(expires.replace('Z', '+00:00'))
                    now = datetime.now(timezone.utc)
                    if exp_date < now:
                        status_emoji = '⏰ EXPIRED'
                    else:
                        time_left = exp_date - now
                        mins = int(time_left.total_seconds() / 60)
                        status_emoji = f'⏳ {mins}m left'
                except:
                    status_emoji = '❓'
            else:
                status_emoji = '♾️ No expiry'
            
            print(f"\n🔑 {key}")
            print(f"   Status: {status} {verified}")
            print(f"   Expires: {expires} {status_emoji}")
            print(f"   Plan: {license.get('plan', 'N/A')}")
            print(f"   User ID: {license.get('user_id', 'N/A')}")
        
        print("=" * 80)
        
        # Show usable licenses
        usable = [l for l in result.data if l.get('status') == 'verified' and l.get('admin_verified')]
        if usable:
            print(f"\n✅ {len(usable)} license(s) ready to use:")
            for l in usable:
                print(f"   {l['license_key']}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    list_licenses()
