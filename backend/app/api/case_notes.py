"""Case notes API — the running-commentary stream. Firm-scoped, gated by
case_files permissions (read = list, update = create/edit/delete)."""
from flask import Blueprint, request, jsonify, g
from app.models.models import db
from app.models.case import CaseFile, CaseNote
from app.middleware.jwt_auth import jwt_required
from app.middleware.firm_context import require_permission

bp = Blueprint('case_notes', __name__)

LINK_FIELDS = ('event_id', 'document_id')


def _case_or_404(case_id):
    return CaseFile.query.filter_by(id=case_id, firm_id=g.firm_id).first()


def _note_or_404(note_id):
    return CaseNote.query.filter_by(id=note_id, firm_id=g.firm_id).first()


@bp.route('/case-files/<int:case_id>/notes', methods=['GET'])
@jwt_required
@require_permission('case_files.read')
def list_notes(case_id):
    if not _case_or_404(case_id):
        return jsonify({'error': 'Case not found'}), 404
    notes = (CaseNote.query.filter_by(case_file_id=case_id)
             .order_by(CaseNote.pinned.desc(), CaseNote.id.desc()).all())
    return jsonify([n.to_dict() for n in notes])


@bp.route('/case-files/<int:case_id>/notes', methods=['POST'])
@jwt_required
@require_permission('case_files.update')
def create_note(case_id):
    if not _case_or_404(case_id):
        return jsonify({'error': 'Case not found'}), 404
    data = request.get_json() or {}
    body = (data.get('body') or '').strip()
    if not body:
        return jsonify({'error': 'Note body is required'}), 400
    note = CaseNote(firm_id=g.firm_id, case_file_id=case_id, created_by_user_id=g.user.id,
                    body=body, pinned=bool(data.get('pinned', False)),
                    event_id=data.get('event_id'), document_id=data.get('document_id'))
    db.session.add(note)
    db.session.commit()
    return jsonify(note.to_dict()), 201


@bp.route('/case-notes/<int:note_id>', methods=['PATCH'])
@jwt_required
@require_permission('case_files.update')
def update_note(note_id):
    note = _note_or_404(note_id)
    if not note:
        return jsonify({'error': 'Note not found'}), 404
    data = request.get_json() or {}
    if 'body' in data:
        body = (data['body'] or '').strip()
        if not body:
            return jsonify({'error': 'Note body is required'}), 400
        note.body = body
    if 'pinned' in data:
        note.pinned = bool(data['pinned'])
    for field in LINK_FIELDS:
        if field in data:
            setattr(note, field, data[field])
    db.session.commit()
    return jsonify(note.to_dict())


@bp.route('/case-notes/<int:note_id>', methods=['DELETE'])
@jwt_required
@require_permission('case_files.update')
def delete_note(note_id):
    note = _note_or_404(note_id)
    if not note:
        return jsonify({'error': 'Note not found'}), 404
    db.session.delete(note)
    db.session.commit()
    return jsonify({'message': 'Note deleted'})
