"""Tests for Firm/Role/FirmInvite models and firm-scoped billing columns."""
from app.models.models import db, Client
from app.models.auth import User, Firm, Role, FirmInvite


def test_firm_role_invite_roundtrip(app):
    with app.app_context():
        firm = Firm(name="Acme Legal")
        db.session.add(firm); db.session.flush()
        role = Role(firm_id=firm.id, name="Owner",
                    permissions=["clients.read"], is_system=True)
        db.session.add(role); db.session.flush()
        u = User(email="a@b.com", supabase_id="sub-1",
                 firm_id=firm.id, role_id=role.id)
        db.session.add(u); db.session.commit()
        assert firm.to_dict()["name"] == "Acme Legal"
        assert role.to_dict()["permissions"] == ["clients.read"]
        assert role.to_dict()["is_system"] is True


def test_billing_rows_are_firm_scoped_with_creator(app):
    with app.app_context():
        firm = Firm(name="F"); db.session.add(firm); db.session.flush()
        c = Client(firm_id=firm.id, created_by_user_id=7, name="Client X")
        db.session.add(c); db.session.commit()
        d = c.to_dict()
        assert d["firm_id"] == firm.id
        assert d["created_by_user_id"] == 7
        assert "user_id" not in d


def test_invite_to_dict_hides_token(app):
    with app.app_context():
        firm = Firm(name="F"); db.session.add(firm); db.session.flush()
        inv = FirmInvite(firm_id=firm.id, email="x@y.com", role_id=1,
                         token="secret-token", status="pending", invited_by=1)
        db.session.add(inv); db.session.commit()
        assert "token" not in inv.to_dict()
        assert inv.to_dict()["email"] == "x@y.com"
