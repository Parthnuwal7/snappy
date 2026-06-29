"""Authentication API endpoints - Supabase JWT Auth + multi-tenant support"""
from flask import Blueprint, request, jsonify, g, session
from app.models.models import db
from app.models.auth import User, FirmDetails, BankAccount, Role, Firm, FirmInvite
from app.middleware.jwt_auth import jwt_required, jwt_optional
from app.services.firm_service import provision_firm_for_user
from app.services import invite_service
from app.rbac.permissions import ALL_PERMISSIONS
from datetime import datetime
from functools import wraps
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

bp = Blueprint('auth', __name__)


def _membership_for(user):
    """The caller's firm + role + effective permissions, or None if firm-less.

    Mirrors load_firm_context: the Owner system role resolves to ALL_PERMISSIONS
    so the catalog is the single source of truth for owner capability.
    """
    if not user.firm_id or not user.role_id:
        return None
    role = Role.query.get(user.role_id)
    if not role:
        return None
    if role.is_system and role.name == 'Owner':
        permissions = sorted(ALL_PERMISSIONS)
    else:
        permissions = sorted(role.permissions or [])
    return {
        'firm_id': user.firm_id,
        'role': {'id': role.id, 'name': role.name, 'is_system': role.is_system},
        'permissions': permissions,
    }

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per hour"],
    storage_uri="memory://"
)


def _bank_upi_error(upi_id, payee_name):
    """Return an error message when UPI identity is incomplete, else None."""
    if not (upi_id or '').strip() or not (payee_name or '').strip():
        return 'UPI ID and UPI payee name are required'
    return None


@bp.route('/me', methods=['GET'])
@jwt_required
def get_current_user():
    """Get current logged in user's profile and firm details"""
    user_id = g.user_id  # Set by jwt_required decorator
    
    # Get user from database
    user = User.query.filter_by(supabase_id=user_id).first()
    
    response = {
        'user': {
            'id': user_id,
            'email': g.user_email,
        },
        'profile': None,
        'firm': None,
        'bank': None,
        'membership': None,
        'pending_invite': None,
        'setup': None,
    }

    if user:
        response['profile'] = {
            'id': user.id,
            'device_id': getattr(user, 'device_id', None),
            'device_info': getattr(user, 'device_info', None),
            'is_onboarded': user.is_onboarded,
            'full_name': user.full_name,
            'designation': user.designation,
            'bar_council_number': user.bar_council_number,
            'personal_phone': user.personal_phone,
            'is_solo': user.is_solo,
            'checklist_dismissed': bool(user.checklist_dismissed),
            'created_at': user.created_at.isoformat() if user.created_at else None,
            'updated_at': user.updated_at.isoformat() if user.updated_at else None,
        }

        response['membership'] = _membership_for(user)

        if user.is_onboarded and user.firm_details:
            response['firm'] = user.firm_details.to_dict()

            # Get default bank account
            default_bank = BankAccount.query.filter_by(user_id=user.id, is_default=True).first()
            if default_bank:
                response['bank'] = default_bank.to_dict()

    # Pending-invite surfacing: a firm-less user whose email was invited.
    if user and not user.firm_id:
        pend = invite_service.pending_invite_for(g.user_email)
        if pend:
            firm = Firm.query.get(pend.firm_id)
            role = Role.query.get(pend.role_id)
            response['pending_invite'] = {
                'firm_name': firm.name if firm else None,
                'role_name': role.name if role else None,
            }

    # Derived setup checklist state (only meaningful once in a firm).
    if user and user.firm_id:
        fd = user.firm_details
        has_bank = BankAccount.query.filter_by(firm_id=user.firm_id).count() > 0
        has_branding = bool(fd and (fd.logo_path or fd.signature_path))
        has_billing = bool(fd and fd.billing_terms)
        has_team = FirmInvite.query.filter_by(firm_id=user.firm_id).count() > 0
        response['setup'] = {
            'bank': has_bank,
            'branding': has_branding,
            'billing': has_billing,
            'team': has_team,
            'dismissed': bool(user.checklist_dismissed),
            'complete': all([has_bank, has_branding, has_billing, has_team]),
        }

    return jsonify(response)


@bp.route('/device', methods=['POST'])
@jwt_required
def update_device_info():
    """Update device info for the current user"""
    user_id = g.user_id
    data = request.get_json()
    
    # Find or create user profile
    user = User.query.filter_by(supabase_id=user_id).first()
    
    if not user:
        # Create a new user profile linked to Supabase user
        user = User(
            supabase_id=user_id,
            email=g.user_email,
            is_active=True,
            is_onboarded=False
        )
        db.session.add(user)
    
    # Update device info
    user.device_id = data.get('device_id')
    if hasattr(user, 'set_device_info'):
        user.set_device_info(data.get('device_info'))
    else:
        user.device_info = data.get('device_info')
    
    user.last_login = datetime.utcnow()
    db.session.commit()
    
    return jsonify({'message': 'Device info updated'})


