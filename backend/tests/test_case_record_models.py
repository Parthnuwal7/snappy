from datetime import date
from app.models.models import db, Client
from app.models.auth import User
from app.models.case import CaseFile, CaseStageChange, CaseExpense
from app.services.firm_service import provision_firm_for_user


def _case(app):
    with app.app_context():
        u = User(supabase_id='sb-r', email='r@firm.com')
        db.session.add(u); db.session.commit()
        firm = provision_firm_for_user(u, 'Acme')
        c = Client(firm_id=firm.id, created_by_user_id=u.id, name='X')
        db.session.add(c); db.session.commit()
        cf = CaseFile(firm_id=firm.id, created_by_user_id=u.id,
                      case_number='CF/2026/0001', title='M', client_id=c.id,
                      agreed_fee=50000)
        db.session.add(cf); db.session.commit()
        return firm.id, u.id, cf.id


def test_agreed_fee_serialized_as_float(app):
    firm_id, uid, cf_id = _case(app)
    with app.app_context():
        assert CaseFile.query.get(cf_id).to_dict()['agreed_fee'] == 50000.0


def test_stage_change_and_expense_cascade(app):
    firm_id, uid, cf_id = _case(app)
    with app.app_context():
        db.session.add(CaseStageChange(firm_id=firm_id, case_file_id=cf_id,
                                       from_stage=None, to_stage='engaged', changed_by_user_id=uid))
        db.session.add(CaseExpense(firm_id=firm_id, case_file_id=cf_id,
                                   expense_date=date(2026, 6, 1), description='Court fee',
                                   category='court_fee', amount=1500, created_by_user_id=uid))
        db.session.commit()
        assert CaseExpense.query.first().to_dict()['amount'] == 1500.0
        cf = CaseFile.query.get(cf_id)
        db.session.delete(cf); db.session.commit()
        assert CaseStageChange.query.filter_by(case_file_id=cf_id).count() == 0
        assert CaseExpense.query.filter_by(case_file_id=cf_id).count() == 0
