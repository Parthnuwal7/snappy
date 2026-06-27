"""Seed the v1 legal feed source registry. Idempotent (keyed on feed_url)."""
from app.models.models import db, LegalFeedSource

IK = 'https://indiankanoon.org/feeds/latest/'

# News-only product. Judgement (Indian Kanoon) sources were retired on
# 2026-06-26 — see _disable_non_news() and migrations/020_news_only_feed.sql.
V1_SOURCES = [
    # News — feed URLs verified to return valid RSS (200) on 2026-06-18.
    ('LiveLaw',     'news', None, 'https://www.livelaw.in/google_feeds.xml', 4),
    ('Bar & Bench', 'news', None, 'https://prod-qt-images.s3.amazonaws.com/production/barandbench/feed.xml', 4),
]


def seed_sources() -> int:
    """Ensure the v1 sources exist with correct feed URLs.

    Matched by ``name`` (which is unique within V1_SOURCES). Missing sources are
    inserted; an existing source whose ``feed_url`` has drifted from the canonical
    value is healed in place (so re-running after a URL correction fixes live data
    without creating duplicates). Returns the number of rows inserted or updated.
    """
    changed = 0
    for name, content_type, court, feed_url, weight in V1_SOURCES:
        existing = LegalFeedSource.query.filter_by(name=name).first()
        if existing is None:
            db.session.add(LegalFeedSource(
                name=name, content_type=content_type, court=court,
                kind='rss', feed_url=feed_url, enabled=True, weight=weight,
            ))
            changed += 1
        elif existing.feed_url != feed_url:
            existing.feed_url = feed_url
            changed += 1
    changed += _disable_non_news()
    db.session.commit()
    return changed


def _disable_non_news() -> int:
    """News-only product: switch off any still-enabled non-news source so
    ingestion stops pulling judgements. Returns the number disabled."""
    return (LegalFeedSource.query
            .filter(LegalFeedSource.content_type != 'news',
                    LegalFeedSource.enabled.is_(True))
            .update({'enabled': False}, synchronize_session=False))


if __name__ == '__main__':
    # One-off operational seeding: `cd backend && python -m app.services.legal_feed.seed`
    from app.main import create_app
    app = create_app()
    with app.app_context():
        n = seed_sources()
        print(f'Seeded {n} new legal feed source(s).')
