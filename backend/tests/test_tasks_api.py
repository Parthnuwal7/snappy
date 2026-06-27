def test_task_crud_and_filters(client, make_owner):
    headers, _ = make_owner()
    a = client.post('/api/v1/tasks', headers=headers,
                    json={'title': 'File reply', 'due_date': '2026-07-01', 'priority': 'high'}).get_json()
    assert a['done'] is False and a['priority'] == 'high'
    client.post('/api/v1/tasks', headers=headers, json={'title': 'Call', 'due_date': '2026-07-10'})

    # range filter
    win = client.get('/api/v1/tasks?from=2026-07-01&to=2026-07-05', headers=headers).get_json()
    assert [t['title'] for t in win] == ['File reply']

    # mark done + status filter
    client.patch(f"/api/v1/tasks/{a['id']}", headers=headers, json={'done': True})
    assert len(client.get('/api/v1/tasks?status=open', headers=headers).get_json()) == 1
    assert len(client.get('/api/v1/tasks?status=done', headers=headers).get_json()) == 1

    assert client.delete(f"/api/v1/tasks/{a['id']}", headers=headers).status_code == 200


def test_task_requires_title(client, make_owner):
    headers, _ = make_owner()
    assert client.post('/api/v1/tasks', headers=headers, json={'due_date': '2026-07-01'}).status_code == 400


def test_tasks_firm_isolation(client, make_owner):
    headers, _ = make_owner()
    headers_b, _ = make_owner(supabase_id='sb-b', email='b@firm.com', firm_name='B')
    t = client.post('/api/v1/tasks', headers=headers, json={'title': 'x', 'due_date': '2026-07-01'}).get_json()
    assert client.patch(f"/api/v1/tasks/{t['id']}", headers=headers_b, json={'done': True}).status_code == 404
    assert client.get('/api/v1/tasks', headers=headers_b).get_json() == []