@bp.route('/onboard', methods=['POST'])
@jwt_required
def onboard():
    """Complete user onboarding with firm details"""
    user_id = g.user_id
    
    # Find or create user profile
    user = User.query.filter_by(supabase_id=user_id).first()
    
    if not user:
        user = User(
            supabase_id=user_id,
            email=g.user_email,
            is_active=True,
            is_onboarded=False
        )
        db.session.add(user)
        db.session.flush()  # Get the user ID
    
    if user.is_onboarded:
        return jsonify({'error': 'User already onboarded'}), 400

    data = request.get_json() or {}

    # Minimal gate: identify the person and name the firm. Everything else
    # (banking, branding, billing, address) is deferred to the Home checklist.
    if not data.get('full_name'):
        return jsonify({'error': 'full_name is required'}), 400
    if not data.get('firm_name'):
        return jsonify({'error': 'firm_name is required'}), 400

    # Personal/professional profile.
    user.full_name = data['full_name']
    user.designation = data.get('designation')
    user.bar_council_number = data.get('bar_council_number')
    user.personal_phone = data.get('personal_phone')
    user.is_solo = bool(data.get('is_solo', False))

    # Provision the firm tenant + seeded roles, making this user its Owner.
    # Idempotent guard: only provision if the user isn't already in a firm.
    if not user.firm_id:
        provision_firm_for_user(user, data['firm_name'])

    # Minimal firm profile — address/branding/billing land later via the checklist.
    firm = FirmDetails(
        user_id=user.id,
        firm_id=user.firm_id,
        firm_name=data['firm_name'],
        firm_address=data.get('firm_address'),
    )
    db.session.add(firm)

    user.is_onboarded = True
    db.session.commit()

    return jsonify({
        'message': 'Onboarding completed successfully',
        'firm': firm.to_dict()
    }), 201


@bp.route('/profile', methods=['PATCH'])
@jwt_required
def update_profile():
    """Update the caller's personal/professional profile fields."""
    user = User.query.filter_by(supabase_id=g.user_id).first()
    if not user:
        user = User(supabase_id=g.user_id, email=g.user_email,
                    is_active=True, is_onboarded=False)
        db.session.add(user)
        db.session.flush()

    data = request.get_json() or {}
    for field in ('full_name', 'designation', 'bar_council_number', 'personal_phone'):
        if field in data:
            setattr(user, field, data[field])

    db.session.commit()
    return jsonify({'profile': {
        'full_name': user.full_name,
        'designation': user.designation,
        'bar_council_number': user.bar_council_number,
        'personal_phone': user.personal_phone,
    }})


@bp.route('/dismiss-checklist', methods=['POST'])
@jwt_required
def dismiss_checklist():
    """Hide the Home 'Finish setting up' checklist for this user."""
    user = User.query.filter_by(supabase_id=g.user_id).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    user.checklist_dismissed = True
    db.session.commit()
    return jsonify({'checklist_dismissed': True})


@bp.route('/firm', methods=['GET', 'PUT'])
@jwt_required
def manage_firm():
    """Get or update firm details"""
    user_id = g.user_id
    user = User.query.filter_by(supabase_id=user_id).first()
    
    if not user or not user.firm_details:
        return jsonify({'error': 'Firm not found'}), 404
    
    if request.method == 'GET':
        result = user.firm_details.to_dict()
        # Include bank account if exists
        bank = BankAccount.query.filter_by(user_id=user.id, is_default=True).first()
        if bank:
            result.update({
                'bank_name': bank.bank_name,
                'account_number': bank.account_number,
                'account_holder_name': bank.account_holder_name,
                'ifsc_code': bank.ifsc_code,
                'upi_id': bank.upi_id,
                'upi_payee_name': bank.upi_payee_name,
                'upi_note': bank.upi_note
            })
        return jsonify(result)
    
    # UPDATE
    data = request.get_json()
    firm = user.firm_details
    
    # Update firm details fields
    firm_fields = [
        'firm_name', 'firm_address', 'firm_email', 'firm_phone', 'firm_phone_2',
        'firm_website', 'terms_and_conditions', 'billing_terms',
        'email_subject_template', 'email_body_template', 'whatsapp_template',
        'default_template', 'invoice_prefix', 'currency', 'logo_path', 'signature_path'
    ]
    
    for field in firm_fields:
        if field in data:
            setattr(firm, field, data[field])
    
    if 'default_tax_rate' in data:
        firm.default_tax_rate = float(data['default_tax_rate'])
    
    if 'show_due_date' in data:
        firm.show_due_date = bool(data['show_due_date'])
    
    if 'use_invoice_prefix' in data:
        firm.use_invoice_prefix = bool(data['use_invoice_prefix'])
    
    # Update bank account fields
    bank_fields = ['bank_name', 'account_number', 'account_holder_name', 'ifsc_code', 'upi_id', 'upi_payee_name', 'upi_note']
    bank_data = {k: data[k] for k in bank_fields if k in data}
    
    if bank_data:
        bank = BankAccount.query.filter_by(user_id=user.id, is_default=True).first()
        if not bank:
            bank = BankAccount(user_id=user.id, is_default=True)
            db.session.add(bank)

        for field, value in bank_data.items():
            setattr(bank, field, value)

        err = _bank_upi_error(bank.upi_id, bank.upi_payee_name)
        if err:
            db.session.rollback()
            return jsonify({'error': err}), 400

    db.session.commit()
    
    # Return combined response
    result = firm.to_dict()
    bank = BankAccount.query.filter_by(user_id=user.id, is_default=True).first()
    if bank:
        result.update({
            'bank_name': bank.bank_name,
            'account_number': bank.account_number,
            'account_holder_name': bank.account_holder_name,
            'ifsc_code': bank.ifsc_code,
            'upi_id': bank.upi_id,
            'upi_payee_name': bank.upi_payee_name,
            'upi_note': bank.upi_note
        })

    return jsonify({'firm': result})


