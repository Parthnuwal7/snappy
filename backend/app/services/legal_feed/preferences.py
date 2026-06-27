"""User feed-preference persistence + interest-phrase embedding on save."""
from app.models.models import db, LegalFeedPreference
from app.services.legal_feed.taxonomy import PRACTICE_AREAS
from app.services.legal_feed.enrichment import get_enrichment_client

_VALID = set(PRACTICE_AREAS)


def get_preference(user_id):
    return LegalFeedPreference.query.filter_by(user_id=user_id).first()


def _clean_weights(raw):
    if not isinstance(raw, dict):
        return {}
    out = {}
    for k, v in raw.items():
        if k in _VALID:
            try:
                out[k] = float(v)
            except (TypeError, ValueError):
                continue
    return out


def upsert_preference(user_id, topic_weights, courts, interest_phrases, client='__default__'):
    if client == '__default__':
        client = get_enrichment_client()

    pref = get_preference(user_id) or LegalFeedPreference(user_id=user_id)
    pref.topic_weights = _clean_weights(topic_weights)
    pref.courts = list(courts or [])
    phrases = [p for p in (interest_phrases or []) if isinstance(p, str) and p.strip()]
    pref.interest_phrases = phrases

    if phrases and client is not None:
        pref.interest_embedding = client.embed(' '.join(phrases))
        pref.embed_model = getattr(client, 'embed_model', None)
    else:
        pref.interest_embedding = None
        pref.embed_model = None

    db.session.add(pref)
    db.session.commit()
    return pref
