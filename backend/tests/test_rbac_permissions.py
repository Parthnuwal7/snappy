"""Tests for the code-defined permission catalog."""
from app.rbac.permissions import (
    MODULES, ALL_PERMISSIONS, DEFAULT_ROLES, is_valid_permission,
)


def test_catalog_has_billing_and_admin_modules():
    keys = {m["key"] for m in MODULES}
    assert {"clients", "invoices", "items", "recurring",
            "bank_accounts", "firm_settings", "members", "roles"} <= keys


def test_all_permissions_are_module_dot_action():
    assert "invoices.create" in ALL_PERMISSIONS
    assert "members.invite" in ALL_PERMISSIONS
    assert "roles.manage" in ALL_PERMISSIONS
    for key in ALL_PERMISSIONS:
        assert "." in key


def test_owner_default_role_has_every_permission():
    assert set(DEFAULT_ROLES["Owner"]) == ALL_PERMISSIONS


def test_non_owner_defaults_are_subsets():
    for name in ("Partner", "Associate", "Staff"):
        assert set(DEFAULT_ROLES[name]) <= ALL_PERMISSIONS
    assert "invoices.delete" not in DEFAULT_ROLES["Associate"]
    assert "roles.manage" not in DEFAULT_ROLES["Staff"]


def test_is_valid_permission():
    assert is_valid_permission("clients.read")
    assert not is_valid_permission("clients.teleport")
    assert not is_valid_permission("garbage")
