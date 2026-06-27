"""
SNAPPY Backend - Flask Application
Main application factory and configuration
"""
from flask import Flask, request
from flask_cors import CORS
from dotenv import load_dotenv
from datetime import timedelta
import os

from app.models.models import db, init_db, Keepalive
from app.api import invoices, clients, analytics, import_csv, backup, auth, admin, items, storage, recurring, public, legal_feed, firm, roles, invites, case_files, case_events, case_documents, case_expenses, leads, case_notes, case_exhibits, calendar, tasks, writing

# Load environment variables
load_dotenv()


def create_app():
    """Application factory pattern"""
    app = Flask(__name__)

    # Configuration. Force DATABASE_URL to be set so the app never silently
    # falls back to a local SQLite file when prod env vars are misconfigured.
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise RuntimeError(
            "DATABASE_URL is not set. Configure it in your environment "
            "(see backend/.env.example) before starting the backend."
        )
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-prod')
    app.config['INVOICE_PREFIX'] = os.getenv('INVOICE_PREFIX', 'LAW')
    app.config['CURRENCY'] = os.getenv('CURRENCY', 'INR')
    app.config['DEFAULT_TAX_RATE'] = float(os.getenv('DEFAULT_TAX_RATE', '18'))
    
    # Session configuration - use simple signed cookie sessions
    # No filesystem storage needed, sessions stored in browser cookies
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['SESSION_COOKIE_SECURE'] = False  # Set to True in production with HTTPS
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)  # Sessions last 7 days
    
    # Enable CORS for frontend (Vercel) and local development
    CORS(app, 
         resources={r"/*": {"origins": "*"}},
         supports_credentials=True,
         allow_headers=["Content-Type", "Authorization"],
         methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
    )
    
    # Initialize database
    db.init_app(app)
    
    with app.app_context():
        init_db()
        # Import all models to ensure tables are created
        from app.models.auth import User, Firm, Role, FirmInvite, FirmDetails, BankAccount
        from app.models.models import Item  # Ensure items table is created
        from app.models.models import RecurringSchedule  # ensure table is created
        from app.models.case import CaseFile, CaseEvent, CaseDocument, CaseStageChange, CaseExpense, CaseNote  # ensure case tables are created
        from app.models.lead import Lead  # ensure leads table is created
        from app.models.task import Task  # ensure tasks table is created
        from app.models.writing import WritingDoc  # ensure writing_documents table is created
        from app.models.models import (
            LegalFeedSource, LegalFeedItem, LegalFeedRun, LegalFeedSetting,
            LegalFeedPreference, LegalFeedEvent,
        )  # ensure legal feed tables are created
        db.create_all()
    
    # Register blueprints with API versioning (v1)
    # All API endpoints are now under /api/v1/
    app.register_blueprint(auth.bp, url_prefix='/api/v1/auth')
    app.register_blueprint(admin.bp, url_prefix='/admin')  # Admin panel stays at /admin
    app.register_blueprint(clients.bp, url_prefix='/api/v1')
    app.register_blueprint(invoices.bp, url_prefix='/api/v1')
    app.register_blueprint(analytics.bp, url_prefix='/api/v1/analytics')
    app.register_blueprint(import_csv.bp, url_prefix='/api/v1')
    app.register_blueprint(backup.bp, url_prefix='/api/v1')
    app.register_blueprint(items.bp, url_prefix='/api/v1')
    app.register_blueprint(storage.bp, url_prefix='/api/v1/storage')
    app.register_blueprint(recurring.bp, url_prefix='/api/v1')
    app.register_blueprint(public.bp, url_prefix='/api/v1')
    app.register_blueprint(legal_feed.bp, url_prefix='/api/v1')
    app.register_blueprint(firm.bp, url_prefix='/api/v1')
    app.register_blueprint(roles.bp, url_prefix='/api/v1')
    app.register_blueprint(invites.bp, url_prefix='/api/v1')
    app.register_blueprint(case_files.bp, url_prefix='/api/v1')
    app.register_blueprint(case_events.bp, url_prefix='/api/v1')
    app.register_blueprint(case_documents.bp, url_prefix='/api/v1')
    app.register_blueprint(case_expenses.bp, url_prefix='/api/v1')
    app.register_blueprint(leads.bp, url_prefix='/api/v1')
    app.register_blueprint(case_notes.bp, url_prefix='/api/v1')
    app.register_blueprint(case_exhibits.bp, url_prefix='/api/v1')
    app.register_blueprint(calendar.bp, url_prefix='/api/v1')
    app.register_blueprint(tasks.bp, url_prefix='/api/v1')
    app.register_blueprint(writing.bp, url_prefix='/api/v1')

    @app.route('/health')
    def health():
        """Read-only liveness check. Cheap, no side effects, no DB writes."""
        return {'status': 'healthy', 'app': 'SNAPPY', 'version': '1.0.0'}, 200

    @app.route('/keepalive', methods=['GET', 'POST'])
    def keepalive():
        """Heartbeat endpoint pinged by Cloud Scheduler every 3 days.

        Performs both DB and Supabase-gateway activity so the project never
        crosses the 7-day idle threshold that triggers free-tier auto-pause.
        Side effects:
          * INSERTs a row into the `keepalive` table (DB activity).
          * Calls Supabase Storage list_buckets (Supabase API gateway activity).
        """
        source = (request.args.get('source') or 'unknown')[:50]
        row = Keepalive(source=source)
        db.session.add(row)
        db.session.commit()

        storage_check = 'ok'
        try:
            from app.services.supabase_client import get_supabase_client
            get_supabase_client().storage.list_buckets()
        except Exception as e:
            storage_check = f'error: {e}'

        return {
            'status': 'ok',
            'pinged_at': row.pinged_at.isoformat(),
            'source': source,
            'storage_check': storage_check,
        }, 200
    
    @app.route('/api/v1')
    def api_root():
        """API root endpoint - shows available API versions"""
        return {
            'version': 'v1',
            'app': 'SNAPPY',
            'company': 'Parth Nuwal',
            'endpoints': {
                'health': '/health',
                'keepalive': '/keepalive',
                'auth': '/api/v1/auth',
                'clients': '/api/v1/clients',
                'invoices': '/api/v1/invoices',
                'items': '/api/v1/items',
                'analytics': '/api/v1/analytics',
                'backup': '/api/v1/backup',
                'storage': '/api/v1/storage'
            }
        }, 200
    
    return app


if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)
