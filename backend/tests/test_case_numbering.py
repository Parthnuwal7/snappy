from datetime import date

from app.models.models import db, Client
from app.models.auth import User
from app.models.case import CaseFile
from app.services.firm_service import provision_firm_for_user
from app.services.case_service import generate_case_number


def _seed(app):
    with app.app_context():
        user = User(supabase_id='sb-num', email='n@firm.com')
        db.session.add(user)
        db.session.commit()
        firm = provision_firm_for_user(user, 'Acme')
        client = Client(firm_id=firm.id, created_by_user_id=user.id, name='X')
        db.session.add(client)
        db.session.commit()
        return firm.id, user.id, client.id


def test_first_case_number_for_year(app):
    firm_id, _, _ = _seed(app)
    with app.app_context():
        assert generate_case_number(firm_id) == f"CF/{date.today().year}/0001"


def test_sequence_increments_per_firm(app):
    firm_id, user_id, client_id = _seed(app)
    with app.app_context():
        year = date.today().year
        db.session.add(CaseFile(firm_id=firm_id, created_by_user_id=user_id,
                                case_number=f"CF/{year}/0001", title='A', client_id=client_id))
        db.session.commit()
        assert generate_case_number(firm_id) == f"CF/{year}/0002"


def test_numbering_is_isolated_between_firms(app):
    firm_a, user_a, client_a = _seed(app)
    with app.app_context():
        year = date.today().year
        db.session.add(CaseFile(firm_id=firm_a, created_by_user_id=user_a,
                                case_number=f"CF/{year}/0001", title='A', client_id=client_a))
        db.session.commit()
        userb = User(supabase_id='sb-b', email='b@firm.com')
        db.session.add(userb)
        db.session.commit()
        firm_b = provision_firm_for_user(userb, 'Beta')
        assert generate_case_number(firm_b.id) == f"CF/{year}/0001"
