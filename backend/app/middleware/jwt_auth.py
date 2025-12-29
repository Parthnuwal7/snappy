"""JWT authentication middleware for Supabase tokens"""
import os
import jwt
from functools import wraps
from flask import request, jsonify, g
from dotenv import load_dotenv

# Load .env file explicitly
load_dotenv()

# Cache JWT secret (loaded once at startup)
_jwt_secret_cache = None

def get_jwt_secret():
    """Get the JWT secret for token validation"""
    global _jwt_secret_cache
    
    if _jwt_secret_cache is not None:
        return _jwt_secret_cache
    
    secret = os.getenv('SUPABASE_JWT_SECRET', '')
    _jwt_secret_cache = secret
    
    # Debug: only print once at first load
    if secret:
        print(f"✅ JWT Secret loaded: {secret[:10]}...")
    else:
        print("❌ JWT Secret NOT FOUND in environment")
        print(f"   Available env vars with 'SUPABASE': {[k for k in os.environ if 'SUPABASE' in k]}")
    
    return secret

def jwt_required(f):
    """
    Decorator to require a valid Supabase JWT token.
    Sets g.user_id with the authenticated user's ID.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        
        if not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Missing or invalid Authorization header'}), 401
        
        token = auth_header.split(' ', 1)[1]
        
        if not token:
            return jsonify({'error': 'No token provided'}), 401
        
        jwt_secret = get_jwt_secret()
        
        if not jwt_secret:
            # Fallback for development without Supabase configured
            return jsonify({'error': 'JWT authentication not configured'}), 500
        
        try:
            # Decode and verify the JWT token
            # Supabase uses HS256 algorithm
            payload = jwt.decode(
                token,
                jwt_secret,
                algorithms=['HS256'],
                audience='authenticated'
            )
            
            # Extract user ID from the 'sub' claim
            user_id = payload.get('sub')
            if not user_id:
                return jsonify({'error': 'Invalid token: missing user ID'}), 401
            
            # Store user ID in Flask's g object for use in route handlers
            g.user_id = user_id
            g.user_email = payload.get('email')
            
            return f(*args, **kwargs)
            
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired'}), 401
        except jwt.InvalidAudienceError:
            return jsonify({'error': 'Invalid token audience'}), 401
        except jwt.InvalidTokenError as e:
            return jsonify({'error': f'Invalid token: {str(e)}'}), 401
    
    return decorated_function


def jwt_optional(f):
    """
    Decorator that tries to authenticate but doesn't require it.
    Sets g.user_id if token is valid, otherwise g.user_id is None.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        
        g.user_id = None
        g.user_email = None
        
        if auth_header.startswith('Bearer '):
            token = auth_header.split(' ', 1)[1]
            jwt_secret = get_jwt_secret()
            
            if token and jwt_secret:
                try:
                    payload = jwt.decode(
                        token,
                        jwt_secret,
                        algorithms=['HS256'],
                        audience='authenticated'
                    )
                    g.user_id = payload.get('sub')
                    g.user_email = payload.get('email')
                except jwt.InvalidTokenError:
                    pass  # Token invalid, continue without auth
        
        return f(*args, **kwargs)
    
    return decorated_function
