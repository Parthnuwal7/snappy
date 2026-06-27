"""Case document vault API — firm-scoped, gated by the documents RBAC module."""
from flask import Blueprint, request, jsonify, g
from app.models.models import db
from app.models.case import CaseFile, CaseEvent, CaseDocument
from app.middleware.jwt_auth import jwt_required
from app.middleware.firm_context import require_permission
from app.services import document_storage
from app.case.documents import (
    DEFAULT_DOC_TYPE, MAX_DOCUMENT_BYTES, is_valid_doc_type,
    is_allowed_filename, extension_of,
)

bp = Blueprint('case_documents', __name__)


def _doc_or_404(doc_id):
    return CaseDocument.query.filter_by(id=doc_id, firm_id=g.firm_id).first()


@bp.route('/case-files/<int:case_id>/documents', methods=['GET'])
@jwt_required
@require_permission('documents.read')
def list_documents(case_id):
    case_file = CaseFile.query.filter_by(id=case_id, firm_id=g.firm_id).first()
    if not case_file:
        return jsonify({'error': 'Case not found'}), 404
    query = CaseDocument.query.filter_by(case_file_id=case_id).filter(
        CaseDocument.is_exhibit.isnot(True))  # exhibit-register rows live in the Evidence tab
    doc_type = request.args.get('doc_type')
    event_id = request.args.get('event_id', type=int)
    if doc_type:
        query = query.filter_by(doc_type=doc_type)
    if event_id:
        query = query.filter_by(event_id=event_id)
    docs = query.order_by(CaseDocument.created_at.desc(), CaseDocument.id.desc()).all()
    return jsonify([d.to_dict() for d in docs])


@bp.route('/case-files/<int:case_id>/documents', methods=['POST'])
@jwt_required
@require_permission('documents.create')
def upload_document(case_id):
    case_file = CaseFile.query.filter_by(id=case_id, firm_id=g.firm_id).first()
    if not case_file:
        return jsonify({'error': 'Case not found'}), 404

    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    upload = request.files['file']
    if not upload.filename:
        return jsonify({'error': 'No file selected'}), 400
    if not is_allowed_filename(upload.filename):
        return jsonify({'error': 'File type not allowed'}), 400

    title = (request.form.get('title') or '').strip()
    if not title:
        return jsonify({'error': 'Title is required'}), 400
    doc_type = request.form.get('doc_type') or DEFAULT_DOC_TYPE
    if not is_valid_doc_type(doc_type):
        return jsonify({'error': 'Invalid doc_type'}), 400

    event_id = request.form.get('event_id', type=int)
    if event_id:
        event = CaseEvent.query.filter_by(id=event_id, case_file_id=case_id).first()
        if not event:
            return jsonify({'error': 'Timeline step not found for this case'}), 400

    data = upload.read()
    if len(data) > MAX_DOCUMENT_BYTES:
        return jsonify({'error': 'File too large (max 25MB)'}), 400

    ext = extension_of(upload.filename)
    storage_path = document_storage.build_storage_path(g.firm_id, case_id, ext)
    try:
        document_storage.put_object(storage_path, data, upload.mimetype)
    except document_storage.StorageError as e:
        return jsonify({'error': str(e)}), 503

    doc = CaseDocument(
        firm_id=g.firm_id, case_file_id=case_id, event_id=event_id,
        uploaded_by_user_id=g.user.id, title=title, doc_type=doc_type,
        file_name=upload.filename, mime_type=upload.mimetype,
        size_bytes=len(data), storage_path=storage_path,
        description=request.form.get('description'),
    )
    db.session.add(doc)
    db.session.commit()
    return jsonify(doc.to_dict()), 201


@bp.route('/case-documents/<int:doc_id>/download', methods=['GET'])
@jwt_required
@require_permission('documents.read')
def download_document(doc_id):
    doc = _doc_or_404(doc_id)
    if not doc:
        return jsonify({'error': 'Document not found'}), 404
    try:
        url = document_storage.signed_url(doc.storage_path)
    except document_storage.StorageError as e:
        return jsonify({'error': str(e)}), 503
    return jsonify({'url': url})


@bp.route('/case-documents/<int:doc_id>', methods=['PATCH'])
@jwt_required
@require_permission('documents.update')
def update_document(doc_id):
    doc = _doc_or_404(doc_id)
    if not doc:
        return jsonify({'error': 'Document not found'}), 404
    data = request.get_json() or {}
    if 'title' in data:
        doc.title = (data['title'] or '').strip() or doc.title
    if 'doc_type' in data:
        if not is_valid_doc_type(data['doc_type']):
            return jsonify({'error': 'Invalid doc_type'}), 400
        doc.doc_type = data['doc_type']
    if 'description' in data:
        doc.description = data['description']
    if 'event_id' in data:
        if data['event_id'] is None:
            doc.event_id = None
        else:
            event = CaseEvent.query.filter_by(id=data['event_id'],
                                              case_file_id=doc.case_file_id).first()
            if not event:
                return jsonify({'error': 'Timeline step not found for this case'}), 400
            doc.event_id = event.id
    db.session.commit()
    return jsonify(doc.to_dict())


@bp.route('/case-documents/<int:doc_id>', methods=['DELETE'])
@jwt_required
@require_permission('documents.delete')
def delete_document(doc_id):
    doc = _doc_or_404(doc_id)
    if not doc:
        return jsonify({'error': 'Document not found'}), 404
    try:
        document_storage.remove_object(doc.storage_path)
    except document_storage.StorageError:
        pass  # best-effort; still drop the row
    from app.models.case import CaseNote
    CaseNote.query.filter_by(document_id=doc.id).update({'document_id': None})
    # Exhibit rows that referenced this file (linked_document_id) keep their record.
    CaseDocument.query.filter_by(linked_document_id=doc.id).update({'linked_document_id': None})
    db.session.delete(doc)
    db.session.commit()
    return jsonify({'message': 'Document deleted'})
