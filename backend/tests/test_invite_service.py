"""Tests for the firm invite lifecycle service."""
from datetime import datetime, timedelta
import pytest

from app.models.models import db
from app.models.auth import User, Role, FirmInvite
from app.services.firm_service import provision_firm_for_user
from app.services import invite_service


class FakeTransport:
    def __init__(self):
        self.sent = None

    def send(self, **kwargs):
        self.sent = kwargs
        return {'id': 'fake'}


def _firm(app):
    with app.app_context():
        owner = User(supabase_id='sb-o', email='o@firm.com')
        db.session.add(owner)
        db.session.commit()
        firm = provision_firm_for_user(owner, 'Acme')
        staff = Role.query.filter_by(firm_id=firm.id, name='Staff').first()
        return firm.id, owner.id, staff.id


def test_create_invite_generates_token_and_pending(app):
    firm_id, owner_id, staff_id = _firm(app)
    with app.app_context():
        inv = invite_service.create_invite(
            firm_id=firm_id, email='new@firm.com', role_id=staff_id,
            invited_by=owner_id)
        db.session.commit()
        assert inv.token and len(inv.token) >= 32
        assert inv.status == 'pending'
        assert inv.expires_at > datetime.utcnow()


def test_create_invite_calls_supabase_inviter_with_accept_link(app):
    firm_id, owner_id, staff_id = _firm(app)
    with app.app_context():
        calls = {}

        def fake_inviter(*, email, redirect_to):
            calls['email'] = email
            calls['redirect_to'] = redirect_to
            return 'sent'

        invite_service.create_invite(
            firm_id=firm_id, email='New@Firm.com', role_id=staff_id,
            invited_by=owner_id, inviter=fake_inviter, base_url='https://app')
        assert calls['email'] == 'new@firm.com'
        assert '/accept-invite/' in calls['redirect_to']


def test_existing_account_falls_back_to_email(app):
    # When Supabase reports the address already exists, we email the accept link.
    firm_id, owner_id, staff_id = _firm(app)
    with app.app_context():
        transport = FakeTransport()
        invite_service.create_invite(
            firm_id=firm_id, email='dup@firm.com', role_id=staff_id,
            invited_by=owner_id, base_url='https://app',
            inviter=lambda **kw: 'exists', transport=transport)
        assert transport.sent['to'] == 'dup@firm.com'
        assert '/accept-invite/' in transport.sent['body']


def test_accept_invite_rejects_email_mismatch(app):
    firm_id, owner_id, staff_id = _firm(app)
    with app.app_context():
        inv = invite_service.create_invite(
            firm_id=firm_id, email='intended@firm.com', role_id=staff_id,
            invited_by=owner_id)
        db.session.commit()
        token = inv.token
        intruder = User(supabase_id='sb-x', email='someone.else@firm.com')
        db.session.add(intruder)
        db.session.commit()
        with pytest.raises(invite_service.InviteError):
            invite_service.accept_invite(token, intruder)


def test_accept_invite_assigns_firm_and_role(app):
    firm_id, owner_id, staff_id = _firm(app)
    with app.app_context():
        inv = invite_service.create_invite(
            firm_id=firm_id, email='new@firm.com', role_id=staff_id,
            invited_by=owner_id)
        db.session.commit()
        token = inv.token

        joiner = User(supabase_id='sb-new', email='new@firm.com')
        db.session.add(joiner)
        db.session.commit()

        result = invite_service.accept_invite(token, joiner)
        db.session.commit()
        assert joiner.firm_id == firm_id
        assert joiner.role_id == staff_id
        assert joiner.is_onboarded is True
        assert result.status == 'accepted'
        assert result.accepted_at is not None


def test_accept_invite_rejects_unknown_token(app):
    _firm(app)
    with app.app_context():
        joiner = User(supabase_id='sb-new', email='new@firm.com')
        db.session.add(joiner)
        db.session.commit()
        with pytest.raises(invite_service.InviteError):
            invite_service.accept_invite('nope', joiner)


def test_accept_invite_rejects_expired(app):
    firm_id, owner_id, staff_id = _firm(app)
    with app.app_context():
        inv = invite_service.create_invite(
            firm_id=firm_id, email='new@firm.com', role_id=staff_id,
            invited_by=owner_id)
        inv.expires_at = datetime.utcnow() - timedelta(days=1)
        db.session.commit()
        token = inv.token

        joiner = User(supabase_id='sb-new', email='new@firm.com')
        db.session.add(joiner)
        db.session.commit()
        with pytest.raises(invite_service.InviteError):
            invite_service.accept_invite(token, joiner)


def test_accept_invite_rejects_already_accepted(app):
    firm_id, owner_id, staff_id = _firm(app)
    with app.app_context():
        inv = invite_service.create_invite(
            firm_id=firm_id, email='new@firm.com', role_id=staff_id,
            invited_by=owner_id)
        db.session.commit()
        token = inv.token
        joiner = User(supabase_id='sb-new', email='new@firm.com')
        db.session.add(joiner)
        db.session.commit()
        invite_service.accept_invite(token, joiner)
        db.session.commit()

        other = User(supabase_id='sb-2', email='other@firm.com')
        db.session.add(other)
        db.session.commit()
        with pytest.raises(invite_service.InviteError):
            invite_service.accept_invite(token, other)


def test_revoke_invite_sets_status(app):
    firm_id, owner_id, staff_id = _firm(app)
    with app.app_context():
        inv = invite_service.create_invite(
            firm_id=firm_id, email='new@firm.com', role_id=staff_id,
            invited_by=owner_id)
        db.session.commit()
        invite_service.revoke_invite(inv)
        db.session.commit()
        assert inv.status == 'revoked'


def test_accept_revoked_invite_fails(app):
    firm_id, owner_id, staff_id = _firm(app)
    with app.app_context():
        inv = invite_service.create_invite(
            firm_id=firm_id, email='new@firm.com', role_id=staff_id,
            invited_by=owner_id)
        db.session.commit()
        token = inv.token
        invite_service.revoke_invite(inv)
        db.session.commit()
        joiner = User(supabase_id='sb-new', email='new@firm.com')
        db.session.add(joiner)
        db.session.commit()
        with pytest.raises(invite_service.InviteError):
            invite_service.accept_invite(token, joiner)
