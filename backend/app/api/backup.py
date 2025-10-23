"""Backup and Restore API endpoints"""
from flask import Blueprint, request, jsonify, send_file
from backend.app.services.backup_service import encrypt_backup, decrypt_backup
from datetime import datetime
import os
import shutil
import io

bp = Blueprint('backup', __name__)


@bp.route('/backup', methods=['POST'])
def create_backup():
    """Create a backup of the database"""
    data = request.get_json() or {}
    encrypt = data.get('encrypt', False)
    password = data.get('password')
    
    if encrypt and not password:
        return jsonify({'error': 'Password required for encrypted backup'}), 400
    
    try:
        # Database file path
        db_path = 'snappy.db'
        
        if not os.path.exists(db_path):
            return jsonify({'error': 'Database file not found'}), 404
        
        # Read database file
        with open(db_path, 'rb') as f:
            db_data = f.read()
        
        # Encrypt if requested
        if encrypt:
            db_data = encrypt_backup(db_data, password)
        
        # Generate filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"snappy_backup_{timestamp}.{'enc' if encrypt else 'db'}"
        
        # Return as downloadable file
        return send_file(
            io.BytesIO(db_data),
            mimetype='application/octet-stream',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        return jsonify({'error': f'Backup failed: {str(e)}'}), 500


@bp.route('/restore', methods=['POST'])
def restore_backup():
    """Restore database from backup"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    password = request.form.get('password')
    is_encrypted = request.form.get('encrypted', 'false').lower() == 'true'
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if is_encrypted and not password:
        return jsonify({'error': 'Password required for encrypted backup'}), 400
    
    try:
        # Read backup file
        backup_data = file.read()
        
        # Decrypt if necessary
        if is_encrypted:
            try:
                backup_data = decrypt_backup(backup_data, password)
            except Exception:
                return jsonify({'error': 'Failed to decrypt backup. Wrong password?'}), 400
        
        # Create backup of current database
        db_path = 'snappy.db'
        if os.path.exists(db_path):
            backup_current = f"snappy_before_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            shutil.copy2(db_path, backup_current)
        
        # Write restored database
        with open(db_path, 'wb') as f:
            f.write(backup_data)
        
        return jsonify({
            'success': True,
            'message': 'Database restored successfully'
        })
        
    except Exception as e:
        return jsonify({'error': f'Restore failed: {str(e)}'}), 500
