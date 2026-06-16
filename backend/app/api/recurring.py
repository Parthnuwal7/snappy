"""Recurring invoice schedule endpoints (CRUD) + secret-gated run endpoint."""
import os
from datetime import datetime, date
from flask import Blueprint, request, jsonify, g
from app.models.models import db, RecurringSchedule, Client
from app.models.auth import User
from app.middleware.jwt_auth import jwt_required
from app.services.recurring_service import run_due_schedules

bp = Blueprint('recurring', __name__)


def _current_user_id():
    supabase_id = getattr(g, 'user_id', None)
    if not supabase_id:
        return None
    user = User.query.filter_by(supabase_id=supabase_id).first()
    return user.id if user else None


def _parse_date(value):
    return datetime.fromisoformat(value).date() if value else None


@bp.route('/recurring', methods=['GET'])
@jwt_required
def list_schedules():
    user_id = _current_user_id()
    if not user_id:
        return jsonify({'error': 'User not found'}), 401
    rows = (RecurringSchedule.query
            .filter_by(user_id=user_id)
            .order_by(RecurringSchedule.next_run_date.asc())
            .all())
    return jsonify([s.to_dict() for s in rows])


@bp.route('/recurring', methods=['POST'])
@jwt_required
def create_schedule():
    user_id = _current_user_id()
    if not user_id:
        return jsonify({'error': 'User not found'}), 401
    data = request.get_json() or {}

    if not data.get('client_id'):
        return jsonify({'error': 'client_id is required'}), 400
    client = Client.query.filter_by(id=data['client_id'], user_id=user_id).first()
    if not client:
        return jsonify({'error': 'Client not found'}), 404
    if data.get('frequency') not in ('weekly', 'monthly'):
        return jsonify({'error': 'frequency must be weekly or monthly'}), 400
    start = _parse_date(data.get('start_date'))
    if not start:
        return jsonify({'error': 'start_date is required'}), 400

    sched = RecurringSchedule(
        user_id=user_id,
        client_id=data['client_id'],
        title=data.get('title'),
        items=data.get('items', []),
        tax_rate=float(data.get('tax_rate', client.default_tax_rate)),
        short_desc=data.get('short_desc'),
        notes=data.get('notes'),
        frequency=data['frequency'],
        start_date=start,
        next_run_date=start,           # first draft is created on the start date
        end_date=_parse_date(data.get('end_date')),
        active=data.get('active', True),
    )
    db.session.add(sched)
    db.session.commit()
    return jsonify(sched.to_dict()), 201


@bp.route('/recurring/<int:schedule_id>', methods=['PUT'])
@jwt_required
def update_schedule(schedule_id):
    user_id = _current_user_id()
    if not user_id:
        return jsonify({'error': 'User not found'}), 401
    sched = RecurringSchedule.query.filter_by(id=schedule_id, user_id=user_id).first()
    if not sched:
        return jsonify({'error': 'Schedule not found'}), 404
    data = request.get_json() or {}

    if 'title' in data:
        sched.title = data['title']
    if 'items' in data:
        sched.items = data['items']
    if 'tax_rate' in data:
        sched.tax_rate = float(data['tax_rate'])
    if 'short_desc' in data:
        sched.short_desc = data['short_desc']
    if 'notes' in data:
        sched.notes = data['notes']
    if data.get('frequency') in ('weekly', 'monthly'):
        sched.frequency = data['frequency']
    if 'start_date' in data:
        sched.start_date = _parse_date(data['start_date'])
    if 'next_run_date' in data:
        sched.next_run_date = _parse_date(data['next_run_date'])
    if 'end_date' in data:
        sched.end_date = _parse_date(data['end_date'])
    if 'active' in data:
        sched.active = bool(data['active'])
    db.session.commit()
    return jsonify(sched.to_dict())


@bp.route('/recurring/<int:schedule_id>', methods=['DELETE'])
@jwt_required
def delete_schedule(schedule_id):
    user_id = _current_user_id()
    if not user_id:
        return jsonify({'error': 'User not found'}), 401
    sched = RecurringSchedule.query.filter_by(id=schedule_id, user_id=user_id).first()
    if not sched:
        return jsonify({'error': 'Schedule not found'}), 404
    db.session.delete(sched)
    db.session.commit()
    return jsonify({'message': 'Schedule deleted'})


@bp.route('/recurring/reminders', methods=['GET'])
@jwt_required
def reminders():
    """Recurring-generated drafts awaiting review — the in-app reminder feed."""
    from app.models.models import Invoice
    user_id = _current_user_id()
    if not user_id:
        return jsonify({'error': 'User not found'}), 401
    drafts = (Invoice.query
              .filter_by(user_id=user_id, status='draft', source='recurring')
              .order_by(Invoice.created_at.desc())
              .all())
    return jsonify([inv.to_dict() for inv in drafts])


@bp.route('/recurring/run', methods=['POST'])
def run():
    """Secret-gated endpoint hit daily by Cloud Scheduler. No JWT — uses a shared secret."""
    expected = os.getenv('CRON_SECRET')
    provided = request.headers.get('X-Cron-Secret')
    if not expected or provided != expected:
        return jsonify({'error': 'Unauthorized'}), 401
    created = run_due_schedules(db.session, today=date.today())
    return jsonify({'created': len(created)}), 200
