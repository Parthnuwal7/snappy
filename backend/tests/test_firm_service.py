"""Tests for firm provisioning (seed firm + default roles + owner)."""
from app.models.models import db
from app.models.auth import User, Role
from app.rbac.permissions import ALL_PERMISSIONS
from app.services.firm_service import (
    provision_firm, owner_role, provision_firm_for_user,
)


def test_provision_seeds_four_default_roles(app):
    with app.app_context():
        firm = provision_firm("Acme Legal")
        roles = Role.query.filter_by(firm_id=firm.id).all()
        names = {r.name for r in roles}
        assert names == {"Owner", "Partner", "Associate", "Staff"}


def test_owner_role_is_system_and_omnipotent(app):
    with app.app_context():
        firm = provision_firm("Acme")
        owner = owner_role(firm)
        assert owner.is_system is True
        assert set(owner.permissions) == ALL_PERMISSIONS


def test_provision_for_user_makes_them_owner(app):
    with app.app_context():
        u = User(email="o@firm.com", supabase_id="sub-o")
        db.session.add(u); db.session.commit()
        firm = provision_firm_for_user(u, "O's Firm")
        assert u.firm_id == firm.id
        assert u.role_id == owner_role(firm).id
