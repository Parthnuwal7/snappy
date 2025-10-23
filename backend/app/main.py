"""
SNAPPY Backend - Flask Application
Main application factory and configuration
"""
from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv
import os

from backend.app.models.models import db, init_db
from backend.app.api import invoices, clients, analytics, import_csv, backup

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
    
    # Enable CORS for Tauri/local development
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    
    # Initialize database
    db.init_app(app)
    
    with app.app_context():
        init_db()
    
    # Register blueprints
    app.register_blueprint(clients.bp, url_prefix='/api')
    app.register_blueprint(invoices.bp, url_prefix='/api')
    app.register_blueprint(analytics.bp, url_prefix='/api/analytics')
    app.register_blueprint(import_csv.bp, url_prefix='/api')
    app.register_blueprint(backup.bp, url_prefix='/api')
    
    @app.route('/health')
    def health():
        """Health check endpoint"""
        return {'status': 'healthy', 'app': 'SNAPPY'}, 200
    
    return app


if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)
