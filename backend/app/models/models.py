"""Database models for SNAPPY"""
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy import func

db = SQLAlchemy()


def _money(val):
    """Coerce a NUMERIC column value to float for JSON serialization.

    Postgres NUMERIC -> psycopg2 Decimal; stdlib json can't encode Decimal.
    Returning float here keeps API payloads JSON-safe without each route
    having to remember. Internal arithmetic still uses Decimal because the
    model column type is Numeric — only the wire format changes.
    """
    return float(val) if val is not None else None


class Client(db.Model):
    """Client/Customer model - scoped to user"""
    __tablename__ = 'clients'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False, index=True)
    email = db.Column(db.String(200))
    phone = db.Column(db.String(50))
    address = db.Column(db.Text)
    tax_id = db.Column(db.String(100))
    default_tax_rate = db.Column(db.Numeric(5, 2), default=18.0)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', back_populates='clients')
    invoices = db.relationship('Invoice', back_populates='client', lazy='dynamic')
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'address': self.address,
            'tax_id': self.tax_id,
            'default_tax_rate': _money(self.default_tax_rate),
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class Item(db.Model):
    """Reusable service/product item catalog - scoped to user"""
    __tablename__ = 'items'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False, index=True)
    alias = db.Column(db.String(100), index=True)
    description = db.Column(db.Text)
    default_rate = db.Column(db.Numeric(12, 2), default=0.0)
    unit = db.Column(db.String(50), default='hour')
    hsn_code = db.Column(db.String(50))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', back_populates='items')
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'alias': self.alias,
            'description': self.description,
            'default_rate': _money(self.default_rate),
            'unit': self.unit,
            'hsn_code': self.hsn_code,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class Invoice(db.Model):
    """Invoice model - scoped to user"""
    __tablename__ = 'invoices'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    invoice_number = db.Column(db.String(50), nullable=False, index=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    invoice_date = db.Column(db.Date, nullable=False, default=datetime.utcnow().date)
    due_date = db.Column(db.Date)
    short_desc = db.Column(db.Text)

    # Amounts (Numeric in DB; arithmetic uses Decimal — see _money() for JSON coercion)
    subtotal = db.Column(db.Numeric(12, 2), default=0.0)
    tax_rate = db.Column(db.Numeric(5, 2), default=18.0)
    tax_amount = db.Column(db.Numeric(12, 2), default=0.0)
    total = db.Column(db.Numeric(12, 2), default=0.0)
    
    # Status
    status = db.Column(db.String(20), default='draft')
    paid_date = db.Column(db.Date)

    # Delivery tracking — set when the invoice is sent to the client.
    sent_at = db.Column(db.DateTime)
    sent_channel = db.Column(db.String(20))  # 'email' | 'whatsapp'

    # Provenance: 'manual' (default) or 'recurring' (created by a schedule)
    source = db.Column(db.String(20), default='manual')

    # Metadata
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Match the live DB constraint applied in migration 002 — one invoice number per user.
    __table_args__ = (
        db.UniqueConstraint('user_id', 'invoice_number', name='invoices_user_id_invoice_number_key'),
    )

    # Relationships
    user = db.relationship('User', back_populates='invoices')
    client = db.relationship('Client', back_populates='invoices')
    items = db.relationship('InvoiceItem', back_populates='invoice', cascade='all, delete-orphan')

    def calculate_totals(self):
        """Calculate subtotal, tax, and total from items"""
        self.subtotal = sum(item.amount for item in self.items)
        self.tax_amount = self.subtotal * (self.tax_rate / 100)
        self.total = self.subtotal + self.tax_amount
    
    def to_dict(self, include_items=False):
        result = {
            'id': self.id,
            'user_id': self.user_id,
            'invoice_number': self.invoice_number,
            'client_id': self.client_id,
            'client_name': self.client.name if self.client else None,
            'invoice_date': self.invoice_date.isoformat() if self.invoice_date else None,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'short_desc': self.short_desc,
            'subtotal': _money(self.subtotal),
            'tax_rate': _money(self.tax_rate),
            'tax_amount': _money(self.tax_amount),
            'total': _money(self.total),
            'status': self.status,
            'source': self.source,
            'paid_date': self.paid_date.isoformat() if self.paid_date else None,
            'sent_at': self.sent_at.isoformat() if self.sent_at else None,
            'sent_channel': self.sent_channel,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
        if include_items:
            result['items'] = [item.to_dict() for item in self.items]
        return result


class InvoiceItem(db.Model):
    """Invoice line item model"""
    __tablename__ = 'invoice_items'
    
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id'), nullable=False)
    description = db.Column(db.Text, nullable=False)
    quantity = db.Column(db.Numeric(12, 3), default=1.0)
    rate = db.Column(db.Numeric(12, 2), nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    
    # Relationships
    invoice = db.relationship('Invoice', back_populates='items')
    
    def to_dict(self):
        return {
            'id': self.id,
            'invoice_id': self.invoice_id,
            'description': self.description,
            'quantity': _money(self.quantity),
            'rate': _money(self.rate),
            'amount': _money(self.amount)
        }


class RecurringSchedule(db.Model):
    """A recurring invoice template that auto-creates draft invoices on a cadence."""
    __tablename__ = 'recurring_schedules'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    title = db.Column(db.String(200))
    items = db.Column(db.JSON, nullable=False, default=list)
    tax_rate = db.Column(db.Numeric(5, 2), default=18.0)
    short_desc = db.Column(db.Text)
    notes = db.Column(db.Text)
    frequency = db.Column(db.String(20), nullable=False)  # 'weekly' | 'monthly'
    start_date = db.Column(db.Date, nullable=False)
    next_run_date = db.Column(db.Date, nullable=False, index=True)
    end_date = db.Column(db.Date)            # optional; None = until paused
    last_run_date = db.Column(db.Date)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    client = db.relationship('Client')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'client_id': self.client_id,
            'client_name': self.client.name if self.client else None,
            'title': self.title,
            'items': self.items or [],
            'tax_rate': _money(self.tax_rate),
            'short_desc': self.short_desc,
            'notes': self.notes,
            'frequency': self.frequency,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'next_run_date': self.next_run_date.isoformat() if self.next_run_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'last_run_date': self.last_run_date.isoformat() if self.last_run_date else None,
            'active': self.active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class Keepalive(db.Model):
    """Heartbeat written by Cloud Scheduler to prevent Supabase auto-pause.

    Free-tier Supabase projects pause after 7 days of inactivity. A row
    inserted here every 3 days counts as DB activity and resets that timer.
    Not scoped to any user; this is infrastructure plumbing.
    """
    __tablename__ = 'keepalive'

    id = db.Column(db.BigInteger, primary_key=True)
    pinged_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    source = db.Column(db.String(50))

    def to_dict(self):
        return {
            'id': self.id,
            'pinged_at': self.pinged_at.isoformat() if self.pinged_at else None,
            'source': self.source,
        }


def init_db():
    """Initialize database tables"""
    db.create_all()
