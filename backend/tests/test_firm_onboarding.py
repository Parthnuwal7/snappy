"""Onboarding provisions a firm and makes the user its Owner."""
from app.models.models import db
from app.models.auth import User, FirmDetails
from app.services.firm_service import provision_firm_for_user, owner_role


def test_provision_for_user_links_firm_details(app):
    with app.app_context():
        u = User(email="new@firm.com", supabase_id="sub-new")
        db.session.add(u); db.session.commit()
        firm = provision_firm_for_user(u, "New Firm")
        fd = FirmDetails(user_id=u.id, firm_id=firm.id,
                         firm_name="New Firm", firm_address="addr")
        db.session.add(fd); db.session.commit()
        assert u.firm_id == firm.id
        assert u.role_id == owner_role(firm).id
        assert FirmDetails.query.filter_by(firm_id=firm.id).count() == 1
