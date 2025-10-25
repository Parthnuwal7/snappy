"""
SNAPPY Backend - Flask Application
Main application factory and configuration
"""
from flask import Flask
from flask_cors import CORS
from flask_session import Session
from dotenv import load_dotenv
from datetime import timedelta
import os

from backend.app.models.models import db, init_db
from backend.app.api import invoices, clients, analytics, import_csv, backup, auth, admin

# Load environment variables
load_dotenv()


def create_app():
    """Application factory pattern"""
    app = Flask(__name__)
    
    # Configuration
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///snappy.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-prod')
    app.config['INVOICE_PREFIX'] = os.getenv('INVOICE_PREFIX', 'LAW')
    app.config['CURRENCY'] = os.getenv('CURRENCY', 'INR')
    app.config['DEFAULT_TAX_RATE'] = float(os.getenv('DEFAULT_TAX_RATE', '18'))
    
    # Session configuration
    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['SESSION_PERMANENT'] = True
    app.config['SESSION_USE_SIGNER'] = False  # Set to False to avoid bytes/string issue
    app.config['SESSION_FILE_DIR'] = os.path.join(os.path.dirname(__file__), '..', 'flask_session')
    app.config['SESSION_FILE_THRESHOLD'] = 500
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['SESSION_COOKIE_SECURE'] = False  # Set to True in production with HTTPS
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)  # Sessions last 7 days
    Session(app)
    
    # Enable CORS for Tauri/local development
    CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)
    
    # Initialize database
    db.init_app(app)
    
    with app.app_context():
        init_db()
        # Import auth models to create tables
        from backend.app.models.auth import User, Firm, ProductKey
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
    
    @app.route('/health')
    def health():
        """Health check endpoint"""
        return {'status': 'healthy', 'app': 'SNAPPY', 'version': '1.0.0'}, 200
    
    @app.route('/api/v1')
    def api_root():
        """API root endpoint - shows available API versions"""
        return {
            'version': 'v1',
            'app': 'SNAPPY',
            'company': 'Parth Nuwal',
            'endpoints': {
                'health': '/health',
                'auth': '/api/v1/auth',
                'clients': '/api/v1/clients',
                'invoices': '/api/v1/invoices',
                'analytics': '/api/v1/analytics',
                'backup': '/api/v1/backup'
            }
        }, 200
    
    return app


if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)
