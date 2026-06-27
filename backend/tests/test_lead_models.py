from app.models.models import db
from app.models.lead import Lead, LEAD_STATUSES, DEFAULT_LEAD_STATUS


def test_lead_defaults_and_to_dict(app):
    with app.app_context():
        lead = Lead(firm_id=1, created_by_user_id=1,
                    contact_name='Mehta', phone='99', email='m@x.com',
                    matter_summary='Property dispute', intake_notes='Heard him out')
        db.session.add(lead); db.session.commit()
        d = lead.to_dict()
        assert d['contact_name'] == 'Mehta'
        assert d['status'] == DEFAULT_LEAD_STATUS == 'open'
        assert d['converted_case_file_id'] is None
        assert d['intake_notes'] == 'Heard him out'
        assert LEAD_STATUSES == {'open', 'accepted', 'declined'}
