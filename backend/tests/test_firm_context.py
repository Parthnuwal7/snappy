"""Tests for firm-context resolution and the require_permission decorator."""
from flask import g, jsonify
from app.models.models import db
from app.models.auth import User, Role
from app.services.firm_service import provision_firm, owner_role
from app.middleware.firm_context import require_permission


def _seed_user(app, perms, is_owner=False):
    with app.app_context():
        u = User(email="u@f.com", supabase_id="sub-x")
        db.session.add(u); db.session.commit()
        firm = provision_firm("F")
        if is_owner:
            u.firm_id = firm.id; u.role_id = owner_role(firm).id
        else:
            r = Role(firm_id=firm.id, name="Custom", permissions=perms)
            db.session.add(r); db.session.flush()
            u.firm_id = firm.id; u.role_id = r.id
        db.session.commit()
        return u.id


def _register_probe(app):
    if "_probe" in app.view_functions:
        return

    @app.route("/probe-create")
    @require_permission("invoices.create")
    def _probe():
        return jsonify({"firm_id": g.firm_id})


def test_denies_without_permission(app, client, monkeypatch):
    _seed_user(app, perms=["invoices.read"])
    _register_probe(app)
    monkeypatch.setattr("app.middleware.firm_context._resolve_supabase_id", lambda: "sub-x")
    assert client.get("/probe-create").status_code == 403


def test_allows_with_permission(app, client, monkeypatch):
    _seed_user(app, perms=["invoices.create"])
    _register_probe(app)
    monkeypatch.setattr("app.middleware.firm_context._resolve_supabase_id", lambda: "sub-x")
    assert client.get("/probe-create").status_code == 200


def test_owner_bypasses_check(app, client, monkeypatch):
    _seed_user(app, perms=[], is_owner=True)
    _register_probe(app)
    monkeypatch.setattr("app.middleware.firm_context._resolve_supabase_id", lambda: "sub-x")
    assert client.get("/probe-create").status_code == 200


def test_no_firm_is_401(app, client, monkeypatch):
    with app.app_context():
        u = User(email="lonely@f.com", supabase_id="sub-lonely")
        db.session.add(u); db.session.commit()
    _register_probe(app)
    monkeypatch.setattr("app.middleware.firm_context._resolve_supabase_id", lambda: "sub-lonely")
    assert client.get("/probe-create").status_code == 401
