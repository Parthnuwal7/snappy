"""Authentication API endpoints"""
from flask import Blueprint, request, jsonify, session, current_app
from backend.app.models.models import db
from backend.app.models.auth import User, Firm, ProductKey
from datetime import datetime, timedelta
from functools import wraps

bp = Blueprint('auth', __name__)


def login_required(f):
    """Decorator to require login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            # Don't log 401s in development - they're expected when checking auth status
            if current_app.debug:
                pass  # Silent in debug mode
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function


@bp.route('/register', methods=['POST'])
def register():
    """Register new user"""
    data = request.get_json()
    
    # Validate required fields
    if not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Email and password are required'}), 400
    
    # Product key is MANDATORY
    product_key = data.get('product_key')
    if not product_key:
        return jsonify({'error': 'Product key is required'}), 400
    
    # Check if user already exists
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already registered'}), 400
    
    # Validate product key
    key_obj = ProductKey.query.filter_by(key=product_key, is_used=False).first()
    if not key_obj:
        return jsonify({'error': 'Invalid or already used product key'}), 400
    
    # Check if key is expired
    if key_obj.expires_at and key_obj.expires_at < datetime.utcnow():
        return jsonify({'error': 'Product key has expired'}), 400
    
    # Create user
    user = User(email=data['email'])
    user.set_password(data['password'])
    
    db.session.add(user)
    db.session.commit()
    
    # Mark product key as used
    key_obj.is_used = True
    key_obj.user_id = user.id
    key_obj.activated_at = datetime.utcnow()
    db.session.commit()
    
    # Automatically log in the user after registration
    session['user_id'] = user.id
    user.last_login = datetime.utcnow()
    db.session.commit()
    
    return jsonify({
        'message': 'Registration successful',
        'user': user.to_dict()
    }), 201


@bp.route('/login', methods=['POST'])
def login():
    """Login user"""
    data = request.get_json()
    
    if not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Email and password are required'}), 400
    
    user = User.query.filter_by(email=data['email']).first()
    
    if not user or not user.check_password(data['password']):
        return jsonify({'error': 'Invalid email or password'}), 401
    
    if not user.is_active:
        return jsonify({'error': 'Account is disabled'}), 403
    
    # Update last login
    user.last_login = datetime.utcnow()
    db.session.commit()
    
    # Set session
    session['user_id'] = user.id
    
    return jsonify({
        'message': 'Login successful',
        'user': user.to_dict()
    })


@bp.route('/logout', methods=['POST'])
@login_required
def logout():
    """Logout user"""
    session.pop('user_id', None)
    return jsonify({'message': 'Logout successful'})


@bp.route('/me', methods=['GET'])
@login_required
def get_current_user():
    """Get current logged in user"""
    user = User.query.get(session['user_id'])
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    response = {
        'user': user.to_dict()
    }
    
    # Include firm details if onboarded
    if user.is_onboarded and user.firm:
        response['firm'] = user.firm.to_dict()
    
    return jsonify(response)


@bp.route('/onboard', methods=['POST'])
@login_required
def onboard():
    """Complete user onboarding with firm details"""
    user = User.query.get(session['user_id'])
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    if user.is_onboarded:
        return jsonify({'error': 'User already onboarded'}), 400
    
    data = request.get_json()
    
    # Validate required fields
    required_fields = ['firm_name', 'firm_address']
    for field in required_fields:
        if not data.get(field):
            return jsonify({'error': f'{field} is required'}), 400
    
    # Create firm
    firm = Firm(
        user_id=user.id,
        firm_name=data['firm_name'],
        firm_address=data['firm_address'],
        firm_email=data.get('firm_email'),
        firm_phone=data.get('firm_phone'),
        firm_phone_2=data.get('firm_phone_2'),
        firm_website=data.get('firm_website'),
        bank_name=data.get('bank_name'),
        account_number=data.get('account_number'),
        account_holder_name=data.get('account_holder_name'),
        ifsc_code=data.get('ifsc_code'),
        upi_id=data.get('upi_id'),
        terms_and_conditions=data.get('terms_and_conditions'),
        billing_terms=data.get('billing_terms'),
        default_template=data.get('default_template', 'LAW_001'),
        invoice_prefix=data.get('invoice_prefix', 'LAW'),
        default_tax_rate=float(data.get('default_tax_rate', 18.0)),
        currency=data.get('currency', 'INR')
    )
    
    db.session.add(firm)
    user.is_onboarded = True
    db.session.commit()
    
    return jsonify({
        'message': 'Onboarding completed successfully',
        'firm': firm.to_dict()
    }), 201


@bp.route('/firm', methods=['GET', 'PUT'])
@login_required
def manage_firm():
    """Get or update firm details"""
    user = User.query.get(session['user_id'])
    if not user or not user.firm:
        return jsonify({'error': 'Firm not found'}), 404
    
    if request.method == 'GET':
        return jsonify(user.firm.to_dict())
    
    # UPDATE
    data = request.get_json()
    firm = user.firm
    
    # Update all allowed fields
    if 'firm_name' in data:
        firm.firm_name = data['firm_name']
    if 'firm_address' in data:
        firm.firm_address = data['firm_address']
    if 'firm_email' in data:
        firm.firm_email = data['firm_email']
    if 'firm_phone' in data:
        firm.firm_phone = data['firm_phone']
    if 'firm_phone_2' in data:
        firm.firm_phone_2 = data['firm_phone_2']
    if 'firm_website' in data:
        firm.firm_website = data['firm_website']
    if 'bank_name' in data:
        firm.bank_name = data['bank_name']
    if 'account_number' in data:
        firm.account_number = data['account_number']
    if 'account_holder_name' in data:
        firm.account_holder_name = data['account_holder_name']
    if 'ifsc_code' in data:
        firm.ifsc_code = data['ifsc_code']
    if 'upi_id' in data:
        firm.upi_id = data['upi_id']
    if 'terms_and_conditions' in data:
        firm.terms_and_conditions = data['terms_and_conditions']
    if 'billing_terms' in data:
        firm.billing_terms = data['billing_terms']
    if 'default_template' in data:
        firm.default_template = data['default_template']
    if 'invoice_prefix' in data:
        firm.invoice_prefix = data['invoice_prefix']
    if 'default_tax_rate' in data:
        firm.default_tax_rate = float(data['default_tax_rate'])
    if 'currency' in data:
        firm.currency = data['currency']
    
    db.session.commit()
    
    return jsonify({'firm': firm.to_dict()})


@bp.route('/firm/core', methods=['PUT'])
@login_required
def update_firm_core():
    """Update core firm details (name, logo, address, contacts) - settings only"""
    user = User.query.get(session['user_id'])
    if not user or not user.firm:
        return jsonify({'error': 'Firm not found'}), 404
    
    data = request.get_json()
    firm = user.firm
    
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


@bp.route('/validate-key', methods=['POST'])
def validate_product_key():
    """Validate product key"""
    data = request.get_json()
    key = data.get('key')
    
    if not key:
        return jsonify({'error': 'Product key is required'}), 400
    
    key_obj = ProductKey.query.filter_by(key=key).first()
    
    if not key_obj:
        return jsonify({'valid': False, 'error': 'Invalid product key'}), 200
    
    if key_obj.is_used:
        return jsonify({'valid': False, 'error': 'Product key already used'}), 200
    
    if key_obj.expires_at and key_obj.expires_at < datetime.utcnow():
        return jsonify({'valid': False, 'error': 'Product key has expired'}), 200
    
    return jsonify({'valid': True}), 200


@bp.route('/admin/keys/generate', methods=['POST'])
def generate_keys():
    """Generate product keys (admin only - add proper auth later)"""
    data = request.get_json()
    count = data.get('count', 1)
    days = data.get('days', 365)  # Valid for 1 year by default
    
    keys = []
    for _ in range(count):
        key = ProductKey(
            key=ProductKey.generate_key(),
            expires_at=datetime.utcnow() + timedelta(days=days)
        )
        db.session.add(key)
        keys.append(key.key)
    
    db.session.commit()
    
    return jsonify({
        'message': f'{count} product keys generated',
        'keys': keys
    }), 201


@bp.route('/delete-account', methods=['DELETE'])
@login_required
def delete_account():
    """Delete user account and all associated data"""
    data = request.get_json()
    confirmation = data.get('confirmation')
    
    # Require explicit confirmation
    if confirmation != 'confirm':
        return jsonify({'error': 'Account deletion requires confirmation'}), 400
    
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    try:
        # Import models needed for cleanup
        from backend.app.models.models import Invoice, InvoiceItem, Client
        
        # Since invoices and clients don't have firm_id in the current schema,
        # we'll delete ALL data (assumes single-user system per instance)
        # In a multi-user system, you'd need to add firm_id to these models
        
        # Delete all invoice items first (foreign key constraint)
        InvoiceItem.query.delete()
        
        # Delete all invoices
        Invoice.query.delete()
        
        # Delete all clients
        Client.query.delete()
        
        # Delete firm if exists
        if user.firm:
            db.session.delete(user.firm)
        
        # Mark product key as unused (allow reuse)
        product_key = ProductKey.query.filter_by(user_id=user.id).first()
        if product_key:
            product_key.is_used = False
            product_key.user_id = None
            product_key.activated_at = None
        
        # Delete user
        db.session.delete(user)
        db.session.commit()
        
        # Clear session
        session.pop('user_id', None)
        
        return jsonify({'message': 'Account deleted successfully'}), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to delete account: {str(e)}'}), 500
