"""Tests for signed public invoice links."""
from app.utils import invoice_links as il


def test_sign_is_deterministic_and_verifies():
    sig = il.sign(1, 42)
    assert il.verify(1, 42, sig) is True
    # Same inputs -> same signature.
    assert il.sign(1, 42) == sig


def test_tampered_signature_rejected():
    sig = il.sign(1, 42)
    assert il.verify(1, 42, sig[:-1] + ('0' if sig[-1] != '0' else '1')) is False
    assert il.verify(1, 42, '') is False
    assert il.verify(1, 42, 'deadbeef') is False


def test_signature_is_bound_to_both_ids():
    sig = il.sign(1, 42)
    # Wrong user or wrong invoice must not verify (prevents enumeration).
    assert il.verify(2, 42, sig) is False
    assert il.verify(1, 43, sig) is False


def test_build_link_shape():
    link = il.build_link(7, 99, base_url='https://example.com/')
    expected_sig = il.sign(7, 99)
    assert link == f"https://example.com/i/7/99/{expected_sig}"
