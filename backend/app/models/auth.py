"""Authentication models - User, FirmDetails, BankAccount"""
from app.models.models import db, _money
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import String
from datetime import datetime
import json


class User(db.Model):
    """User account linked to Supabase Auth"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    # Postgres column is uuid; as_uuid=False keeps Python-side values as plain strings
    # so JSON serialization, JWT sub comparisons, and frontend payloads all line up.
    # UUID on Postgres (prod); plain string on SQLite so the test suite can run
    # against an in-memory DB without a Postgres-only type failing to compile.
    supabase_id = db.Column(UUID(as_uuid=False).with_variant(String(36), 'sqlite'), unique=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    is_active = db.Column(db.Boolean, default=True)
    is_onboarded = db.Column(db.Boolean, default=False)
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
    # Firm tenancy: a user belongs to exactly one firm with exactly one role.
    firm_id = db.Column(db.Integer, db.ForeignKey('firms.id'), index=True)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))
    device_id = db.Column(db.Text)
    device_info = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Relationships
    firm_details = db.relationship('FirmDetails', back_populates='user', uselist=False, cascade='all, delete-orphan')
    bank_accounts = db.relationship('BankAccount', back_populates='user',
                                    foreign_keys='BankAccount.user_id',
                                    cascade='all, delete-orphan')
    clients = db.relationship('Client', back_populates='user', cascade='all, delete-orphan')
    items = db.relationship('Item', back_populates='user', cascade='all, delete-orphan')
    invoices = db.relationship('Invoice', back_populates='user', cascade='all, delete-orphan')
    
    def get_device_info(self):
        if self.device_info:
            if isinstance(self.device_info, str):
                try:
                    return json.loads(self.device_info)
                except:
                    return {}
            return self.device_info
        return {}
    
    def to_dict(self):
        return {
            'id': self.id,
            'supabase_id': self.supabase_id,
            'email': self.email,
            'is_active': self.is_active,
            'is_onboarded': self.is_onboarded,
            'device_id': self.device_id,
            'device_info': self.get_device_info(),
            'full_name': self.full_name,
            'designation': self.designation,
            'bar_council_number': self.bar_council_number,
            'personal_phone': self.personal_phone,
            'is_solo': self.is_solo,
            'checklist_dismissed': bool(self.checklist_dismissed),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }


class FirmDetails(db.Model):
    """Firm/Company details - one per user"""
    __tablename__ = 'firm_details'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    # One profile per firm. Nullable during transition; backfilled by migration 008.
    firm_id = db.Column(db.Integer, db.ForeignKey('firms.id'), unique=True, index=True)

    # Firm Details
    firm_name = db.Column(db.String(200), nullable=False)
    # Nullable: the minimal onboarding gate creates the firm profile with just a
    # name; the address is filled later via the Home setup checklist / Settings.
    firm_address = db.Column(db.Text)
    firm_email = db.Column(db.String(120))
    firm_phone = db.Column(db.String(50))
    firm_phone_2 = db.Column(db.String(50))
    firm_website = db.Column(db.String(200))
    
    # Branding
    logo_path = db.Column(db.Text)
    signature_path = db.Column(db.Text)
    
    # Terms
    terms_and_conditions = db.Column(db.Text)
    billing_terms = db.Column(db.Text)

    # Message templates for invoice sending (null -> built-in defaults)
    email_subject_template = db.Column(db.Text)
    email_body_template = db.Column(db.Text)
    whatsapp_template = db.Column(db.Text)
    
    # Preferences
    default_template = db.Column(db.String(50), default='Simple')
    invoice_prefix = db.Column(db.String(20), default='INV')
    use_invoice_prefix = db.Column(db.Boolean, default=True)  # True = PREFIX/SEQ, False = SEQ only
    default_tax_rate = db.Column(db.Numeric(5, 2), default=18.0)
    currency = db.Column(db.String(10), default='INR')
    show_due_date = db.Column(db.Boolean, default=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', back_populates='firm_details')
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'firm_name': self.firm_name,
            'firm_address': self.firm_address,
            'firm_email': self.firm_email,
            'firm_phone': self.firm_phone,
            'firm_phone_2': self.firm_phone_2,
            'firm_website': self.firm_website,
            'logo_path': self.logo_path,
            'signature_path': self.signature_path,
            'terms_and_conditions': self.terms_and_conditions,
            'billing_terms': self.billing_terms,
            'email_subject_template': self.email_subject_template,
            'email_body_template': self.email_body_template,
            'whatsapp_template': self.whatsapp_template,
            'default_template': self.default_template,
            'invoice_prefix': self.invoice_prefix,
            'use_invoice_prefix': self.use_invoice_prefix if self.use_invoice_prefix is not None else True,
            'default_tax_rate': _money(self.default_tax_rate),
            'currency': self.currency,
            'show_due_date': self.show_due_date,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class BankAccount(db.Model):
    """Bank account details - can have multiple per user"""
    __tablename__ = 'bank_accounts'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    # Firm-owned payment details (transition: user_id kept; firm_id is the scope).
    firm_id = db.Column(db.Integer, db.ForeignKey('firms.id'), index=True)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    bank_name = db.Column(db.String(200))
    account_number = db.Column(db.String(100))
    account_holder_name = db.Column(db.String(200))
    ifsc_code = db.Column(db.String(50))
    upi_id = db.Column(db.String(100))
    upi_payee_name = db.Column(db.String(200))
    upi_note = db.Column(db.String(120))
    is_default = db.Column(db.Boolean, default=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships — pin foreign_keys since two columns FK to users.id now.
    user = db.relationship('User', back_populates='bank_accounts', foreign_keys=[user_id])

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'firm_id': self.firm_id,
            'created_by_user_id': self.created_by_user_id,
            'bank_name': self.bank_name,
            'account_number': self.account_number,
            'account_holder_name': self.account_holder_name,
            'ifsc_code': self.ifsc_code,
            'upi_id': self.upi_id,
            'upi_payee_name': self.upi_payee_name,
            'upi_note': self.upi_note,
            'is_default': self.is_default,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class Firm(db.Model):
    """The tenant. Owns all billing data; has many members (users)."""
    __tablename__ = 'firms'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class Role(db.Model):
    """Firm-owned, editable bundle of permission keys (a module x action matrix)."""
    __tablename__ = 'roles'
    __table_args__ = (
        db.UniqueConstraint('firm_id', 'name', name='roles_firm_name_key'),
    )

    id = db.Column(db.Integer, primary_key=True)
    firm_id = db.Column(db.Integer, db.ForeignKey('firms.id'), nullable=False, index=True)
    name = db.Column(db.String(80), nullable=False)
    description = db.Column(db.Text)
    permissions = db.Column(db.JSON, default=list)
    is_system = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'firm_id': self.firm_id,
            'name': self.name,
            'description': self.description,
            'permissions': self.permissions or [],
            'is_system': self.is_system,
        }


class FirmInvite(db.Model):
    """Pending member invitation. The raw token is never serialized."""
    __tablename__ = 'firm_invites'

    id = db.Column(db.Integer, primary_key=True)
    firm_id = db.Column(db.Integer, db.ForeignKey('firms.id'), nullable=False, index=True)
    email = db.Column(db.String(200), nullable=False, index=True)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
    token = db.Column(db.String(64), nullable=False, unique=True, index=True)
    status = db.Column(db.String(20), nullable=False, default='pending')  # pending|accepted|revoked|expired
    invited_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    expires_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    accepted_at = db.Column(db.DateTime)

    def to_dict(self):
        return {
            'id': self.id,
            'firm_id': self.firm_id,
            'email': self.email,
            'role_id': self.role_id,
            'status': self.status,
            'invited_by': self.invited_by,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'accepted_at': self.accepted_at.isoformat() if self.accepted_at else None,
        }
