# Behavior-Curated News Feed Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the news feed learn from engagement (clicks + "Not interested") and present a dense, multi-column "For you" wall that pushes relevant content like X.

**Architecture:** A `LegalFeedEvent` log is the source of truth; an online EMA updates a stored `behavior_embedding` instantly while a batch recompute re-grounds it. `query_for_you` ranks by a blend of the user's typed-phrase vector and the learned behavior vector, demoting (not hiding) items the user rejected. Vector math is pure Python behind `behavior.py`; ranking stays Python cosine.

**Tech Stack:** Flask + Flask-SQLAlchemy, pytest on in-memory SQLite, React 18 + Tailwind.

## Global Constraints

- User-facing endpoints under `/api/v1`; admin under `/admin`.
- No new dependencies.
- Vector math is pure Python in `behavior.py` (testable without DB). Embeddings stored as JSON float arrays.
- **News only** — judgements are not enriched and not part of behavioral learning.
- **Negative guardrail:** a single "Not interested" only *demotes* that one item (ranking penalty, never hidden). Negative *learning* applies only once total `not_interested` events ≥ `NEGATIVE_MIN_EVENTS = 3`. Clicks have no threshold.
- Constants (in `behavior.py`): `EMA_ALPHA = 0.2`, `EMA_BETA = 0.2`, `NEGATIVE_MIN_EVENTS = 3`, `BEHAVIOR_DOMINATES_AT = 5`, `RECOMPUTE_DECAY_DAYS = 30`. `REJECT_PENALTY = 0.05` (in `similarity.py`).
- Blend: `bw = min(1.0, event_count / BEHAVIOR_DOMINATES_AT)`; `blended = normalize((1-bw)·interest + bw·behavior)`.
- Tests run against in-memory SQLite via existing `app`/`client`/`db` fixtures.
- Frontend: no unit runner — verify with `npm run build` and `npm run lint`. Tailwind tokens: `text-ink`, `text-ink-soft`, `text-ink-muted`, `text-ink-faint`, `bg-paper`, `border-rule`, `eyebrow`, `oxblood`, `text-2xs`.
- **Git is performed by the repo owner (Parth), not the agent.** Treat the `git commit` step as a checkpoint marker; do not run git.

---

### Task 1: Behavioral vector math (`behavior.py`)

**Files:**
- Create: `backend/app/services/legal_feed/behavior.py`
- Test: `backend/tests/test_legal_feed_behavior.py`

**Interfaces:**
- Produces:
  - constants `EMA_ALPHA, EMA_BETA, NEGATIVE_MIN_EVENTS, BEHAVIOR_DOMINATES_AT, RECOMPUTE_DECAY_DAYS`
  - `normalize(v) -> list|None`
  - `apply_event(behavior, item_embedding, kind, not_interested_count) -> list|None` — returns the updated behavior vector (or the input unchanged). `kind ∈ {'click','not_interested'}`. `not_interested_count` is the user's total rejections *including the current one*.
  - `blend_interest(interest_embedding, behavior_embedding, event_count) -> list|None`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_legal_feed_behavior.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_legal_feed_behavior.py -v`
Expected: FAIL (`ModuleNotFoundError`)

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/services/legal_feed/behavior.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_legal_feed_behavior.py -v`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/legal_feed/behavior.py backend/tests/test_legal_feed_behavior.py
git commit -m "feat(legal-feed): behavioral vector math (EMA + blend)"
```

---

### Task 2: Schema — event log + behavior columns

**Files:**
- Modify: `backend/app/models/models.py` (add `LegalFeedEvent`; extend `LegalFeedPreference`)
- Modify: `backend/app/main.py` (import `LegalFeedEvent` in the create_all block)
- Test: `backend/tests/test_legal_feed_models.py` (append)

**Interfaces:**
- Produces: `LegalFeedEvent(id, user_id, item_id, kind, created_at)` with `to_dict()`; `LegalFeedPreference.behavior_embedding` (JSON) + `behavior_updated_at` (DateTime).

- [ ] **Step 1: Write the failing test**

```python
# append to backend/tests/test_legal_feed_models.py
from app.models.models import LegalFeedEvent


