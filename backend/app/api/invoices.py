"""Invoice API endpoints - multi-tenant with optimized queries"""
from flask import Blueprint, request, jsonify, send_file, current_app, g
from app.models.models import db, Invoice, InvoiceItem, Client
from app.models.auth import User, FirmDetails, BankAccount
from app.services.pdf_templates import generate_pdf_with_template
from app.middleware.jwt_auth import jwt_required
from app.utils.pagination import pagination_requested, get_pagination_args, paginate_query
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


def get_current_user():
    """Get the current user from Supabase ID"""
    supabase_id = getattr(g, 'user_id', None)
    if not supabase_id:
        return None
    return User.query.filter_by(supabase_id=supabase_id).first()


def generate_invoice_number(user_id):
    """Generate next invoice number for a specific user"""
    user = User.query.get(user_id)
    firm = user.firm_details if user else None
    
    prefix = firm.invoice_prefix if firm else 'INV'
    use_prefix = firm.use_invoice_prefix if firm and firm.use_invoice_prefix is not None else True
    
    # Find last invoice for this user
    if use_prefix:
        # Look for PREFIX/SEQ pattern
        last_invoice = Invoice.query.filter(
            Invoice.user_id == user_id,
            Invoice.invoice_number.like(f"{prefix}/%")
        ).order_by(Invoice.id.desc()).first()
    else:
        # Look for numeric-only pattern
        last_invoice = Invoice.query.filter(
            Invoice.user_id == user_id
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
def get_invoices():
    """Get all invoices for current user with optional filters"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 401
    
    # Query parameters
    client_id = request.args.get('client_id', type=int)
    status = request.args.get('status')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    search = request.args.get('search')
    sort = request.args.get('sort', 'invoice_number')
    order = request.args.get('order', 'desc')

    query = Invoice.query.filter_by(user_id=user.id)

    # Apply filters (these span the whole dataset, independent of pagination)
    if client_id:
        query = query.filter_by(client_id=client_id)
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

    serialize = lambda inv: inv.to_dict(include_items=False)

    if pagination_requested():
        page, page_size = get_pagination_args()
        return jsonify(paginate_query(query, page, page_size, serialize))

    return jsonify([serialize(inv) for inv in query.all()])


@bp.route('/invoices/<int:invoice_id>', methods=['GET'])
@jwt_required
def get_invoice(invoice_id):
    """Get a single invoice with items (must belong to current user)"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 401
    
    invoice = Invoice.query.filter_by(id=invoice_id, user_id=user.id).first()
    if not invoice:
        return jsonify({'error': 'Invoice not found'}), 404
    
    return jsonify(invoice.to_dict(include_items=True))


@bp.route('/invoices', methods=['POST'])
@jwt_required
def create_invoice():
    """Create a new invoice for current user"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 401
    
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('client_id'):
            return jsonify({'error': 'Client ID is required'}), 400
        
        # Verify client exists and belongs to user
        client = Client.query.filter_by(id=data['client_id'], user_id=user.id).first()
        if not client:
            return jsonify({'error': 'Client not found'}), 404
        
        # Generate invoice number for this user
        invoice_number = generate_invoice_number(user.id)
        
        # Parse dates
        invoice_date = datetime.fromisoformat(data['invoice_date']).date() if data.get('invoice_date') else date.today()
        due_date = datetime.fromisoformat(data['due_date']).date() if data.get('due_date') else None
        
        # Get tax rate
        tax_rate = float(data.get('tax_rate', client.default_tax_rate))
        
        # Create invoice
        invoice = Invoice(
            user_id=user.id,
            invoice_number=invoice_number,
            client_id=data['client_id'],
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
        
        return jsonify(invoice.to_dict(include_items=True)), 201
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Invalid request data: {str(e)}'}), 400


@bp.route('/invoices/<int:invoice_id>', methods=['PUT'])
@jwt_required
def update_invoice(invoice_id):
    """Update an existing invoice (must belong to current user)"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 401
    
    invoice = Invoice.query.filter_by(id=invoice_id, user_id=user.id).first()
    if not invoice:
        return jsonify({'error': 'Invoice not found'}), 404
    
    data = request.get_json()
    
    # Update basic fields
    if 'client_id' in data:
        # Verify client belongs to user
        client = Client.query.filter_by(id=data['client_id'], user_id=user.id).first()
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
    return jsonify(invoice.to_dict(include_items=True))


@bp.route('/invoices/<int:invoice_id>/mark_paid', methods=['POST'])
@jwt_required
def mark_invoice_paid(invoice_id):
    """Mark an invoice as paid (must belong to current user)"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 401
    
    invoice = Invoice.query.filter_by(id=invoice_id, user_id=user.id).first()
    if not invoice:
        return jsonify({'error': 'Invoice not found'}), 404
    
    data = request.get_json() or {}
    
    invoice.status = 'paid'
    invoice.paid_date = datetime.fromisoformat(data['paid_date']).date() if data.get('paid_date') else date.today()
    
    db.session.commit()
    return jsonify(invoice.to_dict(include_items=True))


@bp.route('/invoices/<int:invoice_id>/generate_pdf', methods=['POST'])
@jwt_required
def generate_invoice_pdf(invoice_id):
    """Generate PDF for an invoice using firm's template preference"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 401
    
    # Eager load invoice with client and items in single query (3 queries -> 1)
    invoice = Invoice.query.options(
        joinedload(Invoice.client),
        joinedload(Invoice.items)
    ).filter_by(id=invoice_id, user_id=user.id).first()
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
def send_invoice_endpoint(invoice_id):
    """Send an invoice to its client over email or WhatsApp.

    Body: { channel: 'email'|'whatsapp', subject?, body? }
      - email    -> renders + sends via the email transport, attaches the PDF.
      - whatsapp -> returns a wa.me URL for the frontend to open.
    Records sent_at/sent_channel and promotes draft -> sent on success.
    """
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 401

    invoice = Invoice.query.options(
        joinedload(Invoice.client),
        joinedload(Invoice.items),
    ).filter_by(id=invoice_id, user_id=user.id).first()
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
def invoice_share_link(invoice_id):
    """Return a signed public link to the invoice (for copy/share).

    `base_url` query param (the frontend origin) is prepended so the link works
    in both local and production; falls back to PUBLIC_BASE_URL when omitted.
    """
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 401

    invoice = Invoice.query.filter_by(id=invoice_id, user_id=user.id).first()
    if not invoice:
        return jsonify({'error': 'Invoice not found'}), 404

    from app.utils.invoice_links import build_link
    link = build_link(user.id, invoice.id, base_url=request.args.get('base_url'))
    return jsonify({'link': link})


@bp.route('/invoices/<int:invoice_id>', methods=['DELETE'])
@jwt_required
def delete_invoice(invoice_id):
    """Delete/void an invoice (must belong to current user)"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 401
    
    invoice = Invoice.query.filter_by(id=invoice_id, user_id=user.id).first()
    if not invoice:
        return jsonify({'error': 'Invoice not found'}), 404
    
    # Mark as void instead of deleting
    invoice.status = 'void'
    db.session.commit()
    
    return jsonify({'message': 'Invoice voided successfully'})


@bp.route('/invoices/<int:invoice_id>/duplicate', methods=['POST'])
@jwt_required
def duplicate_invoice(invoice_id):
    """Duplicate an invoice with a new invoice number (must belong to current user)"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 401
    
    original = Invoice.query.filter_by(id=invoice_id, user_id=user.id).first()
    if not original:
        return jsonify({'error': 'Invoice not found'}), 404
    
    # Generate new invoice number
    new_invoice_number = generate_invoice_number(user.id)
    
    # Create new invoice with copied data
    new_invoice = Invoice(
        user_id=user.id,
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
        'invoice': new_invoice.to_dict()
    }), 201
