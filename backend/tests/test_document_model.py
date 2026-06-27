from datetime import date
from app.models.models import db, Client
from app.models.auth import User
from app.models.case import CaseFile, CaseEvent, CaseDocument
from app.services.firm_service import provision_firm_for_user


def _case(app):
    with app.app_context():
        u = User(supabase_id='sb-d', email='d@firm.com')
        db.session.add(u); db.session.commit()
        firm = provision_firm_for_user(u, 'Acme')
        c = Client(firm_id=firm.id, created_by_user_id=u.id, name='X')
        db.session.add(c); db.session.commit()
        cf = CaseFile(firm_id=firm.id, created_by_user_id=u.id,
                      case_number='CF/2026/0001', title='M', client_id=c.id)
        db.session.add(cf); db.session.commit()
        return firm.id, u.id, cf.id


def test_to_dict_omits_storage_path(app):
    firm_id, uid, cf_id = _case(app)
    with app.app_context():
        d = CaseDocument(firm_id=firm_id, case_file_id=cf_id, uploaded_by_user_id=uid,
                         title='Petition', doc_type='pleading', file_name='p.pdf',
                         mime_type='application/pdf', size_bytes=1234,
                         storage_path=f'{firm_id}/{cf_id}/abc.pdf')
        db.session.add(d); db.session.commit()
        out = d.to_dict()
        assert out['title'] == 'Petition'
        assert out['doc_type'] == 'pleading'
        assert out['size_bytes'] == 1234
        assert 'storage_path' not in out


def test_documents_cascade_on_case_delete(app):
    firm_id, uid, cf_id = _case(app)
    with app.app_context():
        db.session.add(CaseDocument(firm_id=firm_id, case_file_id=cf_id, uploaded_by_user_id=uid,
                                    title='D', doc_type='other', file_name='d.pdf',
                                    storage_path='x'))
        db.session.commit()
        cf = CaseFile.query.get(cf_id)
        db.session.delete(cf); db.session.commit()
        assert CaseDocument.query.filter_by(case_file_id=cf_id).count() == 0