@bp.route('/firm/core', methods=['PUT'])
@jwt_required
def update_firm_core():
    """Update core firm details (name, logo, address, contacts)"""
    user_id = g.user_id
    user = User.query.filter_by(supabase_id=user_id).first()
    
    if not user or not user.firm_details:
        return jsonify({'error': 'Firm not found'}), 404
    
    data = request.get_json()
    firm = user.firm_details
    
    if 'firm_name' in data:
        firm.firm_name = data['firm_name']
    if 'firm_address' in data:
        firm.firm_address = data['firm_address']
    if 'firm_phone' in data:
        firm.firm_phone = data['firm_phone']
    if 'firm_phone_2' in data:
        firm.firm_phone_2 = data['firm_phone_2']
    
    db.session.commit()
    
    return jsonify(firm.to_dict())


@bp.route('/bank', methods=['GET', 'POST', 'PUT'])
@jwt_required
def manage_bank():
    """Manage bank account details"""
    user_id = g.user_id
    user = User.query.filter_by(supabase_id=user_id).first()
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    if request.method == 'GET':
        banks = BankAccount.query.filter_by(user_id=user.id).all()
        return jsonify([b.to_dict() for b in banks])
    
    data = request.get_json()
    
    if request.method == 'POST':
        err = _bank_upi_error(data.get('upi_id'), data.get('upi_payee_name'))
        if err:
            return jsonify({'error': err}), 400
        # Create new bank account
        bank = BankAccount(
            user_id=user.id,
            bank_name=data.get('bank_name'),
            account_number=data.get('account_number'),
            account_holder_name=data.get('account_holder_name'),
            ifsc_code=data.get('ifsc_code'),
            upi_id=data.get('upi_id'),
            upi_payee_name=data.get('upi_payee_name'),
            upi_note=data.get('upi_note'),
            is_default=data.get('is_default', False)
        )

        # If this is the first bank or marked as default, make it default
        existing = BankAccount.query.filter_by(user_id=user.id).count()
        if existing == 0 or data.get('is_default'):
            # Unset other defaults
            BankAccount.query.filter_by(user_id=user.id).update({'is_default': False})
            bank.is_default = True
        
        db.session.add(bank)
        db.session.commit()
        
        return jsonify(bank.to_dict()), 201
    
    # PUT - update default bank
    bank = BankAccount.query.filter_by(user_id=user.id, is_default=True).first()
    if not bank:
        bank = BankAccount(user_id=user.id, is_default=True)
        db.session.add(bank)
    
    for field in ['bank_name', 'account_number', 'account_holder_name', 'ifsc_code', 'upi_id', 'upi_payee_name', 'upi_note']:
        if field in data:
            setattr(bank, field, data[field])

    err = _bank_upi_error(bank.upi_id, bank.upi_payee_name)
    if err:
        db.session.rollback()
        return jsonify({'error': err}), 400

    db.session.commit()
    return jsonify(bank.to_dict())


# =====================
# Legacy Session-Based Auth (deprecated)
# =====================

def login_required_legacy(f):
    """Legacy decorator for session-based auth"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function


@bp.route('/register', methods=['POST'])
@limiter.limit("7 per hour")
def register():
    """Legacy register - redirects to use Supabase Auth"""
    return jsonify({
        'error': 'Direct registration is disabled. Please use Supabase Auth.',
        'message': 'Use the frontend registration form which connects to Supabase.'
    }), 400


@bp.route('/login', methods=['POST'])
@limiter.limit("5 per minute")
def login():
    """Legacy login - redirects to use Supabase Auth"""
    return jsonify({
        'error': 'Direct login is disabled. Please use Supabase Auth.',
        'message': 'Use the frontend login form which connects to Supabase.'
    }), 400


@bp.route('/logout', methods=['POST'])
def logout():
    """Legacy logout - clears any session data"""
    session.pop('user_id', None)
    return jsonify({'message': 'Logout successful'})
