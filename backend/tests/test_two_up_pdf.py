"""Two-up half-page PDF generation."""
from datetime import date
from types import SimpleNamespace
from app.services.pdf_templates import generate_pdf_half_page_two_up


def _fake_firm():
    return SimpleNamespace(
        firm_name='Test Firm', firm_address='123 St', firm_phone='999',
        firm_phone_2=None, firm_email='f@x.com', firm_website=None,
        default_template='HALF_PAGE', invoice_prefix='INV',
        billing_terms='Pay within 30 days', terms_and_conditions='Standard terms',
        logo_path=None, signature_path=None, upi_qr_path=None,
        bank_name=None, account_number=None, account_holder_name=None,
        ifsc_code=None, upi_id=None,
    )


def _fake_invoice():
    item = SimpleNamespace(description='Design work', quantity=1, rate=1000, amount=1000)
    return SimpleNamespace(
        invoice_number='INV/0001', invoice_date=date(2026, 6, 1),
        due_date=date(2026, 6, 30), short_desc='Work', tax_rate=18,
        subtotal=1000, tax_amount=180, total=1180, notes='Thanks',
        items=[item],
        client=SimpleNamespace(name='Acme', address='X', tax_id=None),
    )


def test_two_up_returns_single_page_pdf():
    pdf = generate_pdf_half_page_two_up(_fake_invoice(), _fake_firm())
    assert isinstance(pdf, (bytes, bytearray))
    assert pdf[:4] == b'%PDF'
    # One physical page (two copies composited onto it).
    try:
        from pypdf import PdfReader
        from io import BytesIO
        assert len(PdfReader(BytesIO(pdf)).pages) == 1
    except ImportError:
        pass  # pypdf optional; header check above is the minimum guarantee
