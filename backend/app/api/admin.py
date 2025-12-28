"""Admin panel for managing users"""
from flask import Blueprint, request, jsonify, render_template_string, make_response
from app.models.models import db
from app.models.auth import User
from datetime import datetime
from functools import wraps

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
        .badge-warning {
            background: #fff3cd;
            color: #856404;
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
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔐 SNAPPY Admin Panel</h1>
            <p class="subtitle">User Management System</p>
        </div>

        <div class="card">
            <div class="stats">
                <div class="stat-box">
                    <div class="stat-value" id="totalUsers">-</div>
                    <div class="stat-label">Total Users</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value" id="onboardedUsers">-</div>
                    <div class="stat-label">Onboarded Users</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value" id="activeUsers">-</div>
                    <div class="stat-label">Active Users</div>
                </div>
            </div>
        </div>

        <div class="card">
            <h2>Users</h2>
            <div id="usersMessage" class="message"></div>
            <button class="btn" onclick="loadUsers()" style="margin-bottom: 20px;">Refresh Users</button>
            <table>
                <thead>
                    <tr>
                        <th>User ID</th>
                        <th>Email</th>
                        <th>Onboarded</th>
                        <th>Firm Name</th>
                        <th>Registered</th>
                        <th>Last Login</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody id="usersTable">
                    <tr><td colspan="7" style="text-align:center;color:#666;">Loading...</td></tr>
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

        async function loadUsers() {
            try {
                const response = await fetch('/admin/api/users');
                const data = await response.json();
                
                if (response.ok) {
                    // Update stats
                    document.getElementById('totalUsers').textContent = data.stats.total;
                    document.getElementById('onboardedUsers').textContent = data.stats.onboarded;
                    document.getElementById('activeUsers').textContent = data.stats.active;

                    const tbody = document.getElementById('usersTable');
                    if (data.users.length === 0) {
                        tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;color:#666;">No users found</td></tr>';
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
                               `- Delete their firm data\n\n` +
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
                } else {
                    showMessage('usersMessage', data.error || 'Failed to delete user', 'error');
                }
            } catch (error) {
                showMessage('usersMessage', 'Failed to delete user: ' + error.message, 'error');
            }
        }

        // Load users on page load
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


@bp.route('/api/users', methods=['GET'])
@requires_admin_auth
def get_all_users():
    """Get all users with their firm info"""
    users = User.query.order_by(User.created_at.desc()).all()
    
    stats = {
        'total': len(users),
        'onboarded': sum(1 for u in users if u.is_onboarded),
        'active': sum(1 for u in users if u.is_active)
    }
    
    users_data = []
    for user in users:
        # Get firm info if user is onboarded
        firm_name = None
        if user.firm:
            firm_name = user.firm.firm_name
        
        users_data.append({
            'id': user.id,
            'email': user.email,
            'is_onboarded': user.is_onboarded,
            'is_active': user.is_active,
            'firm_name': firm_name,
            'created_at': user.created_at.isoformat() if user.created_at else None,
            'last_login': user.last_login.isoformat() if user.last_login else None
        })
    
    return jsonify({'users': users_data, 'stats': stats})


@bp.route('/api/users/<int:user_id>', methods=['DELETE'])
@requires_admin_auth
def delete_user_admin(user_id):
    """Delete a user"""
    user = User.query.get_or_404(user_id)
    
    try:
        # Import models needed for cleanup
        from app.models.models import Invoice, InvoiceItem, Client
        
        # Get user's email for response message
        user_email = user.email
        
        # Delete all user's data
        # Delete invoice items first (foreign key constraint)
        InvoiceItem.query.delete()
        
        # Delete all invoices
        Invoice.query.delete()
        
        # Delete all clients
        Client.query.delete()
        
        # Delete firm if exists
        if user.firm:
            db.session.delete(user.firm)
        
        # Delete user
        db.session.delete(user)
        db.session.commit()
        
        return jsonify({
            'message': f'User "{user_email}" deleted successfully'
        }), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to delete user: {str(e)}'}), 500