def test_event_roundtrip(db):
    item = LegalFeedItem(content_type='news', title='t', source_url='u',
                         source_name='s', dedup_key='ev-model')
    db.session.add(item)
    db.session.commit()
    ev = LegalFeedEvent(user_id=3, item_id=item.id, kind='click')
    db.session.add(ev)
    db.session.commit()
    assert LegalFeedEvent.query.filter_by(user_id=3, kind='click').count() == 1


def test_preference_has_behavior_columns(db):
    pref = LegalFeedPreference(user_id=9, behavior_embedding=[0.1, 0.2])
    db.session.add(pref)
    db.session.commit()
    got = LegalFeedPreference.query.filter_by(user_id=9).first()
    assert got.behavior_embedding == [0.1, 0.2]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_legal_feed_models.py -v`
Expected: FAIL (`ImportError: cannot import name 'LegalFeedEvent'`)

- [ ] **Step 3: Write minimal implementation**

In `models.py`, add to `LegalFeedPreference` (after `embed_model`):

```python
    behavior_embedding = db.Column(db.JSON)        # learned interest vector
    behavior_updated_at = db.Column(db.DateTime)
```

Add a new model after `LegalFeedPreference` (before `def init_db():`):

```python
class LegalFeedEvent(db.Model):
    """User engagement with a feed item — the source of truth for behavioral
    personalization. kind: 'click' (positive) | 'not_interested' (negative)."""
    __tablename__ = 'legal_feed_events'
    __table_args__ = (db.Index('ix_lfe_user_kind', 'user_id', 'kind'),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False, index=True)
    item_id = db.Column(db.Integer, db.ForeignKey('legal_feed_items.id'), index=True)
    kind = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id, 'user_id': self.user_id, 'item_id': self.item_id,
            'kind': self.kind,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
```

In `backend/app/main.py`, add `LegalFeedEvent` to the legal-feed model import inside the `db.create_all()` block:

```python
        from app.models.models import (
            LegalFeedSource, LegalFeedItem, LegalFeedRun, LegalFeedSetting,
            LegalFeedPreference, LegalFeedEvent,
        )  # ensure legal feed tables are created
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_legal_feed_models.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/models.py backend/app/main.py backend/tests/test_legal_feed_models.py
git commit -m "feat(legal-feed): event log + behavior columns"
```

---

### Task 3: Demotion in ranking (`similarity.py`)

**Files:**
- Modify: `backend/app/services/legal_feed/similarity.py` (`rank_by_similarity` + `REJECT_PENALTY`)
- Test: `backend/tests/test_legal_feed_similarity.py` (extend `FakeItem`, add test)

**Interfaces:**
- Produces: `REJECT_PENALTY = 0.05`; `rank_by_similarity(items, interest_embedding, now=None, penalized_ids=None, penalty=REJECT_PENALTY)` — items whose `id` is in `penalized_ids` have their score multiplied by `penalty` (sink to the bottom).

- [ ] **Step 1: Write the failing test**

In `backend/tests/test_legal_feed_similarity.py`, give `FakeItem` an `id` and add a test:

```python
# change FakeItem.__init__ signature to accept id:
class FakeItem:
    def __init__(self, embedding, importance=50, age_days=0, id=None):
        self.embedding = embedding
        self.importance = importance
        self.published_at = datetime(2026, 6, 22) - timedelta(days=age_days)
        self.ingested_at = self.published_at
        self.id = id


def test_demotion_pushes_penalized_last():
    a = FakeItem([1.0, 0.0], id=1)
    b = FakeItem([1.0, 0.0], id=2)
    ranked = rank_by_similarity([a, b], [1.0, 0.0], now=NOW, penalized_ids={1})
    assert ranked[0] is b and ranked[1] is a
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_legal_feed_similarity.py -v`
Expected: FAIL (penalized item still ranks first / TypeError on unexpected kwarg)

- [ ] **Step 3: Write minimal implementation**

In `similarity.py`, add the constant near the top:

```python
REJECT_PENALTY = 0.05
```

Replace `rank_by_similarity`:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_legal_feed_similarity.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/legal_feed/similarity.py backend/tests/test_legal_feed_similarity.py
git commit -m "feat(legal-feed): demotion penalty in similarity ranking"
```

