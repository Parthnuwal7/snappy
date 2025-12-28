"""Items API endpoints - Service/Product catalog - multi-tenant"""
from flask import Blueprint, request, jsonify, g
from app.models.models import db, Item
from app.models.auth import User
from app.middleware.jwt_auth import jwt_required
from rapidfuzz import fuzz, process

bp = Blueprint('items', __name__)


def get_current_user_id():
    """Get the internal user ID from Supabase ID"""
    supabase_id = getattr(g, 'user_id', None)
    if not supabase_id:
        return None
    user = User.query.filter_by(supabase_id=supabase_id).first()
    return user.id if user else None


@bp.route('/items', methods=['GET'])
@jwt_required
def get_items():
    """Get all items for current user with optional fuzzy search"""
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({'error': 'User not found'}), 401
    
    search = request.args.get('search', '')
    active_only = request.args.get('active', 'true').lower() == 'true'
    
    query = Item.query.filter_by(user_id=user_id)
    
    if active_only:
        query = query.filter_by(is_active=True)
    
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
def get_item(item_id):
    """Get a single item by ID (must belong to current user)"""
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({'error': 'User not found'}), 401
    
    item = Item.query.filter_by(id=item_id, user_id=user_id).first()
    if not item:
        return jsonify({'error': 'Item not found'}), 404
    
    return jsonify(item.to_dict())


@bp.route('/items', methods=['POST'])
@jwt_required
def create_item():
    """Create a new item for current user"""
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({'error': 'User not found'}), 401
    
    data = request.get_json()
    
    # Validate required fields
    if not data.get('name'):
        return jsonify({'error': 'Item name is required'}), 400
    
    item = Item(
        user_id=user_id,
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
def update_item(item_id):
    """Update an existing item (must belong to current user)"""
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({'error': 'User not found'}), 401
    
    item = Item.query.filter_by(id=item_id, user_id=user_id).first()
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
def delete_item(item_id):
    """Soft delete an item (mark as inactive)"""
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({'error': 'User not found'}), 401
    
    item = Item.query.filter_by(id=item_id, user_id=user_id).first()
    if not item:
        return jsonify({'error': 'Item not found'}), 404
    
    # Soft delete - just mark as inactive
    item.is_active = False
    db.session.commit()
    
    return jsonify({'message': 'Item deactivated successfully'})
