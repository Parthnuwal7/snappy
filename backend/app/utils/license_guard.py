"""
License Guard - Validates license on app startup
Blocks app usage if license is expired
"""
from datetime import datetime, timezone
from flask import jsonify
from backend.app.models.auth import User
from backend.app.models.models import db


class LicenseExpiredError(Exception):
    """Custom exception for expired licenses"""
    pass


def check_user_license_valid(user):
    """
    Check if user's license is valid (not expired)
    
    Args:
        user: User object from database
        
    Returns:
        dict: Status information
        
    Raises:
        LicenseExpiredError: If license has expired
    """
    # No expiry set - allow access (legacy users)
    if not user.license_expires_at:
        return {
            'valid': True,
            'message': 'License valid (no expiry set)',
            'expires_at': None
        }
    
    # Check expiry (works offline)
    now = datetime.now(timezone.utc)
    expires_at = user.license_expires_at
    
    # Make timezone-aware if needed
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    
    if expires_at <= now:
        # License expired
        time_expired = now - expires_at
        days_expired = time_expired.days
        
        raise LicenseExpiredError({
            'expired': True,
            'expired_at': expires_at.isoformat(),
            'days_expired': days_expired,
            'license_key': user.license_key,
            'email': user.email
        })
    
    # License still valid
    time_remaining = expires_at - now
    days_remaining = time_remaining.days
    
    return {
        'valid': True,
        'expires_at': expires_at.isoformat(),
        'days_remaining': days_remaining,
        'license_key': user.license_key
    }


def get_license_expiry_response(user):
    """
    Get formatted response for license expiry status
    Used for API responses
    """
    try:
        status = check_user_license_valid(user)
        return {
            'license_valid': True,
            'license_status': status
        }
    except LicenseExpiredError as e:
        error_info = e.args[0]
        return {
            'license_valid': False,
            'license_expired': True,
            'error': 'License expired',
            'message': f'Your license expired {error_info["days_expired"]} day(s) ago. Please contact admin to renew.',
            'expired_at': error_info['expired_at'],
            'license_key': error_info['license_key'],
            'days_expired': error_info['days_expired']
        }
