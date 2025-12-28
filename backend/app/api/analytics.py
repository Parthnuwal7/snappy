"""Analytics API endpoints - multi-tenant"""
from flask import Blueprint, request, jsonify, g
from app.services.duckdb_service import get_duckdb_service
from app.middleware.jwt_auth import jwt_required
from app.models.auth import User
from datetime import datetime, timedelta

bp = Blueprint('analytics', __name__)


def get_current_user():
    """Get the current user from Supabase ID"""
    supabase_id = getattr(g, 'user_id', None)
    if not supabase_id:
        return None
    return User.query.filter_by(supabase_id=supabase_id).first()


@bp.route('/monthly', methods=['GET'])
@jwt_required
def get_monthly_revenue():
    """Get monthly revenue data for current user only"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 401
    
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    # Default to last 12 months if not provided
    if not end_date:
        end_date = datetime.now().date().isoformat()
    if not start_date:
        start = datetime.now().date() - timedelta(days=365)
        start_date = start.isoformat()
    
    try:
        duckdb_service = get_duckdb_service()
        data = duckdb_service.get_monthly_revenue(user.id, start_date, end_date)
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/top_clients', methods=['GET'])
@jwt_required
def get_top_clients():
    """Get top clients by revenue for current user only"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 401
    
    limit = request.args.get('limit', default=5, type=int)
    
    try:
        duckdb_service = get_duckdb_service()
        data = duckdb_service.get_top_clients(user.id, limit)
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/aging', methods=['GET'])
@jwt_required
def get_aging_analysis():
    """Get aging buckets for unpaid invoices for current user only"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 401
    
    try:
        duckdb_service = get_duckdb_service()
        data = duckdb_service.get_aging_buckets(user.id)
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
