"""Task: a firm-scoped, date-scheduled to-do, optionally linked to a case."""
from datetime import datetime
from app.models.models import db


class Task(db.Model):
    __tablename__ = 'tasks'

    id = db.Column(db.Integer, primary_key=True)
    firm_id = db.Column(db.Integer, db.ForeignKey('firms.id'), index=True)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
    title = db.Column(db.String(300), nullable=False)
    due_date = db.Column(db.Date, index=True)
    case_file_id = db.Column(db.Integer, db.ForeignKey('case_files.id'))
    done = db.Column(db.Boolean, nullable=False, default=False)
    priority = db.Column(db.String(20), nullable=False, default='normal')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    case_file = db.relationship('CaseFile')

    def to_dict(self):
        return {
            'id': self.id,
            'firm_id': self.firm_id,
            'created_by_user_id': self.created_by_user_id,
            'title': self.title,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'case_file_id': self.case_file_id,
            'case_number': self.case_file.case_number if self.case_file else None,
            'case_title': self.case_file.title if self.case_file else None,
            'done': self.done,
            'priority': self.priority,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
