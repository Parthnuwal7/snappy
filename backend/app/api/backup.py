"""Backup API endpoints"""
from flask import Blueprint, request, jsonify, g, Response
from app.middleware.jwt_auth import jwt_required
from app.services.backup_job import (
    create_backup_for_user,
    get_user_backups,
    download_backup,
    delete_old_backups
)

bp = Blueprint('backup', __name__)


@bp.route('/backup', methods=['POST'])
@jwt_required
def create_backup():
    """Create a new backup of all invoices for the current user"""
    user_id = g.user_id
    user_email = g.user_email
    
    result = create_backup_for_user(user_id, user_email)
    
    if result:
        return jsonify({
            'message': 'Backup created successfully',
            'backup': result
        }), 201
    else:
        return jsonify({'error': 'Failed to create backup'}), 500


@bp.route('/backup', methods=['GET'])
@jwt_required
def list_backups():
    """List all backups for the current user"""
    user_id = g.user_id
    
    backups = get_user_backups(user_id)
    
    return jsonify({
        'backups': backups,
        'count': len(backups)
    })


@bp.route('/backup/<file_name>', methods=['GET'])
@jwt_required
def get_backup(file_name):
    """Download a specific backup file"""
    user_id = g.user_id
    
    content = download_backup(user_id, file_name)
    
    if content:
        return Response(
            content,
            mimetype='application/json',
            headers={
                'Content-Disposition': f'attachment; filename={file_name}'
            }
        )
    else:
        return jsonify({'error': 'Backup not found'}), 404


@bp.route('/backup/<file_name>', methods=['DELETE'])
@jwt_required
def delete_backup(file_name):
    """Delete a specific backup file"""
    user_id = g.user_id
    
    try:
        from app.services.supabase_client import get_supabase_client
        supabase = get_supabase_client()
        
        file_path = f"{user_id}/{file_name}"
        supabase.storage.from_('invoice-backups').remove([file_path])
        
        return jsonify({'message': 'Backup deleted successfully'})
    except Exception as e:
        return jsonify({'error': f'Failed to delete backup: {str(e)}'}), 500


@bp.route('/backup/cleanup', methods=['POST'])
@jwt_required
def cleanup_old_backups():
    """Delete backups older than retention period"""
    user_id = g.user_id
    
    data = request.get_json() or {}
    retention_days = data.get('retention_days', 30)
    
    deleted_count = delete_old_backups(user_id, retention_days)
    
    return jsonify({
        'message': f'Deleted {deleted_count} old backups',
        'deleted_count': deleted_count
    })
