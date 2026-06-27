"""Case file spine models: CaseFile + its parties and timeline (case_events).

Scope = firm_id (like clients/invoices); attribution = created_by_user_id.
case_events carries a denormalized firm_id so the later calendar can range-query
all of a firm's dated steps without a join.
"""
from datetime import datetime, date
from app.models.models import db, _money
from app.case.stages import DEFAULT_STAGE, DEFAULT_PRIORITY


class CaseFile(db.Model):
    __tablename__ = 'case_files'
    __table_args__ = (
        db.UniqueConstraint('firm_id', 'case_number',
                            name='case_files_firm_id_case_number_key'),
    )

    id = db.Column(db.Integer, primary_key=True)
    firm_id = db.Column(db.Integer, db.ForeignKey('firms.id'), index=True)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
    case_number = db.Column(db.String(50), nullable=False, index=True)
    title = db.Column(db.String(300), nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    matter_type = db.Column(db.String(80))
    court = db.Column(db.String(200))
    court_case_number = db.Column(db.String(120))
    jurisdiction = db.Column(db.String(120))
    act_section = db.Column(db.String(200))
    opposing_counsel = db.Column(db.String(200))
    stage = db.Column(db.String(40), nullable=False, default=DEFAULT_STAGE)
    priority = db.Column(db.String(20), nullable=False, default=DEFAULT_PRIORITY)
    position = db.Column(db.Integer, nullable=False, default=0)
    agreed_fee = db.Column(db.Numeric(12, 2))
    handling_advocate_user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    filing_date = db.Column(db.Date)
    next_hearing_date = db.Column(db.Date)
    open_date = db.Column(db.Date, default=date.today)
    description = db.Column(db.Text)
    # use_alter breaks the leads<->case_files FK cycle for create_all/drop_all.
    lead_id = db.Column(db.Integer, db.ForeignKey(
        'leads.id', use_alter=True, name='fk_case_files_lead_id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Parties live inline as a JSON list of {name, role} (was the case_parties table).
    parties = db.Column(db.JSON, default=list)

    client = db.relationship('Client')
    events = db.relationship('CaseEvent', back_populates='case_file',
                             cascade='all, delete-orphan')
    documents = db.relationship('CaseDocument', back_populates='case_file',
                                cascade='all, delete-orphan')
    stage_changes = db.relationship('CaseStageChange', back_populates='case_file',
                                    cascade='all, delete-orphan')
    expenses = db.relationship('CaseExpense', back_populates='case_file',
                               cascade='all, delete-orphan')
    notes = db.relationship('CaseNote', back_populates='case_file',
                            cascade='all, delete-orphan')

    def to_dict(self, include_parties=False):
        d = {
            'id': self.id,
            'firm_id': self.firm_id,
            'created_by_user_id': self.created_by_user_id,
            'case_number': self.case_number,
            'title': self.title,
            'client_id': self.client_id,
            'client_name': self.client.name if self.client else None,
            'matter_type': self.matter_type,
            'court': self.court,
            'court_case_number': self.court_case_number,
            'jurisdiction': self.jurisdiction,
            'act_section': self.act_section,
            'opposing_counsel': self.opposing_counsel,
            'stage': self.stage,
            'priority': self.priority,
            'position': self.position,
            'agreed_fee': _money(self.agreed_fee),
            'handling_advocate_user_id': self.handling_advocate_user_id,
            'filing_date': self.filing_date.isoformat() if self.filing_date else None,
            'next_hearing_date': self.next_hearing_date.isoformat() if self.next_hearing_date else None,
            'open_date': self.open_date.isoformat() if self.open_date else None,
            'description': self.description,
            'lead_id': self.lead_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_parties:
            d['parties'] = self.parties or []
        return d


class CaseEvent(db.Model):
    __tablename__ = 'case_events'

    id = db.Column(db.Integer, primary_key=True)
    case_file_id = db.Column(db.Integer, db.ForeignKey('case_files.id'), index=True)
    firm_id = db.Column(db.Integer, db.ForeignKey('firms.id'), index=True)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    event_date = db.Column(db.Date, nullable=False, index=True)
    kind = db.Column(db.String(30), nullable=False, default='note')
    title = db.Column(db.String(300), nullable=False)
    notes = db.Column(db.Text)
    purpose = db.Column(db.String(80))
    outcome = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    case_file = db.relationship('CaseFile', back_populates='events')

    def to_dict(self):
        return {
            'id': self.id,
            'case_file_id': self.case_file_id,
            'firm_id': self.firm_id,
            'created_by_user_id': self.created_by_user_id,
            'event_date': self.event_date.isoformat() if self.event_date else None,
            'kind': self.kind,
            'title': self.title,
            'notes': self.notes,
            'purpose': self.purpose,
            'outcome': self.outcome,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class CaseDocument(db.Model):
    __tablename__ = 'case_documents'

    id = db.Column(db.Integer, primary_key=True)
    firm_id = db.Column(db.Integer, db.ForeignKey('firms.id'), index=True)
    case_file_id = db.Column(db.Integer, db.ForeignKey('case_files.id'), index=True)
    event_id = db.Column(db.Integer, db.ForeignKey('case_events.id'), index=True)
    uploaded_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    title = db.Column(db.String(300), nullable=False)
    doc_type = db.Column(db.String(40), nullable=False, default='other')
    file_name = db.Column(db.String(300))
    mime_type = db.Column(db.String(120))
    size_bytes = db.Column(db.Integer)
    storage_path = db.Column(db.String(500))  # nullable: exhibit-register rows have no file
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    # Evidence exhibit register (was the case_exhibits table). is_exhibit rows are
    # hidden from the Documents tab and surfaced via the exhibits API.
    is_exhibit = db.Column(db.Boolean, default=False)
    exhibit_mark = db.Column(db.String(40))
    party = db.Column(db.String(40))
    exhibit_status = db.Column(db.String(20))
    hearing_event_id = db.Column(db.Integer, db.ForeignKey('case_events.id'))
    linked_document_id = db.Column(db.Integer, db.ForeignKey('case_documents.id'))

    case_file = db.relationship('CaseFile', back_populates='documents')

    def to_dict(self):
        return {
            'id': self.id,
            'firm_id': self.firm_id,
            'case_file_id': self.case_file_id,
            'event_id': self.event_id,
            'uploaded_by_user_id': self.uploaded_by_user_id,
            'title': self.title,
            'doc_type': self.doc_type,
            'file_name': self.file_name,
            'mime_type': self.mime_type,
            'size_bytes': self.size_bytes,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def exhibit_to_dict(self):
        return {
            'id': self.id,
            'firm_id': self.firm_id,
            'case_file_id': self.case_file_id,
            'exhibit_mark': self.exhibit_mark,
            'description': self.description,
            'party': self.party,
            'status': self.exhibit_status,
            'document_id': self.linked_document_id,
            'hearing_event_id': self.hearing_event_id,
            'created_by_user_id': self.uploaded_by_user_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class CaseStageChange(db.Model):
    __tablename__ = 'case_stage_changes'

    id = db.Column(db.Integer, primary_key=True)
    firm_id = db.Column(db.Integer, db.ForeignKey('firms.id'), index=True)
    case_file_id = db.Column(db.Integer, db.ForeignKey('case_files.id'), index=True)
    from_stage = db.Column(db.String(40))
    to_stage = db.Column(db.String(40))
    changed_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    changed_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    case_file = db.relationship('CaseFile', back_populates='stage_changes')

    def to_dict(self):
        return {
            'id': self.id,
            'case_file_id': self.case_file_id,
            'from_stage': self.from_stage,
            'to_stage': self.to_stage,
            'changed_by_user_id': self.changed_by_user_id,
            'changed_at': self.changed_at.isoformat() if self.changed_at else None,
        }


class CaseExpense(db.Model):
    __tablename__ = 'case_expenses'

    id = db.Column(db.Integer, primary_key=True)
    firm_id = db.Column(db.Integer, db.ForeignKey('firms.id'), index=True)
    case_file_id = db.Column(db.Integer, db.ForeignKey('case_files.id'), index=True)
    expense_date = db.Column(db.Date)
    description = db.Column(db.String(300), nullable=False)
    category = db.Column(db.String(40), default='misc')
    amount = db.Column(db.Numeric(12, 2))
    created_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    case_file = db.relationship('CaseFile', back_populates='expenses')

    def to_dict(self):
        return {
            'id': self.id,
            'firm_id': self.firm_id,
            'case_file_id': self.case_file_id,
            'expense_date': self.expense_date.isoformat() if self.expense_date else None,
            'description': self.description,
            'category': self.category,
            'amount': _money(self.amount),
            'created_by_user_id': self.created_by_user_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class CaseNote(db.Model):
    __tablename__ = 'case_notes'

    id = db.Column(db.Integer, primary_key=True)
    firm_id = db.Column(db.Integer, db.ForeignKey('firms.id'), index=True)
    case_file_id = db.Column(db.Integer, db.ForeignKey('case_files.id'), index=True)
    body = db.Column(db.Text, nullable=False)
    pinned = db.Column(db.Boolean, nullable=False, default=False)
    event_id = db.Column(db.Integer, db.ForeignKey('case_events.id'))
    document_id = db.Column(db.Integer, db.ForeignKey('case_documents.id'))
    created_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    case_file = db.relationship('CaseFile', back_populates='notes')

    def to_dict(self):
        return {
            'id': self.id,
            'firm_id': self.firm_id,
            'case_file_id': self.case_file_id,
            'body': self.body,
            'pinned': self.pinned,
            'event_id': self.event_id,
            'document_id': self.document_id,
            'created_by_user_id': self.created_by_user_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


