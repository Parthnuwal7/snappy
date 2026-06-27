"""Firm invite lifecycle: create (+ email), accept, revoke.

An invite is a one-time token tying an email to a firm + role. Accepting it
attaches the accepting user to that firm with that role. Tokens are URL-safe
random strings; the raw token is only ever delivered by email, never serialized.

Delivery is Supabase-native: creating an invite triggers a Supabase "invite"
email so a brand-new person sets their own password, then is redirected to
`/accept-invite/<token>` to join the firm. For an address that already has an
account (Supabase can't re-invite it), we fall back to a plain Resend email
carrying the same accept link.
"""
import secrets
from datetime import datetime, timedelta

from app.models.models import db
from app.models.auth import FirmInvite, Firm, Role

DEFAULT_EXPIRY_DAYS = 7


class InviteError(Exception):
    """Raised when an invite cannot be created or accepted."""


def _accept_url(base_url, token):
    return f"{(base_url or '').rstrip('/')}/accept-invite/{token}"


def supabase_email_inviter(*, email, redirect_to):
    """Send a Supabase invite email (account setup + password), redirect to accept.

    Returns 'sent' for a fresh invite, or 'exists' when the address already has
    an account — that can't be re-invited, so the caller emails the accept link
    instead. Genuine failures (misconfig, provider down) raise InviteError.
    """
    from app.services.supabase_client import get_supabase_client
    client = get_supabase_client()
    try:
        client.auth.admin.invite_user_by_email(email, {"redirect_to": redirect_to})
        return 'sent'
    except Exception as e:  # SDK raises assorted auth errors; classify by message
        msg = str(e).lower()
        if any(s in msg for s in ('already', 'exist', 'registered')):
            return 'exists'
        raise InviteError(f'Could not send invitation email: {e}') from e


def create_invite(*, firm_id, email, role_id, invited_by,
                  expires_days=DEFAULT_EXPIRY_DAYS, base_url=None,
                  inviter=None, transport=None):
    """Create a pending invite and dispatch its email. Caller commits.

    `inviter(email=, redirect_to=) -> 'sent'|'exists'` sends the Supabase invite.
    `transport` is the Resend fallback used when the address already exists.
    Returns the FirmInvite (added + flushed).
    """
    email = (email or '').strip().lower()
    if not email:
        raise InviteError('Invite email is required')

    role = Role.query.filter_by(id=role_id, firm_id=firm_id).first()
    if not role:
        raise InviteError('Role not found for this firm')

    invite = FirmInvite(
        firm_id=firm_id,
        email=email,
        role_id=role_id,
        token=secrets.token_urlsafe(32),
        status='pending',
        invited_by=invited_by,
        expires_at=datetime.utcnow() + timedelta(days=expires_days),
    )
    db.session.add(invite)
    db.session.flush()

    redirect_to = _accept_url(base_url, invite.token)
    if inviter is not None:
        outcome = inviter(email=invite.email, redirect_to=redirect_to)
        # An existing account can't be Supabase-invited; mail them the link.
        if outcome == 'exists' and transport is not None:
            _send_invite_email(invite, role, transport, base_url)
    elif transport is not None:
        _send_invite_email(invite, role, transport, base_url)

    return invite


def _send_invite_email(invite, role, transport, base_url):
    firm = Firm.query.get(invite.firm_id)
    firm_name = firm.name if firm else 'a firm'
    link = _accept_url(base_url, invite.token)
    subject = f"You're invited to join {firm_name} on Snappy"
    body = (
        f"You've been invited to join {firm_name} as {role.name}.\n\n"
        f"Accept the invitation: {link}\n\n"
        f"This link expires on {invite.expires_at:%d %b %Y}."
    )
    transport.send(to=invite.email, subject=subject, body=body, from_name=firm_name)


def accept_invite(token, user):
    """Attach `user` to the invite's firm + role. Caller commits. Returns invite."""
    invite = FirmInvite.query.filter_by(token=token).first()
    if not invite:
        raise InviteError('Invalid invitation')
    if invite.status != 'pending':
        raise InviteError(f'Invitation is {invite.status}')
    if invite.expires_at and invite.expires_at < datetime.utcnow():
        invite.status = 'expired'
        raise InviteError('Invitation has expired')
    # The invite is bound to a specific address; a different signed-in account
    # must not consume it (e.g. a forwarded link).
    if user.email and invite.email and user.email.strip().lower() != invite.email:
        raise InviteError('This invitation was sent to a different email address')

    user.firm_id = invite.firm_id
    user.role_id = invite.role_id
    # Joining a firm completes onboarding — the invitee must not run the
    # firm-provisioning onboarding flow (that would create a second firm).
    user.is_onboarded = True
    invite.status = 'accepted'
    invite.accepted_at = datetime.utcnow()
    return invite


def revoke_invite(invite):
    """Mark a pending invite as revoked. Caller commits."""
    if invite.status == 'accepted':
        raise InviteError('Cannot revoke an accepted invitation')
    invite.status = 'revoked'
    return invite
