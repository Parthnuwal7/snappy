"""Pytest configuration"""
import os

# Force the app to build against an in-memory SQLite DB for tests. Must be set
# before importing app.main, because create_app() reads DATABASE_URL and opens
# a connection at startup — without this, tests hang trying to reach prod Supabase.
# load_dotenv(override=False) inside create_app won't clobber this value.
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'

# Neutralize the enrichment provider for tests so create_app()'s load_dotenv()
# can't pull a real OPENAI_API_KEY from backend/.env and trigger live API calls
# during ingestion. Tests that exercise enrichment inject a fake client instead.
os.environ['OPENAI_API_KEY'] = ''

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


@pytest.fixture
def make_owner(app, monkeypatch):
    """Factory: create a user who owns a fresh firm, returning auth headers.

    Signs a real HS256 token (matching the Supabase scheme) so the full
    jwt_required -> require_permission chain runs in endpoint tests.
    """
    import jwt as _pyjwt
    from app.models.auth import User
    from app.services.firm_service import provision_firm_for_user

    monkeypatch.setattr('app.middleware.jwt_auth.get_jwt_secret', lambda: 'test-secret')

    def _make(supabase_id='sb-owner', email='owner@firm.com', firm_name='Test Firm'):
        with app.app_context():
            user = User(supabase_id=supabase_id, email=email)
            _db.session.add(user)
            _db.session.commit()
            tenant = provision_firm_for_user(user, firm_name)
            firm_id = tenant.id
        token = _pyjwt.encode(
            {'sub': supabase_id, 'email': email, 'aud': 'authenticated'},
            'test-secret', algorithm='HS256',
        )
        return {'Authorization': f'Bearer {token}'}, firm_id

    return _make
