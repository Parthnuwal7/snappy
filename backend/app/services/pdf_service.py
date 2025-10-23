"""PDF generation service using ReportLab"""
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_RIGHT, TA_CENTER
from io import BytesIO
import os


def number_to_words_indian(num):
    """Convert number to words in Indian English"""
    if num == 0:
        return "Zero"
    
    # Indian number system
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
    
    # Handle crores, lakhs, thousands
    crore = num // 10000000
    lakh = (num % 10000000) // 100000
    thousand = (num % 100000) // 1000
    hundred = num % 1000
    
    result = []
    if crore:
        result.append(convert_hundreds(crore) + " Crore")
    if lakh:
        result.append(convert_hundreds(lakh) + " Lakh")
    if thousand:
        result.append(convert_hundreds(thousand) + " Thousand")
    if hundred:
        result.append(convert_hundreds(hundred))
    
    return " ".join(result).strip()


def format_currency(amount, currency="INR"):
    """Format amount with currency symbol"""
    if currency == "INR":
        return f"₹{amount:,.2f}"
    else:
        return f"{currency} {amount:,.2f}"


INVOICE_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif;
            font-size: 11pt;
            line-height: 1.5;
            color: #1f2937;
            padding: 40px;
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
            border-bottom: 3px solid #2563eb;
            padding-bottom: 20px;
        }
        .header h1 {
            font-size: 32pt;
            color: #1e40af;
            margin-bottom: 5px;
        }
        .header p {
            color: #6b7280;
            font-size: 11pt;
        }
        .invoice-meta {
            display: flex;
            justify-content: space-between;
            margin-bottom: 30px;
        }
        .invoice-meta div {
            width: 48%;
        }
        .invoice-meta h3 {
            font-size: 13pt;
            color: #1f2937;
            margin-bottom: 10px;
            border-bottom: 2px solid #e5e7eb;
            padding-bottom: 5px;
        }
        .invoice-meta p {
            margin: 5px 0;
            font-size: 10pt;
        }
        .invoice-details {
            background: #f3f4f6;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 25px;
        }
        .invoice-details table {
            width: 100%;
        }
        .invoice-details td {
            padding: 5px 0;
            font-size: 10pt;
        }
        .invoice-details td:first-child {
            font-weight: 600;
            width: 40%;
        }
        .items-table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 20px;
        }
        .items-table th {
            background: #2563eb;
            color: white;
            padding: 12px;
            text-align: left;
            font-size: 11pt;
            font-weight: 600;
        }
        .items-table td {
            padding: 10px 12px;
            border-bottom: 1px solid #e5e7eb;
        }
        .items-table tr:last-child td {
            border-bottom: 2px solid #2563eb;
        }
        .items-table .text-right {
            text-align: right;
        }
        .totals {
            margin-left: auto;
            width: 350px;
            margin-bottom: 20px;
        }
        .totals table {
            width: 100%;
        }
        .totals td {
            padding: 8px;
            font-size: 11pt;
        }
        .totals .total-row {
            background: #eff6ff;
            font-weight: 700;
            font-size: 13pt;
            color: #1e40af;
        }
        .total-words {
            background: #fef3c7;
            padding: 12px;
            border-left: 4px solid #f59e0b;
            margin-bottom: 25px;
            font-size: 10pt;
        }
        .total-words strong {
            color: #92400e;
        }
        .signature {
            margin-top: 50px;
            text-align: right;
        }
        .signature img {
            max-width: 200px;
            max-height: 80px;
        }
        .signature-line {
            border-top: 2px solid #000;
            width: 250px;
            margin-left: auto;
            margin-top: 10px;
            padding-top: 5px;
            text-align: center;
            font-size: 10pt;
        }
        .footer {
            margin-top: 40px;
            text-align: center;
            color: #6b7280;
            font-size: 9pt;
            border-top: 1px solid #e5e7eb;
            padding-top: 15px;
        }
        .notes {
            margin-top: 20px;
            padding: 15px;
            background: #f9fafb;
            border-left: 3px solid #6b7280;
            font-size: 10pt;
        }
        .notes h4 {
            margin-bottom: 8px;
            color: #374151;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>SNAPPY</h1>
        <p>Professional Billing & Invoicing</p>
    </div>

    <div class="invoice-meta">
        <div>
            <h3>Bill To:</h3>
            <p><strong>{{ client.name }}</strong></p>
            {% if client.address %}
            <p>{{ client.address | replace('\n', '<br>') | safe }}</p>
            {% endif %}
            {% if client.email %}
            <p>Email: {{ client.email }}</p>
            {% endif %}
            {% if client.phone %}
            <p>Phone: {{ client.phone }}</p>
            {% endif %}
            {% if client.tax_id %}
            <p>Tax ID: {{ client.tax_id }}</p>
            {% endif %}
        </div>
        <div>
            <h3>Invoice Details:</h3>
            <div class="invoice-details">
                <table>
                    <tr>
                        <td>Invoice Number:</td>
                        <td><strong>{{ invoice.invoice_number }}</strong></td>
                    </tr>
                    <tr>
                        <td>Invoice Date:</td>
                        <td>{{ invoice.invoice_date }}</td>
                    </tr>
                    {% if invoice.due_date %}
                    <tr>
                        <td>Due Date:</td>
                        <td>{{ invoice.due_date }}</td>
                    </tr>
                    {% endif %}
                    <tr>
                        <td>Status:</td>
                        <td><strong style="text-transform: uppercase;">{{ invoice.status }}</strong></td>
                    </tr>
                </table>
            </div>
        </div>
    </div>

    {% if invoice.short_desc %}
    <div style="margin-bottom: 20px; padding: 10px; background: #eff6ff; border-left: 3px solid #2563eb;">
        <strong>Description:</strong> {{ invoice.short_desc }}
    </div>
    {% endif %}

    <table class="items-table">
        <thead>
            <tr>
                <th style="width: 5%;">#</th>
                <th style="width: 50%;">Description</th>
                <th style="width: 10%;" class="text-right">Qty</th>
                <th style="width: 15%;" class="text-right">Rate</th>
                <th style="width: 20%;" class="text-right">Amount</th>
            </tr>
        </thead>
        <tbody>
            {% for item in items %}
            <tr>
                <td>{{ loop.index }}</td>
                <td>{{ item.description }}</td>
                <td class="text-right">{{ item.quantity }}</td>
                <td class="text-right">{{ format_currency(item.rate) }}</td>
                <td class="text-right">{{ format_currency(item.amount) }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>

    <div class="totals">
        <table>
            <tr>
                <td>Subtotal:</td>
                <td class="text-right">{{ format_currency(invoice.subtotal) }}</td>
            </tr>
            <tr>
                <td>Tax ({{ invoice.tax_rate }}%):</td>
                <td class="text-right">{{ format_currency(invoice.tax_amount) }}</td>
            </tr>
            <tr class="total-row">
                <td>Total:</td>
                <td class="text-right">{{ format_currency(invoice.total) }}</td>
            </tr>
        </table>
    </div>

    <div class="total-words">
        <strong>Amount in Words:</strong> {{ total_in_words }} {{ currency }} Only
    </div>

    {% if invoice.notes %}
    <div class="notes">
        <h4>Notes:</h4>
        <p>{{ invoice.notes }}</p>
    </div>
    {% endif %}

    <div class="signature">
        {% if signature_path and signature_exists %}
        <img src="file://{{ signature_path }}" alt="Signature">
        {% endif %}
        <div class="signature-line">
            Authorized Signature
        </div>
    </div>

    <div class="footer">
        <p>Generated by SNAPPY - Invoice Management System</p>
        <p>Generated on: {{ generation_date }}</p>
    </div>
</body>
</html>
"""


def generate_pdf(invoice):
    """
    Generate PDF invoice from invoice model using ReportLab
    
    Args:
        invoice: Invoice model instance with related client and items
        
    Returns:
        bytes: PDF file content
    """
    from datetime import datetime
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    
    # Container for the 'Flowable' objects
    elements = []
    
    # Define styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], fontSize=24, textColor=colors.HexColor('#1e40af'), alignment=TA_CENTER)
    heading_style = ParagraphStyle('CustomHeading', parent=styles['Heading2'], fontSize=14, textColor=colors.HexColor('#1e40af'))
    normal_style = styles['Normal']
    right_align_style = ParagraphStyle('RightAlign', parent=styles['Normal'], alignment=TA_RIGHT)
    
    # Title
    elements.append(Paragraph("INVOICE", title_style))
    elements.append(Spacer(1, 0.3*inch))
    
    # Invoice Details Table
    invoice_info = [
        ['Invoice Number:', invoice.invoice_number],
        ['Date:', invoice.invoice_date.strftime('%d %B %Y')],
        ['Status:', invoice.status.upper()],
    ]
    if invoice.due_date:
        invoice_info.append(['Due Date:', invoice.due_date.strftime('%d %B %Y')])
    if invoice.paid_date:
        invoice_info.append(['Paid Date:', invoice.paid_date.strftime('%d %B %Y')])
    
    invoice_table = Table(invoice_info, colWidths=[2*inch, 3*inch])
    invoice_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(invoice_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Bill To Section
    elements.append(Paragraph("BILL TO", heading_style))
    elements.append(Spacer(1, 0.1*inch))
    client = invoice.client
    client_info = f"<b>{client.name}</b><br/>{client.address.replace(chr(10), '<br/>')}<br/>Email: {client.email}<br/>Phone: {client.phone}"
    if client.tax_id:
        client_info += f"<br/>Tax ID: {client.tax_id}"
    elements.append(Paragraph(client_info, normal_style))
    elements.append(Spacer(1, 0.3*inch))
    
    # Line Items Table
    elements.append(Paragraph("ITEMS", heading_style))
    elements.append(Spacer(1, 0.1*inch))
    
    # Table data
    data = [['#', 'Description', 'Quantity', 'Rate', 'Amount']]
    for idx, item in enumerate(invoice.items, 1):
        data.append([
            str(idx),
            Paragraph(item.description, normal_style),
            str(item.quantity),
            f"₹{item.rate:,.2f}",
            f"₹{item.amount:,.2f}"
        ])
    
    # Add totals
    data.append(['', '', '', 'Subtotal:', f"₹{invoice.subtotal:,.2f}"])
    data.append(['', '', '', f'Tax ({invoice.tax_rate}%):', f"₹{invoice.tax_amount:,.2f}"])
    data.append(['', '', '', 'TOTAL:', f"₹{invoice.total:,.2f}"])
    
    # Create table
    item_table = Table(data, colWidths=[0.5*inch, 3.5*inch, 0.8*inch, 1.2*inch, 1.2*inch])
    item_table.setStyle(TableStyle([
        # Header row
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e40af')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        
        # Data rows
        ('ALIGN', (2, 1), (-1, -4), 'RIGHT'),
        ('FONTNAME', (0, 1), (-1, -4), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -4), 9),
        ('BOTTOMPADDING', (0, 1), (-1, -4), 8),
        ('GRID', (0, 0), (-1, -4), 0.5, colors.grey),
        
        # Totals rows
        ('ALIGN', (3, -3), (-1, -1), 'RIGHT'),
        ('FONTNAME', (3, -3), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (3, -3), (-1, -1), 10),
        ('LINEABOVE', (3, -3), (-1, -3), 1, colors.grey),
        ('LINEABOVE', (3, -1), (-1, -1), 2, colors.HexColor('#1e40af')),
    ]))
    elements.append(item_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Amount in words
    total_words = number_to_words_indian(int(invoice.total))
    elements.append(Paragraph(f"<b>Amount in Words:</b> {total_words} Rupees Only", normal_style))
    elements.append(Spacer(1, 0.3*inch))
    
    # Signature
    if invoice.signature_path and os.path.exists(invoice.signature_path):
        try:
            sig_img = Image(invoice.signature_path, width=2*inch, height=1*inch)
            elements.append(sig_img)
        except:
            pass
    
    elements.append(Spacer(1, 0.2*inch))
    elements.append(Paragraph("Authorized Signature", right_align_style))
    
    # Build PDF
    doc.build(elements)
    
    # Get PDF bytes
    pdf_bytes = buffer.getvalue()
    buffer.close()
    
    return pdf_bytes
