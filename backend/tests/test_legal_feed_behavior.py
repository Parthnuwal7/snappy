from app.services.legal_feed.behavior import (
    normalize, apply_event, blend_interest, NEGATIVE_MIN_EVENTS,
)


def test_normalize_unit_length():
    assert normalize([3.0, 4.0]) == [0.6, 0.8]
    assert normalize([0.0, 0.0]) is None
    assert normalize(None) is None


def test_click_initializes_then_moves_toward_item():
    v = apply_event(None, [1.0, 0.0], 'click', 0)
    assert v == [1.0, 0.0]
    v2 = apply_event([0.0, 1.0], [1.0, 0.0], 'click', 0)
    assert v2[0] > 0  # pulled toward [1,0]


def test_rejection_ignored_below_threshold():
    v = [1.0, 0.0]
    assert apply_event(v, [1.0, 0.0], 'not_interested', NEGATIVE_MIN_EVENTS - 1) == v


def test_rejection_applied_at_threshold():
    v = normalize([1.0, 1.0])
    out = apply_event(v, [1.0, 0.0], 'not_interested', NEGATIVE_MIN_EVENTS)
    assert out != v  # steered away


def test_item_without_embedding_is_noop():
    v = [1.0, 0.0]
    assert apply_event(v, None, 'click', 0) == v


def test_blend_weights_behavior_by_count():
    interest, behavior = [1.0, 0.0], [0.0, 1.0]
    assert blend_interest(interest, behavior, 0) == [1.0, 0.0]      # bw=0 -> interest
    assert blend_interest(interest, behavior, 999) == [0.0, 1.0]    # bw=1 -> behavior
    assert blend_interest(None, behavior, 3) == behavior
    assert blend_interest(interest, None, 3) == interest
