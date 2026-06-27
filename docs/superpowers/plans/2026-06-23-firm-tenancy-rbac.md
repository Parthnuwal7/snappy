# Firm Tenancy & RBAC Foundation — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate Snappy from single-user scoping to a firm tenant with many users, where each user has one role whose permissions are a custom module × CRUD matrix.

**Architecture:** A new `Firm` tenant owns all billing data (re-scoped from `user_id` to `firm_id`, with the old `user_id` renamed to `created_by_user_id` for attribution). A code-defined permission catalog drives editable, firm-owned `Role` rows. Request middleware resolves user → firm → permissions into `g`, and a `@require_permission` decorator guards endpoints. Members join via tokenized email invites. Migration is in-place and non-destructive; Parth applies the SQL on Supabase manually, while tests build the schema from models on SQLite.

**Tech Stack:** Flask, SQLAlchemy, Postgres (Supabase) in prod / SQLite in tests, Supabase JWT auth, Resend email, React + TypeScript (Vite) frontend.

## Global Constraints

- Tenancy is **strict 1:1**: a user has exactly one `firm_id` and one `role_id`. No firm switcher.
- Billing data is **firm-owned**: scope every query by `g.firm_id`, never `user_id`.
- The five billing tables (`clients`, `items`, `invoices`, `recurring_schedules`, `bank_accounts`) **rename `user_id` → `created_by_user_id`** and **add `firm_id`**. No column is dropped, moved, or copied.
- `legal_feed_preferences`, `legal_feed_events`, and `users.device_*` stay **user-scoped** (personal, not firm data).
- The **Owner** role (`is_system=True`) has all permissions, is undeletable, and the last Owner cannot be demoted/removed.
- Permission keys are `"<module>.<action>"` from the code catalog only. Firm-owned roles store a JSON list of those keys.
- Tests run on in-memory SQLite via `db.create_all()`; all new models must compile on SQLite (use `db.JSON`, no Postgres-only types without `.with_variant`).
- **Do not run git commits** — Parth handles git. End each task at a green test run, not a commit.
- The Supabase SQL migration (Task 14) is delivered as a file for Parth to apply manually; no code path executes it.

---

### Task 1: Permission catalog

**Files:**
- Create: `backend/app/rbac/__init__.py` (empty)
- Create: `backend/app/rbac/permissions.py`
- Test: `backend/tests/test_rbac_permissions.py`

**Interfaces:**
- Produces:
  - `MODULES: list[dict]` — `[{"key": "clients", "label": "Clients", "actions": ["create","read","update","delete"]}, ...]`
  - `ALL_PERMISSIONS: set[str]` — every valid `"module.action"` key.
  - `DEFAULT_ROLES: dict[str, list[str]]` — keys `"Owner"`, `"Partner"`, `"Associate"`, `"Staff"`; Owner maps to `sorted(ALL_PERMISSIONS)`.
  - `is_valid_permission(key: str) -> bool`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_rbac_permissions.py
from app.rbac.permissions import (
    MODULES, ALL_PERMISSIONS, DEFAULT_ROLES, is_valid_permission,
)

def test_catalog_has_billing_and_admin_modules():
    keys = {m["key"] for m in MODULES}
    assert {"clients", "invoices", "items", "recurring",
            "bank_accounts", "firm_settings", "members", "roles"} <= keys

def test_all_permissions_are_module_dot_action():
    assert "invoices.create" in ALL_PERMISSIONS
    assert "members.invite" in ALL_PERMISSIONS
    assert "roles.manage" in ALL_PERMISSIONS
    for key in ALL_PERMISSIONS:
        assert "." in key

def test_owner_default_role_has_every_permission():
    assert set(DEFAULT_ROLES["Owner"]) == ALL_PERMISSIONS

def test_non_owner_defaults_are_subsets():
    for name in ("Partner", "Associate", "Staff"):
        assert set(DEFAULT_ROLES[name]) <= ALL_PERMISSIONS
    # Associate cannot delete invoices; Staff cannot manage roles
    assert "invoices.delete" not in DEFAULT_ROLES["Associate"]
    assert "roles.manage" not in DEFAULT_ROLES["Staff"]

