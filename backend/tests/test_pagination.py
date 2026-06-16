"""Tests for server-side pagination helpers."""
from app.models.models import db, Client
from app.models.auth import User
from app.utils.pagination import (
    pagination_requested,
    get_pagination_args,
    paginate_query,
    paginate_sequence,
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
)


def test_paginate_sequence_slices_and_reports_totals():
    items = list(range(0, 125))  # 125 items
    env = paginate_sequence(items, page=2, page_size=50)
    assert env['data'] == list(range(50, 100))
    assert env['total'] == 125
    assert env['page'] == 2
    assert env['page_size'] == 50
    assert env['total_pages'] == 3


def test_paginate_sequence_last_partial_page():
    items = list(range(0, 125))
    env = paginate_sequence(items, page=3, page_size=50)
    assert env['data'] == list(range(100, 125))  # 25 leftover
    assert env['total_pages'] == 3


def test_paginate_sequence_empty():
    env = paginate_sequence([], page=1, page_size=50)
    assert env['data'] == []
    assert env['total'] == 0
    assert env['total_pages'] == 0


def test_pagination_requested_and_args_defaults(app):
    with app.test_request_context('/clients'):
        assert pagination_requested() is False
    with app.test_request_context('/clients?page=1'):
        assert pagination_requested() is True
        page, size = get_pagination_args()
        assert page == 1 and size == DEFAULT_PAGE_SIZE


def test_get_pagination_args_clamps(app):
    with app.test_request_context('/clients?page=0&page_size=9999'):
        page, size = get_pagination_args()
        assert page == 1            # floored to 1
        assert size == MAX_PAGE_SIZE  # capped
    with app.test_request_context('/clients?page=4&page_size=10'):
        page, size = get_pagination_args()
        assert page == 4 and size == 10


def test_paginate_query_against_db(app):
    with app.app_context():
        db.create_all()
        user = User(supabase_id='sb-pg-1', email='pg@example.com')
        db.session.add(user)
        db.session.flush()
        for n in range(120):
            db.session.add(Client(user_id=user.id, name=f"Client {n:03d}"))
        db.session.commit()

        query = Client.query.filter_by(user_id=user.id).order_by(Client.name)
        env = paginate_query(query, page=2, page_size=50, serialize=lambda c: c.to_dict())
        assert env['total'] == 120
        assert env['total_pages'] == 3
        assert len(env['data']) == 50
        # Page 2 should start at the 51st client by name.
        assert env['data'][0]['name'] == 'Client 050'
