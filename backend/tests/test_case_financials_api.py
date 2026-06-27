from app.models.models import db, Client
from app.models.auth import User


def _cid(client, firm_id):
    with client.application.app_context():
        c = Client(firm_id=firm_id, created_by_user_id=User.query.filter_by(
            email='owner@firm.com').first().id, name='X')
        db.session.add(c); db.session.commit()
        return c.id


def _case(client, headers, firm_id, fee=None):
    cid = _cid(client, firm_id)
    return client.post('/api/v1/case-files', headers=headers,
                       json={'title': 'M', 'client_id': cid, 'agreed_fee': fee}).get_json()['id'], cid


def test_expense_crud(client, make_owner):
    headers, firm_id = make_owner()
    case_id, _ = _case(client, headers, firm_id)
    e = client.post(f'/api/v1/case-files/{case_id}/expenses', headers=headers,
                    json={'expense_date': '2026-06-01', 'description': 'Court fee',
                          'category': 'court_fee', 'amount': 1500}).get_json()
    assert e['amount'] == 1500.0
    lst = client.get(f'/api/v1/case-files/{case_id}/expenses', headers=headers).get_json()
    assert len(lst) == 1
    client.patch(f"/api/v1/case-expenses/{e['id']}", headers=headers, json={'amount': 2000})
    assert client.get(f'/api/v1/case-files/{case_id}/expenses', headers=headers).get_json()[0]['amount'] == 2000.0
    assert client.delete(f"/api/v1/case-expenses/{e['id']}", headers=headers).status_code == 200


def test_financials_summary(client, make_owner):
    headers, firm_id = make_owner()
    case_id, cid = _case(client, headers, firm_id, fee=50000)
    client.post(f'/api/v1/case-files/{case_id}/expenses', headers=headers,
                json={'expense_date': '2026-06-01', 'description': 'fee', 'category': 'court_fee', 'amount': 1500})
    inv = client.post('/api/v1/invoices', headers=headers, json={
        'client_id': cid, 'case_file_id': case_id, 'invoice_date': '2026-06-01', 'tax_rate': 0,
        'items': [{'description': 'x', 'quantity': 1, 'rate': 25000, 'amount': 25000}]}).get_json()
    client.put(f"/api/v1/invoices/{inv['id']}", headers=headers, json={'status': 'paid'})
    client.post('/api/v1/invoices', headers=headers, json={
        'client_id': cid, 'case_file_id': case_id, 'invoice_date': '2026-06-02', 'tax_rate': 0,
        'items': [{'description': 'y', 'quantity': 1, 'rate': 16000, 'amount': 16000}]})
    fin = client.get(f'/api/v1/case-files/{case_id}/financials', headers=headers).get_json()
    assert fin['agreed_fee'] == 50000.0
    assert fin['total_expenses'] == 1500.0
    assert fin['total_invoiced'] == 41000.0
    assert fin['total_paid'] == 25000.0
    assert fin['outstanding'] == 16000.0


def test_expenses_isolated(client, make_owner):
    headers, firm_id = make_owner()
    headers_b, _ = make_owner(supabase_id='sb-b', email='b@firm.com', firm_name='B')
    case_id, _ = _case(client, headers, firm_id)
    e = client.post(f'/api/v1/case-files/{case_id}/expenses', headers=headers,
                    json={'expense_date': '2026-06-01', 'description': 'x', 'amount': 100}).get_json()
    assert client.patch(f"/api/v1/case-expenses/{e['id']}", headers=headers_b, json={'amount': 1}).status_code == 404
    assert client.get(f'/api/v1/case-files/{case_id}/financials', headers=headers_b).status_code == 404