def test_is_valid_permission():
    assert is_valid_permission("clients.read")
    assert not is_valid_permission("clients.teleport")
    assert not is_valid_permission("garbage")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_rbac_permissions.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.rbac'`

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/rbac/permissions.py
"""Code-defined permission catalog. Roles are firm-owned bundles of these keys.

A permission key is "<module>.<action>". CRUD modules expose create/read/update/
delete; a few modules add non-CRUD capabilities where CRUD doesn't fit. New CRM
modules (matters, calendar, documents...) are added here without schema change.
"""

CRUD = ["create", "read", "update", "delete"]

MODULES = [
    {"key": "clients", "label": "Clients", "actions": CRUD},
    {"key": "invoices", "label": "Invoices", "actions": CRUD + ["send"]},
    {"key": "items", "label": "Items", "actions": CRUD},
    {"key": "recurring", "label": "Recurring", "actions": CRUD},
    {"key": "bank_accounts", "label": "Bank Accounts", "actions": CRUD},
    {"key": "firm_settings", "label": "Firm Settings", "actions": ["read", "update"]},
    {"key": "members", "label": "Members", "actions": ["read", "invite", "remove", "manage_roles"]},
    {"key": "roles", "label": "Roles", "actions": ["read", "manage"]},
]

ALL_PERMISSIONS = {
    f"{m['key']}.{a}" for m in MODULES for a in m["actions"]
}


def is_valid_permission(key):
    return key in ALL_PERMISSIONS


def _perms(*specs):
    """Expand ("clients", CRUD) style specs into a flat permission list."""
    out = []
    for module, actions in specs:
        out.extend(f"{module}.{a}" for a in actions)
    return sorted(set(out) & ALL_PERMISSIONS)


DEFAULT_ROLES = {
    "Owner": sorted(ALL_PERMISSIONS),
    "Partner": _perms(
        ("clients", CRUD), ("invoices", CRUD + ["send"]), ("items", CRUD),
        ("recurring", CRUD), ("bank_accounts", CRUD),
        ("firm_settings", ["read", "update"]), ("members", ["read", "invite"]),
        ("roles", ["read"]),
    ),
    "Associate": _perms(
        ("clients", ["create", "read", "update"]),
        ("invoices", ["create", "read", "update", "send"]),
        ("items", ["create", "read", "update"]),
        ("recurring", ["read"]), ("bank_accounts", ["read"]),
        ("firm_settings", ["read"]), ("members", ["read"]),
    ),
    "Staff": _perms(
        ("clients", ["create", "read", "update"]),
        ("invoices", ["create", "read", "update"]),
        ("items", ["read"]), ("recurring", ["read"]),
        ("bank_accounts", ["read"]), ("members", ["read"]),
    ),
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_rbac_permissions.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Stop for review** (no commit — Parth handles git)

---

### Task 2: Firm, Role, FirmInvite models + user/billing column changes

**Files:**
- Modify: `backend/app/models/auth.py` (add Firm, Role, FirmInvite; add columns to User, FirmDetails, BankAccount)
- Modify: `backend/app/models/models.py` (rename `user_id`→`created_by_user_id`, add `firm_id` on Client, Item, Invoice, RecurringSchedule)
- Modify: `backend/app/main.py:58-64` (import new models so `create_all()` builds them)
- Test: `backend/tests/test_firm_models.py`

**Interfaces:**
- Produces:
  - `Firm(id, name, created_at)` with `to_dict()`.
  - `Role(id, firm_id, name, description, permissions: list, is_system, created_at, updated_at)` with `to_dict()`.
  - `FirmInvite(id, firm_id, email, role_id, token, status, invited_by, expires_at, created_at, accepted_at)` with `to_dict()` (omits raw token).
  - `User.firm_id`, `User.role_id`.
  - `Client/Item/Invoice/RecurringSchedule/BankAccount/FirmDetails`.`firm_id`; the four billing tables expose `created_by_user_id` (renamed from `user_id`).

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_firm_models.py
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
        assert "user_id" not in d  # old key gone

def test_invite_to_dict_hides_token(app):
    with app.app_context():
        firm = Firm(name="F"); db.session.add(firm); db.session.flush()
        inv = FirmInvite(firm_id=firm.id, email="x@y.com", role_id=1,
                         token="secret-token", status="pending", invited_by=1)
        db.session.add(inv); db.session.commit()
        assert "token" not in inv.to_dict()
        assert inv.to_dict()["email"] == "x@y.com"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_firm_models.py -v`
Expected: FAIL with `ImportError: cannot import name 'Firm'` (or `Client() got unexpected keyword 'firm_id'`)

- [ ] **Step 3: Write minimal implementation**

In `backend/app/models/auth.py`, add to the top of `User` (after `is_onboarded`):

```python
    firm_id = db.Column(db.Integer, db.ForeignKey('firms.id'), index=True)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))
