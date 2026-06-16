"""Phone-number normalization for WhatsApp deep-links.

WhatsApp's wa.me links require a number in E.164 *digits only* form (country
code + national number, no '+', spaces, or punctuation). Indian numbers are the
common case, so a bare 10-digit number is assumed to be +91.
"""
import re

DEFAULT_COUNTRY_CODE = '91'  # India


def normalize_e164(raw: str | None) -> str | None:
    """Return digits-only E.164 (no leading '+'), or None if unusable.

    Examples:
        '+91 98765 43210' -> '919876543210'
        '9876543210'      -> '919876543210'
        '098765 43210'    -> '919876543210'  (strips a national trunk 0)
        '00919876543210'  -> '919876543210'  (strips international 00 prefix)
    """
    if not raw:
        return None

    had_plus = raw.strip().startswith('+')
    digits = re.sub(r'\D', '', raw)
    if not digits:
        return None

    # International access code '00' -> treat as already country-coded.
    if not had_plus and digits.startswith('00'):
        digits = digits[2:]
        had_plus = True

    if had_plus:
        # Already includes a country code; just hand back the digits.
        return digits if len(digits) >= 10 else None

    # No country code provided. Drop a national trunk '0' then prepend default.
    if digits.startswith('0'):
        digits = digits.lstrip('0')
    if len(digits) == 10:
        return DEFAULT_COUNTRY_CODE + digits
    # Already long enough to contain a country code (e.g. pasted without '+').
    if len(digits) > 10:
        return digits
    return None
