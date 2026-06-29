# Onboarding Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the front-loaded firm-setup wizard with a minimal onboarding gate plus a derived Home "Finish setting up" checklist, add a personal-profile layer, and converge the owner and invitee paths (including auto-routing a direct signup whose email matches a pending invite).

**Architecture:** Flask/SQLAlchemy backend (Cloud Run, Postgres/Supabase prod, in-memory SQLite for tests) + React/TS/Vite frontend (Vercel). New `users` columns + a relaxed `firm_details.firm_address`; slimmed `/auth/onboard`; new `PATCH /auth/profile`, `POST /invites/accept-pending`, `POST /auth/dismiss-checklist`; `/auth/me` gains a `pending_invite` block and a derived `setup` block. Frontend rewrites onboarding to a single gate, adds a shared invitee-profile step, and a Home checklist card.

**Tech Stack:** Flask, SQLAlchemy, pytest, PyJWT (HS256 test tokens), React, TanStack Query, TipTap-unrelated, Tailwind, lucide-react.

## Global Constraints

- Migrations are **numbered SQL files** in `backend/migrations/`, applied **manually by Parth on Supabase** — never run by code. This plan's migration is `023_onboarding_profile.sql`.
- **Never run git commits/pushes** — Parth does git himself. The "Commit" step in each task is for Parth; agentic workers should stop at green tests and leave the commit to him (or stage only if explicitly asked).
- Backend test suite is currently **312 passing**; every backend task must keep it green (`pytest -q`).
- Frontend has no JS unit-test infra; the gate for frontend tasks is `npm run build` clean plus the explicit behavioral checks listed.
- `users.supabase_id` is a string-variant UUID; test tokens are signed HS256 with secret `'test-secret'` (the `make_owner` fixture monkeypatches `app.middleware.jwt_auth.get_jwt_secret`).
- Solo vs Firm is a **first-run nudge only** — no permission/RBAC difference.
- Out of scope: the `firm_details → firms` (R3) merge; email-template redesign.

---

### Task 1: Migration 023 + model columns (personal-profile layer)

**Files:**
- Create: `backend/migrations/023_onboarding_profile.sql`
- Modify: `backend/app/models/auth.py` (User class ~lines 9-63; FirmDetails `firm_address` ~line 77; User.to_dict ~lines 51-63)
- Test: `backend/tests/test_onboarding_profile_model.py`

**Interfaces:**
- Produces: `User.full_name`, `User.designation`, `User.bar_council_number`, `User.personal_phone` (all `str|None`), `User.is_solo` (`bool|None`), `User.checklist_dismissed` (`bool`, default `False`). `FirmDetails.firm_address` becomes nullable. `User.to_dict()` includes the four personal fields + `is_solo` + `checklist_dismissed`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_onboarding_profile_model.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_onboarding_profile_model.py -v`
Expected: FAIL — `TypeError: 'full_name' is an invalid keyword argument for User` (and the null-address insert would fail the NOT NULL constraint).

- [ ] **Step 3: Add the model columns**

In `backend/app/models/auth.py`, inside `class User`, after the `is_onboarded` column (line ~22) add:

```python
    # Personal/professional profile (migration 023). Captured at onboarding for
    # owners and invitees; used by the Home greeting, team roster, and document
    # merge-fields.
    full_name = db.Column(db.String(200))
    designation = db.Column(db.String(120))
    bar_council_number = db.Column(db.String(120))
    personal_phone = db.Column(db.String(50))
    # Solo vs firm is a first-run nudge only (drives checklist emphasis).
    is_solo = db.Column(db.Boolean)
    # Single dismiss flag for the Home "Finish setting up" checklist.
    checklist_dismissed = db.Column(db.Boolean, default=False)
```

In the same file, change the `FirmDetails.firm_address` column (line ~77) from:

```python
    firm_address = db.Column(db.Text, nullable=False)
```

to:

```python
    # Nullable: the minimal onboarding gate creates the firm profile with just a
    # name; the address is filled later via the Home setup checklist / Settings.
    firm_address = db.Column(db.Text)
```

Then extend `User.to_dict()` (the returned dict, ~lines 52-62) by inserting these keys before `'created_at'`:

```python
            'full_name': self.full_name,
            'designation': self.designation,
            'bar_council_number': self.bar_council_number,
            'personal_phone': self.personal_phone,
            'is_solo': self.is_solo,
            'checklist_dismissed': bool(self.checklist_dismissed),
```

- [ ] **Step 4: Write the migration SQL**

```sql
-- backend/migrations/023_onboarding_profile.sql
-- Onboarding redesign: personal-profile layer on users + relax firm_address.
-- Idempotent (safe to re-run). Apply manually on Supabase.

ALTER TABLE users ADD COLUMN IF NOT EXISTS full_name           VARCHAR(200);
ALTER TABLE users ADD COLUMN IF NOT EXISTS designation         VARCHAR(120);
ALTER TABLE users ADD COLUMN IF NOT EXISTS bar_council_number  VARCHAR(120);
ALTER TABLE users ADD COLUMN IF NOT EXISTS personal_phone      VARCHAR(50);
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_solo             BOOLEAN;
ALTER TABLE users ADD COLUMN IF NOT EXISTS checklist_dismissed BOOLEAN DEFAULT FALSE;

-- The minimal gate creates a firm profile with no address yet.
ALTER TABLE firm_details ALTER COLUMN firm_address DROP NOT NULL;
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_onboarding_profile_model.py -v`
Expected: PASS (2 passed).

- [ ] **Step 6: Run the full suite**

Run: `cd backend && python -m pytest -q`
Expected: all green (314 passed — 312 prior + 2 new). If `test_firm_onboarding.py` still passes, the nullable change didn't break the existing required-address insert (it passes an address, so it's unaffected).

- [ ] **Step 7: Commit (Parth)**

```bash
git add backend/migrations/023_onboarding_profile.sql backend/app/models/auth.py backend/tests/test_onboarding_profile_model.py
git commit -m "feat(onboarding): add personal-profile columns + nullable firm_address (migration 023)"
```

---

### Task 2: invite_service — shared attach helper + accept-pending + lookup

**Files:**
- Modify: `backend/app/services/invite_service.py` (`accept_invite` ~lines 103-125)
- Test: `backend/tests/test_invite_service.py` (append)

**Interfaces:**
- Produces:
  - `accept_invite(token, user) -> FirmInvite` (unchanged signature; now delegates to `_attach`).
  - `accept_pending_invite(user) -> FirmInvite` — finds the newest **pending, unexpired** invite matching `user.email` and attaches; raises `InviteError` if none.
  - `pending_invite_for(email) -> FirmInvite | None` — newest pending, unexpired invite for an email (used by `/auth/me`).

- [ ] **Step 1: Write the failing tests**

```python
# append to backend/tests/test_invite_service.py
from datetime import datetime, timedelta
from app.models.models import db
from app.models.auth import User, Firm, Role, FirmInvite
from app.services import invite_service


