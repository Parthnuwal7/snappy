def test_lead_crud_and_decline(client, make_owner):
    headers, firm_id = make_owner()
    created = client.post('/api/v1/leads', headers=headers, json={
        'contact_name': 'Mehta', 'phone': '99', 'email': 'm@x.com',
        'matter_summary': 'Property dispute', 'intake_notes': 'Heard the facts'}).get_json()
    assert created['status'] == 'open'
    lid = created['id']

    assert len(client.get('/api/v1/leads', headers=headers).get_json()) == 1
    assert client.get(f'/api/v1/leads/{lid}', headers=headers).get_json()['contact_name'] == 'Mehta'

    declined = client.patch(f'/api/v1/leads/{lid}', headers=headers,
                            json={'status': 'declined'}).get_json()
    assert declined['status'] == 'declined'
    assert declined['decided_at'] is not None

    assert client.delete(f'/api/v1/leads/{lid}', headers=headers).status_code == 200
    assert client.get('/api/v1/leads', headers=headers).get_json() == []


def test_lead_requires_contact_name(client, make_owner):
    headers, _ = make_owner()
    assert client.post('/api/v1/leads', headers=headers, json={'phone': '1'}).status_code == 400


def test_lead_status_filter(client, make_owner):
    headers, _ = make_owner()
    a = client.post('/api/v1/leads', headers=headers, json={'contact_name': 'A'}).get_json()
    client.post('/api/v1/leads', headers=headers, json={'contact_name': 'B'})
    client.patch(f"/api/v1/leads/{a['id']}", headers=headers, json={'status': 'declined'})
    assert len(client.get('/api/v1/leads?status=open', headers=headers).get_json()) == 1


def test_lead_accept_via_patch_rejected(client, make_owner):
    headers, _ = make_owner()
    lid = client.post('/api/v1/leads', headers=headers, json={'contact_name': 'A'}).get_json()['id']
    assert client.patch(f'/api/v1/leads/{lid}', headers=headers,
                        json={'status': 'accepted'}).status_code == 400


def test_leads_firm_isolation(client, make_owner):
    headers, _ = make_owner()
    headers_b, _ = make_owner(supabase_id='sb-b', email='b@firm.com', firm_name='B')
    lid = client.post('/api/v1/leads', headers=headers, json={'contact_name': 'A'}).get_json()['id']
    assert client.get(f'/api/v1/leads/{lid}', headers=headers_b).status_code == 404
    assert client.patch(f'/api/v1/leads/{lid}', headers=headers_b, json={'phone': '1'}).status_code == 404
    assert client.get('/api/v1/leads', headers=headers_b).get_json() == []
