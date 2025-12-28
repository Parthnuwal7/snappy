"""
License Enforcement Middleware
Checks license expiry every 10 requests for performance optimization
"""
from flask import request, jsonify, session
from functools import wraps
from app.models.auth import User
from app.utils.license_guard import get_license_expiry_response


def require_valid_license(f):
    """
    Decorator to enforce license validity every 10 API requests
    Improves performance by checking license only periodically
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Skip if no user session
        if 'user_id' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        
        # Initialize request counter in session if not exists
        if 'api_request_count' not in session:
            session['api_request_count'] = 0
            session['last_license_check_valid'] = True
        
        # Increment request counter
        session['api_request_count'] += 1
        
        # Check license every 10 requests
        if session['api_request_count'] % 10 == 0:
            # Get user
            user = User.query.get(session['user_id'])
            if not user:
                return jsonify({'error': 'User not found'}), 404
            
            # Check license validity
            license_status = get_license_expiry_response(user)
            
            if not license_status.get('license_valid'):
                # License expired - block API access
                session['last_license_check_valid'] = False
                print(f"🚫 License check #{session['api_request_count']}: EXPIRED - {license_status.get('license_key')}")
                
                return jsonify({
                    'error': 'LICENSE_EXPIRED',
                    'license_expired': True,
                    'message': license_status.get('message'),
                    'expired_at': license_status.get('expired_at'),
                    'license_key': license_status.get('license_key'),
                    'days_expired': license_status.get('days_expired'),
                    'checked_at_request': session['api_request_count']
                }), 403
            else:
                # License valid
                session['last_license_check_valid'] = True
                print(f"✅ License check #{session['api_request_count']}: VALID - {license_status.get('license_key')}")
        else:
            # Between checks - use cached result
            if not session.get('last_license_check_valid', True):
                # Last check failed, block immediately
                return jsonify({
                    'error': 'LICENSE_EXPIRED',
                    'license_expired': True,
                    'message': 'Your license has expired. Please renew.',
                    'last_checked_at': session['api_request_count'] - (session['api_request_count'] % 10)
                }), 403
        
        # Proceed to route
        return f(*args, **kwargs)
    
    return decorated_function
