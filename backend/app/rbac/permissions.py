"""Code-defined permission catalog. Roles are firm-owned bundles of these keys.

A permission key is "<module>.<action>". CRUD modules expose create/read/update/
delete; a few modules add non-CRUD capabilities where CRUD doesn't fit. New CRM
modules (matters, calendar, documents...) are added here without schema change.
"""

CRUD = ["create", "read", "update", "delete"]

MODULES = [
    {"key": "clients", "label": "Clients", "actions": CRUD},
    {"key": "invoices", "label": "Invoices", "actions": CRUD + ["send"]},
    {"key": "items", "label": "Items", "actions": CRUD},
    {"key": "recurring", "label": "Recurring", "actions": CRUD},
    {"key": "bank_accounts", "label": "Bank Accounts", "actions": CRUD},
    {"key": "firm_settings", "label": "Firm Settings", "actions": ["read", "update"]},
    {"key": "members", "label": "Members", "actions": ["read", "invite", "remove", "manage_roles"]},
    {"key": "roles", "label": "Roles", "actions": ["read", "manage"]},
    {"key": "case_files", "label": "Case Files", "actions": CRUD},
    {"key": "documents", "label": "Documents", "actions": CRUD},
    {"key": "leads", "label": "Enquiries", "actions": CRUD},
    {"key": "tasks", "label": "Tasks", "actions": CRUD},
    {"key": "templates", "label": "Templates", "actions": CRUD},
    {"key": "drafts", "label": "Drafts", "actions": CRUD},
]

ALL_PERMISSIONS = {
    f"{m['key']}.{a}" for m in MODULES for a in m["actions"]
}


def is_valid_permission(key):
    return key in ALL_PERMISSIONS


def _perms(*specs):
    """Expand ("clients", [...]) style specs into a flat, validated permission list."""
    out = set()
    for module, actions in specs:
        out.update(f"{module}.{a}" for a in actions)
    return sorted(out & ALL_PERMISSIONS)


DEFAULT_ROLES = {
    "Owner": sorted(ALL_PERMISSIONS),
    "Partner": _perms(
        ("clients", CRUD), ("invoices", CRUD + ["send"]), ("items", CRUD),
        ("recurring", CRUD), ("bank_accounts", CRUD),
        ("firm_settings", ["read", "update"]), ("members", ["read", "invite"]),
        ("roles", ["read"]), ("case_files", CRUD), ("documents", CRUD),
        ("leads", CRUD), ("tasks", CRUD),
        ("templates", CRUD), ("drafts", CRUD),
    ),
    "Associate": _perms(
        ("clients", ["create", "read", "update"]),
        ("invoices", ["create", "read", "update", "send"]),
        ("items", ["create", "read", "update"]),
        ("recurring", ["read"]), ("bank_accounts", ["read"]),
        ("firm_settings", ["read"]), ("members", ["read"]),
        ("case_files", ["create", "read", "update"]),
        ("documents", ["create", "read", "update"]),
        ("leads", ["create", "read", "update"]), ("tasks", CRUD),
        ("templates", ["read"]), ("drafts", CRUD),
    ),
    "Staff": _perms(
        ("clients", ["create", "read", "update"]),
        ("invoices", ["create", "read", "update"]),
        ("items", ["read"]), ("recurring", ["read"]),
        ("bank_accounts", ["read"]), ("members", ["read"]),
        ("case_files", ["read"]),
        ("documents", ["create", "read"]),
        ("leads", ["read"]), ("tasks", CRUD),
        ("templates", ["read"]), ("drafts", CRUD),
    ),
}
