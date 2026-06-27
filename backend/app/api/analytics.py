"""Analytics API endpoints — direct Postgres aggregations.

Queries are simple GROUP BYs that Postgres answers in <50ms at our scale;
the previous DuckDB cache layer added cold-start sync overhead with no
real benefit on Cloud Run (scale-to-zero wipes /tmp anyway).
"""
from datetime import datetime, timedelta
from decimal import Decimal

from flask import Blueprint, g, jsonify, request
from sqlalchemy import text

from app.middleware.jwt_auth import jwt_required
from app.models.auth import User
from app.models.models import db

bp = Blueprint('analytics', __name__)


def get_current_user():
    supabase_id = getattr(g, 'user_id', None)
    if not supabase_id:
        return None
    return User.query.filter_by(supabase_id=supabase_id).first()


def _num(value):
    """Postgres SUM/AVG of NUMERIC columns returns Decimal — JSON wants float."""
    if value is None:
        return 0
    if isinstance(value, Decimal):
        return float(value)
    return value


@bp.route('/monthly', methods=['GET'])
@jwt_required
def get_monthly_revenue():
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 401

    end_date = request.args.get('end_date') or datetime.now().date().isoformat()
    start_date = request.args.get('start_date') or (
        datetime.now().date() - timedelta(days=365)
    ).isoformat()

    try:
        rows = db.session.execute(text("""
            SELECT to_char(invoice_date, 'YYYY-MM') AS month,
                   SUM(total)                     AS revenue,
                   COUNT(*)                       AS invoice_count
            FROM invoices
            WHERE firm_id = :firm_id
              AND status <> 'void'
              AND invoice_date >= :start_date
              AND invoice_date <= :end_date
            GROUP BY month
            ORDER BY month
        """), {
            'firm_id': user.firm_id,
            'start_date': start_date,
            'end_date': end_date,
        }).fetchall()

        return jsonify([
            {'month': r.month, 'revenue': _num(r.revenue), 'invoice_count': r.invoice_count}
            for r in rows
        ])
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/top_clients', methods=['GET'])
@jwt_required
def get_top_clients():
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 401

    limit = request.args.get('limit', default=5, type=int)

    try:
        rows = db.session.execute(text("""
            SELECT c.name        AS client_name,
                   SUM(i.total)  AS total_revenue,
                   COUNT(*)      AS invoice_count,
                   AVG(i.total)  AS avg_invoice
            FROM invoices i
            JOIN clients c ON c.id = i.client_id
            WHERE i.firm_id = :firm_id
              AND i.status <> 'void'
            GROUP BY c.name
            ORDER BY total_revenue DESC
            LIMIT :limit
        """), {'firm_id': user.firm_id, 'limit': limit}).fetchall()

        return jsonify([
            {
                'client_name': r.client_name,
                'total_revenue': _num(r.total_revenue),
                'invoice_count': r.invoice_count,
                'avg_invoice': _num(r.avg_invoice),
            }
            for r in rows
        ])
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/aging', methods=['GET'])
@jwt_required
def get_aging_analysis():
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 401

    try:
        row = db.session.execute(text("""
            SELECT
              COALESCE(SUM(CASE WHEN (CURRENT_DATE - due_date) BETWEEN  0 AND 30
                                THEN total ELSE 0 END), 0) AS bucket_0_30,
              COALESCE(SUM(CASE WHEN (CURRENT_DATE - due_date) BETWEEN 31 AND 60
                                THEN total ELSE 0 END), 0) AS bucket_31_60,
              COALESCE(SUM(CASE WHEN (CURRENT_DATE - due_date) > 60
                                THEN total ELSE 0 END), 0) AS bucket_61_plus,
              COUNT(*)                                    AS total_unpaid
            FROM invoices
            WHERE firm_id = :firm_id
              AND status IN ('draft', 'sent')
              AND due_date IS NOT NULL
        """), {'firm_id': user.firm_id}).fetchone()

        return jsonify({
            'bucket_0_30':    _num(row.bucket_0_30),
            'bucket_31_60':   _num(row.bucket_31_60),
            'bucket_61_plus': _num(row.bucket_61_plus),
            'total_unpaid':   row.total_unpaid,
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
