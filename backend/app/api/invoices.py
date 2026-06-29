"""Invoice API endpoints - multi-tenant with optimized queries"""
from flask import Blueprint, request, jsonify, send_file, current_app, g
from app.models.models import db, Invoice, InvoiceItem, Client
from app.models.auth import User, FirmDetails, BankAccount
from app.models.case import CaseFile
from app.services.pdf_templates import generate_pdf_with_template
from app.middleware.jwt_auth import jwt_required
from app.middleware.firm_context import require_permission
from app.utils.pagination import pagination_requested, get_pagination_args, paginate_query
from app.services.upi import build_upi_uri, compose_note
from sqlalchemy.orm import joinedload
from datetime import datetime, date
import io
import time

bp = Blueprint('invoices', __name__)

# Columns allowed for server-side sorting of the invoice register.
INVOICE_SORT_COLUMNS = {
    'invoice_number': Invoice.invoice_number,
    'invoice_date': Invoice.invoice_date,
    'total': Invoice.total,
}

# Cache for firm/bank details per user (50 minute TTL)
_firm_cache = {}  # {user_id: (firm_dict, bank_dict, timestamp)}
_firm_cache_ttl = 3000  # 50 minutes


def get_cached_firm_bank(user):
    """Get firm and bank details from cache or database"""
    global _firm_cache
    
    cache_key = user.id
    now = time.time()
    
    # Check cache
    if cache_key in _firm_cache:
        firm_dict, bank_dict, timestamp = _firm_cache[cache_key]
        if now - timestamp < _firm_cache_ttl:
            return firm_dict, bank_dict
    
    # Fetch from database
    firm = user.firm_details
    bank = BankAccount.query.filter_by(user_id=user.id, is_default=True).first()
    
    # Store in cache
    _firm_cache[cache_key] = (firm, bank, now)
    
    return firm, bank


def invalidate_firm_cache(user_id):
    """Invalidate cache when firm/bank is updated"""
    global _firm_cache
    if user_id in _firm_cache:
        del _firm_cache[user_id]


def _resolve_bank():
    """The caller's default bank, queried fresh (not the perf cache) so the
    embedded UPI link always reflects the latest saved VPA/payee/note."""
    user = get_current_user()
    if not user:
        return None
    return BankAccount.query.filter_by(user_id=user.id, is_default=True).first()


def _attach_upi(payload, invoice, bank):
    """Inject the per-invoice upi:// deep link into an invoice dict."""
    payload['upi_uri'] = build_upi_uri(
        getattr(bank, 'upi_id', None) if bank else None,
        getattr(bank, 'upi_payee_name', None) if bank else None,
        amount=invoice.total,
        note=compose_note(getattr(bank, 'upi_note', None) if bank else None,
                          invoice.invoice_number),
        invoice_no=invoice.invoice_number,
    )
    return payload


def get_current_user():
    """Get the current user from Supabase ID"""
    supabase_id = getattr(g, 'user_id', None)
    if not supabase_id:
        return None
    return User.query.filter_by(supabase_id=supabase_id).first()


def generate_invoice_number(firm_id):
    """Generate next invoice number for a firm (numbering is per-firm)."""
    firm = FirmDetails.query.filter_by(firm_id=firm_id).first()

    prefix = firm.invoice_prefix if firm else 'INV'
    use_prefix = firm.use_invoice_prefix if firm and firm.use_invoice_prefix is not None else True

    # Find last invoice for this firm
    if use_prefix:
        # Look for PREFIX/SEQ pattern
        last_invoice = Invoice.query.filter(
            Invoice.firm_id == firm_id,
            Invoice.invoice_number.like(f"{prefix}/%")
        ).order_by(Invoice.id.desc()).first()
    else:
        # Look for numeric-only pattern
        last_invoice = Invoice.query.filter(
            Invoice.firm_id == firm_id
        ).order_by(Invoice.id.desc()).first()
    
    if last_invoice:
        parts = last_invoice.invoice_number.split('/')
        try:
            # Get the last numeric part
            last_seq = int(parts[-1])
            next_seq = last_seq + 1
        except ValueError:
            # If last invoice was just a number, try parsing it directly
            try:
                last_seq = int(last_invoice.invoice_number)
                next_seq = last_seq + 1
            except ValueError:
                next_seq = 1
    else:
        next_seq = 1
    
    if use_prefix:
        return f"{prefix}/{str(next_seq).zfill(4)}"
    else:
        return str(next_seq).zfill(4)


