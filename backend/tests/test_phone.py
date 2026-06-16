"""Tests for phone normalization used in WhatsApp deep-links."""
from app.utils.phone import normalize_e164


def test_bare_indian_10_digit_gets_country_code():
    assert normalize_e164('9876543210') == '919876543210'


def test_strips_separators_and_plus():
    assert normalize_e164('+91 98765 43210') == '919876543210'
    assert normalize_e164('+91-98765-43210') == '919876543210'


def test_strips_national_trunk_zero():
    assert normalize_e164('098765 43210') == '919876543210'


def test_international_double_zero_prefix():
    assert normalize_e164('00919876543210') == '919876543210'


def test_already_country_coded_without_plus():
    assert normalize_e164('919876543210') == '919876543210'


def test_invalid_inputs_return_none():
    assert normalize_e164(None) is None
    assert normalize_e164('') is None
    assert normalize_e164('abc') is None
    assert normalize_e164('12345') is None
