"""Admin panel for managing users"""
from flask import Blueprint, request, jsonify, render_template_string, make_response
from app.models.models import db
from app.models.auth import User
from datetime import datetime
from functools import wraps

bp = Blueprint('admin', __name__)

# Admin credentials come from environment. ADMIN_PASSWORD is required; the
# panel refuses to serve if it is unset (no insecure default).
import os
import hmac


def _admin_password():
    return os.getenv('ADMIN_PASSWORD')


def _admin_username():
    return os.getenv('ADMIN_USERNAME', 'admin')


def check_admin_auth(username, password):
    """Constant-time credential check. False if ADMIN_PASSWORD is unset."""
    expected_pw = _admin_password()
    if not expected_pw:
        return False
    user_ok = hmac.compare_digest(username or '', _admin_username())
    pw_ok = hmac.compare_digest(password or '', expected_pw)
    return user_ok and pw_ok

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
        if not _admin_password():
            return make_response('Admin panel disabled: ADMIN_PASSWORD not set', 503)
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

        <div class="card">
            <h2>Legal Feed</h2>
            <div id="lfMessage" class="message"></div>
            <button class="btn" onclick="lfRunNow()">Run ingestion now</button>
            <button class="btn" onclick="lfSeed()" style="margin-left:8px;">Seed v1 sources</button>
            <button class="btn" onclick="lfBackfill()" style="margin-left:8px;">Enrich backlog</button>
            <button class="btn" onclick="lfRecompute()" style="margin-left:8px;">Recompute behavior</button>
            <button class="btn" onclick="lfLoad()" style="margin-left:8px;">Refresh</button>

            <h3 style="margin-top:24px;">Ordering mode</h3>
            <select id="lfMode" onchange="lfSetMode()">
                <option value="recency">Recency (newest first)</option>
                <option value="weighted">Weighted (by source priority)</option>
            </select>

            <h3 style="margin-top:24px;">Latest runs</h3>
            <table><thead><tr><th>Started</th><th>Trigger</th><th>Status</th><th>Ingested</th></tr></thead>
                <tbody id="lfRuns"><tr><td colspan="4">&mdash;</td></tr></tbody></table>

            <h3 style="margin-top:24px;">Sources</h3>
            <table><thead><tr><th>Name</th><th>Type</th><th>Court</th><th>Enabled</th><th>Weight</th><th>24h</th><th>Last run</th><th></th></tr></thead>
                <tbody id="lfSources"><tr><td colspan="8">&mdash;</td></tr></tbody></table>
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

        // Legal Feed admin
        async function lfLoad() {
            const runs = await (await fetch('/admin/api/legal-feed/runs')).json();
            document.getElementById('lfRuns').innerHTML = (runs.runs || []).map(r =>
                `<tr><td>${r.started_at || '-'}</td><td>${r.trigger}</td><td>${r.status}</td><td>${r.total_ingested}</td></tr>`
            ).join('') || '<tr><td colspan="4">No runs yet</td></tr>';

            const s = await (await fetch('/admin/api/legal-feed/sources')).json();
            document.getElementById('lfSources').innerHTML = (s.sources || []).map(src =>
                `<tr><td>${src.name}</td><td>${src.content_type}</td><td>${src.court || '-'}</td>
                 <td>${src.enabled ? 'Yes' : 'No'}</td><td>${src.weight}</td>
                 <td>${src.count_24h ?? '-'}</td><td>${src.count_last_run ?? '-'}</td>
                 <td><button class="btn btn-small" onclick="lfToggle(${src.id}, ${!src.enabled})">${src.enabled ? 'Disable' : 'Enable'}</button></td></tr>`
            ).join('') || '<tr><td colspan="8">No sources — click "Seed v1 sources"</td></tr>';

            const set = await (await fetch('/admin/api/legal-feed/settings')).json();
            document.getElementById('lfMode').value = set.ordering_mode;
        }
        async function lfRunNow() {
            const r = await (await fetch('/admin/api/legal-feed/run', {method:'POST'})).json();
            showMessage('lfMessage', `Run ${r.status}: ${r.total_ingested} new item(s), ${r.enriched || 0} enriched, ${r.enrich_failed || 0} failed`, 'success');
            lfLoad();
        }
        async function lfSeed() {
            const r = await (await fetch('/admin/api/legal-feed/seed', {method:'POST'})).json();
            showMessage('lfMessage', `Seeded ${r.inserted} source(s)`, 'success');
            lfLoad();
        }
        async function lfBackfill() {
            const r = await (await fetch('/admin/api/legal-feed/backfill',
                {method:'POST', headers:{'Content-Type':'application/json'},
                 body: JSON.stringify({limit: 100})})).json();
            showMessage('lfMessage', `Backfill: attempted ${r.attempted}, enriched ${r.enriched}, failed ${r.failed}`, 'success');
            lfLoad();
        }
        async function lfRecompute() {
            const r = await (await fetch('/admin/api/legal-feed/recompute-behavior', {method:'POST'})).json();
            showMessage('lfMessage', `Recomputed behavior for ${r.recomputed} user(s)`, 'success');
        }
        async function lfToggle(id, enabled) {
            await fetch(`/admin/api/legal-feed/sources/${id}`, {method:'PUT',
                headers:{'Content-Type':'application/json'}, body: JSON.stringify({enabled})});
            lfLoad();
        }
        async function lfSetMode() {
            const ordering_mode = document.getElementById('lfMode').value;
            await fetch('/admin/api/legal-feed/settings', {method:'PUT',
                headers:{'Content-Type':'application/json'}, body: JSON.stringify({ordering_mode})});
            showMessage('lfMessage', `Ordering set to ${ordering_mode}`, 'success');
        }

        // Load users on page load
        loadUsers();
        lfLoad();
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
        # Get firm info if user is onboarded. The User relationship is
        # 'firm_details' (see models/auth.py); 'user.firm' does not exist.
        firm_name = None
        if user.firm_details:
            firm_name = user.firm_details.firm_name
        
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


