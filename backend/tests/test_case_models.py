from datetime import date

from app.models.models import db, Client
from app.models.auth import User
from app.models.case import CaseFile, CaseEvent
from app.services.firm_service import provision_firm_for_user


def _firm_with_client(app):
    with app.app_context():
        user = User(supabase_id='sb-case', email='c@firm.com')
        db.session.add(user)
        db.session.commit()
        firm = provision_firm_for_user(user, 'Acme')
        client = Client(firm_id=firm.id, created_by_user_id=user.id, name='X Corp')
        db.session.add(client)
        db.session.commit()
        return firm.id, user.id, client.id


def test_case_file_defaults_and_to_dict(app):
    firm_id, user_id, client_id = _firm_with_client(app)
    with app.app_context():
        cf = CaseFile(firm_id=firm_id, created_by_user_id=user_id,
                      case_number='CF/2026/0001', title='X vs State',
                      client_id=client_id)
        db.session.add(cf)
        db.session.commit()
        d = cf.to_dict()
        assert d['case_number'] == 'CF/2026/0001'
        assert d['stage'] == 'engaged'       # DEFAULT_STAGE
        assert d['client_name'] == 'X Corp'
        assert d['position'] == 0


def test_events_cascade_on_delete(app):
    firm_id, user_id, client_id = _firm_with_client(app)
    with app.app_context():
        cf = CaseFile(firm_id=firm_id, created_by_user_id=user_id,
                      case_number='CF/2026/0002', title='Y matter', client_id=client_id)
        cf.events.append(CaseEvent(firm_id=firm_id, created_by_user_id=user_id,
                                   event_date=date(2026, 6, 1), kind='filing',
                                   title='Petition filed'))
        db.session.add(cf)
        db.session.commit()
        cf_id = cf.id

        assert CaseEvent.query.filter_by(case_file_id=cf_id).count() == 1

        db.session.delete(cf)
        db.session.commit()
        assert CaseEvent.query.filter_by(case_file_id=cf_id).count() == 0


def test_case_to_dict_includes_parties_when_requested(app):
    firm_id, user_id, client_id = _firm_with_client(app)
    with app.app_context():
        cf = CaseFile(firm_id=firm_id, created_by_user_id=user_id,
                      case_number='CF/2026/0003', title='Z matter', client_id=client_id,
                      parties=[{'name': 'Resp Co', 'role': 'respondent'}])
        db.session.add(cf)
        db.session.commit()
        d = cf.to_dict(include_parties=True)
        assert len(d['parties']) == 1
        assert d['parties'][0]['role'] == 'respondent'
