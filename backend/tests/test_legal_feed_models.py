"""Tests for the legal feed data model."""
from datetime import datetime
from app.models.models import (
    db, LegalFeedSource, LegalFeedItem, LegalFeedRun, LegalFeedSetting,
    LegalFeedPreference, LegalFeedEvent,
)


def test_create_source_and_item(db):
    src = LegalFeedSource(
        name='Indian Kanoon — Supreme Court', content_type='judgement',
        court='Supreme Court', kind='rss',
        feed_url='https://indiankanoon.org/feeds/latest/supremecourt/',
        enabled=True, weight=10,
    )
    db.session.add(src)
    db.session.commit()

    item = LegalFeedItem(
        source_id=src.id, content_type='judgement', title='ABC v. State',
        summary='A summary', source_url='https://example.com/1',
        source_name=src.name, court='Supreme Court',
        published_at=datetime(2026, 6, 17), hidden=False, dedup_key='abc123',
    )
    db.session.add(item)
    db.session.commit()

    fetched = LegalFeedItem.query.filter_by(dedup_key='abc123').first()
    assert fetched.title == 'ABC v. State'
    assert fetched.to_dict()['court'] == 'Supreme Court'
    assert src.to_dict()['feed_url'].endswith('/supremecourt/')


def test_run_and_setting(db):
    run = LegalFeedRun(started_at=datetime(2026, 6, 17), trigger='manual',
                       status='success', total_ingested=3,
                       results=[{'source_id': 1, 'fetched': 5, 'inserted': 3, 'error': None}])
    db.session.add(run)
    setting = LegalFeedSetting(id=1, ordering_mode='recency')
    db.session.add(setting)
    db.session.commit()

    assert LegalFeedRun.query.first().to_dict()['results'][0]['inserted'] == 3
    assert LegalFeedSetting.query.get(1).ordering_mode == 'recency'


def test_item_enrichment_fields_default_and_serialize(db):
    item = LegalFeedItem(
        content_type='news', title='t', source_url='u', source_name='s',
        dedup_key='k-enrich', headline='Punchy', tldr='Why it matters',
        topics=['Tax'], importance=80, image_url='http://img', embedding=[0.1, 0.2],
        embed_model='text-embedding-3-small',
    )
    db.session.add(item)
    db.session.commit()
    d = item.to_dict()
    assert d['headline'] == 'Punchy'
    assert d['topics'] == ['Tax']
    assert d['importance'] == 80
    assert d['image_url'] == 'http://img'
    assert 'embedding' not in d  # never leak vectors to the client


def test_run_has_enrichment_counters(db):
    run = LegalFeedRun(trigger='manual', status='success')
    db.session.add(run)
    db.session.commit()
    d = run.to_dict()
    assert d['enriched'] == 0
    assert d['enrich_failed'] == 0


def test_preference_roundtrip(db):
    pref = LegalFeedPreference(
        user_id=7, topic_weights={'Tax': 1.0}, courts=['Delhi HC'],
        interest_phrases=['GST input credit'], interest_embedding=[0.3, 0.4],
        embed_model='text-embedding-3-small',
    )
    db.session.add(pref)
    db.session.commit()
    d = pref.to_dict()
    assert d['user_id'] == 7
    assert d['topic_weights'] == {'Tax': 1.0}
    assert d['interest_phrases'] == ['GST input credit']
    assert 'interest_embedding' not in d  # vectors stay server-side


def test_event_roundtrip(db):
    item = LegalFeedItem(content_type='news', title='t', source_url='u',
                         source_name='s', dedup_key='ev-model')
    db.session.add(item)
    db.session.commit()
    ev = LegalFeedEvent(user_id=3, item_id=item.id, kind='click')
    db.session.add(ev)
    db.session.commit()
    assert LegalFeedEvent.query.filter_by(user_id=3, kind='click').count() == 1


def test_preference_has_behavior_columns(db):
    pref = LegalFeedPreference(user_id=9, behavior_embedding=[0.1, 0.2])
    db.session.add(pref)
    db.session.commit()
    got = LegalFeedPreference.query.filter_by(user_id=9).first()
    assert got.behavior_embedding == [0.1, 0.2]
