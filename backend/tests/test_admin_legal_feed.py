"""Tests for the admin Legal Feed endpoints."""
import base64
from app.models.models import db, LegalFeedSource, LegalFeedItem


def _h(monkeypatch):
    monkeypatch.setenv('ADMIN_PASSWORD', 'pw')
    raw = base64.b64encode(b'admin:pw').decode()
    return {'Authorization': f'Basic {raw}'}


def test_sources_crud_and_seed(client, monkeypatch):
    h = _h(monkeypatch)
    # seed
    seeded = client.post('/admin/api/legal-feed/seed', headers=h)
    assert seeded.status_code == 200
    assert seeded.get_json()['inserted'] == 2  # news-only product
    # list
    listing = client.get('/admin/api/legal-feed/sources', headers=h)
    assert len(listing.get_json()['sources']) == 2
    # create
    created = client.post('/admin/api/legal-feed/sources', headers=h, json={
        'name': 'The Leaflet', 'content_type': 'news', 'court': None,
        'feed_url': 'https://theleaflet.in/feed/', 'weight': 2})
    assert created.status_code == 201
    sid = created.get_json()['id']
    # disable it
    upd = client.put(f'/admin/api/legal-feed/sources/{sid}', headers=h,
                     json={'enabled': False})
    assert upd.get_json()['enabled'] is False


def test_settings_validation(client, monkeypatch):
    h = _h(monkeypatch)
    assert client.get('/admin/api/legal-feed/settings', headers=h).get_json()['ordering_mode'] == 'recency'
    ok = client.put('/admin/api/legal-feed/settings', headers=h, json={'ordering_mode': 'weighted'})
    assert ok.get_json()['ordering_mode'] == 'weighted'
    bad = client.put('/admin/api/legal-feed/settings', headers=h, json={'ordering_mode': 'bogus'})
    assert bad.status_code == 400


def test_item_moderation(client, monkeypatch):
    h = _h(monkeypatch)
    src = LegalFeedSource(name='SC', content_type='judgement', court='SC',
                          kind='rss', feed_url='https://x/sc', enabled=True, weight=1)
    db.session.add(src); db.session.commit()
    it = LegalFeedItem(source_id=src.id, content_type='judgement', title='T',
                       summary='s', source_url='https://x/1', source_name='SC',
                       court='SC', hidden=False, dedup_key='k1')
    db.session.add(it); db.session.commit()

    resp = client.post(f'/admin/api/legal-feed/items/{it.id}/hide', headers=h,
                       json={'hidden': True})
    assert resp.status_code == 200
    assert resp.get_json()['hidden'] is True


def test_endpoints_reject_without_auth(client, monkeypatch):
    monkeypatch.setenv('ADMIN_PASSWORD', 'pw')
    assert client.get('/admin/api/legal-feed/runs').status_code == 401


def test_sources_include_counts(client, db, monkeypatch):
    from datetime import datetime
    h = _h(monkeypatch)
    src = LegalFeedSource(name='S', content_type='news', kind='rss',
                          feed_url='f', enabled=True, weight=1)
    db.session.add(src)
    db.session.commit()
    db.session.add(LegalFeedItem(content_type='news', title='t', source_url='u',
                                 source_name='S', source_id=src.id, dedup_key='c1',
                                 ingested_at=datetime.utcnow()))
    db.session.commit()
    resp = client.get('/admin/api/legal-feed/sources', headers=h)
    row = [s for s in resp.get_json()['sources'] if s['id'] == src.id][0]
    assert row['count_24h'] == 1


def test_backfill_route(client, db, monkeypatch):
    import app.api.admin as admin_mod
    h = _h(monkeypatch)
    monkeypatch.setattr(admin_mod, 'enrich_backlog',
                        lambda limit=100: {'attempted': 2, 'enriched': 2, 'failed': 0})
    resp = client.post('/admin/api/legal-feed/backfill', headers=h, json={'limit': 5})
    assert resp.status_code == 200
    assert resp.get_json()['enriched'] == 2


def test_recompute_behavior_route(client, db, monkeypatch):
    from app.models.models import LegalFeedPreference
    h = _h(monkeypatch)
    db.session.add(LegalFeedPreference(user_id=1))
    db.session.add(LegalFeedPreference(user_id=2))
    db.session.commit()
    resp = client.post('/admin/api/legal-feed/recompute-behavior', headers=h)
    assert resp.status_code == 200
    assert resp.get_json()['recomputed'] == 2
