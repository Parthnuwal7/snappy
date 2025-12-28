"""
Database Migration: Add License Tracking Columns to Users Table
Run this once to add license_key and license_expires_at columns
"""
import sqlite3
import os
import sys

# Try to find database in multiple locations
POSSIBLE_PATHS = [
    os.path.join(os.path.dirname(__file__), '..', 'instance', 'snappy.db'),  # backend/instance/snappy.db
    os.path.join(os.path.dirname(__file__), '..', '..', 'instance', 'snappy.db'),  # root/instance/snappy.db
    os.path.join(os.path.dirname(__file__), '..', 'snappy.db'),  # backend/snappy.db
    os.path.join(os.path.dirname(__file__), '..', '..', 'snappy.db'),  # root/snappy.db
    'instance/snappy.db',  # Current directory/instance
    'snappy.db',  # Current directory
]

def find_database():
    """Find the SQLite database file"""
    for path in POSSIBLE_PATHS:
        abs_path = os.path.abspath(path)
        if os.path.exists(abs_path):
            return abs_path
    return None

def migrate():
    """Add license tracking columns to users table"""
    
    DB_PATH = find_database()
    
    if not DB_PATH:
        print(f"❌ Database not found in any of these locations:")
        for path in POSSIBLE_PATHS:
            print(f"   - {os.path.abspath(path)}")
        print("\n💡 Please run the Flask app first to create the database:")
        print("   python -m backend.app.main")
        return
    
    print(f"📂 Found database at: {DB_PATH}")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        
        print(f"📋 Current columns in 'users' table: {columns}")
        
        # Add license_key column if it doesn't exist
        if 'license_key' not in columns:
            print("➕ Adding 'license_key' column...")
            cursor.execute("ALTER TABLE users ADD COLUMN license_key TEXT")
            print("✅ Added 'license_key' column")
        else:
            print("⏭️  'license_key' column already exists")
        
        # Add license_expires_at column if it doesn't exist
        if 'license_expires_at' not in columns:
            print("➕ Adding 'license_expires_at' column...")
            cursor.execute("ALTER TABLE users ADD COLUMN license_expires_at DATETIME")
            print("✅ Added 'license_expires_at' column")
        else:
            print("⏭️  'license_expires_at' column already exists")
        
        conn.commit()
        
        # Verify the changes
        cursor.execute("PRAGMA table_info(users)")
        new_columns = [column[1] for column in cursor.fetchall()]
        print(f"\n✅ Migration complete! New columns: {new_columns}")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    print("=" * 60)
    print("🔧 DATABASE MIGRATION: Add License Tracking Columns")
    print("=" * 60)
    migrate()
    print("=" * 60)
