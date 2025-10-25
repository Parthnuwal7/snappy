"""Authentication and User models"""
from backend.app.models.models import db
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import secrets


class User(db.Model):
    """User authentication model"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    is_onboarded = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Relationship to firm
    firm = db.relationship('Firm', back_populates='user', uselist=False)
    
    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Verify password"""
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'is_active': self.is_active,
            'is_onboarded': self.is_onboarded,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }


class Firm(db.Model):
    """Firm/Company details"""
    __tablename__ = 'firms'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Firm Details
    firm_name = db.Column(db.String(200), nullable=False)
    firm_address = db.Column(db.Text, nullable=False)
    firm_email = db.Column(db.String(120))
    firm_phone = db.Column(db.String(50))
    firm_phone_2 = db.Column(db.String(50))
    firm_website = db.Column(db.String(200))
    
    # Branding
    logo_path = db.Column(db.String(500))
    signature_path = db.Column(db.String(500))
    
    # Banking Details
    bank_name = db.Column(db.String(200))
    account_number = db.Column(db.String(100))
    account_holder_name = db.Column(db.String(200))
    ifsc_code = db.Column(db.String(50))
    upi_id = db.Column(db.String(100))
    upi_qr_path = db.Column(db.String(500))
    
    # Terms and Conditions
    terms_and_conditions = db.Column(db.Text)
    billing_terms = db.Column(db.Text)
    
    # Preferences
    default_template = db.Column(db.String(50), default='Simple')
    invoice_prefix = db.Column(db.String(20), default='LAW')
    default_tax_rate = db.Column(db.Float, default=18.0)
    currency = db.Column(db.String(10), default='INR')
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', back_populates='firm')
    
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
            'bank_name': self.bank_name,
            'account_number': self.account_number,
            'account_holder_name': self.account_holder_name,
            'ifsc_code': self.ifsc_code,
            'upi_id': self.upi_id,
            'upi_qr_path': self.upi_qr_path,
            'terms_and_conditions': self.terms_and_conditions,
            'billing_terms': self.billing_terms,
            'default_template': self.default_template,
            'invoice_prefix': self.invoice_prefix,
            'default_tax_rate': self.default_tax_rate,
            'currency': self.currency,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class ProductKey(db.Model):
    """Product activation keys"""
    __tablename__ = 'product_keys'
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    is_used = db.Column(db.Boolean, default=False)
    expires_at = db.Column(db.DateTime)
    activated_at = db.Column(db.DateTime)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    @staticmethod
    def generate_key():
        """Generate a unique product key"""
        return f"SNAPPY-{secrets.token_hex(8).upper()}"
    
    def to_dict(self):
        return {
            'id': self.id,
            'key': self.key,
            'is_used': self.is_used,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'activated_at': self.activated_at.isoformat() if self.activated_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