---

### Task 4: Events service

**Files:**
- Create: `backend/app/services/legal_feed/events.py`
- Test: `backend/tests/test_legal_feed_events.py`

**Interfaces:**
- Consumes: `behavior.apply_event/normalize/RECOMPUTE_DECAY_DAYS/NEGATIVE_MIN_EVENTS` (Task 1); `LegalFeedEvent`, `LegalFeedItem`, `LegalFeedPreference` (Task 2).
- Produces:
  - `VALID_KINDS = {'click', 'not_interested'}`
  - `record_event(user_id, item_id, kind) -> bool` — validates, inserts event, applies online EMA to the user's preference (creating it if absent). Returns False on invalid kind / missing item.
  - `get_rejected_item_ids(user_id) -> set[int]`
  - `event_count(user_id) -> int`
  - `recompute_behavior_embedding(user_id) -> bool` — rebuilds `behavior_embedding` from the event log (recency-decayed; negatives only if rejection count ≥ threshold).

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_legal_feed_events.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_legal_feed_events.py -v`
Expected: FAIL (`ModuleNotFoundError`)

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/services/legal_feed/events.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_legal_feed_events.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/legal_feed/events.py backend/tests/test_legal_feed_events.py
git commit -m "feat(legal-feed): engagement events + behavior maintenance"
```

---

### Task 5: Query — blend, demote, offset

**Files:**
- Modify: `backend/app/services/legal_feed/query.py` (`query_for_you` blend+demote+offset; `query_feed` demotion)
- Test: `backend/tests/test_legal_feed_query.py` (append)

**Interfaces:**
- Consumes: `behavior.blend_interest` (Task 1); `events.get_rejected_item_ids/event_count` (Task 4); `rank_by_similarity(..., penalized_ids=)` (Task 3).
- Produces:
  - `query_for_you(user_id, content_type=None, limit=10, offset=0, window_days=14, now=None)` — blends interest+behavior, demotes rejected, paginates with `offset`.
  - `query_feed(content_type=None, court=None, page=1, page_size=50, demote_ids=None)` — when `demote_ids` is given, rejected items sort last.

- [ ] **Step 1: Write the failing test**

```python
# append to backend/tests/test_legal_feed_query.py
from app.services.legal_feed.events import record_event


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
```

(Reuse the `_item` helper already defined at the top of this test file.)

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_legal_feed_query.py -v`
Expected: FAIL (`query_for_you() got unexpected keyword 'offset'` / demotion not applied)

- [ ] **Step 3: Write minimal implementation**

In `query.py`, update imports:

```python
from sqlalchemy import func, case

