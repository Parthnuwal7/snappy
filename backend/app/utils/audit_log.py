"""
Audit logging for license operations
Tracks all license activities for security monitoring
"""
from flask import request
from datetime import datetime


def log_license_action(supabase_service, license_key, action, success, 
                       status_before=None, status_after=None, 
                       error=None, machine_id=None, email=None):
    """
    Log license action to audit table
    
    Args:
        supabase_service: SupabaseService instance
        license_key: License key being operated on
        action: Action type ('validate', 'register_attempt', 'register_success', 'register_fail', 'void')
        success: Boolean indicating if action succeeded
        status_before: License status before action
        status_after: License status after action
        error: Error message if failed
        machine_id: Machine ID (for registration)
        email: User email
    """
    try:
        log_entry = {
            'license_key': license_key,
            'action': action,
            'success': success,
            'status_before': status_before,
            'status_after': status_after,
            'error_message': error,
            'machine_id': machine_id,
            'email': email,
            'ip_address': _get_client_ip(),
            'user_agent': request.headers.get('User-Agent', '')[:255] if request else None,
            'created_at': datetime.utcnow().isoformat()
        }
        
        supabase_service.supabase.table('license_audit_log').insert(log_entry).execute()
        print(f"📝 Audit log: {action} - {license_key} - {'Success' if success else 'Failed'}")
        
    except Exception as e:
        # Don't fail the operation if logging fails
        print(f"⚠️ Audit logging failed: {e}")


def _get_client_ip():
    """Get client IP address from request"""
    try:
        if request:
            # Check for proxy headers first
            if request.headers.get('X-Forwarded-For'):
                return request.headers.get('X-Forwarded-For').split(',')[0].strip()
            if request.headers.get('X-Real-IP'):
                return request.headers.get('X-Real-IP')
            return request.remote_addr
    except:
        pass
    return 'unknown'
