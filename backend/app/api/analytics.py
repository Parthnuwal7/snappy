"""Analytics API endpoints"""
from flask import Blueprint, request, jsonify
from app.services.duckdb_service import get_duckdb_service
from datetime import datetime, timedelta

bp = Blueprint('analytics', __name__)


@bp.route('/monthly', methods=['GET'])
def get_monthly_revenue():
    """Get monthly revenue data"""
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
        data = duckdb_service.get_monthly_revenue(start_date, end_date)
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/top_clients', methods=['GET'])
def get_top_clients():
    """Get top clients by revenue"""
    limit = request.args.get('limit', default=5, type=int)
    
    try:
        duckdb_service = get_duckdb_service()
        data = duckdb_service.get_top_clients(limit)
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/aging', methods=['GET'])
def get_aging_analysis():
    """Get aging buckets for unpaid invoices"""
    try:
        duckdb_service = get_duckdb_service()
        data = duckdb_service.get_aging_buckets()
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
