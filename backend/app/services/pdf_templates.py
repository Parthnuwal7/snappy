"""Invoice PDF templates"""
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_RIGHT, TA_CENTER, TA_LEFT
from io import BytesIO
import os
import requests


# Use "Rs." instead of ₹ symbol for font compatibility
CURRENCY_SYMBOL = "Rs."

# Image cache to avoid repeated fetches (cache expires after 50 minutes)
_image_cache = {}
_cache_ttl = 3000  # 50 minutes in seconds


def get_supabase_image(user_id, image_type):
    """
    Fetch image from Supabase Storage and return as BytesIO.
    Optimized for speed with caching and shorter timeouts.
    
    Args:
        user_id: The Supabase user ID
        image_type: 'logo', 'signature', or 'qr'
        
    Returns:
        BytesIO object with image data, or None if not found
    """
    import time
    
    if not user_id:
        return None
    
    # Check cache first
    cache_key = f"{user_id}_{image_type}"
    if cache_key in _image_cache:
        cached_data, cached_time = _image_cache[cache_key]
        if time.time() - cached_time < _cache_ttl:
            # Return a new BytesIO from cached bytes
            if cached_data is not None:
                return BytesIO(cached_data)
            return None
    
    try:
        from app.services.supabase_client import get_supabase_client
        supabase = get_supabase_client()
        
        bucket_map = {
            'logo': 'firm-logos',
            'signature': 'signatures',
            'qr': 'qr-codes'
        }
        
        bucket_name = bucket_map.get(image_type)
        if not bucket_name:
            return None
        
        # Try common extensions (png first as most common for logos)
        for ext in ['png', 'jpg']:
            file_path = f"{user_id}/{image_type}.{ext}"
            try:
                # Create signed URL
                result = supabase.storage.from_(bucket_name).create_signed_url(
                    file_path,
                    expires_in=60  # 1 minute (shorter for speed)
                )
                
                if result and result.get('signedURL'):
                    # Download with short timeout
                    response = requests.get(result['signedURL'], timeout=3)
                    if response.status_code == 200:
                        # Cache the raw bytes
                        _image_cache[cache_key] = (response.content, time.time())
                        return BytesIO(response.content)
            except requests.Timeout:
                continue
            except Exception:
                continue
        
        # Cache None result to avoid repeated failed lookups
        _image_cache[cache_key] = (None, time.time())
        return None
    except Exception as e:
        print(f"Error fetching image: {e}")
        return None
        return None


