from app.models.models import db, Client
from app.models.auth import User
from app.models.case import CaseFile, CaseStageChange
from app.services.firm_service import provision_firm_for_user
from app.services.case_service import record_stage_change


def test_record_stage_change_adds_row(app):
    with app.app_context():
        u = User(supabase_id='sb-s', email='s@firm.com')
        db.session.add(u); db.session.commit()
        firm = provision_firm_for_user(u, 'Acme')
        c = Client(firm_id=firm.id, created_by_user_id=u.id, name='X')
        db.session.add(c); db.session.commit()
        cf = CaseFile(firm_id=firm.id, created_by_user_id=u.id,
                      case_number='CF/2026/0001', title='M', client_id=c.id)
        db.session.add(cf); db.session.commit()
        record_stage_change(cf, 'engaged', 'filed', u.id)
        db.session.commit()
        row = CaseStageChange.query.filter_by(case_file_id=cf.id).first()
        assert row.from_stage == 'engaged' and row.to_stage == 'filed'
        assert row.firm_id == firm.id
