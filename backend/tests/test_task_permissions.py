from app.rbac.permissions import ALL_PERMISSIONS, DEFAULT_ROLES


def test_tasks_module_present():
    for a in ('create', 'read', 'update', 'delete'):
        assert f'tasks.{a}' in ALL_PERMISSIONS


def test_tasks_granted_to_working_roles():
    assert 'tasks.delete' in DEFAULT_ROLES['Owner']
    for role in ('Partner', 'Associate', 'Staff'):
        assert {'tasks.create', 'tasks.read', 'tasks.update', 'tasks.delete'} <= set(DEFAULT_ROLES[role])
