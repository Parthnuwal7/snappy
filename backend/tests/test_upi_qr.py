"""Dynamic UPI QR feature: model fields, deep-link builder, QR PNG, JSON, validation."""
from urllib.parse import parse_qs, urlsplit

from app.models.models import db
from app.models.auth import BankAccount
from app.services.upi import build_upi_uri, compose_note, qr_png


def test_bank_account_has_upi_fields_and_no_qr_path(app):
    with app.app_context():
        b = BankAccount(user_id=1, upi_id='adv@okbank',
                        upi_payee_name='Parth Chambers', upi_note='Legal Fee',
                        is_default=True)
        d = b.to_dict()
        assert d['upi_payee_name'] == 'Parth Chambers'
        assert d['upi_note'] == 'Legal Fee'
        assert 'upi_qr_path' not in d


def test_build_upi_uri_full():
    uri = build_upi_uri('adv@okbank', 'Parth Chambers', amount=15000,
                        note='Legal Fee — INV-2026-04', invoice_no='INV-2026-04')
    assert uri.startswith('upi://pay?')
    q = parse_qs(urlsplit(uri).query)
    assert q['pa'] == ['adv@okbank']
    assert q['pn'] == ['Parth Chambers']
    assert q['am'] == ['15000.00']
    assert q['cu'] == ['INR']
    assert q['tn'] == ['Legal Fee — INV-2026-04']
    assert q['tr'] == ['INV-2026-04']


def test_build_upi_uri_omits_amount_when_zero():
    uri = build_upi_uri('adv@okbank', 'Parth Chambers', amount=0, invoice_no='INV-1')
    q = parse_qs(urlsplit(uri).query)
    assert 'am' not in q
    assert q['cu'] == ['INR']


def test_build_upi_uri_empty_without_upi_id():
    assert build_upi_uri('', 'Parth Chambers', amount=100) == ''


def test_compose_note():
    assert compose_note('Legal Fee', 'INV-1') == 'Legal Fee — INV-1'
    assert compose_note('', 'INV-1') == 'INV-1'
    assert compose_note(None, 'INV-1') == 'INV-1'


def test_qr_png_returns_png_bytes():
    data = qr_png(build_upi_uri('adv@okbank', 'Parth Chambers', amount=10, invoice_no='INV-1'))
    assert isinstance(data, (bytes, bytearray))
    assert bytes(data[:8]) == b'\x89PNG\r\n\x1a\n'


# ---- PDF embeds a dynamic QR (or falls back) without crashing ----

def _fake_firm():
    from types import SimpleNamespace
    return SimpleNamespace(
        firm_name='Parth Chambers', firm_address='Court Rd', firm_phone='999',
        firm_phone_2=None, firm_email='f@x.com', firm_website=None,
        default_template='HALF_PAGE', invoice_prefix='INV',
        billing_terms='Pay within 30 days', terms_and_conditions='Standard terms',
        logo_path=None, signature_path=None,
    )


def _fake_invoice():
    from types import SimpleNamespace
    from datetime import date
    item = SimpleNamespace(description='Retainer', quantity=1, rate=15000, amount=15000)
    return SimpleNamespace(
        invoice_number='INV-2026-04', invoice_date=date(2026, 6, 1),
        due_date=date(2026, 6, 30), short_desc='Work', tax_rate=0,
        subtotal=15000, tax_amount=0, total=15000, notes='Thanks',
        items=[item], client=SimpleNamespace(name='Acme', address='X', tax_id=None),
    )


def _as_bytes(out):
    return out.getvalue() if hasattr(out, 'getvalue') else out


def test_half_page_pdf_generates_with_and_without_upi():
    from types import SimpleNamespace
    from app.services.pdf_templates import generate_pdf_half_page
    bank_with = SimpleNamespace(bank_name='HDFC', account_number='123', ifsc_code='HDFC0001',
                                account_holder_name='Parth', upi_id='adv@okbank',
                                upi_payee_name='Parth Chambers', upi_note='Legal Fee')
    bank_without = SimpleNamespace(bank_name='HDFC', account_number='123', ifsc_code='HDFC0001',
                                   account_holder_name='Parth', upi_id=None,
                                   upi_payee_name=None, upi_note=None)
    for bank in (bank_with, bank_without):
        out = generate_pdf_half_page(_fake_invoice(), _fake_firm(), bank=bank)
        assert _as_bytes(out)[:4] == b'%PDF'


# ---- 'qr' upload type retired ----

def test_qr_upload_type_removed(app, client, make_owner):
    headers, _ = make_owner()
    resp = client.post('/api/v1/storage/upload/qr', headers=headers)
    assert resp.status_code in (400, 404)


# ---- upi_uri exposed in invoice + public JSON ----

def _seed_invoice_with_bank(client, headers):
    """Save a default bank with UPI + create one invoice; return invoice id."""
    client.put('/api/v1/auth/bank', headers=headers, json={
        'bank_name': 'HDFC', 'account_number': '123', 'ifsc_code': 'HDFC0001',
        'account_holder_name': 'Parth', 'upi_id': 'adv@okbank',
        'upi_payee_name': 'Parth Chambers', 'upi_note': 'Legal Fee',
    })
    c = client.post('/api/v1/clients', headers=headers,
                    json={'name': 'Acme', 'email': 'a@b.com'}).get_json()
    inv = client.post('/api/v1/invoices', headers=headers, json={
        'client_id': c['id'],
        'invoice_date': '2026-06-01',
        'items': [{'description': 'Retainer', 'quantity': 1, 'rate': 15000, 'amount': 15000}],
    }).get_json()
    return inv['id']


def test_invoice_json_includes_upi_uri(app, client, make_owner):
    headers, _ = make_owner()
    inv_id = _seed_invoice_with_bank(client, headers)
    detail = client.get(f'/api/v1/invoices/{inv_id}', headers=headers).get_json()
    assert 'upi_uri' in detail
    assert detail['upi_uri'].startswith('upi://pay?')
    assert parse_qs(urlsplit(detail['upi_uri']).query)['pa'] == ['adv@okbank']


def test_public_dict_includes_upi_uri():
    from types import SimpleNamespace
    from app.api.public import _public_dict
    invoice = SimpleNamespace(
        invoice_number='INV-1', invoice_date=None, due_date=None, status='sent',
        short_desc='', subtotal=500, tax_rate=0, tax_amount=0, total=500,
        client=SimpleNamespace(name='Acme'), items=[])
    bank = SimpleNamespace(upi_id='adv@okbank', upi_payee_name='Parth Chambers',
                           upi_note='Fee', bank_name='HDFC', account_number='1',
                           ifsc_code='X', account_holder_name='Parth')
    d = _public_dict(invoice, None, bank)
    assert d['payment']['upi_uri'].startswith('upi://pay?')
    assert parse_qs(urlsplit(d['payment']['upi_uri']).query)['pa'] == ['adv@okbank']


# ---- banking save requires UPI identity ----

def test_bank_save_requires_upi(app, client, make_owner):
    headers, _ = make_owner()
    resp = client.put('/api/v1/auth/bank', headers=headers, json={
        'bank_name': 'HDFC', 'account_number': '123',
    })
    assert resp.status_code == 400
    assert 'UPI' in resp.get_json()['error']


def test_bank_save_succeeds_with_upi(app, client, make_owner):
    headers, _ = make_owner()
    resp = client.put('/api/v1/auth/bank', headers=headers, json={
        'bank_name': 'HDFC', 'upi_id': 'adv@okbank', 'upi_payee_name': 'Parth Chambers',
    })
    assert resp.status_code == 200
