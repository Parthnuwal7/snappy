"""Client API endpoints - multi-tenant"""
from flask import Blueprint, request, jsonify, g
from app.models.models import db, Client
from app.models.auth import User
from app.middleware.jwt_auth import jwt_required
from rapidfuzz import fuzz, process

bp = Blueprint('clients', __name__)


def get_current_user_id():
    """Get the internal user ID from Supabase ID"""
    supabase_id = getattr(g, 'user_id', None)
    if not supabase_id:
        return None
    user = User.query.filter_by(supabase_id=supabase_id).first()
    return user.id if user else None


@bp.route('/clients', methods=['GET'])
@jwt_required
def get_clients():
    """Get all clients for current user with optional search"""
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({'error': 'User not found'}), 401
    
    search = request.args.get('search', '')
    
    if search:
        # Fuzzy search clients for this user
        all_clients = Client.query.filter_by(user_id=user_id).all()
        if all_clients:
            matches = process.extract(
                search,
                [c.name for c in all_clients],
                scorer=fuzz.ratio,
                limit=10
            )
            matching_names = [match[0] for match in matches if match[1] > 60]
            clients = Client.query.filter(
                Client.user_id == user_id,
                Client.name.in_(matching_names)
            ).all()
        else:
            clients = []
    else:
        clients = Client.query.filter_by(user_id=user_id).order_by(Client.name).all()
    
    return jsonify([client.to_dict() for client in clients])


@bp.route('/clients/<int:client_id>', methods=['GET'])
@jwt_required
def get_client(client_id):
    """Get a single client by ID (must belong to current user)"""
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({'error': 'User not found'}), 401
    
    client = Client.query.filter_by(id=client_id, user_id=user_id).first()
    if not client:
        return jsonify({'error': 'Client not found'}), 404
    
    return jsonify(client.to_dict())


@bp.route('/clients', methods=['POST'])
@jwt_required
def create_client():
    """Create a new client for current user"""
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({'error': 'User not found'}), 401
    
    data = request.get_json()
    
    # Validate required fields
    if not data.get('name'):
        return jsonify({'error': 'Client name is required'}), 400
    
    client = Client(
        user_id=user_id,
        name=data['name'],
        email=data.get('email'),
        phone=data.get('phone'),
        address=data.get('address'),
        tax_id=data.get('tax_id'),
        default_tax_rate=data.get('default_tax_rate', 18.0),
        notes=data.get('notes')
    )
    
    db.session.add(client)
    db.session.commit()
    
    return jsonify(client.to_dict()), 201


@bp.route('/clients/<int:client_id>', methods=['PUT'])
@jwt_required
def update_client(client_id):
    """Update an existing client (must belong to current user)"""
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({'error': 'User not found'}), 401
    
    client = Client.query.filter_by(id=client_id, user_id=user_id).first()
    if not client:
        return jsonify({'error': 'Client not found'}), 404
    
    data = request.get_json()
    
    # Update fields
    if 'name' in data:
        client.name = data['name']
    if 'email' in data:
        client.email = data['email']
    if 'phone' in data:
        client.phone = data['phone']
    if 'address' in data:
        client.address = data['address']
    if 'tax_id' in data:
        client.tax_id = data['tax_id']
    if 'default_tax_rate' in data:
        client.default_tax_rate = data['default_tax_rate']
    if 'notes' in data:
        client.notes = data['notes']
    
    db.session.commit()
    return jsonify(client.to_dict())


@bp.route('/clients/<int:client_id>', methods=['DELETE'])
@jwt_required
def delete_client(client_id):
    """Delete a client (must belong to current user)"""
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({'error': 'User not found'}), 401
    
    client = Client.query.filter_by(id=client_id, user_id=user_id).first()
    if not client:
        return jsonify({'error': 'Client not found'}), 404
    
    # Check if client has invoices
    if client.invoices.count() > 0:
        return jsonify({'error': 'Cannot delete client with existing invoices'}), 400
    
    db.session.delete(client)
    db.session.commit()
    
    return jsonify({'message': 'Client deleted successfully'})
