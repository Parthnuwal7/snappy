"""Test invoice/client API endpoints end-to-end (firm-scoped, authenticated)."""
import pytest


def test_create_client(client, make_owner):
    headers, _ = make_owner()
    response = client.post('/api/v1/clients', headers=headers, json={
        'name': 'Test Client',
        'email': 'test@example.com',
        'default_tax_rate': 18.0
    })
    assert response.status_code == 201
    data = response.get_json()
    assert data['name'] == 'Test Client'
    assert 'id' in data


def test_get_clients(client, make_owner):
    headers, _ = make_owner()
    response = client.get('/api/v1/clients', headers=headers)
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)


def test_create_invoice(client, make_owner):
    headers, _ = make_owner()
    created = client.post('/api/v1/clients', headers=headers, json={
        'name': 'Test Client', 'email': 'test@example.com', 'default_tax_rate': 18.0,
    }).get_json()

    response = client.post('/api/v1/invoices', headers=headers, json={
        'client_id': created['id'],
        'invoice_date': '2025-01-20',
        'items': [
            {'description': 'Legal Services', 'quantity': 1, 'rate': 25000, 'amount': 25000}
        ]
    })
    assert response.status_code == 201
    data = response.get_json()
    assert 'invoice_number' in data
    assert data['total'] > 0
