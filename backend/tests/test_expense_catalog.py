from app.case.expenses import (
    EXPENSE_CATEGORIES, EXPENSE_CATEGORY_KEYS, DEFAULT_EXPENSE_CATEGORY,
    is_valid_expense_category,
)


def test_categories():
    assert {"court_fee", "filing", "travel", "professional", "misc"} <= EXPENSE_CATEGORY_KEYS
    assert all("label" in c for c in EXPENSE_CATEGORIES)


def test_default_and_validation():
    assert DEFAULT_EXPENSE_CATEGORY == "misc"
    assert is_valid_expense_category("court_fee")
    assert not is_valid_expense_category("bribe")
