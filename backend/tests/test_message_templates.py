"""Tests for invoice message templating."""
from types import SimpleNamespace
from datetime import date

from app.services import message_templates as mt


def _ctx():
    invoice = SimpleNamespace(invoice_number='INV/0007', total=5900, due_date=date(2026, 7, 1))
    firm = SimpleNamespace(firm_name='Acme Legal',
                           email_subject_template=None,
                           email_body_template=None,
                           whatsapp_template=None)
    client = SimpleNamespace(name='Rao & Co')
    return invoice, firm, client


def test_build_context_formats_money_and_due():
    invoice, firm, client = _ctx()
    ctx = mt.build_context(invoice, firm, client, 'https://x/i/1/7/abc', currency='INR')
    assert ctx['client_name'] == 'Rao & Co'
    assert ctx['invoice_number'] == 'INV/0007'
    assert ctx['firm_name'] == 'Acme Legal'
    assert ctx['total'] == '₹5,900.00'
    assert ctx['due_date'] == '2026-07-01'
    assert ctx['invoice_link'] == 'https://x/i/1/7/abc'


def test_render_defaults_used_when_firm_templates_null():
    invoice, firm, client = _ctx()
    ctx = mt.build_context(invoice, firm, client, 'LINK')
    subject, body = mt.render_email(firm, ctx)
    assert subject == 'Invoice INV/0007 from Acme Legal'
    assert 'INV/0007' in body and 'LINK' in body and 'Acme Legal' in body
    wa = mt.render_whatsapp(firm, ctx)
    assert 'Rao & Co' in wa and 'LINK' in wa


def test_firm_custom_template_overrides_default():
    invoice, firm, client = _ctx()
    firm.whatsapp_template = 'Invoice {invoice_number}: {invoice_link}'
    ctx = mt.build_context(invoice, firm, client, 'LINK')
    assert mt.render_whatsapp(firm, ctx) == 'Invoice INV/0007: LINK'


def test_unknown_placeholder_does_not_raise():
    # A mistyped placeholder is left intact rather than blowing up.
    assert mt.render('Hi {oops}', {'client_name': 'x'}) == 'Hi {oops}'


def test_due_date_missing_falls_back():
    invoice = SimpleNamespace(invoice_number='INV/1', total=100, due_date=None)
    ctx = mt.build_context(invoice, None, SimpleNamespace(name='C'), 'L')
    assert ctx['due_date'] == 'on receipt'
    assert ctx['firm_name'] == ''
