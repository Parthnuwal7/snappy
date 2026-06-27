"""Pure-Python ranking for the 'For you' feed. Brute-force cosine over a
taxonomy/recency-filtered candidate set; swap in pgvector here if it grows."""
import math
from datetime import datetime

RECENCY_HALF_LIFE_DAYS = 14
REJECT_PENALTY = 0.05


def cosine(a, b) -> float:
    if not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _recency_decay(item, now) -> float:
    when = getattr(item, 'published_at', None) or getattr(item, 'ingested_at', None)
    if when is None:
        return 0.5
    age_days = max(0.0, (now - when).total_seconds() / 86400.0)
    return 0.5 ** (age_days / RECENCY_HALF_LIFE_DAYS)


def score_item(item, interest_embedding, now) -> float:
    sim = cosine(getattr(item, 'embedding', None), interest_embedding) if interest_embedding else 1.0
    importance = (getattr(item, 'importance', None) or 0) / 100.0
    return sim * (0.5 + 0.5 * importance) * _recency_decay(item, now)


def rank_by_similarity(items, interest_embedding, now=None,
                       penalized_ids=None, penalty=REJECT_PENALTY) -> list:
    now = now or datetime.utcnow()
    pen = penalized_ids or set()

    def _key(it):
        s = score_item(it, interest_embedding, now)
        if getattr(it, 'id', None) in pen:
            s *= penalty
        return s

    return sorted(items, key=_key, reverse=True)
