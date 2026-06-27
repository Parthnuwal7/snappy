"""Case expenses + financial summary — firm-scoped, gated by case_files perms."""
from datetime import datetime
from flask import Blueprint, request, jsonify, g
from sqlalchemy import func
from app.models.models import db, Invoice, _money
from app.models.case import CaseFile, CaseExpense
from app.middleware.jwt_auth import jwt_required
from app.middleware.firm_context import require_permission
from app.case.expenses import DEFAULT_EXPENSE_CATEGORY, is_valid_expense_category

bp = Blueprint('case_expenses', __name__)


def _parse_date(v):
    return datetime.fromisoformat(v).date() if v else None


def _case_or_404(case_id):
    return CaseFile.query.filter_by(id=case_id, firm_id=g.firm_id).first()


@bp.route('/case-files/<int:case_id>/expenses', methods=['GET'])
@jwt_required
@require_permission('case_files.read')
def list_expenses(case_id):
    if not _case_or_404(case_id):
        return jsonify({'error': 'Case not found'}), 404
    rows = (CaseExpense.query.filter_by(case_file_id=case_id)
            .order_by(CaseExpense.expense_date.desc(), CaseExpense.id.desc()).all())
    return jsonify([r.to_dict() for r in rows])


@bp.route('/case-files/<int:case_id>/expenses', methods=['POST'])
@jwt_required
@require_permission('case_files.update')
def add_expense(case_id):
    if not _case_or_404(case_id):
        return jsonify({'error': 'Case not found'}), 404
    data = request.get_json() or {}
    description = (data.get('description') or '').strip()
    if not description:
        return jsonify({'error': 'Description is required'}), 400
    category = data.get('category') or DEFAULT_EXPENSE_CATEGORY
    if not is_valid_expense_category(category):
        return jsonify({'error': 'Invalid category'}), 400
    exp = CaseExpense(
        firm_id=g.firm_id, case_file_id=case_id,
        expense_date=_parse_date(data.get('expense_date')),
        description=description, category=category,
        amount=data.get('amount') or 0, created_by_user_id=g.user.id)
    db.session.add(exp)
    db.session.commit()
    return jsonify(exp.to_dict()), 201


@bp.route('/case-expenses/<int:expense_id>', methods=['PATCH'])
@jwt_required
@require_permission('case_files.update')
def update_expense(expense_id):
    exp = CaseExpense.query.filter_by(id=expense_id, firm_id=g.firm_id).first()
    if not exp:
        return jsonify({'error': 'Expense not found'}), 404
    data = request.get_json() or {}
    if 'description' in data:
        exp.description = (data['description'] or '').strip() or exp.description
    if 'category' in data:
        if not is_valid_expense_category(data['category']):
            return jsonify({'error': 'Invalid category'}), 400
        exp.category = data['category']
    if 'amount' in data:
        exp.amount = data['amount'] or 0
    if 'expense_date' in data:
        exp.expense_date = _parse_date(data['expense_date'])
    db.session.commit()
    return jsonify(exp.to_dict())


@bp.route('/case-expenses/<int:expense_id>', methods=['DELETE'])
@jwt_required
@require_permission('case_files.update')
def delete_expense(expense_id):
    exp = CaseExpense.query.filter_by(id=expense_id, firm_id=g.firm_id).first()
    if not exp:
        return jsonify({'error': 'Expense not found'}), 404
    db.session.delete(exp)
    db.session.commit()
    return jsonify({'message': 'Expense deleted'})


@bp.route('/case-files/<int:case_id>/financials', methods=['GET'])
@jwt_required
@require_permission('case_files.read')
def financials(case_id):
    case_file = _case_or_404(case_id)
    if not case_file:
        return jsonify({'error': 'Case not found'}), 404
    total_expenses = db.session.query(func.coalesce(func.sum(CaseExpense.amount), 0)) \
        .filter(CaseExpense.case_file_id == case_id).scalar()
    total_invoiced = db.session.query(func.coalesce(func.sum(Invoice.total), 0)) \
        .filter(Invoice.case_file_id == case_id).scalar()
    total_paid = db.session.query(func.coalesce(func.sum(Invoice.total), 0)) \
        .filter(Invoice.case_file_id == case_id, Invoice.status == 'paid').scalar()
    return jsonify({
        'agreed_fee': _money(case_file.agreed_fee),
        'total_expenses': _money(total_expenses),
        'total_invoiced': _money(total_invoiced),
        'total_paid': _money(total_paid),
        'outstanding': _money(total_invoiced - total_paid),
    })
