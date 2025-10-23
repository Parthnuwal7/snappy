"""Client API endpoints"""
from flask import Blueprint, request, jsonify
from backend.app.models.models import db, Client
from rapidfuzz import fuzz, process

bp = Blueprint('clients', __name__)


@bp.route('/clients', methods=['GET'])
def get_clients():
    """Get all clients with optional search"""
    search = request.args.get('search', '')
    
    if search:
        # Fuzzy search clients
        all_clients = Client.query.all()
        matches = process.extract(
            search,
            [c.name for c in all_clients],
            scorer=fuzz.ratio,
            limit=10
        )
        matching_names = [match[0] for match in matches if match[1] > 60]
        clients = Client.query.filter(Client.name.in_(matching_names)).all()
    else:
        clients = Client.query.order_by(Client.name).all()
    
    return jsonify([client.to_dict() for client in clients])


@bp.route('/clients/<int:client_id>', methods=['GET'])
def get_client(client_id):
    """Get a single client by ID"""
    client = Client.query.get_or_404(client_id)
    return jsonify(client.to_dict())


@bp.route('/clients', methods=['POST'])
def create_client():
    """Create a new client"""
    data = request.get_json()
    
    # Validate required fields
    if not data.get('name'):
        return jsonify({'error': 'Client name is required'}), 400
    
    client = Client(
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
def update_client(client_id):
    """Update an existing client"""
    client = Client.query.get_or_404(client_id)
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
def delete_client(client_id):
    """Delete a client"""
    client = Client.query.get_or_404(client_id)
    
    # Check if client has invoices
    if client.invoices.count() > 0:
        return jsonify({'error': 'Cannot delete client with existing invoices'}), 400
    
    db.session.delete(client)
    db.session.commit()
    
    return jsonify({'message': 'Client deleted successfully'})
