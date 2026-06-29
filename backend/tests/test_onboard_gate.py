"""The slimmed onboarding gate: profile + firm name only; firm provisioned."""
import jwt as _pyjwt
from app.models.auth import User, FirmDetails, Firm


def _token(sub='sb-gate', email='gate@firm.com'):
    return {'Authorization': 'Bearer ' + _pyjwt.encode(
        {'sub': sub, 'email': email, 'aud': 'authenticated'},
        'test-secret', algorithm='HS256')}


def test_onboard_gate_provisions_firm_with_profile(client, make_owner):
    make_owner()  # ensures jwt secret is monkeypatched to 'test-secret'
    resp = client.post('/api/v1/auth/onboard', headers=_token(),
                       json={'full_name': 'Adv. Asha N', 'designation': 'Advocate',
                             'bar_council_number': 'KAR/99/2019',
                             'personal_phone': '+91-9111111111',
                             'firm_name': 'Asha Chambers', 'is_solo': True})
    assert resp.status_code == 201
    with client.application.app_context():
        u = User.query.filter_by(email='gate@firm.com').first()
        assert u.is_onboarded is True
        assert u.full_name == 'Adv. Asha N'
        assert u.is_solo is True
        assert u.firm_id is not None
        fd = FirmDetails.query.filter_by(firm_id=u.firm_id).first()
        assert fd.firm_name == 'Asha Chambers'
        assert fd.firm_address is None       # gate does not collect address
        assert Firm.query.get(u.firm_id).name == 'Asha Chambers'


def test_onboard_gate_requires_full_name_and_firm_name(client, make_owner):
    make_owner()
    r1 = client.post('/api/v1/auth/onboard', headers=_token(sub='sb-x', email='x@f.com'),
                     json={'firm_name': 'X'})
    assert r1.status_code == 400
    r2 = client.post('/api/v1/auth/onboard', headers=_token(sub='sb-y', email='y@f.com'),
                     json={'full_name': 'Y'})
    assert r2.status_code == 400


def test_onboard_gate_rejects_double_onboard(client, make_owner):
    make_owner()
    h = _token(sub='sb-d', email='d@f.com')
    first = client.post('/api/v1/auth/onboard', headers=h,
                        json={'full_name': 'D', 'firm_name': 'D Firm'})
    assert first.status_code == 201
    again = client.post('/api/v1/auth/onboard', headers=h,
                        json={'full_name': 'D', 'firm_name': 'D Firm 2'})
    assert again.status_code == 400
