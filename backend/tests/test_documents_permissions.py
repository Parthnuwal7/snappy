from app.rbac.permissions import MODULES, ALL_PERMISSIONS, DEFAULT_ROLES


def test_documents_module_present():
    mod = next((m for m in MODULES if m['key'] == 'documents'), None)
    assert mod and mod['actions'] == ['create', 'read', 'update', 'delete']


def test_documents_permissions_registered():
    for a in ('create', 'read', 'update', 'delete'):
        assert f'documents.{a}' in ALL_PERMISSIONS


def test_default_role_grants():
    assert 'documents.read' in DEFAULT_ROLES['Staff']
    assert 'documents.create' in DEFAULT_ROLES['Staff']
    assert 'documents.delete' not in DEFAULT_ROLES['Staff']
    assert 'documents.delete' in DEFAULT_ROLES['Partner']
    assert set(DEFAULT_ROLES['Owner']) == ALL_PERMISSIONS
