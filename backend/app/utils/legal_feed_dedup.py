"""Exact-dedup key for legal feed items."""
import hashlib
import re


def _norm(value: str) -> str:
    return re.sub(r'\s+', ' ', (value or '').strip().lower())


def compute_dedup_key(source_url, source_name, title) -> str:
    if source_url and source_url.strip():
        basis = _norm(source_url)
    else:
        basis = f"{_norm(source_name)}|{_norm(title)}"
    return hashlib.sha256(basis.encode('utf-8')).hexdigest()