from app.services.legal_feed.preferences import get_preference
from app.services.legal_feed.similarity import rank_by_similarity
from app.services.legal_feed import behavior as bx
from app.services.legal_feed.events import get_rejected_item_ids, event_count
```

Replace `query_feed` with a demotion-aware version:

```python
def query_feed(content_type=None, court=None, page=1, page_size=50, demote_ids=None) -> dict:
    q = LegalFeedItem.query.filter_by(hidden=False)
    if content_type:
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
```

Replace `query_for_you`:

```python
def query_for_you(user_id, content_type=None, limit=10, offset=0,
                  window_days=14, now=None) -> list:
    now = now or datetime.utcnow()
    cutoff = now - timedelta(days=window_days)
    pref = get_preference(user_id)

    q = LegalFeedItem.query.filter_by(hidden=False)
    if content_type:
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_legal_feed_query.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/legal_feed/query.py backend/tests/test_legal_feed_query.py
git commit -m "feat(legal-feed): blend behavior, demote rejected, offset paging"
```

---

### Task 6: User API — events endpoint, for-you offset, latest demotion

**Files:**
- Modify: `backend/app/api/legal_feed.py`
- Test: `backend/tests/test_legal_feed_api.py` (append)

**Interfaces:**
- Consumes: `events.record_event/get_rejected_item_ids` (Task 4); `query_for_you` offset, `query_feed` `demote_ids` (Task 5).
- Produces:
  - `POST /api/v1/legal-feed/events` (`@jwt_required`), body `{item_id, kind}` → `{ok: true}` / 400.
  - `GET /api/v1/legal-feed/for-you` gains `offset`.
  - `GET /api/v1/legal-feed` passes the caller's rejected ids as `demote_ids`.

- [ ] **Step 1: Write the failing test**

```python
# append to backend/tests/test_legal_feed_api.py
def test_post_event_click(client, db, auth_headers):
    u = make_user('sb-ev1')
    item = LegalFeedItem(content_type='news', title='t', source_url='u',
                         source_name='s', dedup_key='api-ev1', embedding=[1.0, 0.0])
    db.session.add(item)
    db.session.commit()
    r = client.post('/api/v1/legal-feed/events', headers=auth_headers('sb-ev1'),
                    json={'item_id': item.id, 'kind': 'click'})
    assert r.status_code == 200 and r.get_json()['ok'] is True
    from app.models.models import LegalFeedEvent
    assert LegalFeedEvent.query.filter_by(user_id=u.id, kind='click').count() == 1


def test_post_event_invalid_kind(client, db, auth_headers):
    make_user('sb-ev2')
    item = LegalFeedItem(content_type='news', title='t', source_url='u',
                         source_name='s', dedup_key='api-ev2')
    db.session.add(item)
    db.session.commit()
    r = client.post('/api/v1/legal-feed/events', headers=auth_headers('sb-ev2'),
                    json={'item_id': item.id, 'kind': 'bogus'})
    assert r.status_code == 400


def test_event_requires_auth(client):
    assert client.post('/api/v1/legal-feed/events',
                       json={'item_id': 1, 'kind': 'click'}).status_code == 401
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_legal_feed_api.py -v`
Expected: FAIL (404 on `/events`)

- [ ] **Step 3: Write minimal implementation**

In `legal_feed.py`, extend imports:

```python
from app.services.legal_feed.query import query_feed, list_courts, query_for_you
from app.services.legal_feed.events import record_event, get_rejected_item_ids
```

Update `get_feed` to demote the caller's rejections:

```python
@bp.route('/legal-feed', methods=['GET'])
@jwt_required
def get_feed():
    if pagination_requested():
        page, page_size = get_pagination_args()
    else:
        page, page_size = 1, 50
    uid = _current_user_id()
    demote_ids = get_rejected_item_ids(uid) if uid else None
    return jsonify(query_feed(
        content_type=request.args.get('type'),
        court=request.args.get('court'),
        page=page, page_size=page_size, demote_ids=demote_ids,
    ))
```

Update `get_for_you` to accept `offset`:

```python
@bp.route('/legal-feed/for-you', methods=['GET'])
@jwt_required
def get_for_you():
    uid = _current_user_id()
    if uid is None:
        return jsonify({'error': 'User not found'}), 401
    limit = request.args.get('limit', default=10, type=int)
    offset = request.args.get('offset', default=0, type=int)
    data = query_for_you(uid, content_type=request.args.get('type'),
                         limit=limit, offset=offset)
    return jsonify({'data': data})
