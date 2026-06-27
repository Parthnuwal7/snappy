"""Items API endpoints - Service/Product catalog - firm-scoped."""
from flask import Blueprint, request, jsonify, g
from app.models.models import db, Item
from app.middleware.jwt_auth import jwt_required
from app.middleware.firm_context import require_permission
from app.utils.pagination import pagination_requested, get_pagination_args, paginate_query
from rapidfuzz import fuzz, process

bp = Blueprint('items', __name__)


@bp.route('/items', methods=['GET'])
@jwt_required
@require_permission('items.read')
def get_items():
    """Get all items for the current firm with optional fuzzy search"""
    search = request.args.get('search', '')
    active_only = request.args.get('active', 'true').lower() == 'true'

    query = Item.query.filter_by(firm_id=g.firm_id)

    if active_only:
        query = query.filter_by(is_active=True)

    # Paginated mode (list page): SQL substring filter across all fields, then page.
    # Search spans every item, irrespective of which page is shown.
    if pagination_requested():
        term = search.strip()
        if term:
            like = f"%{term}%"
            query = query.filter(
                db.or_(
                    Item.name.ilike(like),
                    Item.alias.ilike(like),
                    Item.description.ilike(like),
                )
            )
        query = query.order_by(Item.name)
        page, page_size = get_pagination_args()
        return jsonify(paginate_query(query, page, page_size, lambda i: i.to_dict()))

    if search:
        # Fuzzy search on name and alias
        all_items = query.all()

        if not all_items:
            return jsonify([])

        # Create searchable strings (name + alias)
        search_items = []
        for item in all_items:
            search_str = f"{item.name} {item.alias or ''}"
            search_items.append((item, search_str))

        # Fuzzy match
        matches = process.extract(
            search,
            [s[1] for s in search_items],
            scorer=fuzz.partial_ratio,
            limit=10
        )

        # Get matching items with score > 50
        matching_items = []
        for match_str, score, idx in matches:
            if score > 50:
                matching_items.append(search_items[idx][0])

        return jsonify([item.to_dict() for item in matching_items])
    else:
        items = query.order_by(Item.name).all()
        return jsonify([item.to_dict() for item in items])


@bp.route('/items/<int:item_id>', methods=['GET'])
@jwt_required
@require_permission('items.read')
def get_item(item_id):
    """Get a single item by ID (must belong to current firm)"""
    item = Item.query.filter_by(id=item_id, firm_id=g.firm_id).first()
    if not item:
        return jsonify({'error': 'Item not found'}), 404

    return jsonify(item.to_dict())


@bp.route('/items', methods=['POST'])
@jwt_required
@require_permission('items.create')
def create_item():
    """Create a new item for the current firm"""
    data = request.get_json()

    # Validate required fields
    if not data.get('name'):
        return jsonify({'error': 'Item name is required'}), 400

    item = Item(
        firm_id=g.firm_id,
        created_by_user_id=g.user.id,
        name=data['name'],
        alias=data.get('alias'),
        description=data.get('description'),
        default_rate=float(data.get('default_rate', 0.0)),
        unit=data.get('unit', 'hour'),
        hsn_code=data.get('hsn_code'),
        is_active=data.get('is_active', True)
    )

    db.session.add(item)
    db.session.commit()

    return jsonify(item.to_dict()), 201


@bp.route('/items/<int:item_id>', methods=['PUT'])
@jwt_required
@require_permission('items.update')
def update_item(item_id):
    """Update an existing item (must belong to current firm)"""
    item = Item.query.filter_by(id=item_id, firm_id=g.firm_id).first()
    if not item:
        return jsonify({'error': 'Item not found'}), 404

    data = request.get_json()

    # Update fields
    if 'name' in data:
        item.name = data['name']
    if 'alias' in data:
        item.alias = data['alias']
    if 'description' in data:
        item.description = data['description']
    if 'default_rate' in data:
        item.default_rate = float(data['default_rate'])
    if 'unit' in data:
        item.unit = data['unit']
    if 'hsn_code' in data:
        item.hsn_code = data['hsn_code']
    if 'is_active' in data:
        item.is_active = data['is_active']

    db.session.commit()
    return jsonify(item.to_dict())


@bp.route('/items/<int:item_id>', methods=['DELETE'])
@jwt_required
@require_permission('items.delete')
def delete_item(item_id):
    """Soft delete an item (mark as inactive)"""
    item = Item.query.filter_by(id=item_id, firm_id=g.firm_id).first()
    if not item:
        return jsonify({'error': 'Item not found'}), 404

    # Soft delete - just mark as inactive
    item.is_active = False
    db.session.commit()

    return jsonify({'message': 'Item deactivated successfully'})
