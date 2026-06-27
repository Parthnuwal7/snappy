from app.rbac.permissions import MODULES, ALL_PERMISSIONS, DEFAULT_ROLES


def test_case_files_module_present_with_crud():
    mod = next((m for m in MODULES if m['key'] == 'case_files'), None)
    assert mod is not None
    assert mod['actions'] == ['create', 'read', 'update', 'delete']


def test_case_files_permissions_registered():
    for action in ('create', 'read', 'update', 'delete'):
        assert f'case_files.{action}' in ALL_PERMISSIONS


def test_default_roles_grant_case_files():
    assert 'case_files.read' in DEFAULT_ROLES['Staff']
    assert 'case_files.create' in DEFAULT_ROLES['Associate']
    assert set(DEFAULT_ROLES['Partner']) >= {
        'case_files.create', 'case_files.read', 'case_files.update', 'case_files.delete'}
    assert set(DEFAULT_ROLES['Owner']) == ALL_PERMISSIONS
