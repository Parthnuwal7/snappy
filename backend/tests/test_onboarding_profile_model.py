"""Migration 023 model layer: personal-profile columns + nullable firm_address."""
from app.models.models import db
from app.models.auth import User, FirmDetails
from app.services.firm_service import provision_firm_for_user


def test_user_persists_personal_profile_fields(app):
    with app.app_context():
        u = User(email='p@firm.com', supabase_id='sb-p',
                 full_name='Adv. Priya Rao', designation='Advocate',
                 bar_council_number='MAH/1234/2020', personal_phone='+91-9000000000',
                 is_solo=True)
        db.session.add(u)
        db.session.commit()
        got = User.query.filter_by(email='p@firm.com').first()
        assert got.full_name == 'Adv. Priya Rao'
        assert got.designation == 'Advocate'
        assert got.bar_council_number == 'MAH/1234/2020'
        assert got.personal_phone == '+91-9000000000'
        assert got.is_solo is True
        # Defaults: dismiss flag is False out of the box.
        assert got.checklist_dismissed is False
        d = got.to_dict()
        assert d['full_name'] == 'Adv. Priya Rao'
        assert d['is_solo'] is True
        assert d['checklist_dismissed'] is False


def test_firm_details_allows_null_address(app):
    with app.app_context():
        u = User(email='n@firm.com', supabase_id='sb-n')
        db.session.add(u)
        db.session.commit()
        firm = provision_firm_for_user(u, 'No Address Firm')
        fd = FirmDetails(user_id=u.id, firm_id=firm.id, firm_name='No Address Firm',
                         firm_address=None)
        db.session.add(fd)
        db.session.commit()
        assert FirmDetails.query.filter_by(firm_id=firm.id).first().firm_address is None
