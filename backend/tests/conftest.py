"""Pytest configuration"""
import os

# Force the app to build against an in-memory SQLite DB for tests. Must be set
# before importing app.main, because create_app() reads DATABASE_URL and opens
# a connection at startup — without this, tests hang trying to reach prod Supabase.
# load_dotenv(override=False) inside create_app won't clobber this value.
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'

import pytest
from app.main import create_app
from app.models.models import db as _db


@pytest.fixture
def app():
    """Create application for testing"""
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    
    with app.app_context():
        _db.create_all()
        yield app
        _db.session.remove()
        _db.drop_all()


@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()


@pytest.fixture
def db(app):
    """Create database for testing"""
    with app.app_context():
        yield _db