# ---------------------------------------------------------------------------
# Legal Feed administration
# ---------------------------------------------------------------------------
from datetime import timedelta
from app.models.models import (
    LegalFeedSource, LegalFeedItem, LegalFeedRun, LegalFeedSetting,
)
from app.services.legal_feed.ingest import run_ingestion, enrich_backlog
from app.services.legal_feed.events import recompute_behavior_embedding
from app.services.legal_feed.seed import seed_sources
from app.services.legal_feed.query import get_ordering_mode

ALLOWED_ORDERING = {'recency', 'weighted'}


@bp.route('/api/legal-feed/runs', methods=['GET'])
@requires_admin_auth
def lf_runs():
    runs = LegalFeedRun.query.order_by(LegalFeedRun.id.desc()).limit(20).all()
    return jsonify({'runs': [r.to_dict() for r in runs]})


@bp.route('/api/legal-feed/run', methods=['POST'])
@requires_admin_auth
def lf_run_now():
    return jsonify(run_ingestion('manual'))


@bp.route('/api/legal-feed/seed', methods=['POST'])
@requires_admin_auth
def lf_seed():
    return jsonify({'inserted': seed_sources()})


@bp.route('/api/legal-feed/backfill', methods=['POST'])
@requires_admin_auth
def lf_backfill():
    limit = (request.get_json(silent=True) or {}).get('limit', 100)
    return jsonify(enrich_backlog(limit=limit))


@bp.route('/api/legal-feed/recompute-behavior', methods=['POST'])
@requires_admin_auth
def lf_recompute_behavior():
    from app.models.models import LegalFeedPreference
    user_ids = [p.user_id for p in LegalFeedPreference.query.all()]
    for uid in user_ids:
        recompute_behavior_embedding(uid)
    return jsonify({'recomputed': len(user_ids)})


@bp.route('/api/legal-feed/sources', methods=['GET'])
@requires_admin_auth
def lf_sources():
    since = datetime.utcnow() - timedelta(hours=24)
    last_run = LegalFeedRun.query.order_by(LegalFeedRun.id.desc()).first()
    last_run_counts = {}
    if last_run and last_run.results:
        for r in last_run.results:
            last_run_counts[r.get('source_id')] = r.get('inserted', 0)
    out = []
    for s in LegalFeedSource.query.order_by(LegalFeedSource.id).all():
        d = s.to_dict()
        d['count_24h'] = LegalFeedItem.query.filter(
            LegalFeedItem.source_id == s.id,
            LegalFeedItem.ingested_at >= since).count()
        d['count_last_run'] = last_run_counts.get(s.id, 0)
        out.append(d)
    return jsonify({'sources': out})


@bp.route('/api/legal-feed/sources', methods=['POST'])
@requires_admin_auth
def lf_create_source():
    data = request.get_json() or {}
    if not data.get('name') or not data.get('feed_url') or not data.get('content_type'):
        return jsonify({'error': 'name, feed_url and content_type are required'}), 400
    src = LegalFeedSource(
        name=data['name'], content_type=data['content_type'],
        court=data.get('court'), kind=data.get('kind', 'rss'),
        feed_url=data['feed_url'], enabled=data.get('enabled', True),
        weight=int(data.get('weight', 0)),
    )
    db.session.add(src)
    db.session.commit()
    return jsonify(src.to_dict()), 201


@bp.route('/api/legal-feed/sources/<int:source_id>', methods=['PUT'])
@requires_admin_auth
def lf_update_source(source_id):
    src = LegalFeedSource.query.get_or_404(source_id)
    data = request.get_json() or {}
    if 'enabled' in data:
        src.enabled = bool(data['enabled'])
    if 'weight' in data:
        src.weight = int(data['weight'])
    if 'court' in data:
        src.court = data['court']
    db.session.commit()
    return jsonify(src.to_dict())


@bp.route('/api/legal-feed/items', methods=['GET'])
@requires_admin_auth
def lf_items():
    limit = min(request.args.get('limit', default=50, type=int) or 50, 200)
    items = LegalFeedItem.query.order_by(LegalFeedItem.id.desc()).limit(limit).all()
    return jsonify({'items': [i.to_dict() for i in items]})


@bp.route('/api/legal-feed/items/<int:item_id>/hide', methods=['POST'])
@requires_admin_auth
def lf_hide_item(item_id):
    item = LegalFeedItem.query.get_or_404(item_id)
    data = request.get_json() or {}
    item.hidden = bool(data.get('hidden', True))
    db.session.commit()
    return jsonify(item.to_dict())


@bp.route('/api/legal-feed/settings', methods=['GET'])
@requires_admin_auth
def lf_get_settings():
    return jsonify({'ordering_mode': get_ordering_mode()})


@bp.route('/api/legal-feed/settings', methods=['PUT'])
@requires_admin_auth
def lf_put_settings():
    data = request.get_json() or {}
    mode = data.get('ordering_mode')
    if mode not in ALLOWED_ORDERING:
        return jsonify({'error': f'ordering_mode must be one of {sorted(ALLOWED_ORDERING)}'}), 400
    setting = LegalFeedSetting.query.get(1)
    if setting is None:
        setting = LegalFeedSetting(id=1, ordering_mode=mode)
        db.session.add(setting)
    else:
        setting.ordering_mode = mode
    db.session.commit()
    return jsonify(setting.to_dict())
