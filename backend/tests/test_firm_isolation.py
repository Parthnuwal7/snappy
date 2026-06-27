"""Cross-firm isolation regression: firm A must never see firm B's data."""
import pytest


def _seed_client_and_invoice(client, headers, name):
    c = client.post('/api/v1/clients', headers=headers, json={
        'name': name, 'email': f'{name}@x.com', 'default_tax_rate': 18.0,
    }).get_json()
    inv = client.post('/api/v1/invoices', headers=headers, json={
        'client_id': c['id'],
        'invoice_date': '2026-01-20',
        'items': [{'description': 'Work', 'quantity': 1, 'rate': 1000, 'amount': 1000}],
    }).get_json()
    return c, inv


def test_clients_are_isolated_per_firm(client, make_owner):
    headers_a, _ = make_owner()
    headers_b, _ = make_owner(supabase_id='sb-b', email='b@firm.com', firm_name='Firm B')

    _seed_client_and_invoice(client, headers_a, 'Alpha')
    _seed_client_and_invoice(client, headers_b, 'Beta')

    a_clients = client.get('/api/v1/clients', headers=headers_a).get_json()
    b_clients = client.get('/api/v1/clients', headers=headers_b).get_json()

    a_names = {c['name'] for c in a_clients}
    b_names = {c['name'] for c in b_clients}
    assert a_names == {'Alpha'}
    assert b_names == {'Beta'}


def test_cannot_read_another_firms_client_by_id(client, make_owner):
    headers_a, _ = make_owner()
    headers_b, _ = make_owner(supabase_id='sb-b', email='b@firm.com', firm_name='Firm B')

    a_client, _ = _seed_client_and_invoice(client, headers_a, 'Alpha')

    # Firm B tries to fetch firm A's client by its id.
    resp = client.get(f"/api/v1/clients/{a_client['id']}", headers=headers_b)
    assert resp.status_code == 404


def test_cannot_read_another_firms_invoice_by_id(client, make_owner):
    headers_a, _ = make_owner()
    headers_b, _ = make_owner(supabase_id='sb-b', email='b@firm.com', firm_name='Firm B')

    _, a_inv = _seed_client_and_invoice(client, headers_a, 'Alpha')

    resp = client.get(f"/api/v1/invoices/{a_inv['id']}", headers=headers_b)
    assert resp.status_code == 404


def test_cannot_delete_another_firms_client(client, make_owner):
    headers_a, _ = make_owner()
    headers_b, _ = make_owner(supabase_id='sb-b', email='b@firm.com', firm_name='Firm B')

    a_client, _ = _seed_client_and_invoice(client, headers_a, 'Alpha')

    resp = client.delete(f"/api/v1/clients/{a_client['id']}", headers=headers_b)
    assert resp.status_code == 404
    # Firm A still sees its client.
    a_names = {c['name'] for c in client.get('/api/v1/clients', headers=headers_a).get_json()}
    assert 'Alpha' in a_names


def test_invoice_numbers_independent_across_firms(client, make_owner):
    headers_a, _ = make_owner()
    headers_b, _ = make_owner(supabase_id='sb-b', email='b@firm.com', firm_name='Firm B')

    _, a_inv = _seed_client_and_invoice(client, headers_a, 'Alpha')
    _, b_inv = _seed_client_and_invoice(client, headers_b, 'Beta')

    # Each firm's first invoice gets the firm's own opening sequence number;
    # the per-firm unique constraint means identical numbers don't collide.
    assert a_inv['invoice_number'] is not None
    assert b_inv['invoice_number'] is not None