@bp.route('/invoices', methods=['GET'])
@jwt_required
@require_permission('invoices.read')
def get_invoices():
    """Get all invoices for the current firm with optional filters"""

    # Query parameters
    client_id = request.args.get('client_id', type=int)
    status = request.args.get('status')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    search = request.args.get('search')
    sort = request.args.get('sort', 'invoice_number')
    order = request.args.get('order', 'desc')

    case_file_id = request.args.get('case_file_id', type=int)

    query = Invoice.query.filter_by(firm_id=g.firm_id)

    # Apply filters (these span the whole dataset, independent of pagination)
    if client_id:
        query = query.filter_by(client_id=client_id)
    if case_file_id:
        query = query.filter_by(case_file_id=case_file_id)
    if status:
        query = query.filter_by(status=status)
    if start_date:
        query = query.filter(Invoice.invoice_date >= datetime.fromisoformat(start_date).date())
    if end_date:
        query = query.filter(Invoice.invoice_date <= datetime.fromisoformat(end_date).date())
    if search:
        query = query.filter(
            db.or_(
                Invoice.invoice_number.contains(search),
                Invoice.short_desc.contains(search)
            )
        )

    # Sorting — default is invoice number, descending.
    if sort == 'client_name':
        query = query.join(Client, Invoice.client_id == Client.id)
        sort_col = Client.name
    else:
        sort_col = INVOICE_SORT_COLUMNS.get(sort, Invoice.invoice_number)
    query = query.order_by(sort_col.asc() if order == 'asc' else sort_col.desc())

    bank = _resolve_bank()
    serialize = lambda inv: _attach_upi(inv.to_dict(include_items=False), inv, bank)

    if pagination_requested():
        page, page_size = get_pagination_args()
        return jsonify(paginate_query(query, page, page_size, serialize))

    return jsonify([serialize(inv) for inv in query.all()])


@bp.route('/invoices/<int:invoice_id>', methods=['GET'])
@jwt_required
@require_permission('invoices.read')
def get_invoice(invoice_id):
    """Get a single invoice with items (must belong to current firm)"""
    invoice = Invoice.query.filter_by(id=invoice_id, firm_id=g.firm_id).first()
    if not invoice:
        return jsonify({'error': 'Invoice not found'}), 404

    return jsonify(_attach_upi(invoice.to_dict(include_items=True), invoice, _resolve_bank()))


@bp.route('/invoices', methods=['POST'])
@jwt_required
@require_permission('invoices.create')
def create_invoice():
    """Create a new invoice for the current firm"""
    try:
        data = request.get_json()

        # Validate required fields
        if not data.get('client_id'):
            return jsonify({'error': 'Client ID is required'}), 400

        # Verify client exists and belongs to the firm
        client = Client.query.filter_by(id=data['client_id'], firm_id=g.firm_id).first()
        if not client:
            return jsonify({'error': 'Client not found'}), 404

        # Optional case-file link (must belong to the same firm)
        case_file_id = data.get('case_file_id')
        if case_file_id is not None:
            case_file = CaseFile.query.filter_by(id=case_file_id, firm_id=g.firm_id).first()
            if not case_file:
                return jsonify({'error': 'Case not found'}), 404

        # Generate invoice number for this firm
        invoice_number = generate_invoice_number(g.firm_id)

        # Parse dates
        invoice_date = datetime.fromisoformat(data['invoice_date']).date() if data.get('invoice_date') else date.today()
        due_date = datetime.fromisoformat(data['due_date']).date() if data.get('due_date') else None
        
        # Get tax rate
        tax_rate = float(data.get('tax_rate', client.default_tax_rate))
        
        # Create invoice
        invoice = Invoice(
            firm_id=g.firm_id,
            created_by_user_id=g.user.id,
            invoice_number=invoice_number,
            client_id=data['client_id'],
            case_file_id=case_file_id,
            invoice_date=invoice_date,
            due_date=due_date,
            short_desc=data.get('short_desc'),
            tax_rate=tax_rate,
            status=data.get('status', 'draft'),
            notes=data.get('notes'),
        )
        
        # Add line items
        if 'items' in data and data['items']:
            for item_data in data['items']:
                quantity = float(item_data.get('quantity', 1.0))
                rate = float(item_data['rate'])
                item = InvoiceItem(
                    description=item_data['description'],
                    quantity=quantity,
                    rate=rate,
                    amount=quantity * rate
                )
                invoice.items.append(item)
        
        # Calculate totals
        invoice.calculate_totals()
        
        db.session.add(invoice)
        db.session.commit()

        return jsonify(_attach_upi(invoice.to_dict(include_items=True), invoice, _resolve_bank())), 201
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Invalid request data: {str(e)}'}), 400


