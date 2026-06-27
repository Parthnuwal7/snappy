"""Lead / Enquiry: a prospective matter before the firm commits to it.

Lives apart from CaseFile so no CF number is spent until conversion. On accept,
a Lead converts into a CaseFile (see app/api/leads.py:convert_lead).
"""
from datetime import datetime
from app.models.models import db

LEAD_STATUSES = {"open", "accepted", "declined"}
DEFAULT_LEAD_STATUS = "open"


class Lead(db.Model):
    __tablename__ = 'leads'

    id = db.Column(db.Integer, primary_key=True)
    firm_id = db.Column(db.Integer, db.ForeignKey('firms.id'), index=True)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
    contact_name = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(50))
    email = db.Column(db.String(200))
    matter_summary = db.Column(db.Text)
    intake_notes = db.Column(db.Text)
    status = db.Column(db.String(20), nullable=False, default=DEFAULT_LEAD_STATUS)
    decided_at = db.Column(db.DateTime)
    converted_case_file_id = db.Column(db.Integer, db.ForeignKey('case_files.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'firm_id': self.firm_id,
            'created_by_user_id': self.created_by_user_id,
            'contact_name': self.contact_name,
            'phone': self.phone,
            'email': self.email,
            'matter_summary': self.matter_summary,
            'intake_notes': self.intake_notes,
            'status': self.status,
            'decided_at': self.decided_at.isoformat() if self.decided_at else None,
            'converted_case_file_id': self.converted_case_file_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
