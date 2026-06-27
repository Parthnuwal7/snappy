"""Tests for the legal feed read query and ingest endpoint."""
from datetime import datetime
import jwt as pyjwt
import pytest
import app.middleware.jwt_auth as jwt_auth
from app.models.models import db, LegalFeedSource, LegalFeedItem, LegalFeedSetting
from app.models.auth import User
from app.services.legal_feed.query import query_feed, get_ordering_mode

TEST_SECRET = 'test-jwt-secret'


@pytest.fixture
def auth_headers(monkeypatch):
    """Issue valid Supabase-style JWTs signed with a known test secret."""
    monkeypatch.setenv('SUPABASE_JWT_SECRET', TEST_SECRET)
    jwt_auth._jwt_secret_cache = None

    def _headers(supabase_id):
        token = pyjwt.encode(
            {'sub': supabase_id, 'aud': 'authenticated', 'email': f'{supabase_id}@t.test'},
            TEST_SECRET, algorithm='HS256')
        return {'Authorization': f'Bearer {token}'}

    yield _headers
    jwt_auth._jwt_secret_cache = None


def make_user(supabase_id):
    u = User(supabase_id=supabase_id, email=f'{supabase_id}@t.test')
    db.session.add(u)
    db.session.commit()
    return u


def _src(name, court, weight):
    s = LegalFeedSource(name=name, content_type='judgement', court=court,
                        kind='rss', feed_url=f'https://x/{name}', enabled=True, weight=weight)
    db.session.add(s); db.session.commit(); return s


def _item(src, title, ct='news', court='Supreme Court', when=None, hidden=False, key=None):
    db.session.add(LegalFeedItem(
        source_id=src.id, content_type=ct, title=title, summary='s',
        source_url=f'https://x/{title}', source_name=src.name, court=court,
        published_at=when or datetime(2026, 6, 1), hidden=hidden, dedup_key=key or title))
    db.session.commit()


def test_query_filters_by_type_and_court(db):
    s = _src('SC', 'Supreme Court', 10)
    _item(s, 'J1', ct='judgement', court='Supreme Court')
    _item(s, 'N1', ct='news', court=None)
    _item(s, 'J2', ct='judgement', court='Delhi HC')

    res = query_feed(content_type='judgement')
    assert res['total'] == 2
    res2 = query_feed(content_type='judgement', court='Delhi HC')
    assert res2['total'] == 1
    assert res2['data'][0]['title'] == 'J2'


def test_query_excludes_hidden(db):
    s = _src('SC', 'Supreme Court', 10)
    _item(s, 'Visible')
    _item(s, 'Gone', hidden=True, key='gone')
    res = query_feed()
    titles = [d['title'] for d in res['data']]
    assert 'Visible' in titles and 'Gone' not in titles


def test_query_recency_ordering(db):
    s = _src('SC', 'Supreme Court', 10)
    _item(s, 'Older', when=datetime(2026, 1, 1), key='o')
    _item(s, 'Newer', when=datetime(2026, 6, 1), key='n')
    res = query_feed()
    assert res['data'][0]['title'] == 'Newer'


def test_query_weighted_ordering(db):
    high = _src('HighWeight', 'Supreme Court', 100)
    low = _src('LowWeight', 'Delhi HC', 1)
    _item(low, 'FromLow', when=datetime(2026, 6, 2), key='low')
    _item(high, 'FromHigh', when=datetime(2026, 1, 1), key='high')
    db.session.add(LegalFeedSetting(id=1, ordering_mode='weighted')); db.session.commit()

    res = query_feed()
    assert get_ordering_mode() == 'weighted'
    assert res['data'][0]['title'] == 'FromHigh'  # weight beats recency


def test_ingest_endpoint_requires_secret(client, monkeypatch):
    monkeypatch.setenv('LEGAL_FEED_INGEST_SECRET', 'topsecret')
    # missing header
    assert client.post('/api/v1/legal-feed/ingest').status_code == 401
    # wrong header
    assert client.post('/api/v1/legal-feed/ingest',
                       headers={'X-Ingest-Secret': 'nope'}).status_code == 401
    # correct header
    ok = client.post('/api/v1/legal-feed/ingest',
                     headers={'X-Ingest-Secret': 'topsecret'})
    assert ok.status_code == 200
    assert ok.get_json()['trigger'] == 'scheduled'


def test_courts_endpoint(client, db, auth_headers):
    make_user('sb-1')
    db.session.add(LegalFeedSource(name='A', content_type='judgement', court='Delhi HC',
                                   kind='rss', feed_url='f1', enabled=True, weight=1))
    db.session.commit()
    resp = client.get('/api/v1/legal-feed/courts', headers=auth_headers('sb-1'))
    assert resp.status_code == 200
    assert resp.get_json()['courts'] == ['Delhi HC']


def test_put_then_get_preferences(client, db, auth_headers):
    make_user('sb-2')
    put = client.put('/api/v1/legal-feed/preferences', headers=auth_headers('sb-2'),
                     json={'topic_weights': {'Tax': 1.0}, 'courts': ['Delhi HC'],
                           'interest_phrases': []})
    assert put.status_code == 200
    got = client.get('/api/v1/legal-feed/preferences', headers=auth_headers('sb-2'))
    assert got.get_json()['topic_weights'] == {'Tax': 1.0}
    assert got.get_json()['courts'] == ['Delhi HC']


def test_for_you_requires_auth(client):
    assert client.get('/api/v1/legal-feed/for-you').status_code == 401


def test_post_event_click(client, db, auth_headers):
    u = make_user('sb-ev1')
    item = LegalFeedItem(content_type='news', title='t', source_url='u',
                         source_name='s', dedup_key='api-ev1', embedding=[1.0, 0.0])
    db.session.add(item)
    db.session.commit()
    r = client.post('/api/v1/legal-feed/events', headers=auth_headers('sb-ev1'),
                    json={'item_id': item.id, 'kind': 'click'})
    assert r.status_code == 200 and r.get_json()['ok'] is True
    from app.models.models import LegalFeedEvent
    assert LegalFeedEvent.query.filter_by(user_id=u.id, kind='click').count() == 1


def test_post_event_invalid_kind(client, db, auth_headers):
    make_user('sb-ev2')
    item = LegalFeedItem(content_type='news', title='t', source_url='u',
                         source_name='s', dedup_key='api-ev2')
    db.session.add(item)
    db.session.commit()
    r = client.post('/api/v1/legal-feed/events', headers=auth_headers('sb-ev2'),
                    json={'item_id': item.id, 'kind': 'bogus'})
    assert r.status_code == 400


def test_event_requires_auth(client):
    assert client.post('/api/v1/legal-feed/events',
                       json={'item_id': 1, 'kind': 'click'}).status_code == 401
