from datetime import datetime, timedelta
from app.models.models import LegalFeedSource, LegalFeedItem
from app.services.legal_feed.query import list_courts, query_for_you, query_feed
from app.services.legal_feed.preferences import upsert_preference
from app.services.legal_feed.events import record_event


def _item(dedup, topics, importance, embedding, court=None, age_days=0, ctype='news'):
    return LegalFeedItem(
        content_type=ctype, title=dedup, source_url='u/' + dedup, source_name='s',
        dedup_key=dedup, court=court, topics=topics, importance=importance,
        embedding=embedding, enriched_at=datetime.utcnow(),
        published_at=datetime.utcnow() - timedelta(days=age_days),
    )


def test_list_courts_from_enabled_sources(db):
    db.session.add_all([
        LegalFeedSource(name='A', content_type='judgement', court='Delhi HC',
                        kind='rss', feed_url='f1', enabled=True, weight=1),
        LegalFeedSource(name='B', content_type='judgement', court='Bombay HC',
                        kind='rss', feed_url='f2', enabled=True, weight=1),
        LegalFeedSource(name='C', content_type='judgement', court='Hidden HC',
                        kind='rss', feed_url='f3', enabled=False, weight=1),
    ])
    db.session.commit()
    assert list_courts() == ['Bombay HC', 'Delhi HC']


def test_for_you_ranks_matching_topic_highest(db):
    db.session.add_all([
        _item('m', ['Tax'], 50, [1.0, 0.0]),
        _item('o', ['IP'], 90, [0.0, 1.0]),
    ])
    db.session.commit()
    upsert_preference(10, {'Tax': 1.0}, [], ['gst'],
                      client=type('E', (), {'embed_model': 'm', 'embed': lambda self, t: [1.0, 0.0]})())
    out = query_for_you(10, 'news')
    assert out[0]['title'] == 'm'


def test_for_you_cold_start_uses_importance(db):
    db.session.add_all([
        _item('hi', ['Tax'], 95, None),
        _item('lo', ['Tax'], 5, None),
    ])
    db.session.commit()
    out = query_for_you(999, 'news')   # no preference row
    assert out[0]['title'] == 'hi'


def test_for_you_demotes_rejected(db):
    db.session.add_all([
        _item('keep', ['Tax'], 50, [1.0, 0.0]),
        _item('drop', ['Tax'], 50, [1.0, 0.0]),
    ])
    db.session.commit()
    drop = LegalFeedItem.query.filter_by(dedup_key='drop').first()
    record_event(20, drop.id, 'not_interested')
    out = query_for_you(20, 'news')
    assert out[-1]['id'] == drop.id          # rejected ranks last
    assert out[0]['title'] == 'keep'


def test_for_you_offset_paginates(db):
    for n in range(3):
        db.session.add(_item(f'p{n}', ['Tax'], 90 - n, [1.0, 0.0]))
    db.session.commit()
    first = query_for_you(21, 'news', limit=2, offset=0)
    second = query_for_you(21, 'news', limit=2, offset=2)
    assert len(first) == 2 and len(second) == 1
    assert {i['id'] for i in first}.isdisjoint({i['id'] for i in second})


def test_query_feed_demotes_ids(db):
    s = LegalFeedSource(name='S', content_type='news', kind='rss',
                        feed_url='f', enabled=True, weight=1)
    db.session.add(s)
    db.session.commit()
    from datetime import datetime
    a = LegalFeedItem(content_type='news', title='A', source_url='ua', source_name='S',
                      source_id=s.id, dedup_key='qa', published_at=datetime(2026, 6, 20))
    b = LegalFeedItem(content_type='news', title='B', source_url='ub', source_name='S',
                      source_id=s.id, dedup_key='qb', published_at=datetime(2026, 6, 21))
    db.session.add_all([a, b])
    db.session.commit()
    res = query_feed(content_type='news', demote_ids={b.id})
    assert res['data'][-1]['id'] == b.id     # demoted despite being newer
