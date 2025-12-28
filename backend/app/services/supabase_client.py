"""Supabase client for backend operations"""
import os
from supabase import create_client, Client
from functools import lru_cache

@lru_cache(maxsize=1)
def get_supabase_client() -> Client:
    """Get cached Supabase client with service role key for admin operations"""
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    
    if not url or not key:
        raise ValueError(
            "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in environment variables"
        )
    
    return create_client(url, key)


def get_supabase_jwt_secret() -> str:
    """Get the Supabase JWT secret for token validation"""
    secret = os.getenv('SUPABASE_JWT_SECRET')
    if not secret:
        raise ValueError("SUPABASE_JWT_SECRET must be set in environment variables")
    return secret


# Re-export for convenience
supabase = None

def init_supabase():
    """Initialize Supabase client - call this at app startup"""
    global supabase
    try:
        supabase = get_supabase_client()
        print("✅ Supabase client initialized successfully")
    except ValueError as e:
        print(f"⚠️ Supabase not configured: {e}")
        print("   Running in local-only mode (no cloud features)")
