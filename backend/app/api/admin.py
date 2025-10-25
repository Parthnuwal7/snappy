"""Admin panel for managing product keys"""
from flask import Blueprint, request, jsonify, render_template_string, make_response
from backend.app.models.models import db
from backend.app.models.auth import ProductKey, User
from datetime import datetime, timedelta
from functools import wraps
import base64

bp = Blueprint('admin', __name__)

# Admin credentials (change these in production!)
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'SnappyAdmin@2025'

def check_admin_auth(username, password):
    """Check if username/password combination is valid"""
    return username == ADMIN_USERNAME and password == ADMIN_PASSWORD

def authenticate():
    """Send 401 response with auth challenge"""
    return make_response(
        'Authentication required',
        401,
        {'WWW-Authenticate': 'Basic realm="Admin Area"'}
    )

def requires_admin_auth(f):
    """Decorator for routes requiring admin authentication"""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_admin_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated


# HTML Template for Admin Panel
ADMIN_PANEL_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>SNAPPY Admin Panel</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        .header {
            background: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        h1 {
            color: #667eea;
            font-size: 32px;
            margin-bottom: 10px;
        }
        .subtitle {
            color: #666;
            font-size: 14px;
        }
        .card {
            background: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .card h2 {
            color: #333;
            margin-bottom: 20px;
            font-size: 24px;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-box {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }
        .stat-value {
            font-size: 36px;
            font-weight: bold;
            margin-bottom: 5px;
        }
        .stat-label {
            font-size: 14px;
            opacity: 0.9;
        }
        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            margin-bottom: 5px;
            color: #333;
            font-weight: 500;
        }
        input, select {
            width: 100%;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 5px;
            font-size: 14px;
        }
        .btn {
            background: #667eea;
            color: white;
            padding: 12px 24px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 500;
            transition: background 0.3s;
        }
        .btn:hover {
            background: #5568d3;
        }
        .btn-danger {
            background: #dc3545;
        }
        .btn-danger:hover {
            background: #c82333;
        }
        .btn-small {
            padding: 6px 12px;
            font-size: 12px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        th {
            background: #f8f9fa;
            font-weight: 600;
            color: #333;
        }
        .badge {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 500;
        }
        .badge-success {
            background: #d4edda;
            color: #155724;
        }
        .badge-danger {
            background: #f8d7da;
            color: #721c24;
        }
        .badge-warning {
            background: #fff3cd;
            color: #856404;
        }
        .key-code {
            font-family: monospace;
            background: #f8f9fa;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
        }
        .message {
            padding: 12px;
            border-radius: 5px;
            margin-bottom: 20px;
            display: none;
        }
        .message.success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        .message.error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        .inline-form {
            display: grid;
            grid-template-columns: 1fr 1fr auto;
            gap: 10px;
            align-items: end;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔐 SNAPPY Admin Panel</h1>
            <p class="subtitle">Product Key Management System</p>
        </div>

        <div class="card">
            <div class="stats">
                <div class="stat-box">
                    <div class="stat-value" id="totalKeys">-</div>
                    <div class="stat-label">Total Keys</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value" id="usedKeys">-</div>
                    <div class="stat-label">Used Keys</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value" id="availableKeys">-</div>
                    <div class="stat-label">Available Keys</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value" id="expiredKeys">-</div>
                    <div class="stat-label">Expired Keys</div>
                </div>
            </div>
        </div>

        <div class="card">
            <h2>Generate New Keys</h2>
            <div id="generateMessage" class="message"></div>
            <div class="inline-form">
                <div class="form-group">
                    <label>Number of Keys</label>
                    <input type="number" id="keyCount" value="1" min="1" max="100">
                </div>
                <div class="form-group">
                    <label>Valid for (days)</label>
                    <input type="number" id="keyDays" value="365" min="1" max="3650">
                </div>
                <div class="form-group">
                    <label>&nbsp;</label>
                    <button class="btn" onclick="generateKeys()">Generate Keys</button>
                </div>
            </div>
            <div id="generatedKeys" style="margin-top: 20px;"></div>
        </div>

        <div class="card">
            <h2>All Product Keys</h2>
            <div id="keysMessage" class="message"></div>
            <button class="btn" onclick="loadKeys()" style="margin-bottom: 20px;">Refresh List</button>
            <table>
                <thead>
                    <tr>
                        <th>Key</th>
                        <th>Status</th>
                        <th>User</th>
                        <th>Created</th>
                        <th>Expires</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody id="keysTable">
                    <tr><td colspan="6" style="text-align:center;color:#666;">Loading...</td></tr>
                </tbody>
            </table>
        </div>

        <div class="card">
            <h2>Users & Product Keys</h2>
            <div id="usersMessage" class="message"></div>
            <button class="btn" onclick="loadUsers()" style="margin-bottom: 20px;">Refresh Users</button>
            <table>
                <thead>
                    <tr>
                        <th>User ID</th>
                        <th>Email</th>
                        <th>Product Key</th>
                        <th>Onboarded</th>
                        <th>Firm Name</th>
                        <th>Registered</th>
                        <th>Last Login</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody id="usersTable">
                    <tr><td colspan="8" style="text-align:center;color:#666;">Loading...</td></tr>
                </tbody>
            </table>
        </div>
    </div>

    <script>
        function showMessage(elementId, message, type) {
            const el = document.getElementById(elementId);
            el.textContent = message;
            el.className = 'message ' + type;
            el.style.display = 'block';
            setTimeout(() => { el.style.display = 'none'; }, 5000);
        }

        async function generateKeys() {
            const count = document.getElementById('keyCount').value;
            const days = document.getElementById('keyDays').value;

            try {
                const response = await fetch('/admin/api/keys/generate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ count: parseInt(count), days: parseInt(days) })
                });

                const data = await response.json();
                
                if (response.ok) {
                    const keysHtml = data.keys.map(key => 
                        `<div class="key-code" style="margin: 5px 0;">${key}</div>`
                    ).join('');
                    document.getElementById('generatedKeys').innerHTML = 
                        '<strong>Generated Keys:</strong><br>' + keysHtml;
                    showMessage('generateMessage', data.message, 'success');
                    loadKeys();
                } else {
                    showMessage('generateMessage', data.error, 'error');
                }
            } catch (error) {
                showMessage('generateMessage', 'Failed to generate keys', 'error');
            }
        }

        async function loadKeys() {
            try {
                const response = await fetch('/admin/api/keys');
                const data = await response.json();
                
                if (response.ok) {
                    // Update stats
                    const stats = data.stats;
                    document.getElementById('totalKeys').textContent = stats.total;
                    document.getElementById('usedKeys').textContent = stats.used;
                    document.getElementById('availableKeys').textContent = stats.available;
                    document.getElementById('expiredKeys').textContent = stats.expired;

                    // Update table
                    const tbody = document.getElementById('keysTable');
                    if (data.keys.length === 0) {
                        tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:#666;">No keys found</td></tr>';
                        return;
                    }

                    tbody.innerHTML = data.keys.map(key => {
                        let statusBadge = '';
                        if (key.is_used) {
                            statusBadge = '<span class="badge badge-danger">Used</span>';
                        } else if (key.is_expired) {
                            statusBadge = '<span class="badge badge-warning">Expired</span>';
                        } else {
                            statusBadge = '<span class="badge badge-success">Available</span>';
                        }

                        const deleteButton = key.is_used 
                            ? '<span style="color:#999;font-size:12px;">Cannot delete (used)</span>'
                            : `<button class="btn btn-danger btn-small" onclick="deleteKey(${key.id})">Delete</button>`;

                        return `
                            <tr>
                                <td><code class="key-code">${key.key}</code></td>
                                <td>${statusBadge}</td>
                                <td>${key.user_email || '-'}</td>
                                <td>${new Date(key.created_at).toLocaleDateString()}</td>
                                <td>${key.expires_at ? new Date(key.expires_at).toLocaleDateString() : 'Never'}</td>
                                <td>${deleteButton}</td>
                            </tr>
                        `;
                    }).join('');
                }
            } catch (error) {
                showMessage('keysMessage', 'Failed to load keys', 'error');
            }
        }

        async function deleteKey(keyId) {
            if (!confirm('Are you sure you want to delete this key?')) {
                return;
            }

            try {
                const response = await fetch(`/admin/api/keys/${keyId}`, {
                    method: 'DELETE'
                });

                const data = await response.json();
                
                if (response.ok) {
                    showMessage('keysMessage', data.message, 'success');
                    loadKeys();
                } else {
                    showMessage('keysMessage', data.error || 'Failed to delete key', 'error');
                }
            } catch (error) {
                showMessage('keysMessage', 'Failed to delete key: ' + error.message, 'error');
            }
        }

        async function loadUsers() {
            try {
                const response = await fetch('/admin/api/users');
                const data = await response.json();
                
                if (response.ok) {
                    const tbody = document.getElementById('usersTable');
                    if (data.users.length === 0) {
                        tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;color:#666;">No users found</td></tr>';
                        return;
                    }

                    tbody.innerHTML = data.users.map(user => {
                        const onboardedBadge = user.is_onboarded
                            ? '<span class="badge badge-success">Yes</span>'
                            : '<span class="badge badge-warning">No</span>';

                        return `
                            <tr>
                                <td>${user.id}</td>
                                <td>${user.email}</td>
                                <td><code class="key-code">${user.product_key || '-'}</code></td>
                                <td>${onboardedBadge}</td>
                                <td>${user.firm_name || '-'}</td>
                                <td>${user.created_at ? new Date(user.created_at).toLocaleDateString() : '-'}</td>
                                <td>${user.last_login ? new Date(user.last_login).toLocaleDateString() : 'Never'}</td>
                                <td>
                                    <button class="btn btn-danger btn-small" onclick="deleteUser(${user.id}, '${user.email}')">Delete User</button>
                                </td>
                            </tr>
                        `;
                    }).join('');
                }
            } catch (error) {
                showMessage('usersMessage', 'Failed to load users', 'error');
            }
        }

        async function deleteUser(userId, userEmail) {
            const confirmText = `Are you sure you want to delete user "${userEmail}"?\n\n` +
                               `This will:\n` +
                               `- Delete the user account\n` +
                               `- Delete all their invoices and clients\n` +
                               `- Delete their firm data\n` +
                               `- Revoke and make their product key available for reuse\n\n` +
                               `This action CANNOT be undone!`;
            
            if (!confirm(confirmText)) {
                return;
            }

            // Double confirmation
            const typedConfirm = prompt('Type "DELETE" in capital letters to confirm deletion:');
            if (typedConfirm !== 'DELETE') {
                showMessage('usersMessage', 'Deletion cancelled - confirmation text did not match', 'error');
                return;
            }

            try {
                const response = await fetch(`/admin/api/users/${userId}`, {
                    method: 'DELETE'
                });

                const data = await response.json();
                
                if (response.ok) {
                    showMessage('usersMessage', data.message, 'success');
                    loadUsers();
                    loadKeys(); // Refresh keys table too
                } else {
                    showMessage('usersMessage', data.error || 'Failed to delete user', 'error');
                }
            } catch (error) {
                showMessage('usersMessage', 'Failed to delete user: ' + error.message, 'error');
            }
        }

        // Load keys on page load
        loadKeys();
        loadUsers();
    </script>
</body>
</html>
"""


@bp.route('/')
@requires_admin_auth
def admin_panel():
    """Render admin panel"""
    return render_template_string(ADMIN_PANEL_HTML)


@bp.route('/api/keys', methods=['GET'])
@requires_admin_auth
def get_all_keys():
    """Get all product keys with stats"""
    keys = ProductKey.query.order_by(ProductKey.created_at.desc()).all()
    
    stats = {
        'total': len(keys),
        'used': sum(1 for k in keys if k.is_used),
        'available': sum(1 for k in keys if not k.is_used and (not k.expires_at or k.expires_at > datetime.utcnow())),
        'expired': sum(1 for k in keys if k.expires_at and k.expires_at < datetime.utcnow() and not k.is_used)
    }
    
    keys_data = []
    for key in keys:
        user = User.query.get(key.user_id) if key.user_id else None
        keys_data.append({
            'id': key.id,
            'key': key.key,
            'is_used': key.is_used,
            'is_expired': key.expires_at and key.expires_at < datetime.utcnow(),
            'user_email': user.email if user else None,
            'created_at': key.created_at.isoformat() if key.created_at else None,
            'expires_at': key.expires_at.isoformat() if key.expires_at else None,
            'activated_at': key.activated_at.isoformat() if key.activated_at else None
        })
    
    return jsonify({
        'stats': stats,
        'keys': keys_data
    })


@bp.route('/api/keys/generate', methods=['POST'])
@requires_admin_auth
def generate_keys_admin():
    """Generate new product keys"""
    data = request.get_json()
    count = data.get('count', 1)
    days = data.get('days', 365)
    
    keys = []
    for _ in range(count):
        key = ProductKey(
            key=ProductKey.generate_key(),
            expires_at=datetime.utcnow() + timedelta(days=days)
        )
        db.session.add(key)
        keys.append(key.key)
    
    db.session.commit()
    
    return jsonify({
        'message': f'{count} product key(s) generated successfully',
        'keys': keys
    }), 201


@bp.route('/api/keys/<int:key_id>', methods=['DELETE'])
@requires_admin_auth
def delete_key(key_id):
    """Delete a product key"""
    key = ProductKey.query.get_or_404(key_id)
    
    if key.is_used:
        return jsonify({'error': 'Cannot delete a used product key'}), 400
    
    db.session.delete(key)
    db.session.commit()
    
    return jsonify({'message': 'Product key deleted successfully'})


@bp.route('/api/users', methods=['GET'])
@requires_admin_auth
def get_all_users():
    """Get all users with their product keys and firm info"""
    users = User.query.order_by(User.created_at.desc()).all()
    
    users_data = []
    for user in users:
        # Get the product key associated with this user
        product_key = ProductKey.query.filter_by(user_id=user.id).first()
        
        # Get firm info if user is onboarded
        firm_name = None
        if user.firm:
            firm_name = user.firm.firm_name
        
        users_data.append({
            'id': user.id,
            'email': user.email,
            'product_key': product_key.key if product_key else None,
            'is_onboarded': user.is_onboarded,
            'firm_name': firm_name,
            'created_at': user.created_at.isoformat() if user.created_at else None,
            'last_login': user.last_login.isoformat() if user.last_login else None
        })
    
    return jsonify({'users': users_data})


@bp.route('/api/users/<int:user_id>', methods=['DELETE'])
@requires_admin_auth
def delete_user_admin(user_id):
    """Delete a user and revoke their product key"""
    user = User.query.get_or_404(user_id)
    
    try:
        # Import models needed for cleanup
        from backend.app.models.models import Invoice, InvoiceItem, Client
        
        # Get user's email for response message
        user_email = user.email
        
        # Delete all user's data (same logic as self-delete but admin-initiated)
        # Delete invoice items first (foreign key constraint)
        InvoiceItem.query.delete()
        
        # Delete all invoices
        Invoice.query.delete()
        
        # Delete all clients
        Client.query.delete()
        
        # Delete firm if exists
        if user.firm:
            db.session.delete(user.firm)
        
        # Revoke product key - make it available for reuse
        product_key = ProductKey.query.filter_by(user_id=user.id).first()
        if product_key:
            product_key.is_used = False
            product_key.user_id = None
            product_key.activated_at = None
        
        # Delete user
        db.session.delete(user)
        db.session.commit()
        
        return jsonify({
            'message': f'User "{user_email}" deleted successfully and product key revoked'
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to delete user: {str(e)}'}), 500
