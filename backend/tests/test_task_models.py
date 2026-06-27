from datetime import date
from app.models.models import db, Client
from app.models.case import CaseFile
from app.models.task import Task


def _case(app):
    with app.app_context():
        c = Client(firm_id=1, created_by_user_id=1, name='X')
        db.session.add(c); db.session.flush()
        cf = CaseFile(firm_id=1, created_by_user_id=1, case_number='CF/2026/0001', title='Sharma', client_id=c.id)
        db.session.add(cf); db.session.commit()
        return cf.id


def test_task_defaults_and_to_dict(app):
    cf_id = _case(app)
    with app.app_context():
        t = Task(firm_id=1, created_by_user_id=1, title='File reply',
                 due_date=date(2026, 7, 1), case_file_id=cf_id)
        db.session.add(t); db.session.commit()
        d = t.to_dict()
        assert d['title'] == 'File reply'
        assert d['done'] is False
        assert d['priority'] == 'normal'
        assert d['due_date'] == '2026-07-01'
        assert d['case_number'] == 'CF/2026/0001'
        assert d['case_title'] == 'Sharma'


def test_task_without_case(app):
    with app.app_context():
        t = Task(firm_id=1, created_by_user_id=1, title='Call client', due_date=date(2026, 7, 2))
        db.session.add(t); db.session.commit()
        d = t.to_dict()
        assert d['case_file_id'] is None and d['case_number'] is None
