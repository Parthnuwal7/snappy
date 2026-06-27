"""Firm profile + member management API (firm-scoped, permission-gated).

Endpoints are mounted at /api/v1/firm. Every handler stacks @jwt_required
above @require_permission so the firm context is loaded and the caller's
permission enforced before any work happens.
"""
from flask import Blueprint, request, jsonify, g
from app.models.models import db
from app.models.auth import User, Firm, Role
from app.middleware.jwt_auth import jwt_required
from app.middleware.firm_context import require_permission
from app.rbac.permissions import MODULES

bp = Blueprint('firm', __name__)


def _owner_role_id(firm_id):
    role = Role.query.filter_by(firm_id=firm_id, name='Owner', is_system=True).first()
    return role.id if role else None


def _owner_count(firm_id, owner_role_id):
    return User.query.filter_by(firm_id=firm_id, role_id=owner_role_id).count()


def _member_dict(user):
    role = Role.query.get(user.role_id) if user.role_id else None
    return {
        'id': user.id,
        'email': user.email,
        'role_id': user.role_id,
        'role_name': role.name if role else None,
        'is_active': user.is_active,
        'created_at': user.created_at.isoformat() if user.created_at else None,
    }


@bp.route('/firm', methods=['GET'])
@jwt_required
@require_permission('firm_settings.read')
def get_firm():
    """Return the tenant firm record."""
    firm = Firm.query.get(g.firm_id)
    if not firm:
        return jsonify({'error': 'Firm not found'}), 404
    return jsonify(firm.to_dict())


@bp.route('/firm', methods=['PATCH'])
@jwt_required
@require_permission('firm_settings.update')
def update_firm():
    """Rename the tenant firm."""
    firm = Firm.query.get(g.firm_id)
    if not firm:
        return jsonify({'error': 'Firm not found'}), 404
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'error': 'Firm name is required'}), 400
    firm.name = name
    db.session.commit()
    return jsonify(firm.to_dict())


@bp.route('/firm/members', methods=['GET'])
@jwt_required
@require_permission('members.read')
def list_members():
    """List every user belonging to the current firm with their role."""
    members = User.query.filter_by(firm_id=g.firm_id).order_by(User.created_at).all()
    return jsonify([_member_dict(m) for m in members])


@bp.route('/firm/members/<int:user_id>', methods=['PATCH'])
@jwt_required
@require_permission('members.manage_roles')
def change_member_role(user_id):
    """Reassign a member's role. Blocks demoting the firm's last Owner."""
    member = User.query.filter_by(id=user_id, firm_id=g.firm_id).first()
    if not member:
        return jsonify({'error': 'Member not found'}), 404

    data = request.get_json() or {}
    new_role_id = data.get('role_id')
    new_role = Role.query.filter_by(id=new_role_id, firm_id=g.firm_id).first()
    if not new_role:
        return jsonify({'error': 'Role not found'}), 400

    owner_role_id = _owner_role_id(g.firm_id)
    # Guard: never leave the firm without an Owner.
    if member.role_id == owner_role_id and new_role.id != owner_role_id:
        if _owner_count(g.firm_id, owner_role_id) <= 1:
            return jsonify({'error': 'Cannot demote the last Owner'}), 409

    member.role_id = new_role.id
    db.session.commit()
    return jsonify(_member_dict(member))


@bp.route('/firm/members/<int:user_id>', methods=['DELETE'])
@jwt_required
@require_permission('members.remove')
def remove_member(user_id):
    """Detach a member from the firm. Blocks removing the last Owner."""
    member = User.query.filter_by(id=user_id, firm_id=g.firm_id).first()
    if not member:
        return jsonify({'error': 'Member not found'}), 404

    owner_role_id = _owner_role_id(g.firm_id)
    if member.role_id == owner_role_id and _owner_count(g.firm_id, owner_role_id) <= 1:
        return jsonify({'error': 'Cannot remove the last Owner'}), 409

    member.firm_id = None
    member.role_id = None
    db.session.commit()
    return jsonify({'message': 'Member removed'})


@bp.route('/firm/permissions/catalog', methods=['GET'])
@jwt_required
@require_permission('roles.read')
def permissions_catalog():
    """Expose the code-defined module x action catalog for the Roles editor."""
    return jsonify({'modules': MODULES})
