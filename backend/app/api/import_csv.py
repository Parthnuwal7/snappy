"""CSV Import API endpoint"""
from flask import Blueprint, request, jsonify
from backend.app.models.models import db, Client, Invoice, InvoiceItem
import pandas as pd
from rapidfuzz import fuzz, process
from datetime import datetime
import io

bp = Blueprint('import_csv', __name__)


@bp.route('/import/csv', methods=['POST'])
def import_csv():
    """
    Import clients or invoices from CSV
    Expects multipart/form-data with 'file' and 'type' (clients or invoices)
    """
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    import_type = request.form.get('type', 'clients')
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not file.filename.endswith('.csv'):
        return jsonify({'error': 'File must be CSV format'}), 400
    
    try:
        # Read CSV
        df = pd.read_csv(file)
        
        if import_type == 'clients':
            return import_clients(df)
        elif import_type == 'invoices':
            return import_invoices(df)
        else:
            return jsonify({'error': 'Invalid import type'}), 400
            
    except Exception as e:
        return jsonify({'error': f'Import failed: {str(e)}'}), 500


def import_clients(df):
    """Import clients from DataFrame"""
    required_columns = ['name']
    
    # Validate columns
    if not all(col in df.columns for col in required_columns):
        return jsonify({'error': f'CSV must contain columns: {required_columns}'}), 400
    
    imported = 0
    skipped = 0
    duplicates = []
    
    # Get existing clients for fuzzy matching
    existing_clients = Client.query.all()
    existing_names = [c.name for c in existing_clients]
    
    for _, row in df.iterrows():
        client_name = row['name']
        
        # Fuzzy match to detect duplicates
        if existing_names:
            matches = process.extractOne(client_name, existing_names, scorer=fuzz.ratio)
            if matches and matches[1] > 85:  # 85% similarity threshold
                duplicates.append({
                    'csv_name': client_name,
                    'existing_name': matches[0],
                    'similarity': matches[1]
                })
                skipped += 1
                continue
        
        # Create new client
        client = Client(
            name=client_name,
            email=row.get('email'),
            phone=row.get('phone'),
            address=row.get('address'),
            tax_id=row.get('tax_id'),
            default_tax_rate=row.get('default_tax_rate', 18.0),
            notes=row.get('notes')
        )
        
        db.session.add(client)
        existing_names.append(client_name)
        imported += 1
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'imported': imported,
        'skipped': skipped,
        'duplicates': duplicates
    })


def import_invoices(df):
    """Import invoices from DataFrame"""
    required_columns = ['client_name', 'invoice_date', 'description', 'amount']
    
    # Validate columns
    if not all(col in df.columns for col in required_columns):
        return jsonify({'error': f'CSV must contain columns: {required_columns}'}), 400
    
    imported = 0
    errors = []
    
    # Get existing clients for matching
    existing_clients = Client.query.all()
    client_map = {c.name: c for c in existing_clients}
    client_names = list(client_map.keys())
    
    for idx, row in df.iterrows():
        try:
            # Find matching client
            client_name = row['client_name']
            client = None
            
            if client_name in client_map:
                client = client_map[client_name]
            elif client_names:
                # Fuzzy match
                matches = process.extractOne(client_name, client_names, scorer=fuzz.ratio)
                if matches and matches[1] > 80:
                    client = client_map[matches[0]]
            
            if not client:
                errors.append(f"Row {idx}: Client '{client_name}' not found")
                continue
            
            # Parse date
            invoice_date = pd.to_datetime(row['invoice_date']).date()
            
            # This is a simplified import - creates one item per invoice
            # For complex imports with multiple items, CSV structure would need to be different
            
            from app.api.invoices import generate_invoice_number
            invoice_number = generate_invoice_number()
            
            invoice = Invoice(
                invoice_number=invoice_number,
                client_id=client.id,
                invoice_date=invoice_date,
                short_desc=row.get('short_description', row['description'][:120]),
                tax_rate=row.get('tax_rate', client.default_tax_rate),
                status='draft'
            )
            
            # Add single item
            item = InvoiceItem(
                description=row['description'],
                quantity=row.get('quantity', 1.0),
                rate=float(row['amount']) / row.get('quantity', 1.0),
                amount=float(row['amount'])
            )
            invoice.items.append(item)
            
            invoice.calculate_totals()
            db.session.add(invoice)
            imported += 1
            
        except Exception as e:
            errors.append(f"Row {idx}: {str(e)}")
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'imported': imported,
        'errors': errors
    })
