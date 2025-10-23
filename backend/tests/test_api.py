"""Test invoice API endpoints"""
import pytest


def test_create_client(client):
    """Test creating a new client"""
    response = client.post('/api/clients', json={
        'name': 'Test Client',
        'email': 'test@example.com',
        'default_tax_rate': 18.0
    })
    assert response.status_code == 201
    data = response.get_json()
    assert data['name'] == 'Test Client'
    assert 'id' in data


def test_get_clients(client):
    """Test getting all clients"""
    response = client.get('/api/clients')
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)


def test_create_invoice(client, sample_client):
    """Test creating a new invoice"""
    response = client.post('/api/invoices', json={
        'client_id': sample_client['id'],
        'invoice_date': '2025-01-20',
        'items': [
            {
                'description': 'Legal Services',
                'quantity': 1,
                'rate': 25000,
                'amount': 25000
            }
        ]
    })
    assert response.status_code == 201
    data = response.get_json()
    assert 'invoice_number' in data
    assert data['total'] > 0


# Fixtures
@pytest.fixture
def sample_client(client):
    """Create a sample client for testing"""
    response = client.post('/api/clients', json={
        'name': 'Test Client',
        'email': 'test@example.com',
        'default_tax_rate': 18.0
    })
    return response.get_json()
