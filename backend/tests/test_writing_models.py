from app.models.models import db, Client
from app.models.case import CaseFile
from app.models.writing import WritingDoc


def _case(app):
    with app.app_context():
        c = Client(firm_id=1, created_by_user_id=1, name='X'); db.session.add(c); db.session.flush()
        cf = CaseFile(firm_id=1, created_by_user_id=1, case_number='CF/2026/0001', title='Sharma', client_id=c.id)
        db.session.add(cf); db.session.commit()
        return cf.id


def test_template_dict(app):
    with app.app_context():
        t = WritingDoc(firm_id=1, created_by_user_id=1, kind='template', title='Notice', category='notice', body='<p>{{court}}</p>')
        db.session.add(t); db.session.commit()
        d = t.to_template_dict()
        assert d['name'] == 'Notice' and d['category'] == 'notice' and '{{court}}' in d['body']


def test_draft_dict_with_case(app):
    cf_id = _case(app)
    with app.app_context():
        dr = WritingDoc(firm_id=1, created_by_user_id=1, kind='draft', title='Reply', body='<p>x</p>', case_file_id=cf_id)
        db.session.add(dr); db.session.commit()
        d = dr.to_draft_dict()
        assert d['title'] == 'Reply' and d['case_number'] == 'CF/2026/0001' and d['case_title'] == 'Sharma'
