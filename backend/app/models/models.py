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
    # firm_id is the access scope; created_by_user_id is attribution (renamed from
    # user_id by migration 008). Nullable during transition so create_all/backfill work.
    firm_id = db.Column(db.Integer, db.ForeignKey('firms.id'), index=True)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
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
            'firm_id': self.firm_id,
            'created_by_user_id': self.created_by_user_id,
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
    firm_id = db.Column(db.Integer, db.ForeignKey('firms.id'), index=True)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
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
            'firm_id': self.firm_id,
            'created_by_user_id': self.created_by_user_id,
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
    firm_id = db.Column(db.Integer, db.ForeignKey('firms.id'), index=True)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
    invoice_number = db.Column(db.String(50), nullable=False, index=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    # Optional link to a case file (CRM spine); blank preserves standalone billing.
    case_file_id = db.Column(db.Integer, db.ForeignKey('case_files.id'), index=True)
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
    
    # One invoice number per firm (migration 008 swaps the old per-user constraint).
    __table_args__ = (
        db.UniqueConstraint('firm_id', 'invoice_number', name='invoices_firm_id_invoice_number_key'),
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
            'firm_id': self.firm_id,
            'created_by_user_id': self.created_by_user_id,
            'invoice_number': self.invoice_number,
            'client_id': self.client_id,
            'case_file_id': self.case_file_id,
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
    firm_id = db.Column(db.Integer, db.ForeignKey('firms.id'), index=True)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
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
            'firm_id': self.firm_id,
            'created_by_user_id': self.created_by_user_id,
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


class LegalFeedSource(db.Model):
    """A feed the ingestion pipeline polls. Config-driven source registry."""
    __tablename__ = 'legal_feed_sources'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    content_type = db.Column(db.String(20), nullable=False)  # judgement|news|notice
    court = db.Column(db.String(100))
    kind = db.Column(db.String(20), nullable=False, default='rss')  # rss|scrape
    feed_url = db.Column(db.String(500), nullable=False, unique=True)
    enabled = db.Column(db.Boolean, nullable=False, default=True)
    weight = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id, 'name': self.name, 'content_type': self.content_type,
            'court': self.court, 'kind': self.kind, 'feed_url': self.feed_url,
            'enabled': self.enabled, 'weight': self.weight,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class LegalFeedItem(db.Model):
    """A single feed entry: headline + summary + link-out. No full text."""
    __tablename__ = 'legal_feed_items'

    id = db.Column(db.Integer, primary_key=True)
    source_id = db.Column(db.Integer, db.ForeignKey('legal_feed_sources.id'), index=True)
    content_type = db.Column(db.String(20), nullable=False, index=True)
    title = db.Column(db.Text, nullable=False)
    summary = db.Column(db.Text)
    source_url = db.Column(db.String(1000), nullable=False)
    source_name = db.Column(db.String(200), nullable=False)
    court = db.Column(db.String(100), index=True)
    published_at = db.Column(db.DateTime, index=True)
    ingested_at = db.Column(db.DateTime, default=datetime.utcnow)
    hidden = db.Column(db.Boolean, nullable=False, default=False)
    dedup_key = db.Column(db.String(64), nullable=False, unique=True, index=True)
    # Enrichment (best-effort; NULL enriched_at means "not yet enriched")
    headline = db.Column(db.Text)        # punchy rewrite, news only
    tldr = db.Column(db.Text)            # "why it matters", news only
    topics = db.Column(db.JSON)          # subset of taxonomy
    importance = db.Column(db.Integer)   # 0-100
    image_url = db.Column(db.String(1000))
    embedding = db.Column(db.JSON)       # list[float]
    embed_model = db.Column(db.String(80))
    enriched_at = db.Column(db.DateTime)

    def to_dict(self):
        return {
            'id': self.id, 'content_type': self.content_type, 'title': self.title,
            'summary': self.summary, 'source_url': self.source_url,
            'source_name': self.source_name, 'court': self.court,
            'published_at': self.published_at.isoformat() if self.published_at else None,
            'ingested_at': self.ingested_at.isoformat() if self.ingested_at else None,
            'hidden': self.hidden,
            'headline': self.headline, 'tldr': self.tldr,
            'topics': self.topics or [], 'importance': self.importance,
            'image_url': self.image_url,
            'enriched_at': self.enriched_at.isoformat() if self.enriched_at else None,
        }


class LegalFeedRun(db.Model):
    """Audit log of one ingestion run, for the admin status view."""
    __tablename__ = 'legal_feed_runs'

    id = db.Column(db.Integer, primary_key=True)
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    finished_at = db.Column(db.DateTime)
    trigger = db.Column(db.String(20), nullable=False)  # scheduled|manual
    status = db.Column(db.String(20), nullable=False, default='success')
    total_ingested = db.Column(db.Integer, nullable=False, default=0)
    results = db.Column(db.JSON, default=list)  # [{source_id, fetched, inserted, error}]
    enriched = db.Column(db.Integer, nullable=False, default=0)
    enrich_failed = db.Column(db.Integer, nullable=False, default=0)

    def to_dict(self):
        return {
            'id': self.id,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'finished_at': self.finished_at.isoformat() if self.finished_at else None,
            'trigger': self.trigger, 'status': self.status,
            'total_ingested': self.total_ingested, 'results': self.results or [],
            'enriched': self.enriched or 0, 'enrich_failed': self.enrich_failed or 0,
        }


class LegalFeedSetting(db.Model):
    """Singleton (id=1) holding the global feed ordering mode."""
    __tablename__ = 'legal_feed_settings'

    id = db.Column(db.Integer, primary_key=True)
    ordering_mode = db.Column(db.String(20), nullable=False, default='recency')  # recency|weighted

    def to_dict(self):
        return {'id': self.id, 'ordering_mode': self.ordering_mode}


class LegalFeedPreference(db.Model):
    """Per-user feed personalization: macro taxonomy weights + micro interest
    embedding (seeded from free-text phrases). Server-synced (cross-device)."""
    __tablename__ = 'legal_feed_preferences'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False, unique=True, index=True)
    topic_weights = db.Column(db.JSON, default=dict)   # {topic: weight}
    courts = db.Column(db.JSON, default=list)          # [court]
    interest_phrases = db.Column(db.JSON, default=list)
    interest_embedding = db.Column(db.JSON)            # list[float]
    embed_model = db.Column(db.String(80))
    behavior_embedding = db.Column(db.JSON)            # learned interest vector
    behavior_updated_at = db.Column(db.DateTime)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'user_id': self.user_id,
            'topic_weights': self.topic_weights or {},
            'courts': self.courts or [],
            'interest_phrases': self.interest_phrases or [],
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class LegalFeedEvent(db.Model):
    """User engagement with a feed item — the source of truth for behavioral
    personalization. kind: 'click' (positive) | 'not_interested' (negative)."""
    __tablename__ = 'legal_feed_events'
    __table_args__ = (db.Index('ix_lfe_user_kind', 'user_id', 'kind'),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False, index=True)
    item_id = db.Column(db.Integer, db.ForeignKey('legal_feed_items.id'), index=True)
    kind = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id, 'user_id': self.user_id, 'item_id': self.item_id,
            'kind': self.kind,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


def init_db():
    """Initialize database tables"""
    db.create_all()
