"""POST /auth/dismiss-checklist hides the Home setup checklist."""
import jwt as _pyjwt
from app.models.auth import User


def _token(sub='sb-dis', email='dis@firm.com'):
    return {'Authorization': 'Bearer ' + _pyjwt.encode(
        {'sub': sub, 'email': email, 'aud': 'authenticated'},
        'test-secret', algorithm='HS256')}


def test_dismiss_checklist_sets_flag(client, make_owner):
    make_owner()
    h = _token()
    client.post('/api/v1/auth/onboard', headers=h,
                json={'full_name': 'Dis User', 'firm_name': 'Dis Firm'})
    resp = client.post('/api/v1/auth/dismiss-checklist', headers=h)
    assert resp.status_code == 200
    assert resp.get_json()['checklist_dismissed'] is True
    with client.application.app_context():
        assert User.query.filter_by(email='dis@firm.com').first().checklist_dismissed is True
