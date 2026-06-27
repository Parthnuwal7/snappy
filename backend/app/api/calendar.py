"""Firm-wide hearing calendar — aggregates case_events of kind 'hearing'."""
from datetime import date, timedelta, datetime
from flask import Blueprint, request, jsonify, g
from app.models.models import db
from app.models.case import CaseEvent, CaseFile
from app.middleware.jwt_auth import jwt_required
from app.middleware.firm_context import require_permission

bp = Blueprint('calendar', __name__)


def _parse(value, fallback):
    try:
        return datetime.fromisoformat(value).date() if value else fallback
    except ValueError:
        return fallback


@bp.route('/calendar', methods=['GET'])
@jwt_required
@require_permission('case_files.read')
def calendar():
    today = date.today()
    start = _parse(request.args.get('from'), today)
    end = _parse(request.args.get('to'), today + timedelta(days=60))
    rows = (db.session.query(CaseEvent, CaseFile)
            .join(CaseFile, CaseEvent.case_file_id == CaseFile.id)
            .filter(CaseEvent.firm_id == g.firm_id, CaseEvent.kind == 'hearing',
                    CaseEvent.event_date >= start, CaseEvent.event_date <= end)
            .order_by(CaseEvent.event_date.asc(), CaseEvent.id.asc())
            .all())
    out = []
    for ev, cf in rows:
        out.append({
            'event_id': ev.id,
            'case_file_id': cf.id,
            'case_number': cf.case_number,
            'case_title': cf.title,
            'court': cf.court,
            'client_name': cf.client.name if cf.client else None,
            'event_date': ev.event_date.isoformat() if ev.event_date else None,
            'title': ev.title,
            'purpose': ev.purpose,
            'outcome': ev.outcome,
        })
    return jsonify(out)
