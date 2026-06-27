from datetime import datetime, timedelta
from app.services.legal_feed.similarity import cosine, rank_by_similarity


class FakeItem:
    def __init__(self, embedding, importance=50, age_days=0, id=None):
        self.embedding = embedding
        self.importance = importance
        self.published_at = datetime(2026, 6, 22) - timedelta(days=age_days)
        self.ingested_at = self.published_at
        self.id = id


NOW = datetime(2026, 6, 22)


def test_cosine_basic():
    assert cosine([1, 0], [1, 0]) == 1.0
    assert cosine([1, 0], [0, 1]) == 0.0
    assert cosine([], [1, 0]) == 0.0


def test_rank_prefers_higher_similarity():
    near = FakeItem([1.0, 0.0])
    far = FakeItem([0.0, 1.0])
    ranked = rank_by_similarity([far, near], [1.0, 0.0], now=NOW)
    assert ranked[0] is near


def test_cold_start_falls_back_to_importance_and_recency():
    hi = FakeItem([0.0, 0.0], importance=90, age_days=0)
    lo = FakeItem([0.0, 0.0], importance=10, age_days=0)
    ranked = rank_by_similarity([lo, hi], None, now=NOW)
    assert ranked[0] is hi


def test_recency_breaks_ties_when_importance_equal():
    fresh = FakeItem([1.0, 0.0], importance=50, age_days=0)
    stale = FakeItem([1.0, 0.0], importance=50, age_days=30)
    ranked = rank_by_similarity([stale, fresh], [1.0, 0.0], now=NOW)
    assert ranked[0] is fresh


def test_demotion_pushes_penalized_last():
    a = FakeItem([1.0, 0.0], id=1)
    b = FakeItem([1.0, 0.0], id=2)
    ranked = rank_by_similarity([a, b], [1.0, 0.0], now=NOW, penalized_ids={1})
    assert ranked[0] is b and ranked[1] is a