def _firm_with_role(name='Firm A', role='Staff'):
    firm = Firm(name=name)
    db.session.add(firm)
    db.session.flush()
    r = Role(firm_id=firm.id, name=role, permissions=[], is_system=False)
    db.session.add(r)
    db.session.flush()
    return firm, r


def test_accept_pending_invite_attaches_newest(app):
    with app.app_context():
        firm, role = _firm_with_role()
        db.session.add(FirmInvite(firm_id=firm.id, email='joiner@x.com', role_id=role.id,
                                  token='t1', status='pending',
                                  expires_at=datetime.utcnow() + timedelta(days=3)))
        user = User(email='joiner@x.com', supabase_id='sb-j')
        db.session.add(user)
        db.session.commit()
        invite = invite_service.accept_pending_invite(user)
        db.session.commit()
        assert user.firm_id == firm.id
        assert user.role_id == role.id
        assert user.is_onboarded is True
        assert invite.status == 'accepted'


def test_accept_pending_invite_raises_when_none(app):
    with app.app_context():
        user = User(email='lonely@x.com', supabase_id='sb-l')
        db.session.add(user)
        db.session.commit()
        try:
            invite_service.accept_pending_invite(user)
            assert False, 'expected InviteError'
        except invite_service.InviteError:
            pass


def test_pending_invite_for_skips_expired(app):
    with app.app_context():
        firm, role = _firm_with_role(name='Firm B')
        db.session.add(FirmInvite(firm_id=firm.id, email='exp@x.com', role_id=role.id,
                                  token='t2', status='pending',
                                  expires_at=datetime.utcnow() - timedelta(days=1)))
        db.session.commit()
        assert invite_service.pending_invite_for('exp@x.com') is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_invite_service.py -k "accept_pending or pending_invite_for" -v`
Expected: FAIL — `AttributeError: module 'app.services.invite_service' has no attribute 'accept_pending_invite'`.

- [ ] **Step 3: Refactor the service**

In `backend/app/services/invite_service.py`, replace the `accept_invite` function (lines ~103-125) with this trio:

```python
def _attach(user, invite):
    """Attach `user` to `invite`'s firm + role after validating the invite."""
    if invite.status != 'pending':
        raise InviteError(f'Invitation is {invite.status}')
    if invite.expires_at and invite.expires_at < datetime.utcnow():
        invite.status = 'expired'
        raise InviteError('Invitation has expired')
    # The invite is bound to a specific address; a different signed-in account
    # must not consume it (e.g. a forwarded link).
    if user.email and invite.email and user.email.strip().lower() != invite.email:
        raise InviteError('This invitation was sent to a different email address')
    user.firm_id = invite.firm_id
    user.role_id = invite.role_id
    # Joining a firm completes onboarding — the invitee must not run the
    # firm-provisioning onboarding flow (that would create a second firm).
    user.is_onboarded = True
    invite.status = 'accepted'
    invite.accepted_at = datetime.utcnow()
    return invite


def accept_invite(token, user):
    """Attach `user` to the token's firm + role. Caller commits. Returns invite."""
    invite = FirmInvite.query.filter_by(token=token).first()
    if not invite:
        raise InviteError('Invalid invitation')
    return _attach(user, invite)


def pending_invite_for(email):
    """Newest pending, unexpired invite for `email`, or None."""
    email = (email or '').strip().lower()
    if not email:
        return None
    invite = (FirmInvite.query.filter_by(email=email, status='pending')
              .order_by(FirmInvite.created_at.desc()).first())
    if invite and invite.expires_at and invite.expires_at < datetime.utcnow():
        return None
    return invite


def accept_pending_invite(user):
    """Attach `user` to their newest pending invite (matched by email). Caller commits."""
    invite = pending_invite_for(user.email)
    if not invite:
        raise InviteError('No pending invitation for this account')
    return _attach(user, invite)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_invite_service.py -v`
Expected: PASS (existing service tests + 3 new ones).

- [ ] **Step 5: Run the full suite**

Run: `cd backend && python -m pytest -q`
Expected: green (the token-accept path in `test_invites_api.py` still passes since `accept_invite` behavior is unchanged).

- [ ] **Step 6: Commit (Parth)**

```bash
git add backend/app/services/invite_service.py backend/tests/test_invite_service.py
git commit -m "feat(invites): extract attach helper + add accept_pending_invite/pending_invite_for"
```

---

### Task 3: Slim `/auth/onboard` to the minimal gate

**Files:**
- Modify: `backend/app/api/auth.py` (`onboard` ~lines 120-196)
- Test: `backend/tests/test_onboard_gate.py`

**Interfaces:**
- Consumes: `User` profile columns (Task 1); `provision_firm_for_user` (existing).
- Produces: `POST /auth/onboard` accepts `{full_name, designation?, bar_council_number?, personal_phone?, firm_name, is_solo?}`. Required: `full_name`, `firm_name`. Writes profile fields to `users`, provisions the firm (Owner), creates a minimal `FirmDetails(firm_name, firm_address=None)`, sets `is_onboarded=True`. No banking/branding/billing fields required. Returns `201 {message, firm}`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_onboard_gate.py
"""The slimmed onboarding gate: profile + firm name only; firm provisioned."""
import jwt as _pyjwt
from app.models.models import db
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_onboard_gate.py -v`
Expected: FAIL — current `onboard` requires `firm_address` (returns 400 on the happy-path test) and doesn't persist `full_name`/`is_solo`.

- [ ] **Step 3: Rewrite the onboard endpoint**

