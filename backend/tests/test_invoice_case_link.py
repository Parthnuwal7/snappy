from app.models.models import db, Client
from app.models.auth import User


def _client_and_case(client, headers, firm_id):
    with client.application.app_context():
        c = Client(firm_id=firm_id, created_by_user_id=User.query.filter_by(
            email='owner@firm.com').first().id, name='X')
        db.session.add(c)
        db.session.commit()
        cid = c.id
    case_id = client.post('/api/v1/case-files', headers=headers,
                          json={'title': 'M', 'client_id': cid}).get_json()['id']
    return cid, case_id


def test_create_invoice_with_case_link(client, make_owner):
    headers, firm_id = make_owner()
    cid, case_id = _client_and_case(client, headers, firm_id)
    resp = client.post('/api/v1/invoices', headers=headers, json={
        'client_id': cid, 'case_file_id': case_id, 'invoice_date': '2026-06-01',
        'items': [{'description': 'Fee', 'quantity': 1, 'rate': 1000, 'amount': 1000}]})
    assert resp.status_code == 201
    assert resp.get_json()['case_file_id'] == case_id


def test_invoice_rejects_other_firms_case(client, make_owner):
    headers, firm_id = make_owner()
    headers_b, firm_b = make_owner(supabase_id='sb-b', email='b@firm.com', firm_name='B')
    cid, _ = _client_and_case(client, headers, firm_id)
    _, case_b = _client_and_case(client, headers_b, firm_b)
    resp = client.post('/api/v1/invoices', headers=headers, json={
        'client_id': cid, 'case_file_id': case_b, 'invoice_date': '2026-06-01',
        'items': [{'description': 'Fee', 'quantity': 1, 'rate': 1000, 'amount': 1000}]})
    assert resp.status_code == 404


def test_filter_invoices_by_case(client, make_owner):
    headers, firm_id = make_owner()
    cid, case_id = _client_and_case(client, headers, firm_id)
    client.post('/api/v1/invoices', headers=headers, json={
        'client_id': cid, 'case_file_id': case_id, 'invoice_date': '2026-06-01',
        'items': [{'description': 'Fee', 'quantity': 1, 'rate': 1000, 'amount': 1000}]})
    listing = client.get(f'/api/v1/invoices?case_file_id={case_id}', headers=headers).get_json()
    assert len(listing) == 1
    assert listing[0]['case_file_id'] == case_id