```

Add new models in `auth.py`:

```python
class Firm(db.Model):
    """The tenant. Owns all billing data; has many members."""
    __tablename__ = 'firms'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {'id': self.id, 'name': self.name,
                'created_at': self.created_at.isoformat() if self.created_at else None}


class Role(db.Model):
    """Firm-owned, editable bundle of permission keys."""
    __tablename__ = 'roles'
    __table_args__ = (db.UniqueConstraint('firm_id', 'name', name='roles_firm_name_key'),)
    id = db.Column(db.Integer, primary_key=True)
    firm_id = db.Column(db.Integer, db.ForeignKey('firms.id'), nullable=False, index=True)
    name = db.Column(db.String(80), nullable=False)
    description = db.Column(db.Text)
    permissions = db.Column(db.JSON, default=list)
    is_system = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {'id': self.id, 'firm_id': self.firm_id, 'name': self.name,
                'description': self.description, 'permissions': self.permissions or [],
                'is_system': self.is_system}


class FirmInvite(db.Model):
    """Pending member invitation. Token is never serialized."""
    __tablename__ = 'firm_invites'
    id = db.Column(db.Integer, primary_key=True)
    firm_id = db.Column(db.Integer, db.ForeignKey('firms.id'), nullable=False, index=True)
    email = db.Column(db.String(200), nullable=False, index=True)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
    token = db.Column(db.String(64), nullable=False, unique=True, index=True)
    status = db.Column(db.String(20), nullable=False, default='pending')
    invited_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    expires_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    accepted_at = db.Column(db.DateTime)

    def to_dict(self):
        return {'id': self.id, 'firm_id': self.firm_id, 'email': self.email,
                'role_id': self.role_id, 'status': self.status,
                'invited_by': self.invited_by,
                'expires_at': self.expires_at.isoformat() if self.expires_at else None,
                'created_at': self.created_at.isoformat() if self.created_at else None}
```

In `auth.py`, add `firm_id` to `FirmDetails` and `BankAccount`:

```python
    # FirmDetails: one profile per firm (unique). user_id kept for transition.
    firm_id = db.Column(db.Integer, db.ForeignKey('firms.id'), unique=True, index=True)
```
```python
    # BankAccount:
    firm_id = db.Column(db.Integer, db.ForeignKey('firms.id'), index=True)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
```
Add `firm_id` and `created_by_user_id` to `BankAccount.to_dict()`.

In `backend/app/models/models.py`, for **Client, Item, Invoice, RecurringSchedule**: rename the column definition `user_id` → `created_by_user_id` (keep the FK to `users.id`), add `firm_id = db.Column(db.Integer, db.ForeignKey('firms.id'), nullable=False, index=True)`, update the `back_populates` relationships and every `to_dict()` to emit `firm_id` + `created_by_user_id` and drop the `user_id` key. Example for `Client`:

```python
    firm_id = db.Column(db.Integer, db.ForeignKey('firms.id'), nullable=False, index=True)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
```
and in `to_dict()` replace `'user_id': self.user_id,` with
```python
            'firm_id': self.firm_id,
            'created_by_user_id': self.created_by_user_id,
```

Update `User` relationships in `auth.py` to use the new attribute (SQLAlchemy `back_populates` still works; the relationship `primaryjoin` is inferred from the FK, so only rename references in code that read `.user_id`). Add the new model imports to `backend/app/main.py:58-64`:

```python
        from app.models.auth import User, Firm, Role, FirmInvite, FirmDetails, BankAccount
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_firm_models.py -v`
Expected: PASS (3 passed). NOTE: existing billing tests will now fail to import/construct — that is expected and fixed in Tasks 6–9.

- [ ] **Step 5: Stop for review**

---

### Task 3: Firm provisioning service (seed firm + default roles + owner)

**Files:**
- Create: `backend/app/services/firm_service.py`
- Test: `backend/tests/test_firm_service.py`

**Interfaces:**
- Consumes: `DEFAULT_ROLES` from `app.rbac.permissions`; models from Task 2.
- Produces:
  - `provision_firm(name: str) -> Firm` — creates firm + seeds the four default roles, commits, returns firm.
  - `owner_role(firm) -> Role` — the firm's `is_system` Owner role.
  - `assign_owner(user, firm) -> None` — sets `user.firm_id` and `user.role_id = owner_role(firm).id`.
  - `provision_firm_for_user(user, name) -> Firm` — provision + assign owner in one call.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_firm_service.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_firm_service.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.firm_service'`

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/services/firm_service.py
"""Provisioning helpers: create a firm with seeded roles and assign its owner."""
from app.models.models import db
from app.models.auth import Firm, Role
from app.rbac.permissions import DEFAULT_ROLES


