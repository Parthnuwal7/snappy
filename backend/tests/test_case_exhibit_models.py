from app.case.exhibits import (
    EXHIBIT_STATUSES, EXHIBIT_STATUS_KEYS, DEFAULT_EXHIBIT_STATUS,
    EXHIBIT_PARTIES, is_valid_exhibit_status,
)
from app.models.models import db, Client
from app.models.case import CaseFile, CaseDocument


def test_exhibit_catalog():
    assert DEFAULT_EXHIBIT_STATUS == "marked"
    assert {s["key"] for s in EXHIBIT_STATUSES} == EXHIBIT_STATUS_KEYS
    assert {"marked", "admitted", "objected", "denied"} == EXHIBIT_STATUS_KEYS
    assert is_valid_exhibit_status("admitted")
    assert not is_valid_exhibit_status("teleported")
    assert all("label" in p for p in EXHIBIT_PARTIES)


def _case(app):
    with app.app_context():
        c = Client(firm_id=1, created_by_user_id=1, name='X')
        db.session.add(c); db.session.flush()
        cf = CaseFile(firm_id=1, created_by_user_id=1, case_number='CF/2026/0001',
                      title='M', client_id=c.id)
        db.session.add(cf); db.session.commit()
        return cf.id


def test_exhibit_is_a_case_document(app):
    cf_id = _case(app)
    with app.app_context():
        # Exhibit-register rows live in case_documents with is_exhibit=True (no file).
        ex = CaseDocument(firm_id=1, case_file_id=cf_id, uploaded_by_user_id=1, is_exhibit=True,
                          doc_type='evidence', title='Sale deed', description='Sale deed',
                          exhibit_mark='Ex. P-1', party='petitioner', exhibit_status='marked')
        db.session.add(ex); db.session.commit()
        d = ex.exhibit_to_dict()
        assert d['exhibit_mark'] == 'Ex. P-1'
        assert d['status'] == 'marked'
        assert d['party'] == 'petitioner'
        assert d['document_id'] is None and d['hearing_event_id'] is None
        assert ex.storage_path is None  # fileless exhibit allowed