```

Add the events endpoint (after `put_preferences`):

```python
@bp.route('/legal-feed/events', methods=['POST'])
@jwt_required
def post_event():
    uid = _current_user_id()
    if uid is None:
        return jsonify({'error': 'User not found'}), 401
    body = request.get_json() or {}
    if record_event(uid, body.get('item_id'), body.get('kind')):
        return jsonify({'ok': True})
    return jsonify({'error': 'invalid event'}), 400
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_legal_feed_api.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/legal_feed.py backend/tests/test_legal_feed_api.py
git commit -m "feat(legal-feed): events endpoint, for-you offset, latest demotion"
```

---

### Task 7: Admin — batch recompute trigger

**Files:**
- Modify: `backend/app/api/admin.py` (route + panel button/JS)
- Test: `backend/tests/test_admin_legal_feed.py` (append)

**Interfaces:**
- Consumes: `events.recompute_behavior_embedding` (Task 4).
- Produces: `POST /admin/api/legal-feed/recompute-behavior` → `{recomputed: <user count>}`.

- [ ] **Step 1: Write the failing test**

```python
# append to backend/tests/test_admin_legal_feed.py
def test_recompute_behavior_route(client, db, monkeypatch):
    from app.models.models import LegalFeedPreference
    h = _h(monkeypatch)
    db.session.add(LegalFeedPreference(user_id=1))
    db.session.add(LegalFeedPreference(user_id=2))
    db.session.commit()
    resp = client.post('/admin/api/legal-feed/recompute-behavior', headers=h)
    assert resp.status_code == 200
    assert resp.get_json()['recomputed'] == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_admin_legal_feed.py -v`
Expected: FAIL (404)

- [ ] **Step 3: Write minimal implementation**

In `admin.py`, extend the legal-feed import:

```python
from app.services.legal_feed.events import recompute_behavior_embedding
```

Add the route (after `lf_backfill`):

```python
@bp.route('/api/legal-feed/recompute-behavior', methods=['POST'])
@requires_admin_auth
def lf_recompute_behavior():
    from app.models.models import LegalFeedPreference
    user_ids = [p.user_id for p in LegalFeedPreference.query.all()]
    for uid in user_ids:
        recompute_behavior_embedding(uid)
    return jsonify({'recomputed': len(user_ids)})