def provision_firm(name):
    firm = Firm(name=name or "My Firm")
    db.session.add(firm)
    db.session.flush()
    for role_name, perms in DEFAULT_ROLES.items():
        db.session.add(Role(
            firm_id=firm.id, name=role_name, permissions=list(perms),
            is_system=(role_name == "Owner"),
            description=f"Default {role_name} role",
        ))
    db.session.commit()
    return firm


def owner_role(firm):
    return Role.query.filter_by(firm_id=firm.id, name="Owner", is_system=True).first()


def assign_owner(user, firm):
    user.firm_id = firm.id
    user.role_id = owner_role(firm).id
    db.session.commit()


def provision_firm_for_user(user, name):
    firm = provision_firm(name)
    assign_owner(user, firm)
    return firm
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_firm_service.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Stop for review**

---

### Task 4: Firm context middleware + `require_permission` decorator

**Files:**
- Create: `backend/app/middleware/firm_context.py`
- Test: `backend/tests/test_firm_context.py`

**Interfaces:**
- Consumes: `User` (resolve `g.user_id` supabase id → internal user), `Role`.
- Produces:
  - `load_firm_context() -> None` — sets `g.user` (internal User or None), `g.firm_id`, `g.permissions: set[str]`. Owner gets all perms.
  - `require_permission(perm: str)` — decorator; runs `load_firm_context()`, returns 403 if `perm` not in `g.permissions` (Owner role bypasses), 401 if no user/firm.
  - `has_permission(perm: str) -> bool` — reads `g.permissions`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_firm_context.py
import pytest
from flask import g, jsonify
from app.models.models import db
from app.models.auth import User, Role
from app.services.firm_service import provision_firm_for_user, provision_firm, owner_role
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_firm_context.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.middleware.firm_context'`

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/middleware/firm_context.py
"""Resolve the authenticated user into firm + permission context on `g`."""
from functools import wraps
from flask import g, jsonify
from app.models.auth import User, Role


def _resolve_supabase_id():
    """Indirection so tests can monkeypatch the JWT lookup."""
    return getattr(g, 'user_id', None)


def load_firm_context():
    g.user = None
    g.firm_id = None
    g.permissions = set()
    supabase_id = _resolve_supabase_id()
    if not supabase_id:
        return
    user = User.query.filter_by(supabase_id=supabase_id).first()
    if not user or not user.firm_id or not user.role_id:
        g.user = user
        return
    g.user = user
    g.firm_id = user.firm_id
    role = Role.query.get(user.role_id)
    if role and role.is_system and role.name == "Owner":
        from app.rbac.permissions import ALL_PERMISSIONS
        g.permissions = set(ALL_PERMISSIONS)
    elif role:
        g.permissions = set(role.permissions or [])


def has_permission(perm):
    return perm in getattr(g, 'permissions', set())


def require_permission(perm):
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            load_firm_context()
            if g.user is None or g.firm_id is None:
                return jsonify({'error': 'No firm context'}), 401
            if perm not in g.permissions:
                return jsonify({'error': 'Permission denied', 'required': perm}), 403
            return f(*args, **kwargs)
        return wrapped
    return decorator
