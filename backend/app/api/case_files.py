"""Case File API — firm-scoped, gated by the case_files RBAC module."""
from datetime import datetime
from flask import Blueprint, request, jsonify, g
from sqlalchemy.orm import selectinload
from app.models.models import db, Client
from app.models.case import CaseFile, CaseStageChange
from app.middleware.jwt_auth import jwt_required
from app.middleware.firm_context import require_permission
from app.utils.pagination import pagination_requested, get_pagination_args, paginate_query
from app.services.case_service import generate_case_number, record_stage_change
from app.case.stages import (
    STAGES, EVENT_KINDS, PRIORITIES, STAGE_GUIDES, STAGE_FLOW, HEARING_PURPOSES,
    is_valid_stage, is_valid_priority,
)
from app.case.documents import DOC_TYPES
from app.case.expenses import EXPENSE_CATEGORIES
from app.case.exhibits import EXHIBIT_STATUSES, EXHIBIT_PARTIES

bp = Blueprint('case_files', __name__)


def _parse_date(value):
    return datetime.fromisoformat(value).date() if value else None


def _set_parties(case_file, parties_data):
    """Replace the case's parties (inline JSON list of {name, role})."""
    case_file.parties = [
        {'name': (p.get('name') or '').strip(), 'role': p.get('role')}
        for p in (parties_data or []) if (p.get('name') or '').strip()
    ]


@bp.route('/case-files/meta', methods=['GET'])
@jwt_required
@require_permission('case_files.read')
def case_meta():
    return jsonify({'stages': STAGES, 'event_kinds': EVENT_KINDS,
                    'priorities': PRIORITIES, 'doc_types': DOC_TYPES,
                    'expense_categories': EXPENSE_CATEGORIES,
                    'stage_guides': STAGE_GUIDES, 'stage_flow': STAGE_FLOW,
                    'exhibit_statuses': EXHIBIT_STATUSES,
                    'exhibit_parties': EXHIBIT_PARTIES,
                    'hearing_purposes': HEARING_PURPOSES})


@bp.route('/case-files', methods=['GET'])
@jwt_required
@require_permission('case_files.read')
def list_case_files():
    # Eager-load the client so to_dict()'s client_name doesn't fire one query per
    # row (N+1). selectinload batches them into a single IN (...) lookup.
    query = CaseFile.query.options(selectinload(CaseFile.client)).filter_by(firm_id=g.firm_id)
    stage = request.args.get('stage')
    client_id = request.args.get('client_id', type=int)
    assignee = request.args.get('assignee', type=int)
    search = (request.args.get('search') or '').strip()
    if stage:
        query = query.filter_by(stage=stage)
    if client_id:
        query = query.filter_by(client_id=client_id)
    if assignee:
        query = query.filter_by(handling_advocate_user_id=assignee)
    if search:
        like = f"%{search}%"
        query = query.filter(db.or_(
            CaseFile.title.ilike(like),
            CaseFile.case_number.ilike(like),
            CaseFile.court_case_number.ilike(like),
        ))
    query = query.order_by(CaseFile.position, CaseFile.id.desc())
    serialize = lambda c: c.to_dict()
    if pagination_requested():
        page, page_size = get_pagination_args()
        return jsonify(paginate_query(query, page, page_size, serialize))
    return jsonify([serialize(c) for c in query.all()])


@bp.route('/case-files', methods=['POST'])
@jwt_required
@require_permission('case_files.create')
def create_case_file():
    data = request.get_json() or {}
    title = (data.get('title') or '').strip()
    if not title:
        return jsonify({'error': 'Title is required'}), 400
    client = Client.query.filter_by(id=data.get('client_id'), firm_id=g.firm_id).first()
    if not client:
        return jsonify({'error': 'Client not found'}), 404

    stage = data.get('stage')
    if stage and not is_valid_stage(stage):
        return jsonify({'error': 'Invalid stage'}), 400
    priority = data.get('priority')
    if priority and not is_valid_priority(priority):
        return jsonify({'error': 'Invalid priority'}), 400

    case_file = CaseFile(
        firm_id=g.firm_id,
        created_by_user_id=g.user.id,
        case_number=generate_case_number(g.firm_id),
        title=title,
        client_id=client.id,
        matter_type=data.get('matter_type'),
        court=data.get('court'),
        court_case_number=data.get('court_case_number'),
        jurisdiction=data.get('jurisdiction'),
        act_section=data.get('act_section'),
        opposing_counsel=data.get('opposing_counsel'),
        handling_advocate_user_id=data.get('handling_advocate_user_id'),
        agreed_fee=data.get('agreed_fee'),
        filing_date=_parse_date(data.get('filing_date')),
        next_hearing_date=_parse_date(data.get('next_hearing_date')),
        open_date=_parse_date(data.get('open_date')),
        description=data.get('description'),
    )
    if stage:
        case_file.stage = stage
    if priority:
        case_file.priority = priority
    _set_parties(case_file, data.get('parties'))
    db.session.add(case_file)
    db.session.flush()
    record_stage_change(case_file, None, case_file.stage, g.user.id)
    db.session.commit()
    return jsonify(case_file.to_dict(include_parties=True)), 201