@bp.route('/invoices/<int:invoice_id>', methods=['PUT'])
@jwt_required
@require_permission('invoices.update')
def update_invoice(invoice_id):
    """Update an existing invoice (must belong to current firm)"""
    invoice = Invoice.query.filter_by(id=invoice_id, firm_id=g.firm_id).first()
    if not invoice:
        return jsonify({'error': 'Invoice not found'}), 404

    data = request.get_json()

    # Update basic fields
    if 'client_id' in data:
        # Verify client belongs to the firm
        client = Client.query.filter_by(id=data['client_id'], firm_id=g.firm_id).first()
        if client:
            invoice.client_id = data['client_id']
    if 'invoice_date' in data:
        invoice.invoice_date = datetime.fromisoformat(data['invoice_date']).date()
    if 'due_date' in data:
        invoice.due_date = datetime.fromisoformat(data['due_date']).date() if data['due_date'] else None
    if 'short_desc' in data:
        invoice.short_desc = data['short_desc']
    if 'tax_rate' in data:
        invoice.tax_rate = float(data['tax_rate'])
    if 'status' in data:
        invoice.status = data['status']
    if 'notes' in data:
        invoice.notes = data['notes']
    if 'case_file_id' in data:
        if data['case_file_id'] is None:
            invoice.case_file_id = None
        else:
            case_file = CaseFile.query.filter_by(id=data['case_file_id'], firm_id=g.firm_id).first()
            if case_file:
                invoice.case_file_id = case_file.id

    # Update items if provided
    if 'items' in data:
        # Remove old items
        InvoiceItem.query.filter_by(invoice_id=invoice_id).delete()
        
        # Add new items
        for item_data in data['items']:
            quantity = float(item_data.get('quantity', 1.0))
            rate = float(item_data['rate'])
            item = InvoiceItem(
                invoice_id=invoice_id,
                description=item_data['description'],
                quantity=quantity,
                rate=rate,
                amount=quantity * rate
            )
            db.session.add(item)
    
    # Recalculate totals
    invoice.calculate_totals()

    db.session.commit()
    return jsonify(_attach_upi(invoice.to_dict(include_items=True), invoice, _resolve_bank()))


@bp.route('/invoices/<int:invoice_id>/mark_paid', methods=['POST'])
@jwt_required
@require_permission('invoices.update')
def mark_invoice_paid(invoice_id):
    """Mark an invoice as paid (must belong to current firm)"""
    invoice = Invoice.query.filter_by(id=invoice_id, firm_id=g.firm_id).first()
    if not invoice:
        return jsonify({'error': 'Invoice not found'}), 404
    
    data = request.get_json() or {}
    
    invoice.status = 'paid'
    invoice.paid_date = datetime.fromisoformat(data['paid_date']).date() if data.get('paid_date') else date.today()

    db.session.commit()
    return jsonify(_attach_upi(invoice.to_dict(include_items=True), invoice, _resolve_bank()))


@bp.route('/invoices/<int:invoice_id>/generate_pdf', methods=['POST'])
@jwt_required
@require_permission('invoices.read')
def generate_invoice_pdf(invoice_id):
    """Generate PDF for an invoice using firm's template preference"""
    user = g.user

    # Eager load invoice with client and items in single query (3 queries -> 1)
    invoice = Invoice.query.options(
        joinedload(Invoice.client),
        joinedload(Invoice.items)
    ).filter_by(id=invoice_id, firm_id=g.firm_id).first()
    if not invoice:
        return jsonify({'error': 'Invoice not found'}), 404
    
    try:
        # Get firm details and bank account for PDF (from cache)
        firm, bank = get_cached_firm_bank(user)
        template_name = firm.default_template if firm else 'Simple'
        layout = request.args.get('layout', 'single')

        # Generate PDF
        pdf_bytes = generate_pdf_with_template(
            invoice, firm, template_name, user_id=user.supabase_id, bank=bank, layout=layout
        )

        # Return PDF as downloadable file
        suffix = '_2up' if layout == 'two_up' else ''
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f"SNAPPY_INV_{invoice.invoice_number.replace('/', '_')}{suffix}.pdf"
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Failed to generate PDF: {str(e)}'}), 500


