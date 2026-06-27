"""Client API endpoints - firm-scoped with role permissions."""
from flask import Blueprint, request, jsonify, g
from app.models.models import db, Client, Invoice
from app.middleware.jwt_auth import jwt_required
from app.middleware.firm_context import require_permission
from app.utils.pagination import pagination_requested, get_pagination_args, paginate_query
from rapidfuzz import fuzz, process
from sqlalchemy import func

bp = Blueprint('clients', __name__)


@bp.route('/clients', methods=['GET'])
@jwt_required
@require_permission('clients.read')
def get_clients():
    """Get all clients for the current firm with optional search"""
    firm_id = g.firm_id
    search = request.args.get('search', '')

    # Paginated mode (list page): SQL substring filter across all fields, then page.
    # Search spans every client, irrespective of which page is shown.
    if pagination_requested():
        query = Client.query.filter_by(firm_id=firm_id)
        term = search.strip()
        if term:
            like = f"%{term}%"
            query = query.filter(
                db.or_(
                    Client.name.ilike(like),
                    Client.email.ilike(like),
                    Client.phone.ilike(like),
                    Client.address.ilike(like),
                    Client.tax_id.ilike(like),
                )
            )
        query = query.order_by(Client.name)
        page, page_size = get_pagination_args()
        return jsonify(paginate_query(query, page, page_size, lambda c: c.to_dict()))

    if search and len(search) >= 2:  # Minimum 2 chars for search
        # Fuzzy search clients for this firm
        all_clients = Client.query.filter_by(firm_id=firm_id).all()
        if all_clients:
            # Use WRatio for better partial matching (handles "ICICI" matching "icici lomb")
            matches = process.extract(
                search,
                [c.name for c in all_clients],
                scorer=fuzz.WRatio,  # Better for partial/substring matching
                limit=15
            )
            # Lower threshold to 40 for more flexible matching
            matching_names = [match[0] for match in matches if match[1] > 40]
            clients = [c for c in all_clients if c.name in matching_names]
            # Sort by match score (best matches first)
            name_to_score = {match[0]: match[1] for match in matches}
            clients.sort(key=lambda c: name_to_score.get(c.name, 0), reverse=True)
        else:
            clients = []
    else:
        clients = Client.query.filter_by(firm_id=firm_id).order_by(Client.name).all()

    return jsonify([client.to_dict() for client in clients])


def recent_clients_for_firm(firm_id, limit=6):
    """Return the firm's clients ordered by most recent invoice, capped at limit.

    Clients with no invoices are excluded. Returns a list of client dicts.
    """
    rows = (
        db.session.query(Client)
        .join(Invoice, Invoice.client_id == Client.id)
        .filter(Client.firm_id == firm_id)
        .group_by(Client.id)
        .order_by(func.max(Invoice.invoice_date).desc())
        .limit(limit)
        .all()
    )
    return [c.to_dict() for c in rows]


@bp.route('/clients/recent', methods=['GET'])
@jwt_required
@require_permission('clients.read')
def get_recent_clients():
    """Get the current firm's most-recently-billed clients."""
    limit = request.args.get('limit', default=6, type=int)
    return jsonify(recent_clients_for_firm(g.firm_id, limit=limit))


@bp.route('/clients/<int:client_id>', methods=['GET'])
@jwt_required
@require_permission('clients.read')
def get_client(client_id):
    """Get a single client by ID (must belong to current firm)"""
    client = Client.query.filter_by(id=client_id, firm_id=g.firm_id).first()
    if not client:
        return jsonify({'error': 'Client not found'}), 404

    return jsonify(client.to_dict())


@bp.route('/clients', methods=['POST'])
@jwt_required
@require_permission('clients.create')
def create_client():
    """Create a new client for the current firm"""
    data = request.get_json()

    # Validate required fields
    if not data.get('name'):
        return jsonify({'error': 'Client name is required'}), 400

    client = Client(
        firm_id=g.firm_id,
        created_by_user_id=g.user.id,
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
@require_permission('clients.update')
def update_client(client_id):
    """Update an existing client (must belong to current firm)"""
    client = Client.query.filter_by(id=client_id, firm_id=g.firm_id).first()
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
@require_permission('clients.delete')
def delete_client(client_id):
    """Delete a client (must belong to current firm)"""
    client = Client.query.filter_by(id=client_id, firm_id=g.firm_id).first()
    if not client:
        return jsonify({'error': 'Client not found'}), 404

    # Check if client has invoices
    if client.invoices.count() > 0:
        return jsonify({'error': 'Cannot delete client with existing invoices'}), 400

    db.session.delete(client)
    db.session.commit()

    return jsonify({'message': 'Client deleted successfully'})
