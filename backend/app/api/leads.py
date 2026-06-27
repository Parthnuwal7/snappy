"""Lead / Enquiry API — firm-scoped, gated by the leads RBAC module."""
from datetime import datetime, date
from flask import Blueprint, request, jsonify, g
from app.models.models import db, Client
from app.models.lead import Lead, LEAD_STATUSES
from app.models.case import CaseFile, CaseNote
from app.middleware.jwt_auth import jwt_required
from app.middleware.firm_context import require_permission
from app.services.case_service import generate_case_number, record_stage_change
from app.case.stages import DEFAULT_STAGE

bp = Blueprint('leads', __name__)

EDITABLE = ('contact_name', 'phone', 'email', 'matter_summary', 'intake_notes')


def _get_owned(lead_id):
    return Lead.query.filter_by(id=lead_id, firm_id=g.firm_id).first()


@bp.route('/leads', methods=['GET'])
@jwt_required
@require_permission('leads.read')
def list_leads():
    query = Lead.query.filter_by(firm_id=g.firm_id)
    status = request.args.get('status')
    if status:
        query = query.filter_by(status=status)
    leads = query.order_by(Lead.id.desc()).all()
    return jsonify([l.to_dict() for l in leads])


@bp.route('/leads', methods=['POST'])
@jwt_required
@require_permission('leads.create')
def create_lead():
    data = request.get_json() or {}
    name = (data.get('contact_name') or '').strip()
    if not name:
        return jsonify({'error': 'Contact name is required'}), 400
    lead = Lead(firm_id=g.firm_id, created_by_user_id=g.user.id, contact_name=name,
                phone=data.get('phone'), email=data.get('email'),
                matter_summary=data.get('matter_summary'),
                intake_notes=data.get('intake_notes'))
    db.session.add(lead)
    db.session.commit()
    return jsonify(lead.to_dict()), 201


@bp.route('/leads/<int:lead_id>', methods=['GET'])
@jwt_required
@require_permission('leads.read')
def get_lead(lead_id):
    lead = _get_owned(lead_id)
    if not lead:
        return jsonify({'error': 'Lead not found'}), 404
    return jsonify(lead.to_dict())


@bp.route('/leads/<int:lead_id>', methods=['PATCH'])
@jwt_required
@require_permission('leads.update')
def update_lead(lead_id):
    lead = _get_owned(lead_id)
    if not lead:
        return jsonify({'error': 'Lead not found'}), 404
    data = request.get_json() or {}
    for field in EDITABLE:
        if field in data:
            setattr(lead, field, data[field])
    if 'status' in data:
        status = data['status']
        if status not in LEAD_STATUSES:
            return jsonify({'error': 'Invalid status'}), 400
        # Acceptance only happens through /convert.
        if status == 'accepted':
            return jsonify({'error': 'Accept a lead via /convert'}), 400
        lead.status = status
        lead.decided_at = datetime.utcnow() if status == 'declined' else None
    db.session.commit()
    return jsonify(lead.to_dict())


@bp.route('/leads/<int:lead_id>', methods=['DELETE'])
@jwt_required
@require_permission('leads.delete')
def delete_lead(lead_id):
    lead = _get_owned(lead_id)
    if not lead:
        return jsonify({'error': 'Lead not found'}), 404
    db.session.delete(lead)
    db.session.commit()
    return jsonify({'ok': True})


@bp.route('/leads/<int:lead_id>/convert', methods=['POST'])
@jwt_required
@require_permission('leads.update')
def convert_lead(lead_id):
    lead = _get_owned(lead_id)
    if not lead:
        return jsonify({'error': 'Lead not found'}), 404
    if lead.status != 'open':
        return jsonify({'error': 'Lead already decided'}), 400
    data = request.get_json() or {}

    # Resolve the client: reuse an existing firm client or create one from contact.
    client_id = data.get('client_id')
    if client_id:
        client_row = Client.query.filter_by(id=client_id, firm_id=g.firm_id).first()
        if not client_row:
            return jsonify({'error': 'Client not found'}), 404
    else:
        client_row = Client(firm_id=g.firm_id, created_by_user_id=g.user.id,
                            name=lead.contact_name, email=lead.email, phone=lead.phone)
        db.session.add(client_row)
        db.session.flush()

    title = (data.get('title') or lead.matter_summary or lead.contact_name or 'Untitled matter').strip()[:300]
    case_file = CaseFile(
        firm_id=g.firm_id, created_by_user_id=g.user.id,
        case_number=generate_case_number(g.firm_id), title=title,
        client_id=client_row.id, stage=DEFAULT_STAGE, lead_id=lead.id)
    db.session.add(case_file)
    db.session.flush()
    record_stage_change(case_file, None, case_file.stage, g.user.id)

    if (lead.intake_notes or '').strip():
        db.session.add(CaseNote(
            firm_id=g.firm_id, case_file_id=case_file.id, created_by_user_id=g.user.id,
            body=lead.intake_notes, pinned=True))

    lead.status = 'accepted'
    lead.decided_at = datetime.utcnow()
    lead.converted_case_file_id = case_file.id
    db.session.commit()
    return jsonify(case_file.to_dict(include_parties=True)), 201
