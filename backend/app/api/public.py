"""Public, unauthenticated invoice endpoints.

These power the hosted invoice page that clients open via a signed link. Access
is gated by the HMAC signature in `invoice_links`, not by JWT — anyone with a
valid link may view that one invoice. Only a safe subset of fields is exposed.
"""
import io
from flask import Blueprint, request, jsonify, send_file

from app.models.models import Invoice
from app.models.auth import User, BankAccount
from app.utils.invoice_links import verify
from sqlalchemy.orm import joinedload

bp = Blueprint('public', __name__)


def _load_verified_invoice(user_id, invoice_id, sig):
    """Return the invoice if the signature is valid and it's viewable, else None."""
    if not verify(user_id, invoice_id, sig):
        return None
    invoice = Invoice.query.options(
        joinedload(Invoice.client),
        joinedload(Invoice.items),
    ).filter_by(id=invoice_id, created_by_user_id=user_id).first()
    if not invoice or invoice.status == 'void':
        return None
    return invoice


def _public_dict(invoice, firm, bank):
    """Safe, client-facing view of an invoice."""
    return {
        'invoice_number': invoice.invoice_number,
        'invoice_date': invoice.invoice_date.isoformat() if invoice.invoice_date else None,
        'due_date': invoice.due_date.isoformat() if invoice.due_date else None,
        'status': invoice.status,
        'short_desc': invoice.short_desc,
        'subtotal': float(invoice.subtotal) if invoice.subtotal is not None else None,
        'tax_rate': float(invoice.tax_rate) if invoice.tax_rate is not None else None,
        'tax_amount': float(invoice.tax_amount) if invoice.tax_amount is not None else None,
        'total': float(invoice.total) if invoice.total is not None else None,
        'client_name': invoice.client.name if invoice.client else None,
        'items': [it.to_dict() for it in invoice.items],
        'firm': {
            'firm_name': firm.firm_name if firm else None,
            'firm_address': firm.firm_address if firm else None,
            'firm_email': firm.firm_email if firm else None,
            'firm_phone': firm.firm_phone if firm else None,
            'firm_website': firm.firm_website if firm else None,
        } if firm else None,
        'payment': {
            'upi_id': bank.upi_id if bank else None,
            'bank_name': bank.bank_name if bank else None,
            'account_number': bank.account_number if bank else None,
            'ifsc_code': bank.ifsc_code if bank else None,
            'account_holder_name': bank.account_holder_name if bank else None,
        } if bank else None,
    }


@bp.route('/public/invoices/<int:user_id>/<int:invoice_id>', methods=['GET'])
def public_invoice(user_id, invoice_id):
    sig = request.args.get('sig', '')
    invoice = _load_verified_invoice(user_id, invoice_id, sig)
    if not invoice:
        return jsonify({'error': 'Not found'}), 404 if verify(user_id, invoice_id, sig) else 403

    user = User.query.get(user_id)
    firm = user.firm_details if user else None
    bank = BankAccount.query.filter_by(user_id=user_id, is_default=True).first()
    return jsonify(_public_dict(invoice, firm, bank))


@bp.route('/public/invoices/<int:user_id>/<int:invoice_id>/pdf', methods=['GET'])
def public_invoice_pdf(user_id, invoice_id):
    sig = request.args.get('sig', '')
    invoice = _load_verified_invoice(user_id, invoice_id, sig)
    if not invoice:
        return jsonify({'error': 'Not found'}), 404 if verify(user_id, invoice_id, sig) else 403

    from app.services.pdf_templates import generate_pdf_with_template

    user = User.query.get(user_id)
    firm = user.firm_details if user else None
    bank = BankAccount.query.filter_by(user_id=user_id, is_default=True).first()
    template_name = firm.default_template if firm else 'Simple'

    try:
        pdf_bytes = generate_pdf_with_template(
            invoice, firm, template_name,
            user_id=user.supabase_id if user else None, bank=bank, layout='single',
        )
    except Exception as e:  # pragma: no cover - rendering failure
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Failed to generate PDF: {e}'}), 500

    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f"Invoice_{invoice.invoice_number.replace('/', '_')}.pdf",
    )
