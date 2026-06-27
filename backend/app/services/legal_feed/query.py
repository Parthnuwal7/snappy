"""Read-side query logic for the legal feed (testable without HTTP/JWT)."""
from datetime import datetime, timedelta

from sqlalchemy import func, case

from app.models.models import db, LegalFeedItem, LegalFeedSource, LegalFeedSetting
from app.utils.pagination import paginate_query
from app.services.legal_feed.preferences import get_preference
from app.services.legal_feed.similarity import rank_by_similarity
from app.services.legal_feed import behavior as bx
from app.services.legal_feed.events import get_rejected_item_ids, event_count


def get_ordering_mode() -> str:
    setting = LegalFeedSetting.query.get(1)
    if setting is None:
        setting = LegalFeedSetting(id=1, ordering_mode='recency')
        db.session.add(setting)
        db.session.commit()
    return setting.ordering_mode


def query_feed(content_type=None, court=None, page=1, page_size=50, demote_ids=None) -> dict:
    # News-only product: default to news so judgements never surface unless a
    # caller explicitly asks (e.g. admin tooling). See 020_news_only_feed.sql.
    content_type = content_type or 'news'
    q = LegalFeedItem.query.filter_by(hidden=False)
    q = q.filter_by(content_type=content_type)
    if court:
        q = q.filter_by(court=court)

    recency = func.coalesce(LegalFeedItem.published_at, LegalFeedItem.ingested_at).desc()
    order = []
    if demote_ids:
        order.append(case((LegalFeedItem.id.in_(demote_ids), 1), else_=0))

    if get_ordering_mode() == 'weighted':
        q = q.join(LegalFeedSource, LegalFeedItem.source_id == LegalFeedSource.id)
        q = q.order_by(*order, LegalFeedSource.weight.desc(), recency)
    else:
        q = q.order_by(*order, recency)

    return paginate_query(q, page, page_size, lambda i: i.to_dict())


def list_courts() -> list:
    rows = (db.session.query(LegalFeedSource.court)
            .filter(LegalFeedSource.enabled.is_(True),
                    LegalFeedSource.court.isnot(None))
            .distinct().all())
    return sorted({r[0] for r in rows if r[0]})


def query_for_you(user_id, content_type=None, limit=10, offset=0,
                  window_days=14, now=None) -> list:
    now = now or datetime.utcnow()
    cutoff = now - timedelta(days=window_days)
    pref = get_preference(user_id)

    content_type = content_type or 'news'
    q = LegalFeedItem.query.filter_by(hidden=False)
    q = q.filter_by(content_type=content_type)
    q = q.filter(func.coalesce(LegalFeedItem.published_at, LegalFeedItem.ingested_at) >= cutoff)

    candidates = q.all()

    interest = None
    if pref is not None:
        interest = bx.blend_interest(pref.interest_embedding,
                                     pref.behavior_embedding, event_count(user_id))
        topics = set((pref.topic_weights or {}).keys())
        courts = set(pref.courts or [])
        if topics or courts:
            matched = [it for it in candidates
                       if (topics & set(it.topics or [])) or (it.court in courts)]
            if matched:
                candidates = matched

    rejected = get_rejected_item_ids(user_id)
    ranked = rank_by_similarity(candidates, interest, now=now, penalized_ids=rejected)
    return [it.to_dict() for it in ranked[offset:offset + limit]]
