"""Tests for the legal feed dedup key utility."""
from app.utils.legal_feed_dedup import compute_dedup_key


def test_same_url_same_key():
    a = compute_dedup_key('https://x.com/1', 'LiveLaw', 'Title A')
    b = compute_dedup_key('https://X.com/1 ', 'LiveLaw', 'Different title')
    assert a == b  # URL drives the key; normalization ignores case/whitespace


def test_different_url_different_key():
    a = compute_dedup_key('https://x.com/1', 'LiveLaw', 'T')
    b = compute_dedup_key('https://x.com/2', 'LiveLaw', 'T')
    assert a != b


def test_fallback_to_source_and_title_when_no_url():
    a = compute_dedup_key(None, 'SC', 'Order of the day')
    b = compute_dedup_key('', 'sc', 'order of the day ')
    assert a == b
    assert len(a) == 64
