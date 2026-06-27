from app.models.models import db, LegalFeedItem, LegalFeedPreference, LegalFeedEvent
from app.services.legal_feed.events import (
    record_event, get_rejected_item_ids, event_count, recompute_behavior_embedding,
)


def _news(key, embedding=None):
    it = LegalFeedItem(content_type='news', title='t', source_url='u/' + key,
                       source_name='s', dedup_key=key, embedding=embedding)
    db.session.add(it)
    db.session.commit()
    return it


def test_click_records_event_and_sets_vector(db):
    it = _news('e1', [1.0, 0.0])
    assert record_event(5, it.id, 'click') is True
    assert event_count(5) == 1
    assert LegalFeedPreference.query.filter_by(user_id=5).first().behavior_embedding == [1.0, 0.0]


def test_not_interested_is_collected_for_demotion(db):
    it = _news('e2', [1.0, 0.0])
    record_event(6, it.id, 'not_interested')
    assert it.id in get_rejected_item_ids(6)
    # single rejection below threshold -> no learned vector yet
    assert LegalFeedPreference.query.filter_by(user_id=6).first().behavior_embedding is None


def test_invalid_kind_and_missing_item(db):
    it = _news('e3')
    assert record_event(7, it.id, 'bogus') is False
    assert record_event(7, 999999, 'click') is False


def test_recompute_builds_from_clicks(db):
    it = _news('e4', [1.0, 0.0])
    record_event(8, it.id, 'click')
    assert recompute_behavior_embedding(8) is True
    assert LegalFeedPreference.query.filter_by(user_id=8).first().behavior_embedding == [1.0, 0.0]
