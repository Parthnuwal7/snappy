"""Invite API: firm admins create/list/revoke; joiners accept.

Management endpoints (/firm/invites) are firm-scoped + permission-gated.
The accept endpoint (/invites/accept) is authenticated but firm-agnostic —
the accepting user has a Supabase identity but no firm yet.
"""
from flask import Blueprint, request, jsonify, g
from app.models.models import db
from app.models.auth import User, FirmInvite
from app.middleware.jwt_auth import jwt_required
from app.middleware.firm_context import require_permission
from app.services import invite_service
from app.services.email_service import get_transport

bp = Blueprint('invites', __name__)


@bp.route('/firm/invites', methods=['GET'])
@jwt_required
@require_permission('members.read')
def list_invites():
    invites = (FirmInvite.query.filter_by(firm_id=g.firm_id)
               .order_by(FirmInvite.created_at.desc()).all())
    return jsonify([i.to_dict() for i in invites])


@bp.route('/firm/invites', methods=['POST'])
@jwt_required
@require_permission('members.invite')
def create_invite():
    data = request.get_json() or {}
    email = data.get('email')
    role_id = data.get('role_id')
    if not email or not role_id:
        return jsonify({'error': 'email and role_id are required'}), 400

    base_url = data.get('base_url') or request.host_url.rstrip('/')
    try:
        invite = invite_service.create_invite(
            firm_id=g.firm_id, email=email, role_id=role_id,
            invited_by=g.user.id, base_url=base_url,
            inviter=invite_service.supabase_email_inviter,
            transport=get_transport())
        db.session.commit()
    except invite_service.InviteError as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

    return jsonify(invite.to_dict()), 201


@bp.route('/firm/invites/<int:invite_id>', methods=['DELETE'])
@jwt_required
@require_permission('members.invite')
def revoke_invite(invite_id):
    invite = FirmInvite.query.filter_by(id=invite_id, firm_id=g.firm_id).first()
    if not invite:
        return jsonify({'error': 'Invite not found'}), 404
    try:
        invite_service.revoke_invite(invite)
        db.session.commit()
    except invite_service.InviteError as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 409
    return jsonify(invite.to_dict())


@bp.route('/invites/accept', methods=['POST'])
@jwt_required
def accept_invite():
    """Attach the authenticated (firm-less) user to an invite's firm + role.

    A Supabase-invited user is freshly authenticated and may not have a local
    `users` row yet (that's normally created by /auth/device on sign-in). Create
    it on the fly so accepting works the moment the session is established.
    """
    user = User.query.filter_by(supabase_id=g.user_id).first()
    if not user:
        user = User(supabase_id=g.user_id, email=g.user_email,
                    is_active=True, is_onboarded=False)
        db.session.add(user)
        db.session.flush()

    data = request.get_json() or {}
    token = data.get('token')
    if not token:
        return jsonify({'error': 'token is required'}), 400

    try:
        invite = invite_service.accept_invite(token, user)
        db.session.commit()
    except invite_service.InviteError as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

    return jsonify({'firm_id': user.firm_id, 'role_id': user.role_id,
                    'invite': invite.to_dict()})


@bp.route('/invites/accept-pending', methods=['POST'])
@jwt_required
def accept_pending():
    """Attach the authenticated firm-less user to their newest pending invite.

    Used when a person whose email was invited signs up directly instead of
    clicking the email link — we auto-route them into the firm rather than let
    them provision a duplicate.
    """
    user = User.query.filter_by(supabase_id=g.user_id).first()
    if not user:
        user = User(supabase_id=g.user_id, email=g.user_email,
                    is_active=True, is_onboarded=False)
        db.session.add(user)
        db.session.flush()

    try:
        invite = invite_service.accept_pending_invite(user)
        db.session.commit()
    except invite_service.InviteError as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

    return jsonify({'firm_id': user.firm_id, 'role_id': user.role_id,
                    'invite': invite.to_dict()})