In `backend/app/api/auth.py`, replace the body of `onboard()` (everything after the `if user.is_onboarded:` guard, lines ~139-196) with:

```python
    if user.is_onboarded:
        return jsonify({'error': 'User already onboarded'}), 400

    data = request.get_json() or {}

    # Minimal gate: identify the person and name the firm. Everything else
    # (banking, branding, billing, address) is deferred to the Home checklist.
    if not data.get('full_name'):
        return jsonify({'error': 'full_name is required'}), 400
    if not data.get('firm_name'):
        return jsonify({'error': 'firm_name is required'}), 400

    # Personal/professional profile.
    user.full_name = data['full_name']
    user.designation = data.get('designation')
    user.bar_council_number = data.get('bar_council_number')
    user.personal_phone = data.get('personal_phone')
    user.is_solo = bool(data.get('is_solo', False))

    # Provision the firm tenant + seeded roles, making this user its Owner.
    # Idempotent guard: only provision if the user isn't already in a firm.
    if not user.firm_id:
        provision_firm_for_user(user, data['firm_name'])

    # Minimal firm profile — address/branding/billing land later via the checklist.
    firm = FirmDetails(
        user_id=user.id,
        firm_id=user.firm_id,
        firm_name=data['firm_name'],
        firm_address=data.get('firm_address'),
    )
    db.session.add(firm)

    user.is_onboarded = True
    db.session.commit()

    return jsonify({
        'message': 'Onboarding completed successfully',
        'firm': firm.to_dict()
    }), 201
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_onboard_gate.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Reconcile the existing onboarding test**

Run: `cd backend && python -m pytest tests/test_firm_onboarding.py -q`
Expected: PASS — it constructs `FirmDetails` directly (not via the endpoint), so it's unaffected. If any other test posts to `/auth/onboard` with the old required `firm_address`, it still works because the gate now treats address as optional.

- [ ] **Step 6: Run the full suite**

Run: `cd backend && python -m pytest -q`
Expected: green.

- [ ] **Step 7: Commit (Parth)**

```bash
git add backend/app/api/auth.py backend/tests/test_onboard_gate.py
git commit -m "feat(onboarding): slim /auth/onboard to minimal profile+firm gate"
```

---

### Task 4: `PATCH /auth/profile`

**Files:**
- Modify: `backend/app/api/auth.py` (add route near `onboard`)
- Test: `backend/tests/test_profile_endpoint.py`

**Interfaces:**
- Produces: `PATCH /auth/profile` — authenticated; updates any of `full_name`, `designation`, `bar_council_number`, `personal_phone` on the caller's `users` row (auto-creating the row if absent, mirroring `update_device_info`). Returns `200 {profile: <user fields>}`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_profile_endpoint.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_profile_endpoint.py -v`
Expected: FAIL — 404/405 (route doesn't exist).

- [ ] **Step 3: Add the endpoint**

In `backend/app/api/auth.py`, after the `onboard()` function, add:

```python
@bp.route('/profile', methods=['PATCH'])
@jwt_required
def update_profile():
    """Update the caller's personal/professional profile fields."""
    user = User.query.filter_by(supabase_id=g.user_id).first()
    if not user:
        user = User(supabase_id=g.user_id, email=g.user_email,
                    is_active=True, is_onboarded=False)
        db.session.add(user)
        db.session.flush()

    data = request.get_json() or {}
    for field in ('full_name', 'designation', 'bar_council_number', 'personal_phone'):
        if field in data:
            setattr(user, field, data[field])

    db.session.commit()
    return jsonify({'profile': {
        'full_name': user.full_name,
        'designation': user.designation,
        'bar_council_number': user.bar_council_number,
        'personal_phone': user.personal_phone,
    }})
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_profile_endpoint.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Run the full suite**

Run: `cd backend && python -m pytest -q`
Expected: green.

- [ ] **Step 6: Commit (Parth)**

```bash
git add backend/app/api/auth.py backend/tests/test_profile_endpoint.py
git commit -m "feat(auth): add PATCH /auth/profile for personal-profile edits"
```

---

### Task 5: `POST /invites/accept-pending`

**Files:**
- Modify: `backend/app/api/invites.py` (add route after `accept_invite`)
- Test: `backend/tests/test_accept_pending_api.py`

**Interfaces:**
- Consumes: `invite_service.accept_pending_invite(user)` (Task 2).
- Produces: `POST /invites/accept-pending` — authenticated, firm-agnostic; auto-creates the local `users` row if missing, then attaches the user to their newest pending invite by email. Returns `200 {firm_id, role_id, invite}` or `400` if no pending invite.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_accept_pending_api.py
"""Direct-signup reconciliation: POST /invites/accept-pending (no token)."""
import jwt as _pyjwt
from app.models.models import db
from app.models.auth import User, Role, Firm
from app.services import invite_service


def _token(sub, email):
    return {'Authorization': 'Bearer ' + _pyjwt.encode(
        {'sub': sub, 'email': email, 'aud': 'authenticated'},
        'test-secret', algorithm='HS256')}


def test_accept_pending_routes_into_firm(client, make_owner):
    headers, firm_id = make_owner()
    with client.application.app_context():
        staff_id = Role.query.filter_by(firm_id=firm_id, name='Staff').first().id
        owner_id = User.query.filter_by(email='owner@firm.com').first().id
        invite_service.create_invite(firm_id=firm_id, email='direct@firm.com',
                                     role_id=staff_id, invited_by=owner_id)
        db.session.commit()
        firm_count_before = Firm.query.count()
    resp = client.post('/api/v1/invites/accept-pending',
                       headers=_token('sb-direct', 'direct@firm.com'))
    assert resp.status_code == 200
    body = resp.get_json()
    assert body['firm_id'] == firm_id
    with client.application.app_context():
        u = User.query.filter_by(email='direct@firm.com').first()
        assert u.firm_id == firm_id
        assert u.role_id == staff_id
        assert u.is_onboarded is True
        # No second firm was provisioned.
        assert Firm.query.count() == firm_count_before


def test_accept_pending_without_invite_returns_400(client, make_owner):
    make_owner()
    resp = client.post('/api/v1/invites/accept-pending',
                       headers=_token('sb-none', 'noinvite@firm.com'))
    assert resp.status_code == 400
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_accept_pending_api.py -v`
Expected: FAIL — 404/405 (route doesn't exist).

- [ ] **Step 3: Add the endpoint**

In `backend/app/api/invites.py`, after the `accept_invite()` function, add:

```python
@bp.route('/invites/accept-pending', methods=['POST'])
@jwt_required
def accept_pending():
    """Attach the authenticated firm-less user to their newest pending invite.

    Used when a person whose email was invited signs up directly instead of
    clicking the email link — we auto-route them into the firm rather than let
    them provision a duplicate.
    """
    user = User.query.filter_by(supabase_id=g.user_id).first()
    if not user:
        user = User(supabase_id=g.user_id, email=g.user_email,
                    is_active=True, is_onboarded=False)
        db.session.add(user)
        db.session.flush()

    try:
        invite = invite_service.accept_pending_invite(user)
        db.session.commit()
    except invite_service.InviteError as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

    return jsonify({'firm_id': user.firm_id, 'role_id': user.role_id,
                    'invite': invite.to_dict()})
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_accept_pending_api.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Run the full suite**

Run: `cd backend && python -m pytest -q`
Expected: green.

- [ ] **Step 6: Commit (Parth)**

```bash
git add backend/app/api/invites.py backend/tests/test_accept_pending_api.py
git commit -m "feat(invites): add POST /invites/accept-pending for direct-signup reconciliation"
```

---

### Task 6: `/auth/me` — pending_invite + derived setup block + profile fields

**Files:**
- Modify: `backend/app/api/auth.py` (`get_current_user` ~lines 44-84)
- Test: `backend/tests/test_me_setup_block.py`

**Interfaces:**
- Consumes: `invite_service.pending_invite_for(email)` (Task 2); `Role`, `BankAccount`, `FirmInvite`.
- Produces: `GET /auth/me` response gains:
  - `profile` includes `full_name`, `designation`, `bar_council_number`, `personal_phone`, `is_solo`, `checklist_dismissed`.
  - `pending_invite`: `{firm_name, role_name}` when the caller is firm-less and has a pending invite, else `null`.
  - `setup`: `{bank: bool, branding: bool, billing: bool, team: bool, dismissed: bool, complete: bool}` derived live (only meaningful when the user has a firm; `complete` = all four true).

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_me_setup_block.py
"""GET /auth/me surfaces profile fields, derived setup state, and pending invites."""
import jwt as _pyjwt
from app.models.models import db
from app.models.auth import User, Role, BankAccount, FirmInvite
from app.services import invite_service


def _token(sub, email):
    return {'Authorization': 'Bearer ' + _pyjwt.encode(
        {'sub': sub, 'email': email, 'aud': 'authenticated'},
        'test-secret', algorithm='HS256')}


def _onboard(client, headers, full_name='Owner O', firm_name='Owner Firm'):
    return client.post('/api/v1/auth/onboard', headers=headers,
                       json={'full_name': full_name, 'firm_name': firm_name})


def test_me_setup_all_false_after_minimal_onboard(client, make_owner):
    make_owner()
    h = _token('sb-me', 'me@firm.com')
    _onboard(client, h)
    body = client.get('/api/v1/auth/me', headers=h).get_json()
    assert body['profile']['full_name'] == 'Owner O'
    assert body['profile']['checklist_dismissed'] is False
    s = body['setup']
    assert s == {'bank': False, 'branding': False, 'billing': False,
                 'team': False, 'dismissed': False, 'complete': False}


def test_me_setup_flips_true_as_data_appears(client, make_owner):
    make_owner()
    h = _token('sb-me2', 'me2@firm.com')
    _onboard(client, h, firm_name='Filled Firm')
    with client.application.app_context():
        u = User.query.filter_by(email='me2@firm.com').first()
        firm_id = u.firm_id
        fd = u.firm_details
        fd.logo_path = 'logos/x.png'
        fd.billing_terms = 'Net 30'
        db.session.add(BankAccount(user_id=u.id, firm_id=firm_id,
                                   created_by_user_id=u.id, bank_name='SBI'))
        staff = Role.query.filter_by(firm_id=firm_id, name='Staff').first()
        invite_service.create_invite(firm_id=firm_id, email='t@firm.com',
                                     role_id=staff.id, invited_by=u.id)
        db.session.commit()
    s = client.get('/api/v1/auth/me', headers=h).get_json()['setup']
    assert s == {'bank': True, 'branding': True, 'billing': True,
                 'team': True, 'dismissed': False, 'complete': True}


def test_me_surfaces_pending_invite_for_firmless_user(client, make_owner):
    headers, firm_id = make_owner()
    with client.application.app_context():
        staff = Role.query.filter_by(firm_id=firm_id, name='Staff').first()
        owner_id = User.query.filter_by(email='owner@firm.com').first().id
        invite_service.create_invite(firm_id=firm_id, email='invitee@firm.com',
                                     role_id=staff.id, invited_by=owner_id)
        db.session.commit()
        db.session.add(User(supabase_id='sb-inv', email='invitee@firm.com'))
        db.session.commit()
    body = client.get('/api/v1/auth/me', headers=_token('sb-inv', 'invitee@firm.com')).get_json()
    assert body['pending_invite'] is not None
    assert body['pending_invite']['role_name'] == 'Staff'
    assert body['pending_invite']['firm_name']  # firm display name present
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_me_setup_block.py -v`
Expected: FAIL — `body['setup']` KeyError / `pending_invite` missing.

- [ ] **Step 3: Extend get_current_user**

In `backend/app/api/auth.py`, update the imports at the top to include the models/services used:

```python
from app.models.auth import User, FirmDetails, BankAccount, Role, Firm, FirmInvite
from app.services import invite_service
```

(The existing import line imports `User, FirmDetails, BankAccount, Role`; add `Firm, FirmInvite`. Keep `from app.services.firm_service import provision_firm_for_user` as-is and add the `invite_service` import.)

Then, inside `get_current_user`, replace the response-building block. After the existing `if user:` section that sets `profile`/`membership`/`firm`/`bank`, add the new blocks. Concretely, change the `response['profile']` dict (lines ~65-72) to also carry the new fields:

```python
        response['profile'] = {
            'id': user.id,
            'device_id': getattr(user, 'device_id', None),
            'device_info': getattr(user, 'device_info', None),
            'is_onboarded': user.is_onboarded,
            'full_name': user.full_name,
            'designation': user.designation,
            'bar_council_number': user.bar_council_number,
            'personal_phone': user.personal_phone,
            'is_solo': user.is_solo,
            'checklist_dismissed': bool(user.checklist_dismissed),
            'created_at': user.created_at.isoformat() if user.created_at else None,
            'updated_at': user.updated_at.isoformat() if user.updated_at else None,
        }
```

Then, immediately before `return jsonify(response)`, insert:

```python
    # Pending-invite surfacing: a firm-less user whose email was invited.
    if user and not user.firm_id:
        pend = invite_service.pending_invite_for(g.user_email)
        if pend:
            firm = Firm.query.get(pend.firm_id)
            role = Role.query.get(pend.role_id)
            response['pending_invite'] = {
                'firm_name': firm.name if firm else None,
                'role_name': role.name if role else None,
            }

    # Derived setup checklist state (only meaningful once in a firm).
    if user and user.firm_id:
        fd = user.firm_details
        has_bank = BankAccount.query.filter_by(firm_id=user.firm_id).count() > 0
        has_branding = bool(fd and (fd.logo_path or fd.signature_path))
        has_billing = bool(fd and fd.billing_terms)
        has_team = FirmInvite.query.filter_by(firm_id=user.firm_id).count() > 0
        response['setup'] = {
            'bank': has_bank,
            'branding': has_branding,
            'billing': has_billing,
            'team': has_team,
            'dismissed': bool(user.checklist_dismissed),
            'complete': all([has_bank, has_branding, has_billing, has_team]),
        }
```

Also add the two new keys to the initial `response` dict (lines ~53-62) so they're always present:

```python
    response = {
        'user': {
            'id': user_id,
            'email': g.user_email,
        },
        'profile': None,
        'firm': None,
        'bank': None,
        'membership': None,
        'pending_invite': None,
        'setup': None,
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_me_setup_block.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Run the full suite**

Run: `cd backend && python -m pytest -q`
Expected: green.

- [ ] **Step 6: Commit (Parth)**

```bash
git add backend/app/api/auth.py backend/tests/test_me_setup_block.py
git commit -m "feat(auth): /auth/me surfaces profile fields, derived setup, pending_invite"
```

---

### Task 7: `POST /auth/dismiss-checklist`

**Files:**
- Modify: `backend/app/api/auth.py` (add route)
- Test: `backend/tests/test_dismiss_checklist.py`

**Interfaces:**
- Produces: `POST /auth/dismiss-checklist` — authenticated; sets `users.checklist_dismissed=True`. Returns `200 {checklist_dismissed: true}`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_dismiss_checklist.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_dismiss_checklist.py -v`
Expected: FAIL — route missing.

- [ ] **Step 3: Add the endpoint**

In `backend/app/api/auth.py`, after `update_profile()`, add:

```python
@bp.route('/dismiss-checklist', methods=['POST'])
@jwt_required
def dismiss_checklist():
    """Hide the Home 'Finish setting up' checklist for this user."""
    user = User.query.filter_by(supabase_id=g.user_id).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    user.checklist_dismissed = True
    db.session.commit()
    return jsonify({'checklist_dismissed': True})
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_dismiss_checklist.py -v`
Expected: PASS.

- [ ] **Step 5: Run the full suite**

Run: `cd backend && python -m pytest -q`
Expected: green (≈322 passed).

- [ ] **Step 6: Commit (Parth)**

```bash
git add backend/app/api/auth.py backend/tests/test_dismiss_checklist.py
git commit -m "feat(auth): add POST /auth/dismiss-checklist"
```

---

### Task 8: Frontend API client + AuthContext wiring

**Files:**
- Modify: `frontend/src/api.ts` (add methods near `onboard`/`acceptInvite`)
- Modify: `frontend/src/contexts/AuthContext.tsx` (UserProfile type, new context fields, fetchProfile)

**Interfaces:**
- Produces (api):
  - `api.updateProfile(data: { full_name?: string; designation?: string; bar_council_number?: string; personal_phone?: string }) => Promise<any>`
  - `api.acceptPendingInvite() => Promise<{ firm_id: number; role_id: number }>`
  - `api.dismissChecklist() => Promise<{ checklist_dismissed: boolean }>`
- Produces (AuthContext): `useAuth()` exposes `setup: SetupState | null` and `pendingInvite: { firm_name: string; role_name: string } | null`, and `profile` carries the new personal fields. `SetupState = { bank: boolean; branding: boolean; billing: boolean; team: boolean; dismissed: boolean; complete: boolean }`.

- [ ] **Step 1: Add the api client methods**

In `frontend/src/api.ts`, after the `onboard` method (line ~772) add:

```typescript
  updateProfile: (data: {
    full_name?: string; designation?: string;
    bar_council_number?: string; personal_phone?: string;
  }) =>
    fetchAPI<any>(`${API_BASE_URL}/auth/profile`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  dismissChecklist: () =>
    fetchAPI<{ checklist_dismissed: boolean }>(`${API_BASE_URL}/auth/dismiss-checklist`, {
      method: 'POST',
    }),
```

And after the `acceptInvite` method (line ~876) add:

```typescript
  acceptPendingInvite: () =>
    fetchAPI<{ firm_id: number; role_id: number }>(
      `${API_BASE_URL}/invites/accept-pending`,
      { method: 'POST' },
    ),
```

- [ ] **Step 2: Extend AuthContext types + state**

In `frontend/src/contexts/AuthContext.tsx`:

(a) Extend `UserProfile` (lines ~6-13):

```typescript
interface UserProfile {
  id: string;
  device_id: string | null;
  device_info: Record<string, unknown> | null;
  is_onboarded: boolean;
  full_name: string | null;
  designation: string | null;
  bar_council_number: string | null;
  personal_phone: string | null;
  is_solo: boolean | null;
  checklist_dismissed: boolean;
  created_at: string;
  updated_at: string;
}

export interface SetupState {
  bank: boolean;
  branding: boolean;
  billing: boolean;
  team: boolean;
  dismissed: boolean;
  complete: boolean;
}

export interface PendingInvite {
  firm_name: string;
  role_name: string;
}
```

(b) Add to `AuthContextType` (after `membership` ~line 58):

```typescript
  setup: SetupState | null;
  pendingInvite: PendingInvite | null;
```

(c) Add state (after `membership` useState ~line 80):

```typescript
  const [setup, setSetup] = useState<SetupState | null>(null);
  const [pendingInvite, setPendingInvite] = useState<PendingInvite | null>(null);
```

(d) In `fetchProfile`, where it currently sets `setProfile`/`setMembership` on `response.ok` (lines ~101-103), also set the two new pieces:

```typescript
        const data = await response.json();
        setProfile(data.profile || null);
        setMembership(data.membership || null);
        setSetup(data.setup || null);
        setPendingInvite(data.pending_invite || null);
```

(e) In the 404 branch and the signed-out branch of `onAuthStateChange`, clear them alongside the existing resets. In the 404 branch (lines ~123-125) add `setSetup(null); setPendingInvite(null);`. In the signed-out block (lines ~194-199) add `setSetup(null); setPendingInvite(null);`.

(f) Add `setup` and `pendingInvite` to the context provider `value` object (lines ~288-304).

- [ ] **Step 3: Build**

Run: `cd frontend && npm run build`
Expected: clean build, no type errors.

- [ ] **Step 4: Commit (Parth)**

```bash
git add frontend/src/api.ts frontend/src/contexts/AuthContext.tsx
git commit -m "feat(onboarding): api client + AuthContext for profile/setup/pending-invite"
```

---

### Task 9: Rewrite `Onboarding.tsx` as the minimal owner gate

**Files:**
- Modify: `frontend/src/pages/Onboarding.tsx` (full rewrite)

**Interfaces:**
- Consumes: `api.onboard`, `api.acceptPendingInvite`, `api.updateProfile`, `useAuth().refreshProfile`, `useAuth().pendingInvite`, `useAuth().isOnboarded`.
- Behavior: This page is the post-login gate. If `pendingInvite` is present → render the **invitee profile** form ("Join {firm_name} as {role_name}") that calls `acceptPendingInvite()` then `updateProfile(profile)`. Otherwise render the **owner gate** (profile fields + firm name + Solo/Firm) that calls `onboard(...)`. On success → `refreshProfile()` → `navigate('/')`.

- [ ] **Step 1: Rewrite the page**

Replace the entire contents of `frontend/src/pages/Onboarding.tsx` with:

```tsx
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { api } from '../api';
import { ArrowRight, Check } from 'lucide-react';

type Profile = {
  full_name: string;
  designation: string;
  bar_council_number: string;
  personal_phone: string;
};

export default function Onboarding() {
  const navigate = useNavigate();
  const { refreshProfile, isOnboarded, isLoading: isAuthLoading, pendingInvite } = useAuth();

  useEffect(() => {
    if (!isAuthLoading && isOnboarded) navigate('/', { replace: true });
  }, [isAuthLoading, isOnboarded, navigate]);

  const [profile, setProfile] = useState<Profile>({
    full_name: '', designation: '', bar_council_number: '', personal_phone: '',
  });
  const [firmName, setFirmName] = useState('');
  const [isSolo, setIsSolo] = useState(true);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const isInvitee = !!pendingInvite;

  const onProfileChange = (e: React.ChangeEvent<HTMLInputElement>) =>
    setProfile((p) => ({ ...p, [e.target.name]: e.target.value }));

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (!profile.full_name.trim()) return setError('Your name is required');
    if (!isInvitee && !firmName.trim()) return setError('Firm name is required');

    setIsLoading(true);
    try {
      if (isInvitee) {
        await api.acceptPendingInvite();
        await api.updateProfile(profile);
      } else {
        await api.onboard({ ...profile, firm_name: firmName, is_solo: isSolo });
      }
      try { await refreshProfile(); } catch (err) { console.error(err); }
      navigate('/');
    } catch (err: any) {
      setError(err.message || 'Could not complete setup. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-paper py-12 px-6">
      <div className="max-w-2xl mx-auto animate-fade-up">
        <div className="text-center mb-10">
          <span className="font-display text-4xl text-ink"
            style={{ fontVariationSettings: '"opsz" 144, "wght" 500, "SOFT" 30' }}>
            Snappy
          </span>
          <span className="inline-block h-1.5 w-1.5 rounded-full bg-oxblood mb-1 ml-1.5" />
          <div className="eyebrow text-ink-faint mt-2">
            {isInvitee ? `Join ${pendingInvite!.firm_name}` : 'Establish your chambers'}
          </div>
        </div>

        <div className="card p-10">
          {error && <div className="alert-error mb-6" role="alert">{error}</div>}

          <form onSubmit={submit} className="space-y-5">
            <div className="mb-2">
              <div className="page-eyebrow">{isInvitee ? 'Your details' : 'Step I'}</div>
              <h2 className="section-title">
                {isInvitee
                  ? `Joining as ${pendingInvite!.role_name}`
                  : 'Tell us about you and your firm'}
              </h2>
            </div>

            <div>
              <label className="field-label">Your full name *</label>
              <input name="full_name" value={profile.full_name} onChange={onProfileChange}
                     className="field-input" placeholder="e.g., Adv. Priya Sharma" autoFocus />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="field-label">Designation</label>
                <input name="designation" value={profile.designation} onChange={onProfileChange}
                       className="field-input" placeholder="Advocate" />
              </div>
              <div>
                <label className="field-label">Bar Council / enrolment no.</label>
                <input name="bar_council_number" value={profile.bar_council_number}
                       onChange={onProfileChange} className="field-input font-mono"
                       placeholder="MAH/1234/2020" />
              </div>
            </div>

            <div>
              <label className="field-label">Your phone</label>
              <input name="personal_phone" value={profile.personal_phone} onChange={onProfileChange}
                     className="field-input font-mono" placeholder="+91-XXXXXXXXXX" />
            </div>

            {!isInvitee && (
              <>
                <div className="pt-4 border-t border-rule">
                  <label className="field-label">Firm name *</label>
                  <input value={firmName} onChange={(e) => setFirmName(e.target.value)}
                         className="field-input" placeholder="e.g., Sharma & Associates" />
                </div>

                <div>
                  <label className="field-label">Are you practising solo or as a firm?</label>
                  <div className="flex gap-3 mt-1">
                    {[['Solo', true], ['Firm / team', false]].map(([label, val]) => (
                      <button type="button" key={label as string}
                        onClick={() => setIsSolo(val as boolean)}
                        className={`px-4 py-2 rounded-md border text-sm transition-all ${
                          isSolo === val ? 'border-oxblood bg-oxblood/5 text-ink'
                                         : 'border-rule text-ink-muted'}`}>
                        {label}
                      </button>
                    ))}
                  </div>
                </div>
              </>
            )}

            <div className="flex justify-end pt-6 border-t border-rule">
              <button type="submit" disabled={isLoading} className="btn-primary">
                {isLoading ? (
                  <><span className="spinner !w-4 !h-4 !border-paper/40 !border-t-paper" />
                    <span>Setting up…</span></>
                ) : (
                  <><span>{isInvitee ? 'Join firm' : 'Enter Snappy'}</span>
                    {isInvitee ? <Check size={14} strokeWidth={2} />
                               : <ArrowRight size={14} strokeWidth={2} />}</>
                )}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Build**

Run: `cd frontend && npm run build`
Expected: clean build.

- [ ] **Step 3: Manual verification (note for reviewer)**

- Owner path: a fresh signup with no pending invite sees firm-name + Solo/Firm; submitting lands on `/`.
- Invitee path: a signup whose email has a pending invite sees no firm fields and the "Join {firm}" header; submitting joins the firm.

- [ ] **Step 4: Commit (Parth)**

```bash
git add frontend/src/pages/Onboarding.tsx
git commit -m "feat(onboarding): minimal owner gate + invitee reconciliation on /onboarding"
```

---

### Task 10: Shared invitee-profile step + AcceptInvite reroute

**Files:**
- Create: `frontend/src/pages/InviteeProfile.tsx`
- Modify: `frontend/src/pages/AcceptInvite.tsx` (success path)
- Modify: `frontend/src/App.tsx` (add `/invitee-profile` route)

**Interfaces:**
- Consumes: `api.updateProfile`, `useAuth().refreshProfile`.
- Produces: route `/invitee-profile` rendering `InviteeProfile` (authenticated, no onboarding gate). After a successful **token** accept, `AcceptInvite` navigates here so the just-joined member fills their personal profile, then lands on `/`.

- [ ] **Step 1: Create the InviteeProfile page**

```tsx
// frontend/src/pages/InviteeProfile.tsx
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { api } from '../api';
import { Check } from 'lucide-react';

export default function InviteeProfile() {
  const navigate = useNavigate();
  const { refreshProfile } = useAuth();
  const [form, setForm] = useState({
    full_name: '', designation: '', bar_council_number: '', personal_phone: '',
  });
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const onChange = (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((f) => ({ ...f, [e.target.name]: e.target.value }));

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (!form.full_name.trim()) return setError('Your name is required');
    setIsLoading(true);
    try {
      await api.updateProfile(form);
      try { await refreshProfile(); } catch (err) { console.error(err); }
      navigate('/');
    } catch (err: any) {
      setError(err.message || 'Could not save your profile.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-paper py-12 px-6">
      <div className="max-w-2xl mx-auto animate-fade-up">
        <div className="text-center mb-10">
          <div className="page-eyebrow">Welcome aboard</div>
          <h1 className="page-title">Complete your profile</h1>
        </div>
        <div className="card p-10">
          {error && <div className="alert-error mb-6" role="alert">{error}</div>}
          <form onSubmit={submit} className="space-y-5">
            <div>
              <label className="field-label">Your full name *</label>
              <input name="full_name" value={form.full_name} onChange={onChange}
                     className="field-input" placeholder="e.g., Adv. Priya Sharma" autoFocus />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="field-label">Designation</label>
                <input name="designation" value={form.designation} onChange={onChange}
                       className="field-input" placeholder="Associate" />
              </div>
              <div>
                <label className="field-label">Bar Council / enrolment no.</label>
                <input name="bar_council_number" value={form.bar_council_number}
                       onChange={onChange} className="field-input font-mono"
                       placeholder="MAH/1234/2020" />
              </div>
            </div>
            <div>
              <label className="field-label">Your phone</label>
              <input name="personal_phone" value={form.personal_phone} onChange={onChange}
                     className="field-input font-mono" placeholder="+91-XXXXXXXXXX" />
            </div>
            <div className="flex justify-end pt-6 border-t border-rule">
              <button type="submit" disabled={isLoading} className="btn-primary">
                {isLoading ? (
                  <><span className="spinner !w-4 !h-4 !border-paper/40 !border-t-paper" />
                    <span>Saving…</span></>
                ) : (
                  <><span>Go to dashboard</span><Check size={14} strokeWidth={2} /></>
                )}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Reroute AcceptInvite's success path**

In `frontend/src/pages/AcceptInvite.tsx`, in the `useEffect` success branch (lines ~28-31), after `await refreshProfile();` replace the `setStatus('success')`/`setMessage(...)` with a redirect to the profile step:

```typescript
        await api.acceptInvite(token);
        await refreshProfile(); // pick up new firm_id + permissions
        navigate('/invitee-profile', { replace: true });
        return;
```

(Leave the `catch` error handling intact. The `success` JSX branch becomes dead but harmless — optionally remove it; not required for build.)

- [ ] **Step 3: Register the route**

In `frontend/src/App.tsx`, import the page near the other page imports (after the `AcceptInvite` import, line ~25):

```tsx
import InviteeProfile from './pages/InviteeProfile';
```

Then add a route next to `/onboarding` (after the `/onboarding` route block, line ~83). It must be authenticated but NOT gated on onboarding (the user is now onboarded via the accept, so `requireOnboarding` would also pass — but to be safe and match `/onboarding`, gate only on auth):

```tsx
          <Route
            path="/invitee-profile"
            element={
              <ProtectedRoute>
                <InviteeProfile />
              </ProtectedRoute>
            }
          />
```

- [ ] **Step 4: Build**

Run: `cd frontend && npm run build`
Expected: clean build.

- [ ] **Step 5: Commit (Parth)**

```bash
git add frontend/src/pages/InviteeProfile.tsx frontend/src/pages/AcceptInvite.tsx frontend/src/App.tsx
git commit -m "feat(onboarding): invitee-profile step after token accept"
```

---

### Task 11: Home "Finish setting up" checklist card

**Files:**
- Create: `frontend/src/components/SetupChecklist.tsx`
- Modify: `frontend/src/pages/Home.tsx` (render the card)

**Interfaces:**
- Consumes: `useAuth().setup`, `useAuth().profile`, `useAuth().refreshProfile`, `api.dismissChecklist`.
- Behavior: Renders nothing when `setup` is null, `setup.dismissed`, or `setup.complete`. Otherwise shows four rows (bank / branding / billing / team) with done/undone state, each deep-linking to Settings or Team, plus a dismiss (×) that calls `dismissChecklist()` then `refreshProfile()`. The "team" row is de-emphasized (rendered last, muted) when `profile?.is_solo`.

- [ ] **Step 1: Create the component**

```tsx
// frontend/src/components/SetupChecklist.tsx
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { api } from '../api';
import { Check, Circle, X } from 'lucide-react';

type Row = { key: 'bank' | 'branding' | 'billing' | 'team'; label: string; to: string };

const ROWS: Row[] = [
  { key: 'bank', label: 'Add bank / UPI details', to: '/settings' },
  { key: 'branding', label: 'Upload logo & signature', to: '/settings' },
  { key: 'billing', label: 'Set billing terms & tax', to: '/settings' },
  { key: 'team', label: 'Invite your team', to: '/team' },
];

export default function SetupChecklist() {
  const navigate = useNavigate();
  const { setup, profile, refreshProfile } = useAuth();

  if (!setup || setup.dismissed || setup.complete) return null;

  const dismiss = async () => {
    try { await api.dismissChecklist(); await refreshProfile(); }
    catch (e) { console.error(e); }
  };

  // Solo practitioners: push the team row to the end and mute it.
  const rows = profile?.is_solo
    ? [...ROWS.filter((r) => r.key !== 'team'), ...ROWS.filter((r) => r.key === 'team')]
    : ROWS;

  const doneCount = ROWS.filter((r) => setup[r.key]).length;

  return (
    <div className="card p-6 mb-6 relative">
      <button onClick={dismiss} aria-label="Dismiss checklist"
              className="absolute top-4 right-4 text-ink-faint hover:text-ink">
        <X size={16} />
      </button>
      <div className="page-eyebrow">Finish setting up</div>
      <h3 className="section-title !text-lg mb-1">
        {doneCount} of {ROWS.length} done
      </h3>
      <p className="text-sm text-ink-muted mb-4">
        Complete these to get the most out of Snappy. You can do them anytime.
      </p>
      <ul className="space-y-1">
        {rows.map((r) => {
          const done = setup[r.key];
          const muted = profile?.is_solo && r.key === 'team';
          return (
            <li key={r.key}>
              <button onClick={() => navigate(r.to)}
                className={`w-full flex items-center gap-3 px-3 py-2 rounded-md text-left
                            hover:bg-paper-deep transition-colors ${muted ? 'opacity-60' : ''}`}>
                {done
                  ? <Check size={16} className="text-oxblood shrink-0" strokeWidth={2.5} />
                  : <Circle size={16} className="text-ink-faint shrink-0" />}
                <span className={`text-sm ${done ? 'text-ink-muted line-through' : 'text-ink'}`}>
                  {r.label}
                </span>
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
```

- [ ] **Step 2: Render it on Home**

In `frontend/src/pages/Home.tsx`, import the component near the top:

```tsx
import SetupChecklist from '../components/SetupChecklist';
```

Then render `<SetupChecklist />` near the top of the page's main content — directly under the greeting header block, before the rest of the Home content. (Place it as the first child inside the page's main container `div` so it sits above existing widgets.)

- [ ] **Step 3: Build**

Run: `cd frontend && npm run build`
Expected: clean build.

- [ ] **Step 4: Manual verification (note for reviewer)**

- A freshly-onboarded owner sees the checklist with 0/4 done.
- Adding a bank account in Settings flips that row to done after a refresh.
- The × dismiss hides the card and it stays hidden across reloads (flag persisted).
- Solo owners see "Invite your team" muted and last.

- [ ] **Step 5: Commit (Parth)**

```bash
git add frontend/src/components/SetupChecklist.tsx frontend/src/pages/Home.tsx
git commit -m "feat(onboarding): Home 'Finish setting up' checklist card"
```

---

## Self-Review

**Spec coverage:**
- Migration 023 personal-profile layer + nullable firm_address → Task 1 ✓
- invite_service accept-pending / pending lookup → Task 2 ✓
- Slimmed `/auth/onboard` gate (profile + firm_name + is_solo, minimal FirmDetails) → Task 3 ✓
- `PATCH /auth/profile` → Task 4 ✓
- `POST /invites/accept-pending` (auto-route) → Task 5 ✓
- `/auth/me` profile fields + pending_invite + derived setup → Task 6 ✓
- `POST /auth/dismiss-checklist` → Task 7 ✓
- Frontend api + AuthContext → Task 8 ✓
- Minimal owner gate + invitee reconciliation → Task 9 ✓
- Shared invitee-profile step + AcceptInvite reroute → Task 10 ✓
- Home setup checklist → Task 11 ✓
- Out of scope (R3 merge, email templates, RBAC change) → not touched ✓

**Type consistency:** `SetupState`/`setup` keys (`bank/branding/billing/team/dismissed/complete`) match between Task 6 (backend JSON), Task 8 (AuthContext type), and Task 11 (component). `pending_invite` → `pendingInvite { firm_name, role_name }` consistent Tasks 6/8/9/11. `api.updateProfile/acceptPendingInvite/dismissChecklist` signatures consistent Tasks 8/9/10/11.

**Placeholder scan:** No TBD/TODO; every code step shows full code; commands have expected output. The dead `success` JSX in AcceptInvite is explicitly flagged as harmless/optional, not a placeholder.

**Migration ordering note:** Task 1's migration must be applied on Supabase before the backend revision that includes Tasks 3-7 is deployed (the code reads the new columns). Local SQLite tests create the schema from the models, so test order is unaffected.
