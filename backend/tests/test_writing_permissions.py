from app.rbac.permissions import ALL_PERMISSIONS, DEFAULT_ROLES


def test_writing_modules_present():
    for m in ('templates', 'drafts'):
        for a in ('create', 'read', 'update', 'delete'):
            assert f'{m}.{a}' in ALL_PERMISSIONS


def test_writing_grants():
    assert {'templates.create', 'drafts.delete'} <= set(DEFAULT_ROLES['Owner'])
    assert {'templates.create', 'drafts.create'} <= set(DEFAULT_ROLES['Partner'])
    assert 'templates.read' in DEFAULT_ROLES['Associate'] and 'templates.create' not in DEFAULT_ROLES['Associate']
    assert {'drafts.create', 'drafts.update', 'drafts.delete'} <= set(DEFAULT_ROLES['Staff'])
