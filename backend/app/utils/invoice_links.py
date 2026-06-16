"""Signed public-link helpers for invoices.

A public invoice link encodes the owning user and the invoice, plus a short
HMAC-SHA256 signature derived from a server secret. The signature makes links
*unforgeable*: without it, anyone could enumerate other invoices because
invoice ids (and numbers) are sequential. Verification is stateless and
reproducible — nothing is stored.

Link shape:  {PUBLIC_BASE_URL}/i/{user_id}/{invoice_id}/{sig}
"""
import hashlib
import hmac
import os

# Length of the hex signature kept in the URL. 32 hex chars = 128 bits, which
# is far more than enough to make guessing infeasible while keeping links short.
_SIG_LEN = 32


def _secret() -> str:
    secret = os.getenv('INVOICE_LINK_SECRET')
    if not secret:
        # Fall back to the app secret so links still work in environments that
        # haven't set the dedicated secret yet. Production must set both.
        secret = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-prod')
    return secret


def sign(user_id: int, invoice_id: int) -> str:
    """Return the hex signature for a (user_id, invoice_id) pair."""
    msg = f"{user_id}:{invoice_id}".encode('utf-8')
    digest = hmac.new(_secret().encode('utf-8'), msg, hashlib.sha256).hexdigest()
    return digest[:_SIG_LEN]


def verify(user_id: int, invoice_id: int, sig: str) -> bool:
    """Constant-time check that `sig` matches (user_id, invoice_id)."""
    if not sig:
        return False
    expected = sign(user_id, invoice_id)
    return hmac.compare_digest(expected, sig)


def build_link(user_id: int, invoice_id: int, base_url: str | None = None) -> str:
    """Build the full public invoice URL."""
    base = (base_url or os.getenv('PUBLIC_BASE_URL', '')).rstrip('/')
    sig = sign(user_id, invoice_id)
    return f"{base}/i/{user_id}/{invoice_id}/{sig}"
