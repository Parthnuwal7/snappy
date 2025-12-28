"""Backup and restore service"""
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os


def derive_key(password: str, salt: bytes) -> bytes:
    """Derive encryption key from password"""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
    return key


def encrypt_backup(data: bytes, password: str) -> bytes:
    """Encrypt backup data with password"""
    salt = os.urandom(16)
    key = derive_key(password, salt)
    f = Fernet(key)
    encrypted_data = f.encrypt(data)
    # Prepend salt to encrypted data
    return salt + encrypted_data


def decrypt_backup(encrypted_data: bytes, password: str) -> bytes:
    """Decrypt backup data with password"""
    # Extract salt from beginning
    salt = encrypted_data[:16]
    encrypted = encrypted_data[16:]
    
    key = derive_key(password, salt)
    f = Fernet(key)
    return f.decrypt(encrypted)


# ==========================================
# JSON Backup & Supabase Upload Functions
# ==========================================

import json
import gzip
from datetime import datetime


def create_backup_data(app):
    """Create full JSON backup of all data"""
    with app.app_context():
        from app.models.models import db, Client, Item, Invoice, Settings
        from app.models.auth import User, Firm
        
        # Get current user's firm
        user = User.query.first()
        firm = user.firm if user else None
        
        backup_data = {
            'version': '1.0',
            'app': 'SNAPPY',
            'created_at': datetime.utcnow().isoformat(),
            'data': {
                'clients': [c.to_dict() for c in Client.query.all()],
                'items': [i.to_dict() for i in Item.query.all()],
                'invoices': [inv.to_dict(include_items=True) for inv in Invoice.query.all()],
                'settings': [s.to_dict() for s in Settings.query.all()],
                'firm': firm.to_dict() if firm else None,
                'user': {
                    'email': user.email,
                    'is_onboarded': user.is_onboarded
                } if user else None
            }
        }
        
        return backup_data


def save_backup_locally(backup_data, backup_dir=None):
    """Save backup to local filesystem"""
    if backup_dir is None:
        backup_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'backups')
    
    # Create backups directory if it doesn't exist
    os.makedirs(backup_dir, exist_ok=True)
    
    # Generate filename with timestamp
    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    filename = f"snappy_backup_{timestamp}.json"
    filepath = os.path.join(backup_dir, filename)
    
    # Save as JSON
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(backup_data, f, indent=2, ensure_ascii=False)
    
    # Also save compressed version
    gz_filepath = filepath + '.gz'
    with gzip.open(gz_filepath, 'wt', encoding='utf-8') as f:
        json.dump(backup_data, f, ensure_ascii=False)
    
    return {
        'json_path': filepath,
        'gz_path': gz_filepath,
        'timestamp': timestamp
    }


def upload_to_supabase(backup_data, user_email):
    """Upload backup to Supabase Storage bucket"""
    try:
        from app.services.supabase_service import SupabaseService
        
        supabase_service = SupabaseService()
        
        # Generate filename
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        # Sanitize email for filename
        safe_email = user_email.replace('@', '_at_').replace('.', '_')
        filename = f"backups/{safe_email}/snappy_backup_{timestamp}.json.gz"
        
        # Compress data
        json_str = json.dumps(backup_data, ensure_ascii=False)
        compressed = gzip.compress(json_str.encode('utf-8'))
        
        # Upload to Supabase Storage
        result = supabase_service.supabase.storage.from_('snappy-backups').upload(
            filename,
            compressed,
            {'content-type': 'application/gzip'}
        )
        
        return {
            'success': True,
            'filename': filename,
            'timestamp': timestamp
        }
        
    except Exception as e:
        print(f"Supabase backup upload failed: {e}")
        return {
            'success': False,
            'error': str(e)
        }


def run_backup(app, upload_to_cloud=True):
    """Run full backup - local + optional cloud upload"""
    # Create backup data
    backup_data = create_backup_data(app)
    
    # Save locally
    local_result = save_backup_locally(backup_data)
    
    result = {
        'local': local_result,
        'cloud': None
    }
    
    # Upload to Supabase if enabled
    if upload_to_cloud:
        user_email = backup_data['data']['user']['email'] if backup_data['data']['user'] else 'unknown'
        cloud_result = upload_to_supabase(backup_data, user_email)
        result['cloud'] = cloud_result
    
    return result
