"""Authentication models - User, FirmDetails, BankAccount"""
from app.models.models import db
from datetime import datetime
import json


class User(db.Model):
    """User account linked to Supabase Auth"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    supabase_id = db.Column(db.String(100), unique=True)  # UUID from Supabase Auth
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    is_active = db.Column(db.Boolean, default=True)
    is_onboarded = db.Column(db.Boolean, default=False)
    device_id = db.Column(db.Text)
    device_info = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Relationships
    firm_details = db.relationship('FirmDetails', back_populates='user', uselist=False, cascade='all, delete-orphan')
    bank_accounts = db.relationship('BankAccount', back_populates='user', cascade='all, delete-orphan')
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
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }


class FirmDetails(db.Model):
    """Firm/Company details - one per user"""
    __tablename__ = 'firm_details'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    
    # Firm Details
    firm_name = db.Column(db.String(200), nullable=False)
    firm_address = db.Column(db.Text, nullable=False)
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
    
    # Preferences
    default_template = db.Column(db.String(50), default='Simple')
    invoice_prefix = db.Column(db.String(20), default='INV')
    default_tax_rate = db.Column(db.Float, default=18.0)
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
            'default_template': self.default_template,
            'invoice_prefix': self.invoice_prefix,
            'default_tax_rate': self.default_tax_rate,
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
    
    bank_name = db.Column(db.String(200))
    account_number = db.Column(db.String(100))
    account_holder_name = db.Column(db.String(200))
    ifsc_code = db.Column(db.String(50))
    upi_id = db.Column(db.String(100))
    upi_qr_path = db.Column(db.Text)
    is_default = db.Column(db.Boolean, default=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', back_populates='bank_accounts')
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'bank_name': self.bank_name,
            'account_number': self.account_number,
            'account_holder_name': self.account_holder_name,
            'ifsc_code': self.ifsc_code,
            'upi_id': self.upi_id,
            'upi_qr_path': self.upi_qr_path,
            'is_default': self.is_default,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


# Keep Firm as alias for backwards compatibility during migration
Firm = FirmDetails
