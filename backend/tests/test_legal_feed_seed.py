"""Tests for v1 source registry seeding."""
from app.models.models import LegalFeedSource
from app.services.legal_feed.seed import seed_sources


def test_seed_inserts_news_sources_only(db):
    inserted = seed_sources()
    assert inserted == 2
    assert LegalFeedSource.query.count() == 2
    # News-only product: no judgement sources are seeded.
    assert LegalFeedSource.query.filter_by(content_type='judgement').count() == 0
    assert LegalFeedSource.query.filter_by(content_type='news').count() == 2


def test_seed_is_idempotent(db):
    seed_sources()
    second = seed_sources()
    assert second == 0
    assert LegalFeedSource.query.count() == 2


def test_seed_disables_existing_judgement_sources(db):
    # A judgement source seeded under the old product is switched off on re-seed.
    db.session.add(LegalFeedSource(
        name='Indian Kanoon — Supreme Court', content_type='judgement', court='Supreme Court',
        kind='rss', feed_url='https://indiankanoon.org/feeds/latest/supremecourt/', enabled=True, weight=10))
    db.session.commit()

    seed_sources()

    ik = LegalFeedSource.query.filter_by(name='Indian Kanoon — Supreme Court').first()
    assert ik.enabled is False  # judgement source disabled, not deleted


def test_seed_heals_drifted_feed_url(db):
    # Simulate a source seeded earlier with a now-wrong URL.
    db.session.add(LegalFeedSource(
        name='LiveLaw', content_type='news', court=None, kind='rss',
        feed_url='https://www.livelaw.in/rss/', enabled=True, weight=4))
    db.session.commit()

    changed = seed_sources()

    # The drifted LiveLaw row is updated in place (no duplicate), and Bar & Bench inserted.
    assert LegalFeedSource.query.filter_by(name='LiveLaw').count() == 1
    livelaw = LegalFeedSource.query.filter_by(name='LiveLaw').first()
    assert livelaw.feed_url == 'https://www.livelaw.in/google_feeds.xml'
    assert LegalFeedSource.query.count() == 2
    assert changed == 2  # 1 insert (Bar & Bench) + 1 heal (LiveLaw)