@bp.route('/case-files/<int:case_id>', methods=['GET'])
@jwt_required
@require_permission('case_files.read')
def get_case_file(case_id):
    case_file = CaseFile.query.filter_by(id=case_id, firm_id=g.firm_id).first()
    if not case_file:
        return jsonify({'error': 'Case not found'}), 404
    return jsonify(case_file.to_dict(include_parties=True))


@bp.route('/case-files/<int:case_id>', methods=['PATCH'])
@jwt_required
@require_permission('case_files.update')
def update_case_file(case_id):
    case_file = CaseFile.query.filter_by(id=case_id, firm_id=g.firm_id).first()
    if not case_file:
        return jsonify({'error': 'Case not found'}), 404
    data = request.get_json() or {}

    if 'client_id' in data:
        client = Client.query.filter_by(id=data['client_id'], firm_id=g.firm_id).first()
        if not client:
            return jsonify({'error': 'Client not found'}), 404
        case_file.client_id = client.id
    if 'stage' in data:
        if not is_valid_stage(data['stage']):
            return jsonify({'error': 'Invalid stage'}), 400
        if data['stage'] != case_file.stage:
            record_stage_change(case_file, case_file.stage, data['stage'], g.user.id)
            case_file.stage = data['stage']
    if 'priority' in data:
        if not is_valid_priority(data['priority']):
            return jsonify({'error': 'Invalid priority'}), 400
        case_file.priority = data['priority']
    for field in ('title', 'matter_type', 'court', 'court_case_number',
                  'jurisdiction', 'act_section', 'opposing_counsel',
                  'description', 'handling_advocate_user_id', 'agreed_fee'):
        if field in data:
            setattr(case_file, field, data[field])
    if 'filing_date' in data:
        case_file.filing_date = _parse_date(data['filing_date'])
    # next_hearing_date is derived from hearing events — not manually editable here.
    if 'open_date' in data:
        case_file.open_date = _parse_date(data['open_date'])
    if 'parties' in data:
        _set_parties(case_file, data['parties'])

    db.session.commit()
    return jsonify(case_file.to_dict(include_parties=True))


@bp.route('/case-files/<int:case_id>/move', methods=['PATCH'])
@jwt_required
@require_permission('case_files.update')
def move_case_file(case_id):
    case_file = CaseFile.query.filter_by(id=case_id, firm_id=g.firm_id).first()
    if not case_file:
        return jsonify({'error': 'Case not found'}), 404
    data = request.get_json() or {}
    stage = data.get('stage')
    if not stage or not is_valid_stage(stage):
        return jsonify({'error': 'Invalid stage'}), 400
    if stage != case_file.stage:
        record_stage_change(case_file, case_file.stage, stage, g.user.id)
        case_file.stage = stage
    if 'position' in data:
        case_file.position = int(data['position'])
    db.session.commit()
    return jsonify(case_file.to_dict())


@bp.route('/case-files/<int:case_id>', methods=['DELETE'])
@jwt_required
@require_permission('case_files.delete')
def delete_case_file(case_id):
    case_file = CaseFile.query.filter_by(id=case_id, firm_id=g.firm_id).first()
    if not case_file:
        return jsonify({'error': 'Case not found'}), 404
    db.session.delete(case_file)
    db.session.commit()
    return jsonify({'message': 'Case deleted'})


@bp.route('/case-files/<int:case_id>/stage-history', methods=['GET'])
@jwt_required
@require_permission('case_files.read')
def stage_history(case_id):
    case_file = CaseFile.query.filter_by(id=case_id, firm_id=g.firm_id).first()
    if not case_file:
        return jsonify({'error': 'Case not found'}), 404
    rows = (CaseStageChange.query.filter_by(case_file_id=case_id)
            .order_by(CaseStageChange.changed_at.asc(), CaseStageChange.id.asc()).all())
    return jsonify([r.to_dict() for r in rows])
