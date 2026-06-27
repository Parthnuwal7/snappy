"""Resolve the authenticated user into firm + permission context on `g`.

Endpoints stack `@jwt_required` (sets g.user_id = supabase id) above
`@require_permission(...)`. The decorator loads the internal user, their firm,
and their effective permission set, then enforces the required permission.
The Owner system role bypasses all checks.
"""
from functools import wraps
from flask import g, jsonify
from app.models.auth import User, Role


def _resolve_supabase_id():
    """Indirection over the JWT-provided supabase id so tests can monkeypatch it."""
    return getattr(g, 'user_id', None)


def load_firm_context():
    """Populate g.user, g.firm_id, g.permissions from the authenticated identity."""
    g.user = None
    g.firm_id = None
    g.permissions = set()

    supabase_id = _resolve_supabase_id()
    if not supabase_id:
        return

    user = User.query.filter_by(supabase_id=supabase_id).first()
    g.user = user
    if not user or not user.firm_id or not user.role_id:
        return

    g.firm_id = user.firm_id
    role = Role.query.get(user.role_id)
    if role is None:
        return
    if role.is_system and role.name == "Owner":
        from app.rbac.permissions import ALL_PERMISSIONS
        g.permissions = set(ALL_PERMISSIONS)
    else:
        g.permissions = set(role.permissions or [])


def has_permission(perm):
    return perm in getattr(g, 'permissions', set())


def require_permission(perm):
    """Decorator: 401 if no firm context, 403 if the permission is absent."""
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            load_firm_context()
            if g.user is None or g.firm_id is None:
                return jsonify({'error': 'No firm context'}), 401
            if perm not in g.permissions:
                return jsonify({'error': 'Permission denied', 'required': perm}), 403
            return f(*args, **kwargs)
        return wrapped
    return decorator
