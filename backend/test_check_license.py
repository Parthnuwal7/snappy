"""
Test Script: Check license expiry status (simulates offline check)
"""
import os
import sys
from datetime import datetime, timezone

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.models.models import db
from backend.app.models.auth import User
from flask import Flask

def check_user_license(email):
    """Check if user's cached license is expired (offline check)"""
    
    # Initialize Flask app for database access
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///snappy.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    db.init_app(app)
    
    with app.app_context():
        user = User.query.filter_by(email=email).first()
        
        if not user:
            print(f"❌ User not found: {email}")
            return
        
        print("=" * 60)
        print("👤 USER LICENSE STATUS")
        print("=" * 60)
        print(f"Email:          {user.email}")
        print(f"License Key:    {user.license_key}")
        
        if not user.license_expires_at:
            print(f"Expires At:     No expiry set")
            print(f"Status:         ✅ VALID (no expiry)")
        else:
            now = datetime.now(timezone.utc)
            expires_at = user.license_expires_at
            
            # Make timezone-aware if needed
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            
            print(f"Expires At:     {expires_at.strftime('%Y-%m-%d %H:%M:%S')} UTC")
            print(f"Current Time:   {now.strftime('%Y-%m-%d %H:%M:%S')} UTC")
            
            if expires_at > now:
                time_left = expires_at - now
                seconds_left = int(time_left.total_seconds())
                print(f"Status:         ✅ VALID ({seconds_left} seconds remaining)")
            else:
                time_passed = now - expires_at
                seconds_passed = int(time_passed.total_seconds())
                print(f"Status:         ❌ EXPIRED ({seconds_passed} seconds ago)")
        
        print("=" * 60)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_check_license.py <email>")
        print("Example: python test_check_license.py test@example.com")
        sys.exit(1)
    
    email = sys.argv[1]
    check_user_license(email)
