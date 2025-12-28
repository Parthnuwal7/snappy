"""CSV Import API endpoint for data migration - multi-tenant"""
from flask import Blueprint, request, jsonify, g
from app.models.models import db, Client, Invoice, InvoiceItem, Item
from app.models.auth import User
from app.middleware.jwt_auth import jwt_required
from datetime import datetime
import csv
import io

bp = Blueprint('import_csv', __name__)


def get_current_user():
    """Get the current user from Supabase ID"""
    supabase_id = getattr(g, 'user_id', None)
    if not supabase_id:
        return None
    return User.query.filter_by(supabase_id=supabase_id).first()


@bp.route('/import/migration', methods=['POST'])
@jwt_required
def import_migration():
    """
    Import combined invoices + items from CSV for data migration.
    
    Expected CSV format (one row per invoice line item):
    invoice_number,client_name,client_address,client_email,client_phone,invoice_date,due_date,status,item_description,quantity,rate,short_desc
    
    The importer will:
    1. Create clients if they don't exist (matched by exact name)
    2. Create invoices if they don't exist (matched by invoice_number)
    3. Add line items to invoices
    """
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 401
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not file.filename.endswith('.csv'):
        return jsonify({'error': 'File must be CSV format'}), 400
    
    try:
        # Read CSV
        content = file.read().decode('utf-8')
        reader = csv.DictReader(io.StringIO(content))
        
        # Track created/updated entities
        clients_created = 0
        invoices_created = 0
        items_added = 0
        errors = []
        
        # Cache for lookups
        client_cache = {}  # {name: client}
        invoice_cache = {}  # {invoice_number: invoice}
        
        # Load existing clients for this user
        existing_clients = Client.query.filter_by(user_id=user.id).all()
        for c in existing_clients:
            client_cache[c.name.lower()] = c
        
        # Load existing invoices for this user
        existing_invoices = Invoice.query.filter_by(user_id=user.id).all()
        for inv in existing_invoices:
            invoice_cache[inv.invoice_number] = inv
        
        for row_num, row in enumerate(reader, start=2):
            try:
                # Get or create client
                client_name = row.get('client_name', '').strip()
                if not client_name:
                    errors.append(f"Row {row_num}: Missing client_name")
                    continue
                
                client = client_cache.get(client_name.lower())
                if not client:
                    # Create new client
                    client = Client(
                        user_id=user.id,
                        name=client_name,
                        address=row.get('client_address', ''),
                        email=row.get('client_email', ''),
                        phone=row.get('client_phone', ''),
                        tax_id=row.get('client_tax_id', ''),
                        default_tax_rate=18.0
                    )
                    db.session.add(client)
                    db.session.flush()
                    client_cache[client_name.lower()] = client
                    clients_created += 1
                
                # Get or create invoice
                invoice_number = row.get('invoice_number', '').strip()
                if not invoice_number:
                    errors.append(f"Row {row_num}: Missing invoice_number")
                    continue
                
                invoice = invoice_cache.get(invoice_number)
                if not invoice:
                    # Parse dates
                    invoice_date = parse_date(row.get('invoice_date', ''))
                    due_date = parse_date(row.get('due_date', ''))
                    
                    if not invoice_date:
                        invoice_date = datetime.utcnow().date()
                    
                    # Get status (default to 'paid' for historical invoices)
                    status = row.get('status', 'paid').strip().lower()
                    if status not in ['draft', 'sent', 'paid', 'void']:
                        status = 'paid'
                    
                    invoice = Invoice(
                        user_id=user.id,
                        invoice_number=invoice_number,
                        client_id=client.id,
                        invoice_date=invoice_date,
                        due_date=due_date,
                        short_desc=row.get('short_desc', ''),
                        tax_rate=float(row.get('tax_rate', 0)),
                        status=status,
                        paid_date=invoice_date if status == 'paid' else None
                    )
                    db.session.add(invoice)
                    db.session.flush()
                    invoice_cache[invoice_number] = invoice
                    invoices_created += 1
                
                # Add line item
                description = row.get('item_description', '').strip()
                if description:
                    quantity = float(row.get('quantity', 1) or 1)
                    rate = float(row.get('rate', 0) or 0)
                    amount = quantity * rate
                    
                    item = InvoiceItem(
                        invoice_id=invoice.id,
                        description=description,
                        quantity=quantity,
                        rate=rate,
                        amount=amount
                    )
                    db.session.add(item)
                    items_added += 1
                
            except Exception as e:
                errors.append(f"Row {row_num}: {str(e)}")
        
        # Recalculate totals for all new invoices
        for inv in invoice_cache.values():
            inv.calculate_totals()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'clients_created': clients_created,
            'invoices_created': invoices_created,
            'items_added': items_added,
            'errors': errors[:20]  # Return first 20 errors only
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Import failed: {str(e)}'}), 500


@bp.route('/import/items', methods=['POST'])
@jwt_required
def import_items_catalog():
    """
    Import items catalog from CSV.
    
    Expected CSV format:
    name,description,default_rate,unit
    """
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 401
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    try:
        content = file.read().decode('utf-8')
        reader = csv.DictReader(io.StringIO(content))
        
        items_created = 0
        errors = []
        
        for row_num, row in enumerate(reader, start=2):
            try:
                name = row.get('name', '').strip()
                if not name:
                    continue
                
                item = Item(
                    user_id=user.id,
                    name=name,
                    description=row.get('description', ''),
                    default_rate=float(row.get('default_rate', 0) or 0),
                    unit=row.get('unit', 'unit'),
                    is_active=True
                )
                db.session.add(item)
                items_created += 1
                
            except Exception as e:
                errors.append(f"Row {row_num}: {str(e)}")
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'items_created': items_created,
            'errors': errors[:20]
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Import failed: {str(e)}'}), 500


def parse_date(date_str):
    """Parse date string in various formats"""
    if not date_str:
        return None
    
    date_str = date_str.strip()
    formats = [
        '%Y-%m-%d',      # 2024-01-15
        '%d-%m-%Y',      # 15-01-2024
        '%d/%m/%Y',      # 15/01/2024
        '%m/%d/%Y',      # 01/15/2024
        '%Y/%m/%d',      # 2024/01/15
        '%d %B %Y',      # 15 January 2024
        '%B %d, %Y',     # January 15, 2024
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    
    return None