```

Add a button next to "Enrich backlog" in `ADMIN_PANEL_HTML`:

```html
<button class="btn" onclick="lfRecompute()" style="margin-left:8px;">Recompute behavior</button>
```

And the JS handler (near `lfBackfill`):

```javascript
async function lfRecompute() {
    const r = await (await fetch('/admin/api/legal-feed/recompute-behavior', {method:'POST'})).json();
    showMessage('lfMessage', `Recomputed behavior for ${r.recomputed} user(s)`, 'success');
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_admin_legal_feed.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/admin.py backend/tests/test_admin_legal_feed.py
git commit -m "feat(admin): batch recompute of behavior vectors"
```

---

### Task 8: Frontend API — events + for-you offset

**Files:**
- Modify: `frontend/src/api.ts`

**Interfaces:**
- Produces:
  - `api.getLegalFeedForYou({ type, limit?, offset? })` (adds `offset`).
  - `api.postLegalFeedEvent(item_id: number, kind: 'click' | 'not_interested')`.

- [ ] **Step 1: Update `getLegalFeedForYou` and add the event method**

Replace the existing `getLegalFeedForYou` and add `postLegalFeedEvent` alongside it in `api.ts`:

```typescript
  getLegalFeedForYou: async (params: { type: string; limit?: number; offset?: number }): Promise<LegalFeedItem[]> => {
    const q = new URLSearchParams({
      type: params.type,
      limit: String(params.limit ?? 10),
      offset: String(params.offset ?? 0),
    });
    const res = await fetchAPI<{ data: LegalFeedItem[] }>(`${API_ENDPOINTS.legalFeed}/for-you?${q}`);
    return res.data;
  },

  postLegalFeedEvent: (item_id: number, kind: 'click' | 'not_interested') =>
    fetchAPI<{ ok: boolean }>(`${API_ENDPOINTS.legalFeed}/events`, {
      method: 'POST', body: JSON.stringify({ item_id, kind }),
    }),
```

- [ ] **Step 2: Verify it compiles**

Run: `cd frontend && npm run build`
Expected: build succeeds

- [ ] **Step 3: Commit**

```bash
git add frontend/src/api.ts
git commit -m "feat(legal-feed): frontend events API + for-you offset"
```

---

### Task 9: Frontend — dense news wall + click/not-interested

**Files:**
- Create: `frontend/src/components/NewsCard.tsx`
- Modify: `frontend/src/pages/LegalFeed.tsx`

**Interfaces:**
- Consumes: `api.getLegalFeedForYou` (offset), `api.postLegalFeedEvent`, `api.getLegalFeed`, `api.getLegalFeedCourts` (Task 8 + existing).

- [ ] **Step 1: Create the dense news card**

```tsx
// frontend/src/components/NewsCard.tsx
import { api, LegalFeedItem } from '../api';

export default function NewsCard({ item, onNotInterested }: {
  item: LegalFeedItem;
  onNotInterested: (id: number) => void;
}) {
  const open = () => { void api.postLegalFeedEvent(item.id, 'click'); };
  const notInterested = () => {
    void api.postLegalFeedEvent(item.id, 'not_interested');
    onNotInterested(item.id);
  };
  return (
    <div className="break-inside-avoid mb-4 border border-rule rounded-lg p-3 bg-paper">
      <div className="flex items-center gap-2 mb-1">
        <span className="eyebrow text-ink-faint">{item.source_name}</span>
        {item.published_at && (
          <span className="text-2xs text-ink-muted ml-auto">
            {new Date(item.published_at).toLocaleDateString()}
          </span>
        )}
      </div>
      <h3 className="text-ink font-medium leading-snug mb-1">{item.headline || item.title}</h3>
      {(item.tldr || item.summary) && (
        <p className="text-sm text-ink-soft mb-2">{item.tldr || item.summary}</p>
      )}
      <div className="flex items-center justify-between">
        <a href={item.source_url} target="_blank" rel="noopener noreferrer" onClick={open}
          className="text-sm text-oxblood hover:underline">Read at source ↗</a>
        <button onClick={notInterested}
          className="text-2xs text-ink-faint hover:text-ink" title="Not interested">
          Not interested ✕
        </button>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Rewrite `LegalFeed.tsx`**

News tab → dense column wall with a primary "For you" (30, load-more) + a "Latest" section; both use `NewsCard` and support local removal on "Not interested". Judgements tab keeps the existing image-card list.

```tsx
import { useEffect, useState } from 'react';
import { api, LegalFeedItem } from '../api';
import Pagination from '../components/Pagination';
import LegalFeedPersonalize from '../components/LegalFeedPersonalize';
import NewsCard from '../components/NewsCard';

type Tab = 'judgement' | 'news';
const TABS: { key: Tab; label: string }[] = [
  { key: 'judgement', label: 'Judgements' },
  { key: 'news', label: 'Legal News' },
];
const PAGE_SIZE = 20;
const FORYOU_PAGE = 30;

function JudgementCard({ item }: { item: LegalFeedItem }) {
  return (
    <li className="border border-rule rounded-lg p-4 bg-paper">
      <div className="flex items-center gap-2 mb-1">
        <span className="eyebrow text-ink-faint">{item.source_name}</span>
        {item.court && <span className="text-2xs text-ink-muted">· {item.court}</span>}
        {item.published_at && (
          <span className="text-2xs text-ink-muted ml-auto">
            {new Date(item.published_at).toLocaleDateString()}
          </span>
        )}
      </div>
      <h3 className="text-ink font-medium mb-1">{item.title}</h3>
      {item.summary && <p className="text-sm text-ink-soft line-clamp-3 mb-2">{item.summary}</p>}
      <a href={item.source_url} target="_blank" rel="noopener noreferrer"
        className="text-sm text-oxblood hover:underline">Read at source ↗</a>
    </li>
  );
}

export default function LegalFeed() {
  const [tab, setTab] = useState<Tab>('judgement');
  const [court, setCourt] = useState('');
  const [courts, setCourts] = useState<string[]>([]);
  const [forYou, setForYou] = useState<LegalFeedItem[]>([]);
  const [forYouOffset, setForYouOffset] = useState(0);
  const [forYouMore, setForYouMore] = useState(true);
  const [items, setItems] = useState<LegalFeedItem[]>([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showPanel, setShowPanel] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  const isNews = tab === 'news';

  useEffect(() => { api.getLegalFeedCourts().then(setCourts).catch(() => setCourts([])); }, []);

  // For you: reset + load first page whenever tab changes or prefs are saved.
  useEffect(() => {
    setForYouOffset(0);
    api.getLegalFeedForYou({ type: tab, limit: FORYOU_PAGE, offset: 0 })
      .then((d) => { setForYou(d); setForYouMore(d.length === FORYOU_PAGE); })
      .catch(() => { setForYou([]); setForYouMore(false); });
  }, [tab, refreshKey]);

  useEffect(() => {
    setLoading(true);
    setError(null);
    api.getLegalFeed({ page, type: tab, court: court || undefined, page_size: PAGE_SIZE })
      .then((res) => { setItems(res.data); setTotalPages(res.total_pages || 1); setTotal(res.total); })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [tab, court, page]);

  const switchTab = (next: Tab) => { setTab(next); setCourt(''); setPage(1); };

  const loadMore = async () => {
    const next = forYouOffset + FORYOU_PAGE;
    const more = await api.getLegalFeedForYou({ type: tab, limit: FORYOU_PAGE, offset: next });
    setForYou((cur) => [...cur, ...more]);
    setForYouOffset(next);
    setForYouMore(more.length === FORYOU_PAGE);
  };

  const removeItem = (id: number) => {
    setForYou((cur) => cur.filter((i) => i.id !== id));
    setItems((cur) => cur.filter((i) => i.id !== id));
  };

  return (
    <div className="p-8 max-w-6xl mx-auto">
      <div className="flex items-start justify-between">
        <div>
          <div className="eyebrow text-ink-faint mb-1">Library</div>
          <h1 className="font-display text-3xl text-ink mb-6">Legal Feed</h1>
        </div>
        <button onClick={() => setShowPanel(true)}
          className="text-sm border border-rule rounded px-3 py-1.5 text-ink-soft hover:text-ink">
          Personalize
        </button>
      </div>

      <div className="flex items-center gap-6 border-b border-rule mb-5">
        {TABS.map((t) => (
          <button key={t.key} onClick={() => switchTab(t.key)}
            className={['pb-2 text-sm font-medium transition-colors -mb-px border-b-2',
              tab === t.key ? 'text-oxblood border-oxblood' : 'text-ink-soft border-transparent hover:text-ink'].join(' ')}>
            {t.label}
          </button>
        ))}
      </div>

      {/* For you */}
      {forYou.length > 0 && (
        <section className="mb-8">
          <div className="eyebrow text-ink-faint mb-3">For you</div>
          {isNews ? (
            <>
              <div className="columns-1 sm:columns-2 lg:columns-3 gap-4">
                {forYou.map((i) => <NewsCard key={`fy-${i.id}`} item={i} onNotInterested={removeItem} />)}
              </div>
              {forYouMore && (
                <button onClick={loadMore}
                  className="mt-4 text-sm border border-rule rounded px-4 py-1.5 text-ink-soft hover:text-ink">
                  Load more
                </button>
              )}
            </>
          ) : (
            <ul className="space-y-4">{forYou.map((i) => <JudgementCard key={`fy-${i.id}`} item={i} />)}</ul>
          )}
        </section>
      )}

      {/* Latest */}
      <div className="flex items-center justify-between mb-3">
        <div className="eyebrow text-ink-faint">Latest</div>
        {!isNews && courts.length > 0 && (
          <select value={court} onChange={(e) => { setCourt(e.target.value); setPage(1); }}
            className="border border-rule rounded px-3 py-1.5 text-sm bg-paper text-ink">
            <option value="">All courts</option>
            {courts.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
        )}
      </div>

      {loading && <p className="text-ink-muted text-sm">Loading…</p>}
      {error && <p className="text-oxblood text-sm">Failed to load: {error}</p>}
      {!loading && !error && items.length === 0 && (
        <p className="text-ink-muted text-sm">No items yet. Check back soon.</p>
      )}

      {isNews ? (
        <div className="columns-1 sm:columns-2 lg:columns-3 gap-4">
          {items.map((i) => <NewsCard key={i.id} item={i} onNotInterested={removeItem} />)}
        </div>
      ) : (
        <ul className="space-y-4">{items.map((i) => <JudgementCard key={i.id} item={i} />)}</ul>
      )}

      <Pagination page={page} totalPages={totalPages} total={total} pageSize={PAGE_SIZE} onPageChange={setPage} />

      {showPanel && (
        <LegalFeedPersonalize courts={courts} onClose={() => setShowPanel(false)}
          onSaved={() => setRefreshKey((k) => k + 1)} />
      )}
    </div>
  );
}
```

- [ ] **Step 3: Build and lint**

Run: `cd frontend && npm run build` then `cd frontend && npm run lint`
Expected: build succeeds; no new errors/warnings in `NewsCard.tsx` or `LegalFeed.tsx` (pre-existing lint debt in other files is unrelated).

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/NewsCard.tsx frontend/src/pages/LegalFeed.tsx
git commit -m "feat(legal-feed): dense news wall with click/not-interested signals"
```

---

### Task 10: Full suite + docs

**Files:**
- Modify: `docs/superpowers/legal-feed-ops.md`

- [ ] **Step 1: Document the behavioral loop**

Add a subsection under "Enrichment & personalization" in `docs/superpowers/legal-feed-ops.md`:

> **Behavioral curation (news):** the feed learns from engagement — opening an
> article ("Read at source") is a positive signal; "Not interested" demotes that
> item for the user and, after 3+ rejections, steers the feed away from similar
> items. Updates are instant (online), and **"Recompute behavior"** in `/admin`
> re-grounds all users' vectors from the event log (safe to run on a schedule).

- [ ] **Step 2: Run the full backend suite**

Run: `cd backend && python -m pytest -q`
Expected: all legal-feed tests pass (the 3 pre-existing `tests/test_api.py` failures targeting `/api/clients` are unrelated and may remain).

- [ ] **Step 3: Commit**

```bash
git add docs/superpowers/legal-feed-ops.md
git commit -m "docs(legal-feed): document behavioral curation"
```

---

## Self-Review

**Spec coverage:**
- Behavioral driver / signals (clicks + not-interested) → Tasks 2, 4, 6, 9 ✓
- Online EMA + batch recompute → Tasks 1, 4 (+ admin trigger Task 7) ✓
- Negative guardrail (single = demote only; learning at N=3) → Tasks 1 (`apply_event`), 4 (`recompute`), 5 (demotion) ✓
- Blended ranking (phrases + behavior, bw ramp) → Tasks 1 (`blend_interest`), 5 ✓
- Demotion not suppression (REJECT_PENALTY) → Tasks 3, 5, 6 (for-you + latest) ✓
- Volume (30 + load-more via offset) → Tasks 5, 6, 8, 9 ✓
- Dense 3-column news layout; judgements unchanged → Task 9 ✓
- Events API → Task 6 ✓
- Error handling (best-effort events, no-embedding no-op, pref auto-create) → Tasks 4, 9 ✓

**Placeholder scan:** No TODO/TBD; all code blocks complete. Test helpers (`_item`, `auth_headers`, `make_user`, `_h`, `FakeItem`) already exist in their files (Task 3 extends `FakeItem`; Task 5 reuses `_item`; Tasks 6 reuse `auth_headers`/`make_user`; Task 7 reuses `_h`).

**Type consistency:** `apply_event(behavior, item_embedding, kind, not_interested_count)`, `blend_interest(interest, behavior, event_count)`, `record_event(user_id, item_id, kind)`, `get_rejected_item_ids(user_id)`, `event_count(user_id)`, `recompute_behavior_embedding(user_id)`, `rank_by_similarity(..., penalized_ids=, penalty=)`, `query_for_you(user_id, content_type, limit, offset, window_days, now)`, `query_feed(..., demote_ids=)` are used consistently across tasks. Frontend `postLegalFeedEvent(item_id, kind)` and `getLegalFeedForYou({type, limit, offset})` match Task 8 ↔ Task 9.
