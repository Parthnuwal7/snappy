"""Task API — firm-scoped day-planner to-dos. Gated by the tasks RBAC module."""
from datetime import datetime
from flask import Blueprint, request, jsonify, g
from sqlalchemy.orm import selectinload
from app.models.models import db
from app.models.task import Task
from app.middleware.jwt_auth import jwt_required
from app.middleware.firm_context import require_permission
from app.utils.pagination import pagination_requested, get_pagination_args, paginate_query
from app.case.stages import is_valid_priority

bp = Blueprint('tasks', __name__)


def _date(value):
    return datetime.fromisoformat(value).date() if value else None


def _owned(task_id):
    return Task.query.filter_by(id=task_id, firm_id=g.firm_id).first()


@bp.route('/tasks', methods=['GET'])
@jwt_required
@require_permission('tasks.read')
def list_tasks():
    # Eager-load case_file so to_dict()'s case_number/case_title don't N+1.
    q = Task.query.options(selectinload(Task.case_file)).filter_by(firm_id=g.firm_id)
    frm, to = _date(request.args.get('from')), _date(request.args.get('to'))
    if frm:
        q = q.filter(Task.due_date >= frm)
    if to:
        q = q.filter(Task.due_date <= to)
    status = request.args.get('status')
    if status == 'open':
        q = q.filter(Task.done.is_(False))
    elif status == 'done':
        q = q.filter(Task.done.is_(True))
    case_file_id = request.args.get('case_file_id', type=int)
    if case_file_id:
        q = q.filter_by(case_file_id=case_file_id)
    q = q.order_by(Task.due_date.asc(), Task.id.asc())
    serialize = lambda t: t.to_dict()
    if pagination_requested():
        page, page_size = get_pagination_args()
        return jsonify(paginate_query(q, page, page_size, serialize))
    return jsonify([serialize(t) for t in q.all()])


@bp.route('/tasks', methods=['POST'])
@jwt_required
@require_permission('tasks.create')
def create_task():
    data = request.get_json() or {}
    title = (data.get('title') or '').strip()
    if not title:
        return jsonify({'error': 'Title is required'}), 400
    priority = data.get('priority', 'normal')
    if not is_valid_priority(priority):
        return jsonify({'error': 'Invalid priority'}), 400
    task = Task(firm_id=g.firm_id, created_by_user_id=g.user.id, title=title,
                due_date=_date(data.get('due_date')), case_file_id=data.get('case_file_id'),
                priority=priority)
    db.session.add(task)
    db.session.commit()
    return jsonify(task.to_dict()), 201


@bp.route('/tasks/<int:task_id>', methods=['PATCH'])
@jwt_required
@require_permission('tasks.update')
def update_task(task_id):
    task = _owned(task_id)
    if not task:
        return jsonify({'error': 'Task not found'}), 404
    data = request.get_json() or {}
    if 'title' in data:
        task.title = (data['title'] or '').strip() or task.title
    if 'due_date' in data:
        task.due_date = _date(data['due_date'])
    if 'done' in data:
        task.done = bool(data['done'])
    if 'priority' in data:
        if not is_valid_priority(data['priority']):
            return jsonify({'error': 'Invalid priority'}), 400
        task.priority = data['priority']
    if 'case_file_id' in data:
        task.case_file_id = data['case_file_id']
    db.session.commit()
    return jsonify(task.to_dict())


@bp.route('/tasks/<int:task_id>', methods=['DELETE'])
@jwt_required
@require_permission('tasks.delete')
def delete_task(task_id):
    task = _owned(task_id)
    if not task:
        return jsonify({'error': 'Task not found'}), 404
    db.session.delete(task)
    db.session.commit()
    return jsonify({'message': 'Task deleted'})
