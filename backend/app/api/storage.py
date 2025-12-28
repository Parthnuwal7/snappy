"""Storage API endpoints for file uploads (logos, signatures, QR codes)"""
from flask import Blueprint, request, jsonify, g
from backend.app.middleware.jwt_auth import jwt_required
import os
import base64
import io

bp = Blueprint('storage', __name__)

# Allowed file types
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

# Bucket configuration
BUCKETS = {
    'logo': 'firm-logos',
    'signature': 'signatures',
    'qr': 'qr-codes'
}


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_supabase():
    """Get Supabase client (lazy import to avoid circular dependencies)"""
    try:
        from backend.app.services.supabase_client import get_supabase_client
        return get_supabase_client()
    except ValueError:
        return None


@bp.route('/upload/<file_type>', methods=['POST'])
@jwt_required
def upload_file(file_type):
    """
    Upload a file to Supabase Storage.
    
    file_type: 'logo', 'signature', or 'qr'
    
    Accepts:
    - multipart/form-data with 'file' field
    - JSON with 'file' as base64 encoded string
    """
    if file_type not in BUCKETS:
        return jsonify({'error': f'Invalid file type. Must be one of: {list(BUCKETS.keys())}'}), 400
    
    supabase = get_supabase()
    if not supabase:
        return jsonify({'error': 'Storage not configured. Please set Supabase credentials.'}), 503
    
    user_id = g.user_id
    bucket_name = BUCKETS[file_type]
    
    # Handle both multipart form and JSON base64
    file_data = None
    file_ext = 'jpg'
    
    if request.content_type and 'multipart/form-data' in request.content_type:
        # Handle file upload
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'File type not allowed. Use JPG or PNG.'}), 400
        
        file_ext = file.filename.rsplit('.', 1)[1].lower()
        file_data = file.read()
        
    else:
        # Handle JSON with base64
        data = request.get_json()
        if not data or 'file' not in data:
            return jsonify({'error': 'No file data provided'}), 400
        
        try:
            # Remove data URL prefix if present
            base64_str = data['file']
            if ',' in base64_str:
                base64_str = base64_str.split(',')[1]
            file_data = base64.b64decode(base64_str)
        except Exception as e:
            return jsonify({'error': f'Invalid base64 data: {str(e)}'}), 400
        
        # Get extension from filename if provided
        if 'filename' in data and allowed_file(data['filename']):
            file_ext = data['filename'].rsplit('.', 1)[1].lower()
    
    # Check file size
    if len(file_data) > MAX_FILE_SIZE:
        return jsonify({'error': f'File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB'}), 400
    
    # Create file path: {user_id}/{file_type}.{ext}
    file_path = f"{user_id}/{file_type}.{file_ext}"
    
    try:
        # Upload to Supabase Storage
        # First, try to remove existing file if any
        try:
            supabase.storage.from_(bucket_name).remove([file_path])
        except:
            pass  # File might not exist
        
        # Upload new file
        result = supabase.storage.from_(bucket_name).upload(
            file_path,
            file_data,
            file_options={
                'content-type': f'image/{file_ext if file_ext != "jpg" else "jpeg"}',
                'upsert': 'true'
            }
        )
        
        # Get the public URL (will be signed for private buckets)
        file_url = f"{bucket_name}/{file_path}"
        
        return jsonify({
            'message': 'File uploaded successfully',
            'path': file_url,
            'bucket': bucket_name,
            'file_path': file_path
        }), 201
        
    except Exception as e:
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500


@bp.route('/signed-url/<file_type>', methods=['GET'])
@jwt_required
def get_signed_url(file_type):
    """
    Get a signed URL for accessing a private file.
    
    file_type: 'logo', 'signature', or 'qr'
    """
    if file_type not in BUCKETS:
        return jsonify({'error': f'Invalid file type. Must be one of: {list(BUCKETS.keys())}'}), 400
    
    supabase = get_supabase()
    if not supabase:
        return jsonify({'error': 'Storage not configured'}), 503
    
    user_id = g.user_id
    bucket_name = BUCKETS[file_type]
    
    # Try both .jpg and .png extensions
    for ext in ['jpg', 'png', 'jpeg']:
        file_path = f"{user_id}/{file_type}.{ext}"
        
        try:
            # Create signed URL (valid for 1 hour)
            result = supabase.storage.from_(bucket_name).create_signed_url(
                file_path,
                expires_in=3600  # 1 hour
            )
            
            if result and result.get('signedURL'):
                return jsonify({
                    'signed_url': result['signedURL'],
                    'expires_in': 3600,
                    'path': f"{bucket_name}/{file_path}"
                })
        except:
            continue
    
    return jsonify({'error': 'File not found'}), 404


@bp.route('/delete/<file_type>', methods=['DELETE'])
@jwt_required
def delete_file(file_type):
    """
    Delete a file from Supabase Storage.
    
    file_type: 'logo', 'signature', or 'qr'
    """
    if file_type not in BUCKETS:
        return jsonify({'error': f'Invalid file type. Must be one of: {list(BUCKETS.keys())}'}), 400
    
    supabase = get_supabase()
    if not supabase:
        return jsonify({'error': 'Storage not configured'}), 503
    
    user_id = g.user_id
    bucket_name = BUCKETS[file_type]
    
    # Try both extensions
    deleted = False
    for ext in ['jpg', 'png', 'jpeg']:
        file_path = f"{user_id}/{file_type}.{ext}"
        try:
            supabase.storage.from_(bucket_name).remove([file_path])
            deleted = True
        except:
            continue
    
    if deleted:
        return jsonify({'message': 'File deleted successfully'})
    else:
        return jsonify({'error': 'File not found or already deleted'}), 404
