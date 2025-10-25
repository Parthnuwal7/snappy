"""DuckDB analytics service"""
import duckdb
from backend.app.models.models import db, Invoice, Client
import os


class DuckDBService:
    """Service for analytics using DuckDB"""
    
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
    
    def sync_invoices(self):
        """Sync invoice data from SQLite to DuckDB"""
        conn = self.connect()
        
        # Get all invoices with client data
        invoices = db.session.query(Invoice).join(Client).all()
        
        # Always create/recreate the table structure
        conn.execute("DROP TABLE IF EXISTS invoices")
        conn.execute("""
            CREATE TABLE invoices (
                invoice_id INTEGER,
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
        
        # Prepare and insert data only if invoices exist
        if invoices:
            data = []
            for inv in invoices:
                data.append({
                    'invoice_id': inv.id,
                    'invoice_number': inv.invoice_number,
                    'client_id': inv.client_id,
                    'client_name': inv.client.name,
                    'invoice_date': inv.invoice_date.isoformat() if inv.invoice_date else None,
                    'due_date': inv.due_date.isoformat() if inv.due_date else None,
                    'subtotal': inv.subtotal,
                    'tax_amount': inv.tax_amount,
                    'total': inv.total,
                    'status': inv.status,
                    'paid_date': inv.paid_date.isoformat() if inv.paid_date else None
                })
            
            # Insert all rows
            for row in data:
                conn.execute("""
                    INSERT INTO invoices VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, tuple(row.values()))
        
        return len(invoices)
    
    def get_monthly_revenue(self, start_date=None, end_date=None):
        """
        Get monthly revenue aggregation
        
        Returns:
            List of dicts with month and revenue
        """
        self.sync_invoices()
        conn = self.connect()
        
        query = """
            SELECT 
                strftime(invoice_date, '%Y-%m') as month,
                SUM(total) as revenue,
                COUNT(*) as invoice_count
            FROM invoices
            WHERE status != 'void'
        """
        
        params = []
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
    
    def get_top_clients(self, limit=5):
        """
        Get top clients by revenue
        
        Returns:
            List of dicts with client info and revenue
        """
        self.sync_invoices()
        conn = self.connect()
        
        result = conn.execute("""
            SELECT 
                client_name,
                SUM(total) as total_revenue,
                COUNT(*) as invoice_count,
                AVG(total) as avg_invoice
            FROM invoices
            WHERE status != 'void'
            GROUP BY client_name
            ORDER BY total_revenue DESC
            LIMIT ?
        """, [limit]).fetchall()
        
        return [
            {
                'client_name': row[0],
                'total_revenue': row[1],
                'invoice_count': row[2],
                'avg_invoice': row[3]
            }
            for row in result
        ]
    
    def get_aging_buckets(self):
        """
        Get aging analysis (unpaid invoices by age)
        
        Returns:
            Dict with aging buckets
        """
        self.sync_invoices()
        conn = self.connect()
        
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
            WHERE status IN ('draft', 'sent') AND due_date IS NOT NULL
        """).fetchone()
        
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