def number_to_words_indian(num):
    """Convert number to words in Indian English"""
    if num == 0:
        return "Zero"
    
    ones = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine"]
    tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]
    teens = ["Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", 
             "Sixteen", "Seventeen", "Eighteen", "Nineteen"]
    
    def convert_hundreds(n):
        if n >= 100:
            return ones[n // 100] + " Hundred " + convert_tens(n % 100)
        else:
            return convert_tens(n)
    
    def convert_tens(n):
        if n < 10:
            return ones[n]
        elif n < 20:
            return teens[n - 10]
        else:
            return tens[n // 10] + (" " + ones[n % 10] if n % 10 != 0 else "")
    
    def convert_indian(n):
        if n < 100:
            return convert_tens(n)
        elif n < 1000:
            return convert_hundreds(n)
        elif n < 100000:
            return convert_indian(n // 1000) + " Thousand " + (convert_hundreds(n % 1000) if n % 1000 != 0 else "")
        elif n < 10000000:
            return convert_indian(n // 100000) + " Lakh " + (convert_indian(n % 100000) if n % 100000 != 0 else "")
        else:
            return convert_indian(n // 10000000) + " Crore " + (convert_indian(n % 10000000) if n % 10000000 != 0 else "")
    
    return convert_indian(int(num)).strip()


def generate_pdf_simple(invoice, firm):
    """Generate Simple template PDF (original template)"""
    from app.services.pdf_service import generate_pdf as original_generate_pdf
    return original_generate_pdf(invoice)


def generate_pdf_law_001(invoice, firm):
    """
    Generate LAW_001 template PDF (based on provided image)
    Professional invoice template with firm branding
    """
    from datetime import datetime
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    
    elements = []
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle('InvoiceTitle', parent=styles['Heading1'], fontSize=32, textColor=colors.black, alignment=TA_CENTER, spaceAfter=20)
    firm_style = ParagraphStyle('FirmInfo', parent=styles['Normal'], fontSize=9, textColor=colors.black)
    
    # Title
    elements.append(Paragraph("INVOICE", title_style))
    elements.append(Spacer(1, 0.2*inch))
    
    # Header section with yellow background
    header_data = []
    
    # Left side - Firm details with logo
    firm_info_lines = []
    if firm.logo_path and os.path.exists(firm.logo_path):
        logo_cell = Image(firm.logo_path, width=1*inch, height=1*inch)
    else:
        logo_cell = Paragraph("<b>&lt;Firm Logo&gt;</b>", firm_style)
    
    firm_info = f"""<b>{firm.firm_name}</b><br/>
    {firm.firm_address.replace(chr(10), '<br/>')}<br/>"""
    
    if firm.firm_phone:
        firm_info += f"Phone: {firm.firm_phone}<br/>"
    if firm.firm_email:
        firm_info += f"Email: {firm.firm_email}"
    
    firm_cell = Paragraph(firm_info, firm_style)
    
    # Right side - Invoice details
    invoice_info = f"""<b>Invoice No:</b> {invoice.invoice_number}<br/>
    <b>Billing Date:</b> {invoice.invoice_date.strftime('%d %B %Y')}"""
    
    invoice_cell = Paragraph(invoice_info, ParagraphStyle('InvoiceInfo', parent=styles['Normal'], fontSize=10, alignment=TA_RIGHT))
    
    header_table = Table([[logo_cell, firm_cell, invoice_cell]], colWidths=[1.2*inch, 3*inch, 2.5*inch])
    header_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.Color(1, 0.95, 0.7)),  # Light yellow
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('BOX', (0, 0), (-1, -1), 1, colors.black),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 0.2*inch))
    
    # Bill To section
    client = invoice.client
    bill_to_text = f"""<b>Bill to:</b><br/>
    {client.name}<br/>
    {client.address.replace(chr(10), '<br/>')}"""
    
    bill_to = Paragraph(bill_to_text, styles['Normal'])
    elements.append(bill_to)
    elements.append(Spacer(1, 0.2*inch))
    
    # Items table
    items_data = [['S No.', 'Item/Service name', 'Amount']]
    
    for idx, item in enumerate(invoice.items, 1):
        items_data.append([
            str(idx),
            Paragraph(item.description, styles['Normal']),
            f"₹{item.amount:,.2f}"
        ])
    
    # Add empty rows to match template
    while len(items_data) < 5:
        items_data.append(['', '', ''])
    
    items_table = Table(items_data, colWidths=[0.6*inch, 4.7*inch, 1.5*inch])
    items_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 1, colors.black),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.9, 0.9, 0.9)),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(items_table)
    elements.append(Spacer(1, 0.1*inch))
    
    # Amount in words and totals section
    totals_data = [
        [Paragraph(f"<b>Amount (in words)</b><br/>{number_to_words_indian(int(invoice.total))} Rupees Only", styles['Normal']), 
         'Subtotal', f"₹{invoice.subtotal:,.2f}"],
        ['', '', ''],
        [Paragraph(f"<b>Description</b><br/>{invoice.short_desc or ''}", styles['Normal']), 
         'Total', f"₹{invoice.total:,.2f}"]
    ]
    
    totals_table = Table(totals_data, colWidths=[3.5*inch, 1.5*inch, 1.8*inch])
    totals_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 1, colors.black),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('BACKGROUND', (0, 0), (0, -1), colors.Color(0.95, 0.95, 0.95)),
        ('BACKGROUND', (1, 0), (-1, -1), colors.Color(0.95, 0.95, 0.95)),
        ('FONTNAME', (1, 0), (-1, -1), 'Helvetica-Bold'),
        ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(totals_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Footer section with payment details and signature
    footer_data = []
    
    # Left side - Payment details with UPI QR
    account_holder_placeholder = "<Account Holder's Name>"
    account_name_placeholder = "<Account Name>"
    bank_name_placeholder = "<Bank Name>"
    ifsc_placeholder = "<IFSC Code>"
    bank_account_placeholder = "<Bank Account Name>"
    
    payment_info = f"""<b>Name:</b> {firm.account_holder_name or account_name_placeholder}<br/>
    <b>Account Name:</b> {firm.bank_name or bank_name_placeholder}<br/>
    <b>IFSC Code:</b> {firm.ifsc_code or ifsc_placeholder}<br/>
    <b>Account Holder's Name:</b> {firm.account_holder_name or account_holder_placeholder}<br/>
    <b>Bank Account Name:</b> {firm.account_number or bank_account_placeholder}"""
    
    if firm.upi_qr_path and os.path.exists(firm.upi_qr_path):
        upi_cell = Image(firm.upi_qr_path, width=1.2*inch, height=1.2*inch)
    else:
        upi_cell = Paragraph("<b>&lt;UPI QR image&gt;</b><br/>&lt;UPI Scan to pay sticker&gt;", ParagraphStyle('Small', parent=styles['Normal'], fontSize=8))
    
    payment_cell = Paragraph(payment_info, ParagraphStyle('PaymentInfo', parent=styles['Normal'], fontSize=9))
    
    # Right side - Signature
    sig_text = f"""<b>For: {firm.firm_name}</b>"""
    
    if firm.signature_path and os.path.exists(firm.signature_path):
        sig_img = Image(firm.signature_path, width=2*inch, height=0.8*inch)
    else:
        sig_img = Paragraph("<b>&lt;Signature/Seal<br/>Image&gt;</b>", ParagraphStyle('SigPlaceholder', parent=styles['Normal'], fontSize=9, alignment=TA_CENTER))
    
    sig_cell = [
        [Paragraph(sig_text, ParagraphStyle('SigText', parent=styles['Normal'], fontSize=10, alignment=TA_CENTER))],
        [Spacer(1, 0.3*inch)],
        [sig_img],
        [Paragraph("<b>Autorized Signatory</b>", ParagraphStyle('SigLabel', parent=styles['Normal'], fontSize=9, alignment=TA_CENTER))]
    ]
    
    sig_table = Table(sig_cell, colWidths=[2.5*inch])
    sig_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    
    footer_table = Table([[upi_cell, payment_cell, sig_table]], colWidths=[1.3*inch, 2.7*inch, 2.8*inch])
    footer_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 1, colors.black),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('BACKGROUND', (0, 0), (0, -1), colors.Color(1, 0.9, 0.9)),  # Light pink for UPI
        ('BACKGROUND', (2, 0), (2, -1), colors.Color(1, 0.9, 0.9)),  # Light pink for signature
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
    ]))
    elements.append(footer_table)
    elements.append(Spacer(1, 0.2*inch))
    
    # Terms and Conditions
    if firm.billing_terms:
        terms_text = f"<b>Terms and Conditions</b><br/>{firm.billing_terms}"
        elements.append(Paragraph(terms_text, ParagraphStyle('Terms', parent=styles['Normal'], fontSize=8)))
    
    # Build PDF
    doc.build(elements)
    
    pdf_bytes = buffer.getvalue()
    buffer.close()
    
    return pdf_bytes


