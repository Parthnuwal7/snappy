"""Provisioning helpers: create a firm with seeded roles and assign its owner."""
from app.models.models import db
from app.models.auth import Firm, Role
from app.rbac.permissions import DEFAULT_ROLES


def provision_firm(name):
    """Create a Firm and seed the four default roles. Commits and returns it."""
    firm = Firm(name=name or "My Firm")
    db.session.add(firm)
    db.session.flush()
    for role_name, perms in DEFAULT_ROLES.items():
        db.session.add(Role(
            firm_id=firm.id,
            name=role_name,
            permissions=list(perms),
            is_system=(role_name == "Owner"),
            description=f"Default {role_name} role",
        ))
    db.session.commit()
    return firm


def owner_role(firm):
    """The firm's undeletable, all-powerful Owner role."""
    return Role.query.filter_by(firm_id=firm.id, name="Owner", is_system=True).first()


def assign_owner(user, firm):
    """Make the user the Owner of the firm."""
    user.firm_id = firm.id
    user.role_id = owner_role(firm).id
    db.session.commit()


def provision_firm_for_user(user, name):
    """Provision a firm and make the user its Owner in one call."""
    firm = provision_firm(name)
    assign_owner(user, firm)
    return firm
