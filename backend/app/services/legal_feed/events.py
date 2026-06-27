"""Engagement events + behavioral vector maintenance (online + batch)."""
from datetime import datetime

from app.models.models import db, LegalFeedEvent, LegalFeedItem, LegalFeedPreference
from app.services.legal_feed import behavior as bx

VALID_KINDS = {'click', 'not_interested'}


def _get_or_create_pref(user_id):
    pref = LegalFeedPreference.query.filter_by(user_id=user_id).first()
    if pref is None:
        pref = LegalFeedPreference(user_id=user_id)
        db.session.add(pref)
    return pref


def event_count(user_id) -> int:
    return LegalFeedEvent.query.filter_by(user_id=user_id).count()


def _not_interested_count(user_id) -> int:
    return LegalFeedEvent.query.filter_by(user_id=user_id, kind='not_interested').count()


def get_rejected_item_ids(user_id) -> set:
    rows = (db.session.query(LegalFeedEvent.item_id)
            .filter_by(user_id=user_id, kind='not_interested').all())
    return {r[0] for r in rows if r[0] is not None}


def record_event(user_id, item_id, kind) -> bool:
    if kind not in VALID_KINDS:
        return False
    item = LegalFeedItem.query.get(item_id)
    if item is None:
        return False

    db.session.add(LegalFeedEvent(user_id=user_id, item_id=item_id, kind=kind))
    db.session.commit()

    pref = _get_or_create_pref(user_id)
    ni_count = _not_interested_count(user_id)  # includes the event just recorded
    new_vec = bx.apply_event(pref.behavior_embedding, item.embedding, kind, ni_count)
    if new_vec != pref.behavior_embedding:
        pref.behavior_embedding = new_vec
        pref.behavior_updated_at = datetime.utcnow()
    db.session.commit()
    return True


def recompute_behavior_embedding(user_id) -> bool:
    """Rebuild the behavior vector from the event log (source of truth)."""
    rows = (db.session.query(LegalFeedEvent, LegalFeedItem)
            .join(LegalFeedItem, LegalFeedEvent.item_id == LegalFeedItem.id)
            .filter(LegalFeedEvent.user_id == user_id).all())
    ni_total = sum(1 for ev, _ in rows if ev.kind == 'not_interested')
    now = datetime.utcnow()
    acc = None
    for ev, item in rows:
        if not item.embedding:
            continue
        if ev.kind == 'click':
            sign = 1.0
        elif ev.kind == 'not_interested' and ni_total >= bx.NEGATIVE_MIN_EVENTS:
            sign = -1.0
        else:
            continue
        age_days = max(0.0, (now - (ev.created_at or now)).total_seconds() / 86400.0)
        w = sign * (0.5 ** (age_days / bx.RECOMPUTE_DECAY_DAYS))
        if acc is None:
            acc = [0.0] * len(item.embedding)
        for i, x in enumerate(item.embedding):
            acc[i] += w * x

    pref = _get_or_create_pref(user_id)
    pref.behavior_embedding = bx.normalize(acc) if acc else None
    pref.behavior_updated_at = now
    db.session.commit()
    return True
