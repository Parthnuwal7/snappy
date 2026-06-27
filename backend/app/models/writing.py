"""Writing module model: one `writing_documents` table holding both reusable
templates and working drafts, distinguished by `kind`."""
from datetime import datetime
from app.models.models import db


class WritingDoc(db.Model):
    __tablename__ = 'writing_documents'
    id = db.Column(db.Integer, primary_key=True)
    firm_id = db.Column(db.Integer, db.ForeignKey('firms.id'), index=True)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    kind = db.Column(db.String(20), nullable=False)  # 'template' | 'draft'
    title = db.Column(db.String(300), nullable=False)
    category = db.Column(db.String(40))  # templates only
    body = db.Column(db.Text)
    case_file_id = db.Column(db.Integer, db.ForeignKey('case_files.id'))  # drafts only
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    case_file = db.relationship('CaseFile')

    def to_template_dict(self):
        return {'id': self.id, 'firm_id': self.firm_id, 'created_by_user_id': self.created_by_user_id,
                'name': self.title, 'category': self.category, 'body': self.body,
                'created_at': self.created_at.isoformat() if self.created_at else None,
                'updated_at': self.updated_at.isoformat() if self.updated_at else None}

    def to_draft_dict(self):
        return {'id': self.id, 'firm_id': self.firm_id, 'created_by_user_id': self.created_by_user_id,
                'title': self.title, 'body': self.body, 'case_file_id': self.case_file_id,
                'case_number': self.case_file.case_number if self.case_file else None,
                'case_title': self.case_file.title if self.case_file else None,
                'template_id': None,
                'created_at': self.created_at.isoformat() if self.created_at else None,
                'updated_at': self.updated_at.isoformat() if self.updated_at else None}