@bp.route('/invoices/<int:invoice_id>/send', methods=['POST'])
@jwt_required
@require_permission('invoices.send')
def send_invoice_endpoint(invoice_id):
    """Send an invoice to its client over email or WhatsApp.

    Body: { channel: 'email'|'whatsapp', subject?, body? }
      - email    -> renders + sends via the email transport, attaches the PDF.
      - whatsapp -> returns a wa.me URL for the frontend to open.
    Records sent_at/sent_channel and promotes draft -> sent on success.
    """
    user = g.user

    invoice = Invoice.query.options(
        joinedload(Invoice.client),
        joinedload(Invoice.items),
    ).filter_by(id=invoice_id, firm_id=g.firm_id).first()
    if not invoice:
        return jsonify({'error': 'Invoice not found'}), 404

    data = request.get_json() or {}
    channel = data.get('channel')
    if channel not in ('email', 'whatsapp'):
        return jsonify({'error': "channel must be 'email' or 'whatsapp'"}), 400

    # Fetch firm/bank bound to THIS request's session. The module-level
    # get_cached_firm_bank() cache hands back detached ORM instances on later
    # requests, which raise DetachedInstanceError on attribute access.
    firm = user.firm_details
    bank = BankAccount.query.filter_by(user_id=user.id, is_default=True).first()
    currency = firm.currency if firm and firm.currency else 'INR'

    # Only the email path needs a rendered PDF to attach.
    pdf_bytes = None
    if channel == 'email':
        template_name = firm.default_template if firm else 'Simple'
        try:
            pdf_bytes = generate_pdf_with_template(
                invoice, firm, template_name,
                user_id=user.supabase_id, bank=bank, layout='single',
            )
        except Exception as e:
            return jsonify({'error': f'Failed to render PDF: {e}'}), 500

    from app.services.send_service import send_invoice, SendError
    try:
        result = send_invoice(
            invoice, firm, invoice.client, channel,
            pdf_bytes=pdf_bytes,
            subject=data.get('subject'),
            body=data.get('body'),
            currency=currency,
            # Frontend passes its own origin so links resolve in local & prod;
            # build_link falls back to PUBLIC_BASE_URL when absent.
            base_url=data.get('base_url'),
            # CC the firm so the sender stays looped in on what was sent.
            cc=(firm.firm_email if firm else None),
        )
    except SendError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Send failed: {e}'}), 502

    db.session.commit()
    result.update({
        'status': invoice.status,
        'sent_at': invoice.sent_at.isoformat() if invoice.sent_at else None,
        'sent_channel': invoice.sent_channel,
    })
    return jsonify(result)


@bp.route('/invoices/<int:invoice_id>/share_link', methods=['GET'])
@jwt_required
@require_permission('invoices.read')
def invoice_share_link(invoice_id):
    """Return a signed public link to the invoice (for copy/share).

    `base_url` query param (the frontend origin) is prepended so the link works
    in both local and production; falls back to PUBLIC_BASE_URL when omitted.
    """
    invoice = Invoice.query.filter_by(id=invoice_id, firm_id=g.firm_id).first()
    if not invoice:
        return jsonify({'error': 'Invoice not found'}), 404

    from app.utils.invoice_links import build_link
    # Public links are keyed by the invoice's creator (preserves the signature scheme).
    link = build_link(invoice.created_by_user_id, invoice.id, base_url=request.args.get('base_url'))
    return jsonify({'link': link})


@bp.route('/invoices/<int:invoice_id>', methods=['DELETE'])
@jwt_required
@require_permission('invoices.delete')
def delete_invoice(invoice_id):
    """Delete/void an invoice (must belong to current firm)"""
    invoice = Invoice.query.filter_by(id=invoice_id, firm_id=g.firm_id).first()
    if not invoice:
        return jsonify({'error': 'Invoice not found'}), 404
    
    # Mark as void instead of deleting
    invoice.status = 'void'
    db.session.commit()
    
    return jsonify({'message': 'Invoice voided successfully'})


@bp.route('/invoices/<int:invoice_id>/duplicate', methods=['POST'])
@jwt_required
@require_permission('invoices.create')
def duplicate_invoice(invoice_id):
    """Duplicate an invoice with a new invoice number (must belong to current firm)"""
    original = Invoice.query.filter_by(id=invoice_id, firm_id=g.firm_id).first()
    if not original:
        return jsonify({'error': 'Invoice not found'}), 404

    # Generate new invoice number
    new_invoice_number = generate_invoice_number(g.firm_id)

    # Create new invoice with copied data
    new_invoice = Invoice(
        firm_id=g.firm_id,
        created_by_user_id=g.user.id,
        invoice_number=new_invoice_number,
        client_id=original.client_id,
        invoice_date=date.today(),
        due_date=original.due_date,
        short_desc=original.short_desc,
        subtotal=original.subtotal,
        tax_rate=original.tax_rate,
        tax_amount=original.tax_amount,
        total=original.total,
        status='draft',
        notes=original.notes
    )
    
    db.session.add(new_invoice)
    db.session.flush()  # Get the new invoice ID
    
    # Copy line items
    for item in original.items:
        new_item = InvoiceItem(
            invoice_id=new_invoice.id,
            description=item.description,
            quantity=item.quantity,
            rate=item.rate,
            amount=item.amount
        )
        db.session.add(new_item)
    
    db.session.commit()
    
    return jsonify({
        'message': 'Invoice duplicated successfully',
        'invoice': _attach_upi(new_invoice.to_dict(), new_invoice, _resolve_bank())
    }), 201
