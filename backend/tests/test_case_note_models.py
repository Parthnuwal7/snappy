from app.models.models import db, Client
from app.models.case import CaseFile, CaseNote


def _case(app):
    with app.app_context():
        c = Client(firm_id=1, created_by_user_id=1, name='X')
        db.session.add(c); db.session.flush()
        cf = CaseFile(firm_id=1, created_by_user_id=1, case_number='CF/2026/0001',
                      title='M', client_id=c.id)
        db.session.add(cf); db.session.commit()
        return cf.id


def test_case_note_defaults_and_to_dict(app):
    cf_id = _case(app)
    with app.app_context():
        note = CaseNote(firm_id=1, case_file_id=cf_id, created_by_user_id=1,
                        body='Client to bring originals')
        db.session.add(note); db.session.commit()
        d = note.to_dict()
        assert d['body'] == 'Client to bring originals'
        assert d['pinned'] is False
        assert d['event_id'] is None and d['document_id'] is None
        assert d['case_file_id'] == cf_id
