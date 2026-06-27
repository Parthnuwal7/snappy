"""Tests for the ingestion orchestration service."""
import json
from app.models.models import db, LegalFeedSource, LegalFeedItem, LegalFeedRun
from app.services.legal_feed import rss
from app.services.legal_feed.ingest import run_ingestion, enrich_backlog

SAMPLE = """<?xml version="1.0"?><rss version="2.0"><channel>
<item><title>Case One</title><link>https://ik.org/doc/1/</link>
<description>Sum 1</description><pubDate>Tue, 17 Jun 2026 10:00:00 +0530</pubDate></item>
</channel></rss>"""


def _add_source(name='SC', url='https://ik.org/feeds/sc/', enabled=True):
    s = LegalFeedSource(name=name, content_type='judgement', court='Supreme Court',
                        kind='rss', feed_url=url, enabled=enabled, weight=10)
    db.session.add(s)
    db.session.commit()
    return s


def test_ingestion_inserts_and_logs_run(db, monkeypatch):
    _add_source()
    monkeypatch.setattr(rss, 'fetch_raw', lambda url: SAMPLE)

    result = run_ingestion('manual')

    assert result['status'] == 'success'
    assert result['total_ingested'] == 1
    assert LegalFeedItem.query.count() == 1
    assert LegalFeedRun.query.count() == 1
    item = LegalFeedItem.query.first()
    assert item.source_name == 'SC'
    assert item.court == 'Supreme Court'


def test_ingestion_is_idempotent(db, monkeypatch):
    _add_source()
    monkeypatch.setattr(rss, 'fetch_raw', lambda url: SAMPLE)
    run_ingestion('manual')
    run_ingestion('manual')
    assert LegalFeedItem.query.count() == 1  # second run dedupes


def test_ingestion_partial_when_one_source_fails(db, monkeypatch):
    _add_source(name='Good', url='https://ik.org/feeds/good/')
    _add_source(name='Bad', url='https://ik.org/feeds/bad/')

    def fake_fetch(url):
        if 'bad' in url:
            raise RuntimeError('boom')
        return SAMPLE

    monkeypatch.setattr(rss, 'fetch_raw', fake_fetch)
    result = run_ingestion('scheduled')

    assert result['status'] == 'partial'
    assert result['total_ingested'] == 1
    errors = [r for r in result['results'] if r['error']]
    assert len(errors) == 1
    assert 'boom' in errors[0]['error']


def test_ingestion_disabled_source_skipped(db, monkeypatch):
    _add_source(enabled=False)
    monkeypatch.setattr(rss, 'fetch_raw', lambda url: SAMPLE)
    result = run_ingestion('manual')
    assert result['total_ingested'] == 0
    assert LegalFeedItem.query.count() == 0


class _FakeClient:
    embed_model = 'text-embedding-3-small'

    def complete(self, system, user):
        return json.dumps({'headline': 'H', 'tldr': 'T', 'topics': ['Tax'], 'importance': 70})

    def embed(self, text):
        return [0.1, 0.2]


def test_backlog_enriches_unenriched_items(db, monkeypatch):
    import app.services.legal_feed.ingest as ing
    db.session.add(LegalFeedItem(content_type='news', title='t', source_url='u',
                                 source_name='s', dedup_key='b1'))
    db.session.commit()
    monkeypatch.setattr(ing, 'get_enrichment_client', lambda: _FakeClient())

    out = enrich_backlog(limit=10)
    assert out['enriched'] == 1
    item = LegalFeedItem.query.filter_by(dedup_key='b1').first()
    assert item.enriched_at is not None
    assert item.topics == ['Tax']


def test_backlog_noop_without_client(db, monkeypatch):
    import app.services.legal_feed.ingest as ing
    db.session.add(LegalFeedItem(content_type='news', title='t', source_url='u',
                                 source_name='s', dedup_key='b2'))
    db.session.commit()
    monkeypatch.setattr(ing, 'get_enrichment_client', lambda: None)
    out = enrich_backlog()
    assert out['attempted'] == 0


def test_run_records_enrichment_counters(db, monkeypatch):
    import app.services.legal_feed.ingest as ing
    src = LegalFeedSource(name='S', content_type='news', kind='rss',
                          feed_url='http://feed', enabled=True, weight=1)
    db.session.add(src)
    db.session.commit()

    monkeypatch.setattr(ing.rss, 'fetch_raw', lambda url: 'raw')
    monkeypatch.setattr(ing.rss, 'parse_feed', lambda raw: [
        {'title': 'News A', 'summary': 's', 'source_url': 'http://x/a',
         'published_at': None, 'image_url': 'http://img/a'},
    ])
    monkeypatch.setattr(ing, 'get_enrichment_client', lambda: _FakeClient())

    result = run_ingestion('manual')
    assert result['total_ingested'] == 1
    assert result['enriched'] == 1
    item = LegalFeedItem.query.filter_by(source_url='http://x/a').first()
    assert item.image_url == 'http://img/a'
    assert item.headline == 'H'
