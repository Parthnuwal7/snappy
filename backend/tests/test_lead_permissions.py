from app.rbac.permissions import ALL_PERMISSIONS, DEFAULT_ROLES


def test_leads_module_in_catalog():
    for action in ("create", "read", "update", "delete"):
        assert f"leads.{action}" in ALL_PERMISSIONS


def test_default_role_grants_for_leads():
    assert "leads.delete" in DEFAULT_ROLES["Owner"]
    assert {"leads.create", "leads.read", "leads.update", "leads.delete"} <= set(DEFAULT_ROLES["Partner"])
    assert "leads.update" in DEFAULT_ROLES["Associate"]
    assert "leads.delete" not in DEFAULT_ROLES["Associate"]
    assert DEFAULT_ROLES["Staff"].count("leads.read") == 1
    assert "leads.create" not in DEFAULT_ROLES["Staff"]
