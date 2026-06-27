"""Case evidence exhibit-register API. Firm-scoped, gated by case_files
permissions. Exhibits are stored as case_documents rows flagged is_exhibit."""
from flask import Blueprint, request, jsonify, g
from app.models.models import db
from app.models.case import CaseFile, CaseDocument
from app.middleware.jwt_auth import jwt_required
from app.middleware.firm_context import require_permission
from app.case.exhibits import DEFAULT_EXHIBIT_STATUS, is_valid_exhibit_status

bp = Blueprint('case_exhibits', __name__)


def _case_or_404(case_id):
    return CaseFile.query.filter_by(id=case_id, firm_id=g.firm_id).first()


def _exhibit_or_404(exhibit_id):
    return CaseDocument.query.filter_by(id=exhibit_id, firm_id=g.firm_id, is_exhibit=True).first()


def _apply(ex, data):
    if 'exhibit_mark' in data:
        ex.exhibit_mark = data['exhibit_mark']
    if 'description' in data:
        ex.description = data['description']
        ex.title = data['description'] or ex.exhibit_mark or 'Exhibit'
    if 'party' in data:
        ex.party = data['party']
    if 'document_id' in data:
        ex.linked_document_id = data['document_id']
    if 'hearing_event_id' in data:
        ex.hearing_event_id = data['hearing_event_id']


@bp.route('/case-files/<int:case_id>/exhibits', methods=['GET'])
@jwt_required
@require_permission('case_files.read')
def list_exhibits(case_id):
    if not _case_or_404(case_id):
        return jsonify({'error': 'Case not found'}), 404
    rows = (CaseDocument.query.filter_by(case_file_id=case_id, is_exhibit=True)
            .order_by(CaseDocument.id).all())
    return jsonify([e.exhibit_to_dict() for e in rows])


@bp.route('/case-files/<int:case_id>/exhibits', methods=['POST'])
@jwt_required
@require_permission('case_files.update')
def create_exhibit(case_id):
    if not _case_or_404(case_id):
        return jsonify({'error': 'Case not found'}), 404
    data = request.get_json() or {}
    status = data.get('status', DEFAULT_EXHIBIT_STATUS)
    if not is_valid_exhibit_status(status):
        return jsonify({'error': 'Invalid status'}), 400
    ex = CaseDocument(firm_id=g.firm_id, case_file_id=case_id, uploaded_by_user_id=g.user.id,
                      doc_type='evidence', is_exhibit=True, exhibit_status=status,
                      title='Exhibit')
    _apply(ex, data)
    db.session.add(ex)
    db.session.commit()
    return jsonify(ex.exhibit_to_dict()), 201


@bp.route('/case-exhibits/<int:exhibit_id>', methods=['PATCH'])
@jwt_required
@require_permission('case_files.update')
def update_exhibit(exhibit_id):
    ex = _exhibit_or_404(exhibit_id)
    if not ex:
        return jsonify({'error': 'Exhibit not found'}), 404
    data = request.get_json() or {}
    if 'status' in data:
        if not is_valid_exhibit_status(data['status']):
            return jsonify({'error': 'Invalid status'}), 400
        ex.exhibit_status = data['status']
    _apply(ex, data)
    db.session.commit()
    return jsonify(ex.exhibit_to_dict())


@bp.route('/case-exhibits/<int:exhibit_id>', methods=['DELETE'])
@jwt_required
@require_permission('case_files.update')
def delete_exhibit(exhibit_id):
    ex = _exhibit_or_404(exhibit_id)
    if not ex:
        return jsonify({'error': 'Exhibit not found'}), 404
    db.session.delete(ex)
    db.session.commit()
    return jsonify({'message': 'Exhibit deleted'})
