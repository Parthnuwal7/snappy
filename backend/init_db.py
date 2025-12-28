"""
Initialize Database with Updated Schema
This creates/updates the database with all current model definitions
"""
import os
import sys

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.main import create_app
from backend.app.models.models import db
from backend.app.models.auth import User, Firm
from backend.app.models.models import Client, Invoice, InvoiceItem

def init_db():
    """Initialize or update database schema"""
    app = create_app()
    
    with app.app_context():
        print("=" * 60)
        print("🔧 INITIALIZING DATABASE")
        print("=" * 60)
        
        # Create all tables (will add missing columns)
        print("📋 Creating/updating tables...")
        db.create_all()
        
        print("✅ Database initialized successfully!")
        print("=" * 60)
        
        # Show what was created
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        
        for table_name in inspector.get_table_names():
            columns = [col['name'] for col in inspector.get_columns(table_name)]
            print(f"\n📊 Table: {table_name}")
            print(f"   Columns: {', '.join(columns)}")
        
        print("=" * 60)

if __name__ == "__main__":
    init_db()
