"""Invoice API endpoints - multi-tenant"""
from flask import Blueprint, request, jsonify, send_file, current_app, g
from backend.app.models.models import db, Invoice, InvoiceItem, Client
from backend.app.models.auth import User, FirmDetails, BankAccount
from backend.app.services.pdf_templates import generate_pdf_with_template
from backend.app.middleware.jwt_auth import jwt_required
from datetime import datetime, date
import io

bp = Blueprint('invoices', __name__)


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
    current_year = datetime.now().year
    
    # Find last invoice for this user and current year
    last_invoice = Invoice.query.filter(
        Invoice.user_id == user_id,
        Invoice.invoice_number.like(f"{prefix}/{current_year}/%")
    ).order_by(Invoice.id.desc()).first()
    
    if last_invoice:
        parts = last_invoice.invoice_number.split('/')
        if len(parts) >= 3:
            try:
                last_seq = int(parts[-1])
                next_seq = last_seq + 1
            except ValueError:
                next_seq = 1
        else:
            next_seq = 1
    else:
        next_seq = 1
    
    return f"{prefix}/{current_year}/{str(next_seq).zfill(4)}"


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
    
    query = Invoice.query.filter_by(user_id=user.id)
    
    # Apply filters
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
    
    invoices = query.order_by(Invoice.invoice_date.desc()).all()
    return jsonify([inv.to_dict(include_items=False) for inv in invoices])


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
            signature_path=data.get('signature_path')
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
    if 'signature_path' in data:
        invoice.signature_path = data['signature_path']
    
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
    
    invoice = Invoice.query.filter_by(id=invoice_id, user_id=user.id).first()
    if not invoice:
        return jsonify({'error': 'Invoice not found'}), 404
    
    try:
        # Get firm details and bank account for PDF
        firm = user.firm_details
        bank = BankAccount.query.filter_by(user_id=user.id, is_default=True).first()
        template_name = firm.default_template if firm else 'Simple'
        
        print(f"DEBUG PDF: User ID: {user.supabase_id}, Firm: {firm.firm_name if firm else 'None'}")
        print(f"DEBUG PDF: Template: {template_name}")
        
        # Generate PDF
        pdf_bytes = generate_pdf_with_template(invoice, firm, template_name, user_id=user.supabase_id, bank=bank)
        
        # Return PDF as downloadable file
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f"SNAPPY_INV_{invoice.invoice_number.replace('/', '_')}.pdf"
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Failed to generate PDF: {str(e)}'}), 500


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