```

Note: `require_permission` assumes `jwt_required` runs first (sets `g.user_id`). In the probe test we monkeypatch `_resolve_supabase_id` so no real JWT is needed. Real endpoints stack `@jwt_required` above `@require_permission`.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_firm_context.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Stop for review**

---

### Task 5: Provision a firm on registration/onboarding

**Files:**
- Modify: `backend/app/api/auth.py` (in the onboarding/firm-create path, provision a firm + owner for the user)
- Test: `backend/tests/test_firm_onboarding.py`

**Interfaces:**
- Consumes: `provision_firm_for_user` from Task 3.
- Produces: after onboarding, the user has `firm_id` + Owner `role_id`, and their `FirmDetails.firm_id` points at the firm.

**Detail:** Find where `FirmDetails` is currently created during onboarding (search `auth.py` for `FirmDetails(`). At that point, if `user.firm_id` is None, call `provision_firm_for_user(user, firm_name)` first, then set `firm_details.firm_id = user.firm_id`. Keep setting `firm_details.user_id` for the transition.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_firm_onboarding.py
from app.models.models import db
from app.models.auth import User, Firm, FirmDetails

def test_onboarding_provisions_firm_and_owner(app):
    """After provisioning, the user owns a firm and firm_details is linked."""
    from app.services.firm_service import provision_firm_for_user, owner_role
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
```

- [ ] **Step 2: Run test to verify it fails** (only if onboarding wiring is missing; this guards the service contract). Run: `cd backend && python -m pytest tests/test_firm_onboarding.py -v`

- [ ] **Step 3: Wire `provision_firm_for_user` into the `auth.py` onboarding path** as described above.

- [ ] **Step 4: Run test + full auth suite**

Run: `cd backend && python -m pytest tests/test_firm_onboarding.py tests/test_admin_auth.py -v`
Expected: PASS

- [ ] **Step 5: Stop for review**

---

### Tasks 6–9: Re-scope billing endpoints to `firm_id` + `require_permission`

Each task converts one API module from `user_id` scoping to `firm_id` scoping, swaps `@jwt_required`-only for `@jwt_required` + `@require_permission`, sets `created_by_user_id = g.user.id` on create, and updates that module's tests. **Pattern (apply identically per module):**

- Replace `get_current_user_id()` filtering with `g.firm_id` (set by `load_firm_context`, which `require_permission` calls). Add a small helper `current_firm_id()` returning `g.firm_id`.
- `Model.query.filter_by(user_id=user_id)` → `Model.query.filter_by(firm_id=g.firm_id)`.
- On create: `Model(firm_id=g.firm_id, created_by_user_id=g.user.id, ...)`.
- Decorate: GET→`require_permission("<module>.read")`, POST→`.create`, PUT/PATCH→`.update`, DELETE→`.delete`, send→`.send`.

- **Task 6:** `backend/app/api/clients.py` + `backend/tests/test_*clients*` (and `recent_clients_for_user(firm_id, ...)`).
- **Task 7:** `backend/app/api/items.py` + item tests.
- **Task 8:** `backend/app/api/invoices.py` + `backend/tests/test_send_service.py` (invoice send uses `invoices.send`).
- **Task 9:** `backend/app/api/recurring.py` + `backend/app/services/recurring_service.py` (recurring schedules now carry `firm_id` + `created_by_user_id`; the cron creates invoices with the schedule's `firm_id`) + `backend/app/api/analytics.py` (re-scope its aggregate queries to `firm_id`).

Each task: **Step 1** update the module's existing tests to seed a firm + owner and expect firm-scoped results; **Step 2** run them and watch them fail; **Step 3** apply the re-scope; **Step 4** run the module's tests green; **Step 5** stop for review. Add a reusable test fixture in `conftest.py`:

```python
# backend/tests/conftest.py — add
@pytest.fixture
def owner_user(app):
    """A committed User who owns a freshly provisioned firm. Returns (user_id, firm_id)."""
    from app.models.models import db as _d
    from app.models.auth import User
    from app.services.firm_service import provision_firm_for_user
    with app.app_context():
        u = User(email="owner@firm.com", supabase_id="sub-owner")
        _d.session.add(u); _d.session.commit()
        firm = provision_firm_for_user(u, "Test Firm")
        return u.id, firm.id

@pytest.fixture
def auth_as_owner(monkeypatch):
    """Make jwt + firm context resolve to the owner_user's supabase id."""
    monkeypatch.setattr("app.middleware.firm_context._resolve_supabase_id", lambda: "sub-owner")
    monkeypatch.setattr("app.api.clients.get_current_user_id", lambda: None, raising=False)
    return "sub-owner"
```

---

### Task 10: Firm profile + members API

**Files:**
- Create: `backend/app/api/firm.py`
- Modify: `backend/app/main.py` (register blueprint `app.register_blueprint(firm.bp, url_prefix='/api/v1/firm')`)
- Test: `backend/tests/test_firm_api_members.py`

**Endpoints (all `@jwt_required` + `@require_permission`):**
- `GET /` → firm + FirmDetails (`firm_settings.read`).
- `PATCH /` → update FirmDetails (`firm_settings.update`).
- `GET /members` → list users in firm with role names (`members.read`).
- `PATCH /members/<int:user_id>` → set `role_id` (`members.manage_roles`); reject demoting the last Owner with 409.
- `DELETE /members/<int:user_id>` → unset firm/role (`members.remove`); reject removing the last Owner with 409.
- `GET /permissions/catalog` → `{"modules": MODULES}` (`roles.read`).

Write tests covering: list members, change role, last-Owner protection (409), permission denial (403). TDD: failing test → implement → green. Provide a `_last_owner_guard(firm_id, target_user_id)` helper used by both PATCH and DELETE.

---

### Task 11: Roles CRUD API

**Files:**
- Create: `backend/app/api/roles.py`
- Modify: `backend/app/main.py` (register at `/api/v1/firm/roles`)
- Test: `backend/tests/test_firm_api_roles.py`

**Endpoints (`@jwt_required` + `@require_permission`):**
- `GET /` → firm's roles (`roles.read`).
- `POST /` → create role from `{name, description, permissions}` (`roles.manage`); validate every key via `is_valid_permission`, else 400.
- `PATCH /<int:role_id>` → edit name/description/permissions (`roles.manage`); reject editing the Owner system role (409).
- `DELETE /<int:role_id>` → delete (`roles.manage`); reject if `is_system` or if any user still holds it (409).

Tests: create custom role, reject invalid permission key (400), cannot edit/delete Owner (409), cannot delete role in use (409). TDD throughout.

---

### Task 12: Invite lifecycle (service + API + email)

**Files:**
- Create: `backend/app/services/invite_service.py`
- Create: `backend/app/api/invites.py`
- Modify: `backend/app/main.py` (register at `/api/v1/firm/invites`)
- Test: `backend/tests/test_firm_invites.py`

**Interfaces:**
- `create_invite(firm_id, email, role_id, invited_by) -> FirmInvite` — random `secrets.token_urlsafe(32)` token, `expires_at = now + 7d`, status `pending`; sends email via `ResendTransport` (link `{FRONTEND_URL}/accept-invite?token=...`).
- `accept_invite(token, user) -> Firm` — validates pending + not expired + `user.email == invite.email` (case-insensitive); sets `user.firm_id`/`role_id`, marks `accepted`, stamps `accepted_at`; raises `InviteError` on any failure.

**Endpoints:**
- `POST /` (`members.invite`) → create + email; returns invite dict (no token).
- `GET /` (`members.read`) → pending invites for firm.
- `DELETE /<int:invite_id>` (`members.invite`) → status → `revoked`.
- `POST /accept` (`@jwt_required` only, no permission) → body `{token}`; resolves current user; calls `accept_invite`.

Tests (TDD): create→email-sent (inject fake transport), accept as new user joins firm with role, expired token rejected (400), reused token rejected, email-mismatch rejected (403), revoke makes accept fail. Inject the email transport via a module-level `get_transport()` seam mirroring `send_service`.

---

### Task 13: Firm isolation regression test

**Files:**
- Test: `backend/tests/test_firm_isolation.py`

Seed two firms each with an owner and one client. Assert firm A's owner, hitting `GET /api/v1/clients`, sees only firm A's client, and `GET /api/v1/clients/<B's id>` returns 404. This is the cross-firm safety net. No implementation — pure regression guard. Run: `cd backend && python -m pytest tests/test_firm_isolation.py -v` → PASS.

---

### Task 14: Supabase SQL migration file (for Parth to apply manually)

**Files:**
- Create: `backend/migrations/008_firm_tenancy.sql`

Deliver the additive, non-destructive SQL below. **No code path runs this** — Parth applies it in the Supabase SQL editor. It must leave a running app working at every line.

```sql
-- 008_firm_tenancy.sql — Firm tenancy & RBAC. In-place, additive, non-destructive.
-- Apply in Supabase SQL editor. Safe to run once.
BEGIN;

-- 1. New tables
CREATE TABLE IF NOT EXISTS public.firms (
  id SERIAL PRIMARY KEY,
  name VARCHAR(200) NOT NULL,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.roles (
  id SERIAL PRIMARY KEY,
  firm_id INTEGER NOT NULL REFERENCES public.firms(id) ON DELETE CASCADE,
  name VARCHAR(80) NOT NULL,
  description TEXT,
  permissions JSONB DEFAULT '[]'::jsonb,
  is_system BOOLEAN NOT NULL DEFAULT false,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  UNIQUE (firm_id, name)
);

CREATE TABLE IF NOT EXISTS public.firm_invites (
  id SERIAL PRIMARY KEY,
  firm_id INTEGER NOT NULL REFERENCES public.firms(id) ON DELETE CASCADE,
  email VARCHAR(200) NOT NULL,
  role_id INTEGER NOT NULL REFERENCES public.roles(id),
  token VARCHAR(64) NOT NULL UNIQUE,
  status VARCHAR(20) NOT NULL DEFAULT 'pending',
  invited_by INTEGER REFERENCES public.users(id),
  expires_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW(),
  accepted_at TIMESTAMP
);

-- 2. New columns (nullable -> non-blocking)
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS firm_id INTEGER REFERENCES public.firms(id);
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS role_id INTEGER REFERENCES public.roles(id);
ALTER TABLE public.firm_details ADD COLUMN IF NOT EXISTS firm_id INTEGER REFERENCES public.firms(id);
ALTER TABLE public.bank_accounts ADD COLUMN IF NOT EXISTS firm_id INTEGER REFERENCES public.firms(id);
ALTER TABLE public.bank_accounts ADD COLUMN IF NOT EXISTS created_by_user_id INTEGER REFERENCES public.users(id);

-- 3. Rename user_id -> created_by_user_id on the four billing tables (data preserved)
ALTER TABLE public.clients RENAME COLUMN user_id TO created_by_user_id;
ALTER TABLE public.items RENAME COLUMN user_id TO created_by_user_id;
ALTER TABLE public.invoices RENAME COLUMN user_id TO created_by_user_id;
ALTER TABLE public.recurring_schedules RENAME COLUMN user_id TO created_by_user_id;
ALTER TABLE public.clients ADD COLUMN IF NOT EXISTS firm_id INTEGER REFERENCES public.firms(id);
ALTER TABLE public.items ADD COLUMN IF NOT EXISTS firm_id INTEGER REFERENCES public.firms(id);
ALTER TABLE public.invoices ADD COLUMN IF NOT EXISTS firm_id INTEGER REFERENCES public.firms(id);
ALTER TABLE public.recurring_schedules ADD COLUMN IF NOT EXISTS firm_id INTEGER REFERENCES public.firms(id);
-- bank_accounts.user_id stays (legacy); created_by_user_id backfilled below.

-- 4. One firm per existing user, made Owner. Roles seeded to match DEFAULT_ROLES.
--    Owner permissions list must equal the app's ALL_PERMISSIONS; regenerate if
--    the catalog changes. Generated here for the current catalog.
DO $$
DECLARE u RECORD; new_firm_id INTEGER; owner_role_id INTEGER;
BEGIN
  FOR u IN SELECT id, email FROM public.users WHERE firm_id IS NULL LOOP
    INSERT INTO public.firms(name)
      VALUES (COALESCE((SELECT firm_name FROM public.firm_details WHERE user_id = u.id LIMIT 1), u.email))
      RETURNING id INTO new_firm_id;

    INSERT INTO public.roles(firm_id, name, is_system, description, permissions)
      VALUES (new_firm_id, 'Owner', true, 'Default Owner role',
        '["bank_accounts.create","bank_accounts.delete","bank_accounts.read","bank_accounts.update","clients.create","clients.delete","clients.read","clients.update","firm_settings.read","firm_settings.update","invoices.create","invoices.delete","invoices.read","invoices.send","invoices.update","items.create","items.delete","items.read","items.update","members.invite","members.read","members.manage_roles","members.remove","recurring.create","recurring.delete","recurring.read","recurring.update","roles.manage","roles.read"]'::jsonb)
      RETURNING id INTO owner_role_id;
    INSERT INTO public.roles(firm_id, name, is_system, description, permissions) VALUES
      (new_firm_id, 'Partner',  false, 'Default Partner role',  '[]'::jsonb),
      (new_firm_id, 'Associate',false, 'Default Associate role','[]'::jsonb),
      (new_firm_id, 'Staff',    false, 'Default Staff role',    '[]'::jsonb);

    UPDATE public.users SET firm_id = new_firm_id, role_id = owner_role_id WHERE id = u.id;
    UPDATE public.firm_details SET firm_id = new_firm_id WHERE user_id = u.id;
    UPDATE public.clients   SET firm_id = new_firm_id WHERE created_by_user_id = u.id;
    UPDATE public.items     SET firm_id = new_firm_id WHERE created_by_user_id = u.id;
    UPDATE public.invoices  SET firm_id = new_firm_id WHERE created_by_user_id = u.id;
    UPDATE public.recurring_schedules SET firm_id = new_firm_id WHERE created_by_user_id = u.id;
    UPDATE public.bank_accounts SET firm_id = new_firm_id, created_by_user_id = u.id WHERE user_id = u.id;
  END LOOP;
END $$;

COMMIT;
```

After applying, Parth seeds non-Owner default role permissions either via the app's Roles editor or a follow-up `UPDATE`. (Plan note: the backend treats empty non-Owner roles as valid; permissions are editable in UI.)

---

### Task 15: Frontend — API client + permissions hook

**Files:**
- Modify: `frontend/src/api.ts` (add `firmApi`, `membersApi`, `rolesApi`, `invitesApi`, `getPermissionsCatalog`; extend `/me` parsing to expose `permissions`)
- Create: `frontend/src/hooks/usePermissions.ts`
- Test: manual (frontend has no unit harness in repo — verify via `npm run build` typecheck)

**Interfaces:**
- `usePermissions()` returns `{ has(perm: string): boolean, permissions: string[] }`, sourced from `/me`.
- API methods map 1:1 to Tasks 10–12 endpoints.

Provide concrete `api.ts` additions (fetch wrappers mirroring existing ones) and a `usePermissions` hook reading the permissions array the backend adds to `/me`. **Backend addition:** extend `GET /api/v1/auth/me` to include `permissions` (compute via `load_firm_context`) and `role` — add this to Task 4/5 scope and assert it in `test_firm_context.py`.

- [ ] Build check: `cd frontend && npm run build` → typechecks clean.

---

### Task 16: Frontend — Team page

**Files:**
- Create: `frontend/src/pages/Team.tsx`
- Modify: `frontend/src/App.tsx` (route `/team`), `frontend/src/components/Layout.tsx` (nav link, hidden unless `has("members.read")`)

Member list (name/email/role), invite form (email + role dropdown), pending invites with revoke, change-role dropdown, remove-member — each action gated by the matching permission via `usePermissions`. Use the existing design system / component patterns in `pages/`. Build check via `npm run build`.

---

### Task 17: Frontend — Roles editor

**Files:**
- Create: `frontend/src/pages/Roles.tsx`
- Modify: `frontend/src/App.tsx` (route `/roles`), `Layout.tsx` (nav link gated by `has("roles.read")`)

Render the module × action grid from `getPermissionsCatalog()`; each role is a column of checkboxes. Owner shown read-only/all-checked. Create/edit/delete custom roles (delete/edit hidden for `is_system`). Save posts the ticked keys. Build check via `npm run build`.

---

### Task 18: Frontend — Accept-invite page

**Files:**
- Create: `frontend/src/pages/AcceptInvite.tsx`
- Modify: `frontend/src/App.tsx` (public route `/accept-invite`)

Reads `?token=`, ensures the user is logged in (redirect to login carrying the token), then POSTs `/firm/invites/accept`. Shows success → redirect to dashboard, or a clear error for expired/used/mismatched invites. Build check via `npm run build`.

---

### Task 19: Full regression + manual smoke

- [ ] `cd backend && python -m pytest -q` → entire suite green.
- [ ] `cd frontend && npm run build` → clean.
- [ ] Manual: register a new user (provisions firm+Owner), create a client (firm-scoped), invite a second email, accept in a second browser, confirm the second user's permissions gate the UI, edit a custom role and watch a button appear/disappear.
- [ ] Hand the `008_firm_tenancy.sql` to Parth to apply on Supabase; confirm existing prod users become one-person firm Owners with their data intact.

---

## Self-Review notes

- **Spec coverage:** new entities (T2), permission matrix (T1), seeded roles (T1/T3), re-scope with rename (T2,T6–9,T14), enforcement (T4), invites (T12,T18), Team/Roles UI (T16,T17), isolation (T13), migration (T14), `/me` permissions (T15). All spec sections map to a task.
- **Transition:** `user_id` renamed not duplicated; `firm_details.user_id` and `bank_accounts.user_id` retained as harmless legacy during transition.
- **Type consistency:** `created_by_user_id`, `firm_id`, `g.firm_id`, `g.permissions`, `require_permission`, `provision_firm_for_user`, `accept_invite` used consistently across tasks.
