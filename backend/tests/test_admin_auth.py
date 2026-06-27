"""Tests for env-var-based admin authentication."""
import base64


def _basic(user, pw):
    raw = base64.b64encode(f'{user}:{pw}'.encode()).decode()
    return {'Authorization': f'Basic {raw}'}


def test_admin_refuses_when_password_unset(client, monkeypatch):
    monkeypatch.delenv('ADMIN_PASSWORD', raising=False)
    resp = client.get('/admin/')
    assert resp.status_code == 503


def test_admin_requires_correct_credentials(client, monkeypatch):
    monkeypatch.setenv('ADMIN_PASSWORD', 'secretpw')
    assert client.get('/admin/').status_code == 401
    assert client.get('/admin/', headers=_basic('admin', 'wrong')).status_code == 401
    assert client.get('/admin/', headers=_basic('admin', 'secretpw')).status_code == 200
