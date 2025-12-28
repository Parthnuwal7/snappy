"""DuckDB analytics service - multi-tenant with daily sync"""
import duckdb
from app.models.models import db, Invoice, Client
import os
import time
from datetime import datetime

# Sync tracking - per user
_last_sync = {}  # {user_id: timestamp}
_sync_interval = 86400  # 24 hours in seconds


class DuckDBService:
    """Service for analytics using DuckDB - user-scoped with daily sync"""
    
    def __init__(self, db_path='snappy_analytics.duckdb'):
        self.db_path = db_path
        self.conn = None
    
    def connect(self):
        """Connect to DuckDB"""
        if not self.conn:
            self.conn = duckdb.connect(self.db_path)
        return self.conn
    
    def close(self):
        """Close DuckDB connection"""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def _ensure_table_exists(self, conn):
        """Ensure the invoices table exists"""
        conn.execute("""
            CREATE TABLE IF NOT EXISTS invoices (
                invoice_id INTEGER,
                user_id INTEGER,
                invoice_number VARCHAR,
                client_id INTEGER,
                client_name VARCHAR,
                invoice_date DATE,
                due_date DATE,
                subtotal DOUBLE,
                tax_amount DOUBLE,
                total DOUBLE,
                status VARCHAR,
                paid_date DATE
            )
        """)
    
    def should_sync(self, user_id):
        """Check if we should sync for this user (once per day)"""
        global _last_sync
        last = _last_sync.get(user_id, 0)
        return (time.time() - last) > _sync_interval
    
    def force_sync(self, user_id):
        """Force a sync for a user (e.g., after creating/updating invoices)"""
        global _last_sync
        if user_id in _last_sync:
            del _last_sync[user_id]
    
    def sync_invoices(self, user_id):
        """Sync invoice data from PostgreSQL to DuckDB for a specific user (once per day)"""
        global _last_sync
        
        # Skip if synced within the last day
        if not self.should_sync(user_id):
            return 0
        
        conn = self.connect()
        
        # Drop and recreate table to ensure correct schema
        conn.execute("DROP TABLE IF EXISTS invoices")
        conn.execute("""
            CREATE TABLE invoices (
                invoice_id INTEGER,
                user_id INTEGER,
                invoice_number VARCHAR,
                client_id INTEGER,
                client_name VARCHAR,
                invoice_date DATE,
                due_date DATE,
                subtotal DOUBLE,
                tax_amount DOUBLE,
                total DOUBLE,
                status VARCHAR,
                paid_date DATE
            )
        """)
        
        # Get invoices for this user
        invoices = db.session.query(Invoice).join(Client).filter(Invoice.user_id == user_id).all()
        
        # Insert data
        if invoices:
            for inv in invoices:
                conn.execute("""
                    INSERT INTO invoices VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    inv.id,
                    inv.user_id,
                    inv.invoice_number,
                    inv.client_id,
                    inv.client.name,
                    inv.invoice_date.isoformat() if inv.invoice_date else None,
                    inv.due_date.isoformat() if inv.due_date else None,
                    inv.subtotal,
                    inv.tax_amount,
                    inv.total,
                    inv.status,
                    inv.paid_date.isoformat() if inv.paid_date else None
                ))
        
        # Update last sync time
        _last_sync[user_id] = time.time()
        
        return len(invoices)
    
    def get_monthly_revenue(self, user_id, start_date=None, end_date=None):
        """
        Get monthly revenue aggregation for a specific user
        
        Returns:
            List of dicts with month and revenue
        """
        self.sync_invoices(user_id)
        conn = self.connect()
        self._ensure_table_exists(conn)
        
        query = """
            SELECT 
                strftime(invoice_date, '%Y-%m') as month,
                SUM(total) as revenue,
                COUNT(*) as invoice_count
            FROM invoices
            WHERE status != 'void' AND user_id = ?
        """
        
        params = [user_id]
        if start_date:
            query += " AND invoice_date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND invoice_date <= ?"
            params.append(end_date)
        
        query += " GROUP BY month ORDER BY month"
        
        result = conn.execute(query, params).fetchall()
        
        return [
            {'month': row[0], 'revenue': row[1], 'invoice_count': row[2]}
            for row in result
        ]
    
    def get_top_clients(self, user_id, limit=5):
        """
        Get top clients by revenue for a specific user
        
        Returns:
            List of dicts with client info and revenue
        """
        self.sync_invoices(user_id)
        conn = self.connect()
        self._ensure_table_exists(conn)
        
        result = conn.execute("""
            SELECT 
                client_name,
                SUM(total) as total_revenue,
                COUNT(*) as invoice_count,
                AVG(total) as avg_invoice
            FROM invoices
            WHERE status != 'void' AND user_id = ?
            GROUP BY client_name
            ORDER BY total_revenue DESC
            LIMIT ?
        """, [user_id, limit]).fetchall()
        
        return [
            {
                'client_name': row[0],
                'total_revenue': row[1],
                'invoice_count': row[2],
                'avg_invoice': row[3]
            }
            for row in result
        ]
    
    def get_aging_buckets(self, user_id):
        """
        Get aging analysis (unpaid invoices by age) for a specific user
        
        Returns:
            Dict with aging buckets
        """
        self.sync_invoices(user_id)
        conn = self.connect()
        self._ensure_table_exists(conn)
        
        result = conn.execute("""
            SELECT 
                SUM(CASE WHEN DATE_DIFF('day', due_date, CURRENT_DATE) BETWEEN 0 AND 30 
                    THEN total ELSE 0 END) as bucket_0_30,
                SUM(CASE WHEN DATE_DIFF('day', due_date, CURRENT_DATE) BETWEEN 31 AND 60 
                    THEN total ELSE 0 END) as bucket_31_60,
                SUM(CASE WHEN DATE_DIFF('day', due_date, CURRENT_DATE) > 60 
                    THEN total ELSE 0 END) as bucket_61_plus,
                COUNT(*) as total_unpaid
            FROM invoices
            WHERE status IN ('draft', 'sent') AND due_date IS NOT NULL AND user_id = ?
        """, [user_id]).fetchone()
        
        return {
            'bucket_0_30': result[0] or 0,
            'bucket_31_60': result[1] or 0,
            'bucket_61_plus': result[2] or 0,
            'total_unpaid': result[3] or 0
        }


# Singleton instance
_duckdb_service = None

def get_duckdb_service():
    """Get or create DuckDB service instance"""
    global _duckdb_service
    if _duckdb_service is None:
        db_path = os.getenv('DUCKDB_PATH', 'snappy_analytics.duckdb')
        _duckdb_service = DuckDBService(db_path)
    return _duckdb_service
