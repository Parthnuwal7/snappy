"""Invoice PDF templates"""
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_RIGHT, TA_CENTER, TA_LEFT
from io import BytesIO
import os


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
    from backend.app.services.pdf_service import generate_pdf as original_generate_pdf
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


# Template registry
TEMPLATES = {
    'Simple': generate_pdf_simple,
    'LAW_001': generate_pdf_law_001,
}


def generate_pdf_with_template(invoice, firm, template_name=None):
    """Generate PDF using specified template"""
    if not template_name:
        template_name = firm.default_template if firm else 'Simple'
    
    print(f"DEBUG PDF Template: Requested={template_name}, Firm={firm.firm_name if firm else 'None'}")
    print(f"DEBUG PDF Template: Available templates={list(TEMPLATES.keys())}")
    
    generator = TEMPLATES.get(template_name, generate_pdf_simple)
    print(f"DEBUG PDF Template: Using generator={generator.__name__}")
    
    return generator(invoice, firm)
