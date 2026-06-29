"""PATCH /auth/profile updates the personal-profile fields."""
import jwt as _pyjwt
from app.models.models import db
from app.models.auth import User


def _token(sub='sb-prof', email='prof@firm.com'):
    return {'Authorization': 'Bearer ' + _pyjwt.encode(
        {'sub': sub, 'email': email, 'aud': 'authenticated'},
        'test-secret', algorithm='HS256')}


def test_patch_profile_updates_fields(client, make_owner):
    make_owner()
    with client.application.app_context():
        db.session.add(User(supabase_id='sb-prof', email='prof@firm.com'))
        db.session.commit()
    resp = client.patch('/api/v1/auth/profile', headers=_token(),
                        json={'full_name': 'Adv. Meera', 'designation': 'Partner',
                              'bar_council_number': 'TN/55/2018',
                              'personal_phone': '+91-9222222222'})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body['profile']['full_name'] == 'Adv. Meera'
    with client.application.app_context():
        u = User.query.filter_by(email='prof@firm.com').first()
        assert u.designation == 'Partner'
        assert u.bar_council_number == 'TN/55/2018'


def test_patch_profile_autocreates_user(client, make_owner):
    make_owner()
    resp = client.patch('/api/v1/auth/profile', headers=_token(sub='sb-new2', email='new2@firm.com'),
                        json={'full_name': 'Fresh User'})
    assert resp.status_code == 200
    with client.application.app_context():
        assert User.query.filter_by(supabase_id='sb-new2').first().full_name == 'Fresh User'
