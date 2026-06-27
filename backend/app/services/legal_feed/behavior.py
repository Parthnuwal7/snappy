"""Pure-Python behavioral personalization math (no DB). The event log is the
source of truth; these functions compute/update the learned interest vector."""
import math

EMA_ALPHA = 0.2            # click pull
EMA_BETA = 0.2             # rejection push
NEGATIVE_MIN_EVENTS = 3    # rejections needed before negative learning applies
BEHAVIOR_DOMINATES_AT = 5  # events after which behavior fully outweighs phrases
RECOMPUTE_DECAY_DAYS = 30  # half-life for batch recompute weighting


def normalize(v):
    if not v:
        return None
    norm = math.sqrt(sum(x * x for x in v))
    if norm == 0:
        return None
    return [x / norm for x in v]


def apply_event(behavior, item_embedding, kind, not_interested_count):
    """Update the behavior vector for one event. Returns new vector (or input
    unchanged). `not_interested_count` includes the current event."""
    if not item_embedding:
        return behavior
    if kind == 'click':
        if not behavior:
            return normalize(list(item_embedding))
        mixed = [(1 - EMA_ALPHA) * b + EMA_ALPHA * e
                 for b, e in zip(behavior, item_embedding)]
        return normalize(mixed)
    if kind == 'not_interested':
        if not behavior or not_interested_count < NEGATIVE_MIN_EVENTS:
            return behavior
        mixed = [b - EMA_BETA * e for b, e in zip(behavior, item_embedding)]
        return normalize(mixed)
    return behavior


def blend_interest(interest_embedding, behavior_embedding, event_count):
    """Blend explicit (phrases) + learned (behavior). Behavior weight grows from
    0 to 1 over the first BEHAVIOR_DOMINATES_AT events."""
    if not behavior_embedding:
        return interest_embedding
    if not interest_embedding:
        return behavior_embedding
    bw = min(1.0, event_count / BEHAVIOR_DOMINATES_AT)
    mixed = [(1 - bw) * i + bw * b
             for i, b in zip(interest_embedding, behavior_embedding)]
    return normalize(mixed)
