"""Roles CRUD API — firm-owned bundles of permission keys (module x action grid).

Mounted at /api/v1/firm/roles. Reads require roles.read; mutations require
roles.manage. The Owner system role is immutable and undeletable. Permission
keys are validated against the code-defined catalog so a role can never carry
a key the app doesn't enforce.
"""
from flask import Blueprint, request, jsonify, g
from sqlalchemy.exc import IntegrityError
from app.models.models import db
from app.models.auth import Role, User
from app.middleware.jwt_auth import jwt_required
from app.middleware.firm_context import require_permission
from app.rbac.permissions import ALL_PERMISSIONS

bp = Blueprint('roles', __name__)


def _validate_permissions(raw):
    """Return (perms, error). Permissions must be a list of known catalog keys."""
    if raw is None:
        return [], None
    if not isinstance(raw, list):
        return None, 'permissions must be a list'
    unknown = sorted(set(raw) - ALL_PERMISSIONS)
    if unknown:
        return None, f'Unknown permissions: {", ".join(unknown)}'
    return sorted(set(raw)), None


@bp.route('/firm/roles', methods=['GET'])
@jwt_required
@require_permission('roles.read')
def list_roles():
    roles = Role.query.filter_by(firm_id=g.firm_id).order_by(Role.name).all()
    return jsonify([r.to_dict() for r in roles])


@bp.route('/firm/roles', methods=['POST'])
@jwt_required
@require_permission('roles.manage')
def create_role():
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'error': 'Role name is required'}), 400

    perms, err = _validate_permissions(data.get('permissions'))
    if err:
        return jsonify({'error': err}), 400

    if Role.query.filter_by(firm_id=g.firm_id, name=name).first():
        return jsonify({'error': 'A role with that name already exists'}), 409

    role = Role(firm_id=g.firm_id, name=name,
                description=data.get('description'),
                permissions=perms, is_system=False)
    db.session.add(role)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({'error': 'A role with that name already exists'}), 409
    return jsonify(role.to_dict()), 201


@bp.route('/firm/roles/<int:role_id>', methods=['PATCH'])
@jwt_required
@require_permission('roles.manage')
def update_role(role_id):
    role = Role.query.filter_by(id=role_id, firm_id=g.firm_id).first()
    if not role:
        return jsonify({'error': 'Role not found'}), 404
    if role.is_system:
        return jsonify({'error': 'The Owner role cannot be modified'}), 403

    data = request.get_json() or {}
    if 'name' in data:
        name = (data.get('name') or '').strip()
        if not name:
            return jsonify({'error': 'Role name is required'}), 400
        clash = Role.query.filter_by(firm_id=g.firm_id, name=name).first()
        if clash and clash.id != role.id:
            return jsonify({'error': 'A role with that name already exists'}), 409
        role.name = name
    if 'description' in data:
        role.description = data.get('description')
    if 'permissions' in data:
        perms, err = _validate_permissions(data.get('permissions'))
        if err:
            return jsonify({'error': err}), 400
        role.permissions = perms

    db.session.commit()
    return jsonify(role.to_dict())


@bp.route('/firm/roles/<int:role_id>', methods=['DELETE'])
@jwt_required
@require_permission('roles.manage')
def delete_role(role_id):
    role = Role.query.filter_by(id=role_id, firm_id=g.firm_id).first()
    if not role:
        return jsonify({'error': 'Role not found'}), 404
    if role.is_system:
        return jsonify({'error': 'The Owner role cannot be deleted'}), 403

    in_use = User.query.filter_by(firm_id=g.firm_id, role_id=role.id).count()
    if in_use:
        return jsonify({'error': 'Cannot delete a role assigned to members',
                        'members': in_use}), 409

    db.session.delete(role)
    db.session.commit()
    return jsonify({'message': 'Role deleted'})
