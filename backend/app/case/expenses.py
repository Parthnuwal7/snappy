"""Case expense category catalog."""

EXPENSE_CATEGORIES = [
    {"key": "court_fee",    "label": "Court fee"},
    {"key": "filing",       "label": "Filing / registry"},
    {"key": "travel",       "label": "Travel"},
    {"key": "professional", "label": "Professional / counsel"},
    {"key": "misc",         "label": "Miscellaneous"},
]
EXPENSE_CATEGORY_KEYS = {c["key"] for c in EXPENSE_CATEGORIES}
DEFAULT_EXPENSE_CATEGORY = "misc"


def is_valid_expense_category(key):
    return key in EXPENSE_CATEGORY_KEYS
