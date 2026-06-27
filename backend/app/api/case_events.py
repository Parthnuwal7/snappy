"""Case timeline (case_events) API — the diary 'steps'. Firm-scoped."""
from datetime import datetime
from flask import Blueprint, request, jsonify, g
from app.models.models import db
from app.models.case import CaseFile, CaseEvent
from app.middleware.jwt_auth import jwt_required
from app.middleware.firm_context import require_permission
from app.case.stages import is_valid_event_kind
from app.services.case_service import recompute_next_hearing_date

bp = Blueprint('case_events', __name__)


def _parse_date(value):
    return datetime.fromisoformat(value).date() if value else None


@bp.route('/case-files/<int:case_id>/events', methods=['GET'])
@jwt_required
@require_permission('case_files.read')
def list_events(case_id):
    case_file = CaseFile.query.filter_by(id=case_id, firm_id=g.firm_id).first()
    if not case_file:
        return jsonify({'error': 'Case not found'}), 404
    events = (CaseEvent.query
              .filter_by(case_file_id=case_id)
              .order_by(CaseEvent.event_date.asc(), CaseEvent.id.asc())
              .all())
    return jsonify([e.to_dict() for e in events])


@bp.route('/case-files/<int:case_id>/events', methods=['POST'])
@jwt_required
@require_permission('case_files.update')
def add_event(case_id):
    case_file = CaseFile.query.filter_by(id=case_id, firm_id=g.firm_id).first()
    if not case_file:
        return jsonify({'error': 'Case not found'}), 404
    data = request.get_json() or {}
    title = (data.get('title') or '').strip()
    if not title:
        return jsonify({'error': 'Title is required'}), 400
    event_date = _parse_date(data.get('event_date'))
    if not event_date:
        return jsonify({'error': 'event_date is required'}), 400
    kind = data.get('kind', 'note')
    if not is_valid_event_kind(kind):
        return jsonify({'error': 'Invalid kind'}), 400

    event = CaseEvent(
        case_file_id=case_id,
        firm_id=g.firm_id,
        created_by_user_id=g.user.id,
        event_date=event_date,
        kind=kind,
        title=title,
        notes=data.get('notes'),
        purpose=data.get('purpose'),
        outcome=data.get('outcome'),
    )
    db.session.add(event)
    db.session.flush()
    recompute_next_hearing_date(case_file)
    db.session.commit()
    return jsonify(event.to_dict()), 201


@bp.route('/case-events/<int:event_id>', methods=['PATCH'])
@jwt_required
@require_permission('case_files.update')
def update_event(event_id):
    event = CaseEvent.query.filter_by(id=event_id, firm_id=g.firm_id).first()
    if not event:
        return jsonify({'error': 'Event not found'}), 404
    data = request.get_json() or {}
    if 'kind' in data:
        if not is_valid_event_kind(data['kind']):
            return jsonify({'error': 'Invalid kind'}), 400
        event.kind = data['kind']
    if 'title' in data:
        event.title = (data['title'] or '').strip() or event.title
    if 'notes' in data:
        event.notes = data['notes']
    if 'event_date' in data:
        parsed = _parse_date(data['event_date'])
        if parsed:
            event.event_date = parsed
    if 'purpose' in data:
        event.purpose = data['purpose']
    if 'outcome' in data:
        event.outcome = data['outcome']
    recompute_next_hearing_date(event.case_file)
    db.session.commit()
    return jsonify(event.to_dict())


@bp.route('/case-events/<int:event_id>', methods=['DELETE'])
@jwt_required
@require_permission('case_files.update')
def delete_event(event_id):
    event = CaseEvent.query.filter_by(id=event_id, firm_id=g.firm_id).first()
    if not event:
        return jsonify({'error': 'Event not found'}), 404
    case_file = event.case_file
    # Documents pinned to this step survive — detach them from the deleted step.
    from app.models.case import CaseDocument, CaseNote
    CaseDocument.query.filter_by(event_id=event.id).update({'event_id': None})
    CaseNote.query.filter_by(event_id=event.id).update({'event_id': None})
    # Exhibit rows (case_documents) that came in through this hearing keep their record.
    CaseDocument.query.filter_by(hearing_event_id=event.id).update({'hearing_event_id': None})
    db.session.delete(event)
    db.session.flush()
    recompute_next_hearing_date(case_file)
    db.session.commit()
    return jsonify({'message': 'Event deleted'})


def _hearing_or_create_next(case_id, next_date, purpose):
    """Return (or create) the soonest future hearing for the case, set to next_date."""
    from datetime import date
    upcoming = (CaseEvent.query
                .filter(CaseEvent.case_file_id == case_id, CaseEvent.kind == 'hearing',
                        CaseEvent.event_date >= date.today())
                .order_by(CaseEvent.event_date.asc()).first())
    if upcoming:
        upcoming.event_date = next_date
        if purpose is not None:
            upcoming.purpose = purpose
        return upcoming
    ev = CaseEvent(case_file_id=case_id, firm_id=g.firm_id, created_by_user_id=g.user.id,
                   event_date=next_date, kind='hearing', title='Hearing', purpose=purpose)
    db.session.add(ev)
    return ev


@bp.route('/case-files/<int:case_id>/proceedings', methods=['POST'])
@jwt_required
@require_permission('case_files.update')
def record_proceedings(case_id):
    case_file = CaseFile.query.filter_by(id=case_id, firm_id=g.firm_id).first()
    if not case_file:
        return jsonify({'error': 'Case not found'}), 404
    data = request.get_json() or {}
    next_date = _parse_date(data.get('next_date'))
    if not next_date:
        return jsonify({'error': 'next_date is required'}), 400

    current_event_id = data.get('current_event_id')
    if current_event_id:
        cur = CaseEvent.query.filter_by(id=current_event_id, case_file_id=case_id).first()
        if cur:
            cur.outcome = data.get('outcome')

    new_ev = CaseEvent(case_file_id=case_id, firm_id=g.firm_id, created_by_user_id=g.user.id,
                       event_date=next_date, kind='hearing',
                       title=(data.get('purpose') or 'Hearing'), purpose=data.get('purpose'))
    db.session.add(new_ev)
    db.session.flush()
    recompute_next_hearing_date(case_file)
    db.session.commit()
    return jsonify({'case_file': case_file.to_dict(), 'next_event': new_ev.to_dict()})


@bp.route('/case-files/<int:case_id>/next-date', methods=['POST'])
@jwt_required
@require_permission('case_files.update')
def set_next_date(case_id):
    case_file = CaseFile.query.filter_by(id=case_id, firm_id=g.firm_id).first()
    if not case_file:
        return jsonify({'error': 'Case not found'}), 404
    data = request.get_json() or {}
    next_date = _parse_date(data.get('next_date'))
    if not next_date:
        return jsonify({'error': 'next_date is required'}), 400
    _hearing_or_create_next(case_id, next_date, data.get('purpose'))
    db.session.flush()
    recompute_next_hearing_date(case_file)
    db.session.commit()
    return jsonify(case_file.to_dict())