def generate_pdf_half_page(invoice, firm, user_id=None, bank=None):
    """
    Generate HALF_PAGE template PDF - Compact horizontal layout (A5-like on A4)
    Based on the reference image with logo, bank details, QR, signature
    
    Args:
        invoice: Invoice model
        firm: FirmDetails model
        user_id: Supabase user ID for fetching images from storage
        bank: BankAccount model for bank details
    """
    from datetime import datetime
    
    buffer = BytesIO()
    # Use A4 but content designed for half page
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=20, leftMargin=20, topMargin=20, bottomMargin=20)
    
    elements = []
    styles = getSampleStyleSheet()
    
    # Custom styles
    header_style = ParagraphStyle('Header', parent=styles['Normal'], fontSize=7, textColor=colors.black)
    small_style = ParagraphStyle('Small', parent=styles['Normal'], fontSize=7)
    tiny_style = ParagraphStyle('Tiny', parent=styles['Normal'], fontSize=6)
    bold_style = ParagraphStyle('Bold', parent=styles['Normal'], fontSize=8, fontName='Helvetica-Bold')
    
    # ======= INVOICE HEADER =======
    # Title bar
    title_data = [['Invoice']]
    title_table = Table(title_data, colWidths=[7*inch])
    title_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.black),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(title_table)
    
    # Header with Logo, Firm Details, Invoice No/Date
    # Left: Logo + Firm name/address
    logo_img = None
    
    # Try to fetch logo from Supabase Storage
    if user_id:
        logo_data = get_supabase_image(user_id, 'logo')
        if logo_data:
            try:
                logo_img = Image(logo_data, width=0.6*inch, height=0.6*inch)
            except:
                pass
    
    if not logo_img:
        logo_img = Paragraph("<b>LOGO</b>", tiny_style)
    
    # Firm name with larger font
    firm_name_style = ParagraphStyle('FirmName', parent=styles['Normal'], fontSize=10, fontName='Helvetica-Bold', leading=11)
    firm_addr_style = ParagraphStyle('FirmAddr', parent=styles['Normal'], fontSize=7, leading=8)
    
    firm_name_para = Paragraph(f"<b>{firm.firm_name}</b>", firm_name_style)
    
    # Address with tighter spacing (using comma separation instead of line breaks)
    addr_parts = []
    if firm.firm_address:
        addr_parts.append(firm.firm_address.replace(chr(10), ', '))
    if firm.firm_phone:
        phone_str = f"Ph: {firm.firm_phone}"
        if firm.firm_phone_2:
            phone_str += f", {firm.firm_phone_2}"
        addr_parts.append(phone_str)
    if firm.firm_email:
        addr_parts.append(f"Email: {firm.firm_email}")
    
    firm_addr_para = Paragraph("<br/>".join(addr_parts), firm_addr_style)
    
    # Combine firm name and address in a mini table for better control
    firm_content = Table([[firm_name_para], [firm_addr_para]], colWidths=[3.3*inch])
    firm_content.setStyle(TableStyle([
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
    ]))
    firm_cell = firm_content
    
    # Right: Invoice No (without year) and Date
    # Remove year (2025) from invoice number if present
    inv_num_display = invoice.invoice_number
    if inv_num_display and '2025' in inv_num_display:
        inv_num_display = inv_num_display.replace('2025', '').replace('//', '/').strip('/')
    inv_no_cell = Paragraph(f"<b>Invoice No.</b><br/>{inv_num_display}", small_style)
    date_cell = Paragraph(f"<b>Date</b><br/>{invoice.invoice_date.strftime('%d-%m-%Y')}", small_style)
    
    # Create header layout
    left_content = Table([[logo_img, firm_cell]], colWidths=[0.7*inch, 3.3*inch])
    left_content.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    
    header_data = [[left_content, inv_no_cell, date_cell]]
    header_table = Table(header_data, colWidths=[4*inch, 1.5*inch, 1.5*inch])
    header_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.5, colors.black),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(header_table)
    
    # ======= BILL TO SECTION =======
    client = invoice.client
    # Larger font for company name
    client_name_style = ParagraphStyle('ClientName', parent=styles['Normal'], fontSize=9, fontName='Helvetica-Bold')
    bill_to_data = [
        [Paragraph("<b>Bill To</b>", small_style)],
        [Paragraph(f"{client.name}", client_name_style)],
        [Paragraph(f"{client.address.replace(chr(10), ', ') if client.address else ''}", tiny_style)],
    ]
    bill_to_table = Table(bill_to_data, colWidths=[7*inch])
    bill_to_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.5, colors.black),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    elements.append(bill_to_table)
    
    # ======= ITEMS TABLE =======
    items_data = [['#', 'Item name', 'Amount']]
    for idx, item in enumerate(invoice.items, 1):
        items_data.append([
            str(idx),
            Paragraph(item.description, small_style),
            f"{CURRENCY_SYMBOL} {item.amount:,.2f}"
        ])
    
    # Add empty rows if less than 2 items
    while len(items_data) < 3:
        items_data.append(['', '', ''])
    
    items_table = Table(items_data, colWidths=[0.4*inch, 5.1*inch, 1.5*inch])
    items_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.5, colors.black),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('BACKGROUND', (0, 0), (-1, 0), colors.Color(0.95, 0.95, 0.95)),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 7),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(items_table)
    
    # ======= AMOUNT IN WORDS + AMOUNTS SECTION =======
    total_words = number_to_words_indian(int(invoice.total))
    
    # ROW 1: Invoice Amount in Words | Amounts + Sub Total
    row1_left = Paragraph(f"<b>Invoice Amount in Words</b><br/>{total_words} Rupees only", small_style)
    
    # Amounts and Sub Total clubbed in same cell
    row1_right_content = Table(
        [['Amount', ''], ['Sub Total', f"{CURRENCY_SYMBOL} {invoice.subtotal:,.2f}"]],
        colWidths=[1.2*inch, 1.2*inch]
    )
    row1_right_content.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 7),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    
    # ROW 2: Description | Total
    row2_left = Paragraph(f"<b>Description</b><br/>{invoice.short_desc or ''}", small_style)
    
    # Total only (Received and Balance removed)
    row2_right_content = Table(
        [['Total', f"{CURRENCY_SYMBOL} {invoice.total:,.2f}"]],
        colWidths=[1.2*inch, 1.2*inch]
    )
    row2_right_content.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 7),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    
    # Combine into 2-row layout
    # Row 1: Invoice Words (left) | Amounts+SubTotal (right)
    # Row 2: Description (left) | Total (right)
    amounts_combined = Table(
        [
            [row1_left, row1_right_content],
            [row2_left, row2_right_content]
        ],
        colWidths=[4.6*inch, 2.4*inch]
    )
    amounts_combined.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.5, colors.black),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(amounts_combined)
    
    # ======= FOOTER: BANK DETAILS + TERMS + SIGNATURE =======
    # Bank Details with QR
    qr_img = None
    
    # Try to fetch QR from Supabase Storage
    if user_id:
        qr_data = get_supabase_image(user_id, 'qr')
        if qr_data:
            try:
                qr_img = Image(qr_data, width=0.8*inch, height=0.8*inch)
            except:
                pass
    
    if not qr_img:
        qr_img = Paragraph("<b>UPI<br/>QR</b>", tiny_style)
    
    # Get bank details from bank object (or fallback to empty)
    bank_name = bank.bank_name if bank else 'N/A'
    account_number = bank.account_number if bank else 'N/A'
    ifsc_code = bank.ifsc_code if bank else 'N/A'
    account_holder = bank.account_holder_name if bank else 'N/A'
    upi_id = bank.upi_id if bank else None
    
    bank_info = f"""<b>Bank Details</b><br/>
Name : {bank_name or 'N/A'}<br/>
Account No. : {account_number or 'N/A'}<br/>
IFSC code : {ifsc_code or 'N/A'}<br/>
Account holder's name : {account_holder or 'N/A'}"""
    if upi_id:
        bank_info += f"<br/>UPI ID : {upi_id}"
    
    bank_cell = Paragraph(bank_info, tiny_style)
    
    # Terms
    terms_text = f"<b>Terms and conditions</b><br/>{firm.billing_terms or 'N/A'}"
    terms_cell = Paragraph(terms_text, tiny_style)
    
    # Signature
    sig_text = f"<b>For : {firm.firm_name}</b>"
    sig_img = None
    
    # Try to fetch signature from Supabase Storage
    if user_id:
        sig_data = get_supabase_image(user_id, 'signature')
        if sig_data:
            try:
                sig_img = Image(sig_data, width=1.2*inch, height=0.5*inch)
            except:
                pass
    
    if not sig_img:
        sig_img = Spacer(1, 0.4*inch)
    
    sig_content = [
        [Paragraph(sig_text, ParagraphStyle('SigHeader', parent=styles['Normal'], fontSize=7))],
        [sig_img],
        [Paragraph("<b>Authorized Signatory</b>", tiny_style)],
    ]
    sig_table = Table(sig_content, colWidths=[1.8*inch])
    sig_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    
    # Combine footer
    footer_data = [[qr_img, bank_cell, terms_cell, sig_table]]
    footer_table = Table(footer_data, colWidths=[0.9*inch, 2.1*inch, 2.2*inch, 1.8*inch])
    footer_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 0.5, colors.black),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('BACKGROUND', (0, 0), (1, -1), colors.Color(0.95, 0.95, 0.95)),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(footer_table)
    
    # Build PDF
    doc.build(elements)
    
    pdf_bytes = buffer.getvalue()
    buffer.close()
    
    return pdf_bytes


# Template registry
TEMPLATES = {
    'Simple': generate_pdf_simple,
    'LAW_001': generate_pdf_law_001,
    'HALF_PAGE': generate_pdf_half_page,
}


def generate_pdf_with_template(invoice, firm, template_name=None, user_id=None, bank=None):
    """Generate PDF using specified template
    
    Args:
        invoice: Invoice model
        firm: FirmDetails model (or Firm for backwards compatibility)
        template_name: Template name to use
        user_id: Supabase user ID for fetching images
        bank: BankAccount model (optional, for bank details)
    """
    if not template_name:
        template_name = firm.default_template if firm else 'Simple'
    
    print(f"DEBUG PDF Template: Requested={template_name}, Firm={firm.firm_name if firm else 'None'}")
    print(f"DEBUG PDF Template: Available templates={list(TEMPLATES.keys())}")
    
    generator = TEMPLATES.get(template_name, generate_pdf_simple)
    print(f"DEBUG PDF Template: Using generator={generator.__name__}")
    
    # Pass user_id to templates that support it (for fetching images from Supabase)
    if template_name == 'HALF_PAGE' and user_id:
        return generator(invoice, firm, user_id=user_id, bank=bank)
    else:
        return generator(invoice, firm)
