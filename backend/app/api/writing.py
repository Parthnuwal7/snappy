"""Writing API — templates + drafts (one writing_documents table) + meta. Firm-scoped."""
from flask import Blueprint, request, jsonify, g
from sqlalchemy.orm import selectinload
from app.models.models import db
from app.models.writing import WritingDoc
from app.middleware.jwt_auth import jwt_required
from app.middleware.firm_context import require_permission
from app.utils.pagination import pagination_requested, get_pagination_args, paginate_query
from app.writing.merge import MERGE_FIELDS, TEMPLATE_CATEGORIES
from app.writing.builtin import BUILTIN_TEMPLATES

bp = Blueprint('writing', __name__)


def _owned(doc_id, kind):
    return WritingDoc.query.filter_by(id=doc_id, firm_id=g.firm_id, kind=kind).first()


@bp.route('/writing/meta', methods=['GET'])
@jwt_required
@require_permission('drafts.read')
def writing_meta():
    return jsonify({'merge_fields': MERGE_FIELDS, 'template_categories': TEMPLATE_CATEGORIES,
                    'builtin_templates': BUILTIN_TEMPLATES})


# ---- Templates (kind='template') ----
@bp.route('/templates', methods=['GET'])
@jwt_required
@require_permission('templates.read')
def list_templates():
    q = WritingDoc.query.filter_by(firm_id=g.firm_id, kind='template').order_by(WritingDoc.id.desc())
    serialize = lambda t: t.to_template_dict()
    if pagination_requested():
        page, page_size = get_pagination_args()
        return jsonify(paginate_query(q, page, page_size, serialize))
    return jsonify([serialize(t) for t in q.all()])


@bp.route('/templates', methods=['POST'])
@jwt_required
@require_permission('templates.create')
def create_template():
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'error': 'Name is required'}), 400
    t = WritingDoc(firm_id=g.firm_id, created_by_user_id=g.user.id, kind='template',
                   title=name, category=data.get('category', 'other'), body=data.get('body', ''))
    db.session.add(t); db.session.commit()
    return jsonify(t.to_template_dict()), 201


@bp.route('/templates/<int:tid>', methods=['GET'])
@jwt_required
@require_permission('templates.read')
def get_template(tid):
    t = _owned(tid, 'template')
    return (jsonify(t.to_template_dict()) if t else (jsonify({'error': 'Not found'}), 404))


@bp.route('/templates/<int:tid>', methods=['PATCH'])
@jwt_required
@require_permission('templates.update')
def update_template(tid):
    t = _owned(tid, 'template')
    if not t:
        return jsonify({'error': 'Not found'}), 404
    data = request.get_json() or {}
    if 'name' in data:
        t.title = data['name']
    for f in ('category', 'body'):
        if f in data:
            setattr(t, f, data[f])
    db.session.commit()
    return jsonify(t.to_template_dict())


@bp.route('/templates/<int:tid>', methods=['DELETE'])
@jwt_required
@require_permission('templates.delete')
def delete_template(tid):
    t = _owned(tid, 'template')
    if not t:
        return jsonify({'error': 'Not found'}), 404
    db.session.delete(t); db.session.commit()
    return jsonify({'message': 'Template deleted'})


# ---- Drafts (kind='draft') ----
@bp.route('/drafts', methods=['GET'])
@jwt_required
@require_permission('drafts.read')
def list_drafts():
    # Eager-load case_file so to_draft_dict()'s case_number/case_title don't N+1.
    q = WritingDoc.query.options(selectinload(WritingDoc.case_file)).filter_by(
        firm_id=g.firm_id, kind='draft')
    case_file_id = request.args.get('case_file_id', type=int)
    if case_file_id:
        q = q.filter_by(case_file_id=case_file_id)
    q = q.order_by(WritingDoc.id.desc())
    serialize = lambda d: d.to_draft_dict()
    if pagination_requested():
        page, page_size = get_pagination_args()
        return jsonify(paginate_query(q, page, page_size, serialize))
    return jsonify([serialize(d) for d in q.all()])


@bp.route('/drafts', methods=['POST'])
@jwt_required
@require_permission('drafts.create')
def create_draft():
    data = request.get_json() or {}
    title = (data.get('title') or '').strip()
    if not title:
        return jsonify({'error': 'Title is required'}), 400
    d = WritingDoc(firm_id=g.firm_id, created_by_user_id=g.user.id, kind='draft',
                   title=title, body=data.get('body', ''), case_file_id=data.get('case_file_id'))
    db.session.add(d); db.session.commit()
    return jsonify(d.to_draft_dict()), 201


@bp.route('/drafts/<int:did>', methods=['GET'])
@jwt_required
@require_permission('drafts.read')
def get_draft(did):
    d = _owned(did, 'draft')
    return (jsonify(d.to_draft_dict()) if d else (jsonify({'error': 'Not found'}), 404))


@bp.route('/drafts/<int:did>', methods=['PATCH'])
@jwt_required
@require_permission('drafts.update')
def update_draft(did):
    d = _owned(did, 'draft')
    if not d:
        return jsonify({'error': 'Not found'}), 404
    data = request.get_json() or {}
    for f in ('title', 'body', 'case_file_id'):
        if f in data:
            setattr(d, f, data[f])
    db.session.commit()
    return jsonify(d.to_draft_dict())


@bp.route('/drafts/<int:did>', methods=['DELETE'])
@jwt_required
@require_permission('drafts.delete')
def delete_draft(did):
    d = _owned(did, 'draft')
    if not d:
        return jsonify({'error': 'Not found'}), 404
    db.session.delete(d); db.session.commit()
    return jsonify({'message': 'Draft deleted'})
