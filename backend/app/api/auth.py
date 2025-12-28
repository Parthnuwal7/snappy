"""Authentication API endpoints - Supabase JWT Auth + multi-tenant support"""
from flask import Blueprint, request, jsonify, g, session
from backend.app.models.models import db
from backend.app.models.auth import User, FirmDetails, BankAccount
from backend.app.middleware.jwt_auth import jwt_required, jwt_optional
from datetime import datetime
from functools import wraps
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

bp = Blueprint('auth', __name__)

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per hour"],
    storage_uri="memory://"
)


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
        'bank': None
    }
    
    if user:
        response['profile'] = {
            'id': user.id,
            'device_id': getattr(user, 'device_id', None),
            'device_info': getattr(user, 'device_info', None),
            'is_onboarded': user.is_onboarded,
            'created_at': user.created_at.isoformat() if user.created_at else None,
            'updated_at': user.updated_at.isoformat() if user.updated_at else None,
        }
        
        if user.is_onboarded and user.firm_details:
            response['firm'] = user.firm_details.to_dict()
            
            # Get default bank account
            default_bank = BankAccount.query.filter_by(user_id=user.id, is_default=True).first()
            if default_bank:
                response['bank'] = default_bank.to_dict()
    
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
    
    data = request.get_json()
    
    # Validate required fields
    required_fields = ['firm_name', 'firm_address']
    for field in required_fields:
        if not data.get(field):
            return jsonify({'error': f'{field} is required'}), 400
    
    # Create firm details
    firm = FirmDetails(
        user_id=user.id,
        firm_name=data['firm_name'],
        firm_address=data['firm_address'],
        firm_email=data.get('firm_email'),
        firm_phone=data.get('firm_phone'),
        firm_phone_2=data.get('firm_phone_2'),
        firm_website=data.get('firm_website'),
        terms_and_conditions=data.get('terms_and_conditions'),
        billing_terms=data.get('billing_terms'),
        default_template=data.get('default_template', 'Simple'),
        invoice_prefix=data.get('invoice_prefix', 'INV'),
        default_tax_rate=float(data.get('default_tax_rate', 18.0)),
        currency=data.get('currency', 'INR'),
        show_due_date=data.get('show_due_date', True)
    )
    db.session.add(firm)
    
    # Create bank account if provided
    if data.get('bank_name') or data.get('account_number') or data.get('upi_id'):
        bank = BankAccount(
            user_id=user.id,
            bank_name=data.get('bank_name'),
            account_number=data.get('account_number'),
            account_holder_name=data.get('account_holder_name'),
            ifsc_code=data.get('ifsc_code'),
            upi_id=data.get('upi_id'),
            is_default=True
        )
        db.session.add(bank)
    
    user.is_onboarded = True
    db.session.commit()
    
    return jsonify({
        'message': 'Onboarding completed successfully',
        'firm': firm.to_dict()
    }), 201


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
                'upi_qr_path': bank.upi_qr_path
            })
        return jsonify(result)
    
    # UPDATE
    data = request.get_json()
    firm = user.firm_details
    
    # Update firm details fields
    firm_fields = [
        'firm_name', 'firm_address', 'firm_email', 'firm_phone', 'firm_phone_2',
        'firm_website', 'terms_and_conditions', 'billing_terms',
        'default_template', 'invoice_prefix', 'currency', 'logo_path', 'signature_path'
    ]
    
    for field in firm_fields:
        if field in data:
            setattr(firm, field, data[field])
    
    if 'default_tax_rate' in data:
        firm.default_tax_rate = float(data['default_tax_rate'])
    
    if 'show_due_date' in data:
        firm.show_due_date = bool(data['show_due_date'])
    
    # Update bank account fields
    bank_fields = ['bank_name', 'account_number', 'account_holder_name', 'ifsc_code', 'upi_id', 'upi_qr_path']
    bank_data = {k: data[k] for k in bank_fields if k in data}
    
    if bank_data:
        bank = BankAccount.query.filter_by(user_id=user.id, is_default=True).first()
        if not bank:
            bank = BankAccount(user_id=user.id, is_default=True)
            db.session.add(bank)
        
        for field, value in bank_data.items():
            setattr(bank, field, value)
    
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
            'upi_qr_path': bank.upi_qr_path
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
        # Create new bank account
        bank = BankAccount(
            user_id=user.id,
            bank_name=data.get('bank_name'),
            account_number=data.get('account_number'),
            account_holder_name=data.get('account_holder_name'),
            ifsc_code=data.get('ifsc_code'),
            upi_id=data.get('upi_id'),
            upi_qr_path=data.get('upi_qr_path'),
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
    
    for field in ['bank_name', 'account_number', 'account_holder_name', 'ifsc_code', 'upi_id', 'upi_qr_path']:
        if field in data:
            setattr(bank, field, data[field])
    
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
