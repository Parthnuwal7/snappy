"""Invoice API endpoints"""
from flask import Blueprint, request, jsonify, send_file, current_app
from backend.app.models.models import db, Invoice, InvoiceItem, Client, Settings
from backend.app.services.pdf_service import generate_pdf
from datetime import datetime, date
import io

bp = Blueprint('invoices', __name__)


def generate_invoice_number():
    """Generate next invoice number based on settings"""
    prefix_setting = Settings.query.filter_by(key='invoice_prefix').first()
    padding_setting = Settings.query.filter_by(key='invoice_padding').first()
    
    prefix = prefix_setting.value if prefix_setting else 'LAW'
    padding = int(padding_setting.value) if padding_setting else 4
    
    current_year = datetime.now().year
    
    # Find last invoice for current year
    last_invoice = Invoice.query.filter(
        Invoice.invoice_number.like(f"{prefix}/{current_year}/%")
    ).order_by(Invoice.id.desc()).first()
    
    if last_invoice:
        # Extract sequence number from last invoice
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
    
    return f"{prefix}/{current_year}/{str(next_seq).zfill(padding)}"


@bp.route('/invoices', methods=['GET'])
def get_invoices():
    """Get all invoices with optional filters"""
    # Query parameters
    client_id = request.args.get('client_id', type=int)
    status = request.args.get('status')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    search = request.args.get('search')
    
    query = Invoice.query
    
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
def get_invoice(invoice_id):
    """Get a single invoice with items"""
    invoice = Invoice.query.get_or_404(invoice_id)
    return jsonify(invoice.to_dict(include_items=True))


@bp.route('/invoices', methods=['POST'])
def create_invoice():
    """Create a new invoice"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('client_id'):
            return jsonify({'error': 'Client ID is required'}), 400
        
        # Verify client exists
        client = Client.query.get(data['client_id'])
        if not client:
            return jsonify({'error': 'Client not found'}), 404
        
        # Generate invoice number
        invoice_number = generate_invoice_number()
        
        # Parse dates
        invoice_date = datetime.fromisoformat(data['invoice_date']).date() if data.get('invoice_date') else date.today()
        due_date = datetime.fromisoformat(data['due_date']).date() if data.get('due_date') else None
        
        # Get tax rate
        tax_rate = float(data.get('tax_rate', client.default_tax_rate))
        
        # Create invoice
        invoice = Invoice(
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
def update_invoice(invoice_id):
    """Update an existing invoice"""
    invoice = Invoice.query.get_or_404(invoice_id)
    data = request.get_json()
    
    # Update basic fields
    if 'client_id' in data:
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
def mark_invoice_paid(invoice_id):
    """Mark an invoice as paid"""
    invoice = Invoice.query.get_or_404(invoice_id)
    data = request.get_json() or {}
    
    invoice.status = 'paid'
    invoice.paid_date = datetime.fromisoformat(data['paid_date']).date() if data.get('paid_date') else date.today()
    
    db.session.commit()
    return jsonify(invoice.to_dict(include_items=True))


@bp.route('/invoices/<int:invoice_id>/generate_pdf', methods=['POST'])
def generate_invoice_pdf(invoice_id):
    """Generate PDF for an invoice"""
    invoice = Invoice.query.get_or_404(invoice_id)
    
    try:
        pdf_bytes = generate_pdf(invoice)
        
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
def delete_invoice(invoice_id):
    """Delete/void an invoice"""
    invoice = Invoice.query.get_or_404(invoice_id)
    
    # Mark as void instead of deleting
    invoice.status = 'void'
    db.session.commit()
    
    return jsonify({'message': 'Invoice voided successfully'})
