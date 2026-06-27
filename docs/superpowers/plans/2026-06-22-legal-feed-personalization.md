# Legal Feed Personalization & Enrichment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the legal feed impactful and personalized — enrich items at ingest (punchy news headlines, "why it matters" TL;DRs, practice-area topics, importance, embeddings), and serve a per-user "For you" shelf above a chronological "Latest" list — plus three small adjacent fixes.

**Architecture:** Ingestion stays two-phase: a reliable *ingest* phase (unchanged + image extraction) followed by a best-effort *enrich* phase that calls OpenAI (chat + embeddings) behind a pluggable `EnrichmentClient`. Enriched items carry topics/importance/embedding; personalization is a server-side query that filters by the user's stored taxonomy preferences and ranks candidates by Python cosine similarity to the user's interest embedding, blended with importance and recency. Embeddings are stored as JSON float arrays (pgvector is a later drop-in).

**Tech Stack:** Flask 3 + Flask-SQLAlchemy, OpenAI HTTP API via `requests` (no SDK), pytest on in-memory SQLite, React 18 + react-router + Tailwind.

## Global Constraints

- All user-facing endpoints live under `/api/v1` (blueprint registered with that prefix). Admin endpoints live under `/admin`.
- New dependencies: **none** — OpenAI is called via the existing `requests` dependency, mirroring `email_service.py`'s Resend transport.
- Enrichment must **degrade gracefully**: if `OPENAI_API_KEY` is unset or a call fails, the item still ingests with raw fields and `enriched_at` stays NULL.
- The LLM may only emit topics from the fixed taxonomy; **judgements never get a `headline` or `tldr`**.
- Only public RSS content (title/summary) is ever sent to OpenAI — never client/firm/invoice data.
- Embeddings stored as JSON float arrays in `db.JSON` columns (works on SQLite + Postgres). Similarity is computed in Python behind `rank_by_similarity()`.
- Tests run against in-memory SQLite via the existing `app`/`client`/`db` fixtures in `backend/tests/conftest.py`.
- Frontend has no unit runner — verify with `npm run build` (tsc + vite) and `npm run lint -- --max-warnings 0`.
- Tailwind tokens in use: `text-ink`, `text-ink-soft`, `text-ink-muted`, `text-ink-faint`, `bg-paper`, `border-rule`, `eyebrow`, `oxblood`, `text-2xs`.
- **Git is performed by the repo owner (Parth), not the executing agent.** The `git commit` step in each task is a checkpoint marker; the agent prepares the change and the owner commits. Do not run `git` commands.

---

### Task 1: Practice-area taxonomy

**Files:**
- Create: `backend/app/services/legal_feed/taxonomy.py`
- Test: `backend/tests/test_legal_feed_taxonomy.py`

**Interfaces:**
- Produces: `PRACTICE_AREAS: list[str]` (the 12 fixed topics); `normalize_topics(raw: list) -> list[str]` (keeps only valid taxonomy members, de-duplicated, preserving input order).

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_legal_feed_taxonomy.py
from app.services.legal_feed.taxonomy import PRACTICE_AREAS, normalize_topics


def test_taxonomy_has_twelve_fixed_areas():
    assert len(PRACTICE_AREAS) == 12
    assert 'Tax' in PRACTICE_AREAS
    assert 'Arbitration' in PRACTICE_AREAS


def test_normalize_drops_unknown_and_dedupes_preserving_order():
    assert normalize_topics(['Tax', 'Bogus', 'Tax', 'IP']) == ['Tax', 'IP']


def test_normalize_handles_non_list_and_non_strings():
    assert normalize_topics(None) == []
    assert normalize_topics(['Tax', 5, {'x': 1}]) == ['Tax']
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_legal_feed_taxonomy.py -v`
Expected: FAIL with `ModuleNotFoundError: app.services.legal_feed.taxonomy`

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/services/legal_feed/taxonomy.py
"""The fixed practice-area taxonomy shared by the LLM classifier and the user
preference UI. They MUST agree, so both read this one list."""

PRACTICE_AREAS = [
    'Tax', 'Criminal', 'Civil', 'Constitutional', 'Corporate/Commercial', 'IP',
    'Environment', 'Labour/Service', 'Family', 'Property', 'Banking/Insolvency',
    'Arbitration',
]

_VALID = set(PRACTICE_AREAS)


def normalize_topics(raw) -> list:
    """Keep only valid taxonomy members, de-duplicated, in input order."""
    if not isinstance(raw, list):
        return []
    seen, out = set(), []
    for t in raw:
        if isinstance(t, str) and t in _VALID and t not in seen:
            seen.add(t)
            out.append(t)
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_legal_feed_taxonomy.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/legal_feed/taxonomy.py backend/tests/test_legal_feed_taxonomy.py
git commit -m "feat(legal-feed): add fixed practice-area taxonomy"
```

---

### Task 2: Schema — item enrichment columns, run counters, preference table

**Files:**
- Modify: `backend/app/models/models.py:283-330` (LegalFeedItem, LegalFeedRun) and append `LegalFeedPreference` before `def init_db():` (line ~344)
- Modify: `backend/app/main.py` (import the new model in the `db.create_all()` app-context block)
- Test: `backend/tests/test_legal_feed_models.py` (append)

**Interfaces:**
- Produces: `LegalFeedItem` columns `headline, tldr, topics, importance, image_url, embedding, embed_model, enriched_at`; `LegalFeedItem.to_dict()` exposes `headline, tldr, topics, importance, image_url` (NOT embedding). `LegalFeedRun` columns `enriched, enrich_failed` (in `to_dict()`). New `LegalFeedPreference(user_id, topic_weights, courts, interest_phrases, interest_embedding, embed_model, updated_at)` with `to_dict()`.

- [ ] **Step 1: Write the failing test**

```python
# append to backend/tests/test_legal_feed_models.py
from app.models.models import LegalFeedItem, LegalFeedRun, LegalFeedPreference


def test_item_enrichment_fields_default_and_serialize(db):
    item = LegalFeedItem(
        content_type='news', title='t', source_url='u', source_name='s',
        dedup_key='k-enrich', headline='Punchy', tldr='Why it matters',
        topics=['Tax'], importance=80, image_url='http://img', embedding=[0.1, 0.2],
        embed_model='text-embedding-3-small',
    )
    db.session.add(item)
    db.session.commit()
    d = item.to_dict()
    assert d['headline'] == 'Punchy'
    assert d['topics'] == ['Tax']
    assert d['importance'] == 80
    assert d['image_url'] == 'http://img'
    assert 'embedding' not in d  # never leak vectors to the client


def test_run_has_enrichment_counters(db):
    run = LegalFeedRun(trigger='manual', status='success')
    db.session.add(run)
    db.session.commit()
    d = run.to_dict()
    assert d['enriched'] == 0
    assert d['enrich_failed'] == 0


def test_preference_roundtrip(db):
    pref = LegalFeedPreference(
        user_id=7, topic_weights={'Tax': 1.0}, courts=['Delhi HC'],
        interest_phrases=['GST input credit'], interest_embedding=[0.3, 0.4],
        embed_model='text-embedding-3-small',
    )
    db.session.add(pref)
    db.session.commit()
    d = pref.to_dict()
    assert d['user_id'] == 7
    assert d['topic_weights'] == {'Tax': 1.0}
    assert d['interest_phrases'] == ['GST input credit']
    assert 'interest_embedding' not in d  # vectors stay server-side
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_legal_feed_models.py -v`
Expected: FAIL (`ImportError: cannot import name 'LegalFeedPreference'`)

- [ ] **Step 3: Write minimal implementation**

In `backend/app/models/models.py`, add these columns to `LegalFeedItem` (after `dedup_key`, line ~298):

```python
    # Enrichment (best-effort; NULL enriched_at means "not yet enriched")
    headline = db.Column(db.Text)        # punchy rewrite, news only
    tldr = db.Column(db.Text)            # "why it matters", news only
    topics = db.Column(db.JSON)          # subset of taxonomy
    importance = db.Column(db.Integer)   # 0-100
    image_url = db.Column(db.String(1000))
    embedding = db.Column(db.JSON)       # list[float]
    embed_model = db.Column(db.String(80))
    enriched_at = db.Column(db.DateTime)
```

Extend `LegalFeedItem.to_dict()` return dict with (before the closing `}`):

```python
            'headline': self.headline, 'tldr': self.tldr,
            'topics': self.topics or [], 'importance': self.importance,
            'image_url': self.image_url,
            'enriched_at': self.enriched_at.isoformat() if self.enriched_at else None,
```

Add to `LegalFeedRun` (after `results`, line ~321):

```python
    enriched = db.Column(db.Integer, nullable=False, default=0)
    enrich_failed = db.Column(db.Integer, nullable=False, default=0)
```

Extend `LegalFeedRun.to_dict()` with:

```python
            'enriched': self.enriched or 0, 'enrich_failed': self.enrich_failed or 0,
```

Append a new model before `def init_db():`:

```python
class LegalFeedPreference(db.Model):
    """Per-user feed personalization: macro taxonomy weights + micro interest
    embedding (seeded from free-text phrases). Server-synced (cross-device)."""
    __tablename__ = 'legal_feed_preferences'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False, unique=True, index=True)
    topic_weights = db.Column(db.JSON, default=dict)   # {topic: weight}
    courts = db.Column(db.JSON, default=list)          # [court]
    interest_phrases = db.Column(db.JSON, default=list)
    interest_embedding = db.Column(db.JSON)            # list[float]
    embed_model = db.Column(db.String(80))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'user_id': self.user_id,
            'topic_weights': self.topic_weights or {},
            'courts': self.courts or [],
            'interest_phrases': self.interest_phrases or [],
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
```

In `backend/app/main.py`, add `LegalFeedPreference` to the model import inside the `db.create_all()` app-context block (the same line that imports the other legal feed models).

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_legal_feed_models.py -v`
Expected: PASS (all model tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/models.py backend/app/main.py backend/tests/test_legal_feed_models.py
git commit -m "feat(legal-feed): add enrichment columns, run counters, preference table"
```

---

### Task 3: RSS image extraction

**Files:**
- Modify: `backend/app/services/legal_feed/rss.py:29-43` (`parse_feed`)
- Modify: `backend/tests/test_legal_feed_rss.py` (append) and `backend/tests/fixtures/sample_feed.xml` (add an image to one entry)
- Test: `backend/tests/test_legal_feed_rss.py`

**Interfaces:**
- Produces: each dict from `parse_feed` now includes `'image_url'` (str or None). Existing keys (`title, summary, source_url, published_at`) unchanged.
- Consumes (Task 6): `ingest._ingest_source` will read `it.get('image_url')`.

- [ ] **Step 1: Write the failing test**

```python
# append to backend/tests/test_legal_feed_rss.py
def test_parse_feed_extracts_image_from_media_content():
    raw = '''<?xml version="1.0"?>
    <rss xmlns:media="http://search.yahoo.com/mrss/" version="2.0"><channel>
      <item><title>With image</title><link>http://x/1</link>
        <media:content url="http://img/pic.jpg"/></item>
      <item><title>No image</title><link>http://x/2</link></item>
    </channel></rss>'''
    items = parse_feed(raw)
    assert items[0]['image_url'] == 'http://img/pic.jpg'
    assert items[1]['image_url'] is None


def test_parse_feed_falls_back_to_enclosure_image():
    raw = '''<?xml version="1.0"?>
    <rss version="2.0"><channel>
      <item><title>Enc</title><link>http://x/3</link>
        <enclosure url="http://img/enc.png" type="image/png"/></item>
    </channel></rss>'''
    assert parse_feed(raw)[0]['image_url'] == 'http://img/enc.png'
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_legal_feed_rss.py -v`
Expected: FAIL (`KeyError: 'image_url'`)

- [ ] **Step 3: Write minimal implementation**

In `backend/app/services/legal_feed/rss.py`, add a helper above `parse_feed`:

```python
def _extract_image(entry):
    media = entry.get('media_content') or []
    for m in media:
        url = m.get('url')
        if url:
            return url
    for enc in entry.get('enclosures') or []:
        if str(enc.get('type', '')).startswith('image') and enc.get('href'):
            return enc.get('href')
        if enc.get('href') and not enc.get('type'):
            return enc.get('href')
    thumb = entry.get('media_thumbnail') or []
    if thumb and thumb[0].get('url'):
        return thumb[0]['url']
    return None
```

In the `parse_feed` loop, add `'image_url': _extract_image(entry),` to the appended dict.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_legal_feed_rss.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/legal_feed/rss.py backend/tests/test_legal_feed_rss.py
git commit -m "feat(legal-feed): extract item image URL from RSS"
```

---

### Task 4: Similarity ranking

**Files:**
- Create: `backend/app/services/legal_feed/similarity.py`
- Test: `backend/tests/test_legal_feed_similarity.py`

**Interfaces:**
- Produces:
  - `cosine(a: list, b: list) -> float` (0.0 if either is empty/None or zero-norm).
  - `score_item(item, interest_embedding, now) -> float` — blended: `sim * (0.5 + 0.5*importance/100) * recency_decay`, where `sim = cosine(item.embedding, interest_embedding)` but **falls back to 1.0 when `interest_embedding` is falsy** (cold start → importance×recency only), and `recency_decay = 0.5 ** (age_days / 14)` using `published_at or ingested_at`.
  - `rank_by_similarity(items: list, interest_embedding, now=None) -> list` — returns items sorted by `score_item` descending.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_legal_feed_similarity.py
from datetime import datetime, timedelta
from app.services.legal_feed.similarity import cosine, rank_by_similarity


class FakeItem:
    def __init__(self, embedding, importance=50, age_days=0):
        self.embedding = embedding
        self.importance = importance
        self.published_at = datetime(2026, 6, 22) - timedelta(days=age_days)
        self.ingested_at = self.published_at


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_legal_feed_similarity.py -v`
Expected: FAIL (`ModuleNotFoundError`)

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/services/legal_feed/similarity.py
"""Pure-Python ranking for the 'For you' feed. Brute-force cosine over a
taxonomy/recency-filtered candidate set; swap in pgvector here if it grows."""
import math
from datetime import datetime

RECENCY_HALF_LIFE_DAYS = 14


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


def rank_by_similarity(items, interest_embedding, now=None) -> list:
    now = now or datetime.utcnow()
    return sorted(items, key=lambda it: score_item(it, interest_embedding, now), reverse=True)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_legal_feed_similarity.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/legal_feed/similarity.py backend/tests/test_legal_feed_similarity.py
git commit -m "feat(legal-feed): add cosine similarity ranking"
```

---

### Task 5: Enrichment client + content-type-aware enrich

**Files:**
- Create: `backend/app/services/legal_feed/enrichment.py`
- Test: `backend/tests/test_legal_feed_enrichment.py`

**Interfaces:**
- Produces:
  - `class EnrichmentClient` with `complete(system: str, user: str) -> str` and `embed(text: str) -> list[float]`.
  - `class OpenAIEnrichment(EnrichmentClient)` — calls OpenAI chat (`response_format={'type':'json_object'}`) and embeddings via `requests`. Reads `OPENAI_API_KEY`, `LEGAL_FEED_ENRICH_MODEL`, `LEGAL_FEED_EMBED_MODEL` (default `text-embedding-3-small`). `embed_model` attribute exposes the embedding model name.
  - `get_enrichment_client() -> EnrichmentClient | None` — returns `OpenAIEnrichment()` if `OPENAI_API_KEY` set, else `None`.
  - `enrich_item(item, client) -> bool` — content-type-aware. Mutates `item` (headline/tldr for news only; topics/importance/embedding/embed_model/enriched_at for all). Returns True on success, False on any failure (item left with `enriched_at` NULL). Validates topics against taxonomy, clamps importance 0–100, strips headline/tldr for judgements.
- Consumes (Task 6): `ingest` calls `get_enrichment_client()` and `enrich_item(item, client)`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_legal_feed_enrichment.py
import json
from app.models.models import LegalFeedItem
from app.services.legal_feed.enrichment import enrich_item


class FakeClient:
    embed_model = 'text-embedding-3-small'

    def __init__(self, completion):
        self._completion = completion
        self.embed_calls = []

    def complete(self, system, user):
        return self._completion

    def embed(self, text):
        self.embed_calls.append(text)
        return [0.1, 0.2, 0.3]


def _news():
    return LegalFeedItem(content_type='news', title='Court rules on GST',
                         summary='A summary', source_url='u', source_name='s',
                         dedup_key='n1')


def _judgement():
    return LegalFeedItem(content_type='judgement', title='X v. Y',
                         summary='Held that...', source_url='u', source_name='s',
                         dedup_key='j1')


def test_news_gets_full_enrichment(db):
    item = _news()
    client = FakeClient(json.dumps({
        'headline': 'GST relief for exporters',
        'tldr': 'Exporters can now claim refunds faster.',
        'topics': ['Tax', 'NotARealTopic'], 'importance': 150,
    }))
    assert enrich_item(item, client) is True
    assert item.headline == 'GST relief for exporters'
    assert item.tldr.startswith('Exporters')
    assert item.topics == ['Tax']           # bogus topic dropped
    assert item.importance == 100           # clamped
    assert item.embedding == [0.1, 0.2, 0.3]
    assert item.embed_model == 'text-embedding-3-small'
    assert item.enriched_at is not None


def test_judgement_never_gets_headline_or_tldr(db):
    item = _judgement()
    client = FakeClient(json.dumps({
        'headline': 'should be ignored', 'tldr': 'should be ignored',
        'topics': ['Civil'], 'importance': 60,
    }))
    assert enrich_item(item, client) is True
    assert item.headline is None
    assert item.tldr is None
    assert item.topics == ['Civil']
    assert item.importance == 60


def test_bad_json_is_a_failure(db):
    item = _news()
    assert enrich_item(item, FakeClient('not json')) is False
    assert item.enriched_at is None


def test_embed_text_uses_title_and_summary(db):
    item = _judgement()
    client = FakeClient(json.dumps({'topics': ['Civil'], 'importance': 50}))
    enrich_item(item, client)
    assert 'X v. Y' in client.embed_calls[0]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_legal_feed_enrichment.py -v`
Expected: FAIL (`ModuleNotFoundError`)

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/services/legal_feed/enrichment.py
"""LLM enrichment behind a pluggable client (mirrors email_service transports).

Only public RSS content (title/summary) is sent to OpenAI. Failures are
non-fatal: the item keeps its raw fields and enriched_at stays NULL.
"""
import json
import os
from datetime import datetime

from app.services.legal_feed.taxonomy import PRACTICE_AREAS, normalize_topics

OPENAI_CHAT_URL = 'https://api.openai.com/v1/chat/completions'
OPENAI_EMBED_URL = 'https://api.openai.com/v1/embeddings'
DEFAULT_EMBED_MODEL = 'text-embedding-3-small'

_NEWS_SYSTEM = (
    'You are a legal news editor for practising Indian lawyers. Given a news '
    'item title and summary, return STRICT JSON with keys: '
    '"headline" (a punchy, accurate <=12 word rewrite), '
    '"tldr" (1-2 sentences on why it matters to a practitioner), '
    '"topics" (array, each EXACTLY one of: ' + ', '.join(PRACTICE_AREAS) + '), '
    '"importance" (integer 0-100). Do not invent facts beyond the input.'
)
_JUDGEMENT_SYSTEM = (
    'You classify Indian court judgements for practising lawyers. Given a case '
    'title and summary, return STRICT JSON with keys: '
    '"topics" (array, each EXACTLY one of: ' + ', '.join(PRACTICE_AREAS) + '), '
    '"importance" (integer 0-100). Do NOT summarize or restate the holding.'
)


class EnrichmentClient:
    embed_model = DEFAULT_EMBED_MODEL

    def complete(self, system, user):  # pragma: no cover - interface
        raise NotImplementedError

    def embed(self, text):  # pragma: no cover - interface
        raise NotImplementedError


class OpenAIEnrichment(EnrichmentClient):
    def __init__(self, api_key=None, chat_model=None, embed_model=None):
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        self.chat_model = chat_model or os.getenv('LEGAL_FEED_ENRICH_MODEL', 'gpt-4o-mini')
        self.embed_model = embed_model or os.getenv('LEGAL_FEED_EMBED_MODEL', DEFAULT_EMBED_MODEL)

    def _post(self, url, payload):
        import requests
        resp = requests.post(
            url, json=payload,
            headers={'Authorization': f'Bearer {self.api_key}'}, timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    def complete(self, system, user):
        data = self._post(OPENAI_CHAT_URL, {
            'model': self.chat_model,
            'response_format': {'type': 'json_object'},
            'messages': [{'role': 'system', 'content': system},
                         {'role': 'user', 'content': user}],
        })
        return data['choices'][0]['message']['content']

    def embed(self, text):
        data = self._post(OPENAI_EMBED_URL, {'model': self.embed_model, 'input': text})
        return data['data'][0]['embedding']


def get_enrichment_client():
    if not os.getenv('OPENAI_API_KEY'):
        return None
    return OpenAIEnrichment()


def _clamp_importance(raw):
    try:
        return max(0, min(100, int(raw)))
    except (TypeError, ValueError):
        return None


def enrich_item(item, client) -> bool:
    """Enrich one item in place. Returns True on success, False on any failure."""
    is_news = item.content_type == 'news'
    system = _NEWS_SYSTEM if is_news else _JUDGEMENT_SYSTEM
    user = f"Title: {item.title}\nSummary: {item.summary or ''}"
    try:
        parsed = json.loads(client.complete(system, user))
        if not isinstance(parsed, dict):
            return False
        topics = normalize_topics(parsed.get('topics'))
        importance = _clamp_importance(parsed.get('importance'))
        embed_text = f"{item.title}\n{item.summary or ''}"
        if is_news:
            embed_text = f"{parsed.get('headline') or item.title}\n{parsed.get('tldr') or ''}\n{item.summary or ''}"
        embedding = client.embed(embed_text)
    except Exception:
        return False

    if is_news:
        item.headline = (parsed.get('headline') or '').strip() or None
        item.tldr = (parsed.get('tldr') or '').strip() or None
    else:
        item.headline = None
        item.tldr = None
    item.topics = topics
    item.importance = importance
    item.embedding = embedding
    item.embed_model = getattr(client, 'embed_model', DEFAULT_EMBED_MODEL)
    item.enriched_at = datetime.utcnow()
    return True
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_legal_feed_enrichment.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/legal_feed/enrichment.py backend/tests/test_legal_feed_enrichment.py
git commit -m "feat(legal-feed): add OpenAI enrichment client and content-type-aware enrich"
```

---

### Task 6: Wire enrichment into ingestion + backlog backfill

**Files:**
- Modify: `backend/app/services/legal_feed/ingest.py` (insert image on item, add enrich phase, run counters, `enrich_backlog`)
- Test: `backend/tests/test_legal_feed_ingest.py` (append)

**Interfaces:**
- Consumes: `get_enrichment_client()`, `enrich_item(item, client)` (Task 5); `it.get('image_url')` (Task 3).
- Produces:
  - `run_ingestion(trigger)` now: sets `image_url` on inserted items, runs an enrich phase over newly-inserted items when a client is available, and records `run.enriched` / `run.enrich_failed`.
  - `enrich_backlog(limit=100, client=None) -> dict` — enriches up to `limit` items with `enriched_at IS NULL`; returns `{'attempted', 'enriched', 'failed'}`. No-op (`attempted=0`) if no client.

- [ ] **Step 1: Write the failing test**

```python
# append to backend/tests/test_legal_feed_ingest.py
import json
from app.models.models import LegalFeedSource, LegalFeedItem
from app.services.legal_feed.ingest import run_ingestion, enrich_backlog


class _FakeClient:
    embed_model = 'text-embedding-3-small'
    def complete(self, system, user):
        return json.dumps({'headline': 'H', 'tldr': 'T', 'topics': ['Tax'], 'importance': 70})
    def embed(self, text):
        return [0.1, 0.2]


def test_backlog_enriches_unenriched_items(db, monkeypatch):
    import app.services.legal_feed.ingest as ing
    db.session.add(LegalFeedItem(content_type='news', title='t', source_url='u',
                                 source_name='s', dedup_key='b1'))
    db.session.commit()
    monkeypatch.setattr(ing, 'get_enrichment_client', lambda: _FakeClient())

    out = enrich_backlog(limit=10)
    assert out['enriched'] == 1
    item = LegalFeedItem.query.filter_by(dedup_key='b1').first()
    assert item.enriched_at is not None
    assert item.topics == ['Tax']


def test_backlog_noop_without_client(db, monkeypatch):
    import app.services.legal_feed.ingest as ing
    db.session.add(LegalFeedItem(content_type='news', title='t', source_url='u',
                                 source_name='s', dedup_key='b2'))
    db.session.commit()
    monkeypatch.setattr(ing, 'get_enrichment_client', lambda: None)
    out = enrich_backlog()
    assert out['attempted'] == 0


def test_run_records_enrichment_counters(db, monkeypatch):
    import app.services.legal_feed.ingest as ing
    src = LegalFeedSource(name='S', content_type='news', kind='rss',
                          feed_url='http://feed', enabled=True, weight=1)
    db.session.add(src)
    db.session.commit()

    monkeypatch.setattr(ing.rss, 'fetch_raw', lambda url: 'raw')
    monkeypatch.setattr(ing.rss, 'parse_feed', lambda raw: [
        {'title': 'News A', 'summary': 's', 'source_url': 'http://x/a',
         'published_at': None, 'image_url': 'http://img/a'},
    ])
    monkeypatch.setattr(ing, 'get_enrichment_client', lambda: _FakeClient())

    result = run_ingestion('manual')
    assert result['total_ingested'] == 1
    assert result['enriched'] == 1
    item = LegalFeedItem.query.filter_by(source_url='http://x/a').first()
    assert item.image_url == 'http://img/a'
    assert item.headline == 'H'
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_legal_feed_ingest.py -v`
Expected: FAIL (`ImportError: cannot import name 'enrich_backlog'`)

- [ ] **Step 3: Write minimal implementation**

In `backend/app/services/legal_feed/ingest.py`:

Update imports at top:

```python
from app.services.legal_feed import rss
from app.services.legal_feed.enrichment import get_enrichment_client, enrich_item
```

In `_ingest_source`, add `image_url=it.get('image_url'),` to the `LegalFeedItem(...)` constructor, and make it also collect inserted ids. Change the function to track inserted items:

```python
def _ingest_source(source) -> dict:
    result = {'source_id': source.id, 'fetched': 0, 'inserted': 0,
              'inserted_ids': [], 'error': None}
    fetcher = FETCHERS.get(source.kind)
    if fetcher is None:
        result['error'] = f'unknown source kind: {source.kind}'
        return result
    try:
        raw = fetcher.fetch_raw(source.feed_url)
        items = fetcher.parse_feed(raw)
        result['fetched'] = len(items)
        for it in items:
            key = compute_dedup_key(it['source_url'], source.name, it['title'])
            if LegalFeedItem.query.filter_by(dedup_key=key).first():
                continue
            row = LegalFeedItem(
                source_id=source.id, content_type=source.content_type,
                title=it['title'], summary=it.get('summary'),
                source_url=it['source_url'], source_name=source.name,
                court=source.court, published_at=it.get('published_at'),
                image_url=it.get('image_url'), hidden=False, dedup_key=key,
            )
            db.session.add(row)
            db.session.flush()
            result['inserted'] += 1
            result['inserted_ids'].append(row.id)
        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        result['error'] = str(exc)
    return result
```

Add an enrich helper and update `run_ingestion`:

```python
def _enrich_ids(ids, client) -> tuple:
    """Enrich the given item ids. Returns (enriched, failed)."""
    enriched = failed = 0
    for item_id in ids:
        item = LegalFeedItem.query.get(item_id)
        if item is None or item.enriched_at is not None:
            continue
        if enrich_item(item, client):
            enriched += 1
        else:
            failed += 1
    db.session.commit()
    return enriched, failed


def run_ingestion(trigger: str) -> dict:
    run = LegalFeedRun(started_at=datetime.utcnow(), trigger=trigger,
                       status='success', total_ingested=0, results=[])
    db.session.add(run)
    db.session.commit()

    sources = LegalFeedSource.query.filter_by(enabled=True).all()
    results = [_ingest_source(s) for s in sources]

    enriched = failed = 0
    client = get_enrichment_client()
    if client is not None:
        new_ids = [i for r in results for i in r.get('inserted_ids', [])]
        enriched, failed = _enrich_ids(new_ids, client)

    error_count = sum(1 for r in results if r['error'])
    if error_count == 0:
        status = 'success'
    elif error_count == len(results):
        status = 'failed'
    else:
        status = 'partial'

    # inserted_ids is internal bookkeeping; drop it from the persisted audit log.
    for r in results:
        r.pop('inserted_ids', None)

    run.finished_at = datetime.utcnow()
    run.total_ingested = sum(r['inserted'] for r in results)
    run.enriched = enriched
    run.enrich_failed = failed
    run.status = status
    run.results = results
    db.session.commit()
    return run.to_dict()


def enrich_backlog(limit=100, client=None) -> dict:
    """Deliberately enrich already-ingested items (enriched_at IS NULL)."""
    client = client or get_enrichment_client()
    if client is None:
        return {'attempted': 0, 'enriched': 0, 'failed': 0}
    rows = (LegalFeedItem.query
            .filter(LegalFeedItem.enriched_at.is_(None))
            .order_by(LegalFeedItem.id.desc()).limit(limit).all())
    ids = [r.id for r in rows]
    enriched, failed = _enrich_ids(ids, client)
    return {'attempted': len(ids), 'enriched': enriched, 'failed': failed}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_legal_feed_ingest.py -v`
Expected: PASS (existing + 3 new)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/legal_feed/ingest.py backend/tests/test_legal_feed_ingest.py
git commit -m "feat(legal-feed): enrich new items during ingestion + backlog backfill"
```

---

### Task 7: Preferences service

**Files:**
- Create: `backend/app/services/legal_feed/preferences.py`
- Test: `backend/tests/test_legal_feed_preferences.py`

**Interfaces:**
- Produces:
  - `get_preference(user_id) -> LegalFeedPreference | None`.
  - `upsert_preference(user_id, topic_weights, courts, interest_phrases, client=None) -> LegalFeedPreference` — validates topic_weights keys against taxonomy, embeds the joined `interest_phrases` into `interest_embedding` when a client is available (else leaves embedding None), stamps `embed_model`, commits.
- Consumes: `enrichment.get_enrichment_client`, `taxonomy.PRACTICE_AREAS`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_legal_feed_preferences.py
from app.services.legal_feed.preferences import get_preference, upsert_preference


class _Embedder:
    embed_model = 'text-embedding-3-small'
    def embed(self, text):
        return [0.5, 0.6]


def test_upsert_creates_and_embeds(db):
    pref = upsert_preference(1, {'Tax': 1.0, 'Bogus': 9.0}, ['Delhi HC'],
                             ['GST input credit'], client=_Embedder())
    assert pref.topic_weights == {'Tax': 1.0}          # bogus key dropped
    assert pref.interest_embedding == [0.5, 0.6]
    assert pref.embed_model == 'text-embedding-3-small'
    assert get_preference(1).courts == ['Delhi HC']


def test_upsert_updates_existing(db):
    upsert_preference(2, {'IP': 1.0}, [], [], client=_Embedder())
    pref = upsert_preference(2, {'Criminal': 1.0}, ['Bombay HC'], [], client=_Embedder())
    assert pref.topic_weights == {'Criminal': 1.0}
    from app.models.models import LegalFeedPreference
    assert LegalFeedPreference.query.filter_by(user_id=2).count() == 1


def test_upsert_without_client_leaves_embedding_none(db):
    pref = upsert_preference(3, {'Tax': 1.0}, [], ['anything'], client=None)
    assert pref.interest_embedding is None


def test_upsert_no_phrases_clears_embedding(db):
    upsert_preference(4, {'Tax': 1.0}, [], ['x'], client=_Embedder())
    pref = upsert_preference(4, {'Tax': 1.0}, [], [], client=_Embedder())
    assert pref.interest_embedding is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_legal_feed_preferences.py -v`
Expected: FAIL (`ModuleNotFoundError`)

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/services/legal_feed/preferences.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_legal_feed_preferences.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/legal_feed/preferences.py backend/tests/test_legal_feed_preferences.py
git commit -m "feat(legal-feed): add user preference persistence with interest embedding"
```

---

### Task 8: Query — distinct courts + "For you"

**Files:**
- Modify: `backend/app/services/legal_feed/query.py` (add `list_courts`, `query_for_you`)
- Test: `backend/tests/test_legal_feed_query.py` (new)

**Interfaces:**
- Consumes: `preferences.get_preference` (Task 7), `similarity.rank_by_similarity` (Task 4).
- Produces:
  - `list_courts() -> list[str]` — distinct, non-null courts of enabled sources, sorted.
  - `query_for_you(user_id, content_type, limit=10, window_days=14, now=None) -> list[dict]` — candidate filter (content_type, hidden=False, within window, matching the user's topics/courts when a preference exists) then `rank_by_similarity` against the user's `interest_embedding`, top `limit`, serialized via `to_dict()`. With no preference → global importance×recency fallback (cold start).

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_legal_feed_query.py
from datetime import datetime, timedelta
from app.models.models import db as _db, LegalFeedSource, LegalFeedItem
from app.services.legal_feed.query import list_courts, query_for_you
from app.services.legal_feed.preferences import upsert_preference


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_legal_feed_query.py -v`
Expected: FAIL (`ImportError: cannot import name 'list_courts'`)

- [ ] **Step 3: Write minimal implementation**

Add to `backend/app/services/legal_feed/query.py`:

```python
from datetime import datetime, timedelta

from app.services.legal_feed.preferences import get_preference
from app.services.legal_feed.similarity import rank_by_similarity


def list_courts() -> list:
    rows = (db.session.query(LegalFeedSource.court)
            .filter(LegalFeedSource.enabled.is_(True),
                    LegalFeedSource.court.isnot(None))
            .distinct().all())
    return sorted({r[0] for r in rows if r[0]})


def query_for_you(user_id, content_type=None, limit=10, window_days=14, now=None) -> list:
    now = now or datetime.utcnow()
    cutoff = now - timedelta(days=window_days)
    pref = get_preference(user_id)

    q = LegalFeedItem.query.filter_by(hidden=False)
    if content_type:
        q = q.filter_by(content_type=content_type)
    q = q.filter(func.coalesce(LegalFeedItem.published_at, LegalFeedItem.ingested_at) >= cutoff)

    candidates = q.all()

    interest_embedding = None
    if pref is not None:
        interest_embedding = pref.interest_embedding
        topics = set((pref.topic_weights or {}).keys())
        courts = set(pref.courts or [])
        if topics or courts:
            def _matches(it):
                t_ok = bool(topics & set(it.topics or [])) if topics else False
                c_ok = it.court in courts if courts else False
                return t_ok or c_ok
            matched = [it for it in candidates if _matches(it)]
            if matched:
                candidates = matched

    ranked = rank_by_similarity(candidates, interest_embedding, now=now)
    return [it.to_dict() for it in ranked[:limit]]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_legal_feed_query.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/legal_feed/query.py backend/tests/test_legal_feed_query.py
git commit -m "feat(legal-feed): add court list and personalized for-you query"
```

---

### Task 9: User-facing API — courts, for-you, preferences

**Files:**
- Modify: `backend/app/api/legal_feed.py`
- Test: `backend/tests/test_legal_feed_api.py` (append)

**Interfaces:**
- Consumes: `query.list_courts`, `query.query_for_you`, `preferences.get_preference`, `preferences.upsert_preference`. Auth via `@jwt_required`; resolve the app user the same way as `invoices.py` (`User.query.filter_by(supabase_id=g.user_id)`).
- Produces routes (all under `/api/v1`):
  - `GET /legal-feed/courts` → `{'courts': [...]}`
  - `GET /legal-feed/for-you?type=&limit=` → `{'data': [...]}`
  - `GET /legal-feed/preferences` → preference `to_dict()` or defaults
  - `PUT /legal-feed/preferences` (body `{topic_weights, courts, interest_phrases}`) → updated `to_dict()`

- [ ] **Step 1: Write the failing test**

```python
# append to backend/tests/test_legal_feed_api.py
# NOTE: reuse this file's existing auth/JWT mock pattern + the helper that
# creates a User row. Below, `auth_headers` and `make_user` refer to the
# existing fixtures/helpers in this test module.

def test_courts_endpoint(client, db, auth_headers, make_user):
    from app.models.models import LegalFeedSource
    make_user(supabase_id='sb-1')
    db.session.add(LegalFeedSource(name='A', content_type='judgement', court='Delhi HC',
                                   kind='rss', feed_url='f1', enabled=True, weight=1))
    db.session.commit()
    resp = client.get('/api/v1/legal-feed/courts', headers=auth_headers('sb-1'))
    assert resp.status_code == 200
    assert resp.get_json()['courts'] == ['Delhi HC']


def test_put_then_get_preferences(client, db, auth_headers, make_user):
    make_user(supabase_id='sb-2')
    put = client.put('/api/v1/legal-feed/preferences', headers=auth_headers('sb-2'),
                     json={'topic_weights': {'Tax': 1.0}, 'courts': ['Delhi HC'],
                           'interest_phrases': []})
    assert put.status_code == 200
    got = client.get('/api/v1/legal-feed/preferences', headers=auth_headers('sb-2'))
    assert got.get_json()['topic_weights'] == {'Tax': 1.0}
    assert got.get_json()['courts'] == ['Delhi HC']


def test_for_you_requires_auth(client):
    assert client.get('/api/v1/legal-feed/for-you').status_code == 401
```

> If `auth_headers`/`make_user` helpers don't yet exist in `test_legal_feed_api.py`, add small local fixtures mirroring the JWT-mock approach already used by the file's existing `test_get_feed_*` tests (patch `jwt_required` / set `g.user_id`, insert a `User` row with the given `supabase_id`).

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_legal_feed_api.py -v`
Expected: FAIL (404 on the new routes)

- [ ] **Step 3: Write minimal implementation**

Replace `backend/app/api/legal_feed.py` body with the existing routes plus:

```python
from app.models.auth import User
from flask import g
from app.services.legal_feed.query import query_feed, list_courts, query_for_you
from app.services.legal_feed.preferences import get_preference, upsert_preference


def _current_user_id():
    user = User.query.filter_by(supabase_id=getattr(g, 'user_id', None)).first()
    return user.id if user else None


@bp.route('/legal-feed/courts', methods=['GET'])
@jwt_required
def get_courts():
    return jsonify({'courts': list_courts()})


@bp.route('/legal-feed/for-you', methods=['GET'])
@jwt_required
def get_for_you():
    uid = _current_user_id()
    if uid is None:
        return jsonify({'error': 'User not found'}), 401
    limit = request.args.get('limit', default=10, type=int)
    data = query_for_you(uid, content_type=request.args.get('type'), limit=limit)
    return jsonify({'data': data})


@bp.route('/legal-feed/preferences', methods=['GET'])
@jwt_required
def get_preferences():
    uid = _current_user_id()
    if uid is None:
        return jsonify({'error': 'User not found'}), 401
    pref = get_preference(uid)
    if pref is None:
        return jsonify({'user_id': uid, 'topic_weights': {}, 'courts': [],
                        'interest_phrases': [], 'updated_at': None})
    return jsonify(pref.to_dict())


@bp.route('/legal-feed/preferences', methods=['PUT'])
@jwt_required
def put_preferences():
    uid = _current_user_id()
    if uid is None:
        return jsonify({'error': 'User not found'}), 401
    body = request.get_json() or {}
    pref = upsert_preference(
        uid, body.get('topic_weights', {}), body.get('courts', []),
        body.get('interest_phrases', []),
    )
    return jsonify(pref.to_dict())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_legal_feed_api.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/legal_feed.py backend/tests/test_legal_feed_api.py
git commit -m "feat(legal-feed): add courts, for-you, and preferences endpoints"
```

---

### Task 10: Admin — per-source counts + backlog backfill

**Files:**
- Modify: `backend/app/api/admin.py` (`lf_sources` counts; new `lf_backfill` route; panel button + JS)
- Test: `backend/tests/test_admin_legal_feed.py` (append)

**Interfaces:**
- Consumes: `ingest.enrich_backlog` (Task 6).
- Produces:
  - `GET /admin/api/legal-feed/sources` items each gain `count_24h` and `count_last_run`.
  - `POST /admin/api/legal-feed/backfill` (body `{limit?}`) → `enrich_backlog` result dict.

- [ ] **Step 1: Write the failing test**

```python
# append to backend/tests/test_admin_legal_feed.py
# Reuse this file's existing admin-auth header helper (call it `admin_headers`).

def test_sources_include_counts(client, db, admin_headers):
    from datetime import datetime
    from app.models.models import LegalFeedSource, LegalFeedItem
    src = LegalFeedSource(name='S', content_type='news', kind='rss',
                          feed_url='f', enabled=True, weight=1)
    db.session.add(src)
    db.session.commit()
    db.session.add(LegalFeedItem(content_type='news', title='t', source_url='u',
                                 source_name='S', source_id=src.id, dedup_key='c1',
                                 ingested_at=datetime.utcnow()))
    db.session.commit()
    resp = client.get('/admin/api/legal-feed/sources', headers=admin_headers)
    row = [s for s in resp.get_json() if s['id'] == src.id][0]
    assert row['count_24h'] == 1


def test_backfill_route(client, db, admin_headers, monkeypatch):
    import app.api.admin as admin_mod
    monkeypatch.setattr(admin_mod, 'enrich_backlog',
                        lambda limit=100: {'attempted': 2, 'enriched': 2, 'failed': 0})
    resp = client.post('/admin/api/legal-feed/backfill', headers=admin_headers,
                       json={'limit': 5})
    assert resp.status_code == 200
    assert resp.get_json()['enriched'] == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_admin_legal_feed.py -v`
Expected: FAIL (`count_24h` KeyError / 404 on backfill)

- [ ] **Step 3: Write minimal implementation**

At the top of `backend/app/api/admin.py`, add import:

```python
from app.services.legal_feed.ingest import run_ingestion, enrich_backlog
from datetime import datetime, timedelta
```

(Adjust if `run_ingestion` is already imported — keep a single import line.)

Rewrite `lf_sources` (around line 517) to attach counts:

```python
@bp.route('/api/legal-feed/sources', methods=['GET'])
@requires_admin_auth
def lf_sources():
    from app.models.models import LegalFeedSource, LegalFeedItem, LegalFeedRun
    since = datetime.utcnow() - timedelta(hours=24)
    last_run = LegalFeedRun.query.order_by(LegalFeedRun.id.desc()).first()
    last_run_counts = {}
    if last_run and last_run.results:
        for r in last_run.results:
            last_run_counts[r.get('source_id')] = r.get('inserted', 0)
    out = []
    for s in LegalFeedSource.query.order_by(LegalFeedSource.id).all():
        d = s.to_dict()
        d['count_24h'] = LegalFeedItem.query.filter(
            LegalFeedItem.source_id == s.id,
            LegalFeedItem.ingested_at >= since).count()
        d['count_last_run'] = last_run_counts.get(s.id, 0)
        out.append(d)
    return jsonify(out)
```

Add the backfill route after `lf_seed`:

```python
@bp.route('/api/legal-feed/backfill', methods=['POST'])
@requires_admin_auth
def lf_backfill():
    limit = (request.get_json(silent=True) or {}).get('limit', 100)
    return jsonify(enrich_backlog(limit=limit))
```

In `ADMIN_PANEL_HTML`, next to the existing "Seed v1 sources" button (line ~249 area), add:

```html
<button class="btn" onclick="lfBackfill()" style="margin-left:8px;">Enrich backlog</button>
```

And in the `<script>` block, add the handler (near `lfSeed`):

```javascript
async function lfBackfill() {
    const r = await (await fetch('/admin/api/legal-feed/backfill',
        {method:'POST', headers:{'Content-Type':'application/json'},
         body: JSON.stringify({limit: 100})})).json();
    alert('Backfill: attempted ' + r.attempted + ', enriched ' + r.enriched + ', failed ' + r.failed);
    lfLoad();
}
```

In the sources rendering inside `lfLoad()`, append the counts to each source row's displayed text, e.g. ` (24h: ${s.count_24h}, last run: ${s.count_last_run})`.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_admin_legal_feed.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/admin.py backend/tests/test_admin_legal_feed.py
git commit -m "feat(admin): per-source content counts and enrich-backlog action"
```

---

### Task 11: CC the firm on invoice email (#4)

**Files:**
- Modify: `backend/app/services/email_service.py` (`EmailTransport.send`, `ResendTransport.send` accept `cc`)
- Modify: `backend/app/services/send_service.py` (`send_invoice` accepts + forwards `cc`)
- Modify: `backend/app/api/invoices.py:412` (pass `cc=firm.firm_email`)
- Test: `backend/tests/test_send_service.py` (append)

**Interfaces:**
- Produces: `send_invoice(..., cc=None)` forwards a cleaned CC to `transport.send(..., cc=...)`. `ResendTransport.send(..., cc=None)` adds `payload['cc'] = [cc]` only when `cc` is truthy and `cc != to`.

- [ ] **Step 1: Write the failing test**

```python
# append to backend/tests/test_send_service.py
from app.services.send_service import send_invoice


class _CapTransport:
    def __init__(self):
        self.kwargs = None
    def send(self, **kwargs):
        self.kwargs = kwargs


def _make_objs():
    inv = type('I', (), {'user_id': 1, 'id': 2, 'invoice_number': 'INV/1',
                         'status': 'draft', 'sent_at': None, 'sent_channel': None})()
    firm = type('F', (), {'firm_name': 'Acme', 'firm_email': 'firm@acme.test'})()
    client = type('C', (), {'email': 'client@x.test'})()
    return inv, firm, client


def test_cc_forwarded_to_transport(db):
    inv, firm, client = _make_objs()
    t = _CapTransport()
    send_invoice(inv, firm, client, 'email', transport=t, cc='firm@acme.test')
    assert t.kwargs['cc'] == 'firm@acme.test'


def test_cc_skipped_when_equals_recipient(db):
    inv, firm, client = _make_objs()
    client.email = 'firm@acme.test'   # same as cc
    t = _CapTransport()
    send_invoice(inv, firm, client, 'email', transport=t, cc='firm@acme.test')
    assert t.kwargs['cc'] is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_send_service.py -v`
Expected: FAIL (`send_invoice() got an unexpected keyword argument 'cc'`)

- [ ] **Step 3: Write minimal implementation**

In `send_service.py`, change the signature and email branch:

```python
def send_invoice(invoice, firm, client, channel, *, pdf_bytes=None,
                 subject=None, body=None, transport=None, base_url=None,
                 currency='INR', cc=None):
```

Inside the `channel == 'email'` block, compute a safe CC and pass it:

```python
        safe_cc = cc if (cc and cc != client.email) else None
        transport.send(
            to=client.email,
            subject=subject,
            body=body,
            pdf_bytes=pdf_bytes,
            pdf_name=pdf_name,
            from_name=getattr(firm, 'firm_name', None) if firm else None,
            reply_to=getattr(firm, 'firm_email', None) if firm else None,
            cc=safe_cc,
        )
```

In `email_service.py`, add `cc=None` to both `EmailTransport.send` and `ResendTransport.send` signatures, and in `ResendTransport.send` after the `reply_to` block:

```python
        if cc:
            payload['cc'] = [cc]
```

In `invoices.py`, update the `send_invoice(...)` call (line ~412) to add:

```python
            cc=(firm.firm_email if firm else None),
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_send_service.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/email_service.py backend/app/services/send_service.py backend/app/api/invoices.py backend/tests/test_send_service.py
git commit -m "feat(invoices): CC the firm email on invoice send"
```

---

### Task 12: Frontend API client

**Files:**
- Modify: `frontend/src/api.ts`

**Interfaces:**
- Produces:
  - Extended `LegalFeedItem` interface: `headline?: string|null; tldr?: string|null; topics?: string[]; importance?: number|null; image_url?: string|null`.
  - `LegalFeedPreference` interface: `topic_weights: Record<string, number>; courts: string[]; interest_phrases: string[]`.
  - `PRACTICE_AREAS: string[]` constant (mirrors backend taxonomy).
  - `api.getLegalFeedCourts(): Promise<string[]>`
  - `api.getLegalFeedForYou(params: {type: string; limit?: number}): Promise<LegalFeedItem[]>`
  - `api.getLegalFeedPreferences(): Promise<LegalFeedPreference>`
  - `api.putLegalFeedPreferences(p: LegalFeedPreference): Promise<LegalFeedPreference>`

- [ ] **Step 1: Add the constant + interfaces + endpoints**

In `frontend/src/api.ts`, extend the `LegalFeedItem` interface with the new optional fields, and add:

```typescript
export const PRACTICE_AREAS = [
  'Tax', 'Criminal', 'Civil', 'Constitutional', 'Corporate/Commercial', 'IP',
  'Environment', 'Labour/Service', 'Family', 'Property', 'Banking/Insolvency',
  'Arbitration',
];

export interface LegalFeedPreference {
  topic_weights: Record<string, number>;
  courts: string[];
  interest_phrases: string[];
}
```

Add the API methods alongside the existing `getLegalFeed` (follow the same fetch/auth-header helper that `getLegalFeed` uses in this file):

```typescript
  getLegalFeedCourts: async (): Promise<string[]> => {
    const res = await authFetch(`${API_ENDPOINTS.legalFeed}/courts`);
    return (await res.json()).courts as string[];
  },
  getLegalFeedForYou: async (params: { type: string; limit?: number }): Promise<LegalFeedItem[]> => {
    const q = new URLSearchParams({ type: params.type, limit: String(params.limit ?? 10) });
    const res = await authFetch(`${API_ENDPOINTS.legalFeed}/for-you?${q.toString()}`);
    return (await res.json()).data as LegalFeedItem[];
  },
  getLegalFeedPreferences: async (): Promise<LegalFeedPreference> => {
    const res = await authFetch(`${API_ENDPOINTS.legalFeed}/preferences`);
    return res.json();
  },
  putLegalFeedPreferences: async (p: LegalFeedPreference): Promise<LegalFeedPreference> => {
    const res = await authFetch(`${API_ENDPOINTS.legalFeed}/preferences`, {
      method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(p),
    });
    return res.json();
  },
```

> Use whatever the file's existing authenticated-fetch helper is named (the one `getLegalFeed` already uses). If `getLegalFeed` inlines the token header, mirror that exact pattern instead of `authFetch`.

- [ ] **Step 2: Verify it compiles**

Run: `cd frontend && npm run build`
Expected: build succeeds (tsc + vite, no type errors)

- [ ] **Step 3: Commit**

```bash
git add frontend/src/api.ts
git commit -m "feat(legal-feed): frontend API for courts, for-you, preferences"
```

---

### Task 13: Frontend — For-you + Latest + Personalize + images + court list

**Files:**
- Modify: `frontend/src/pages/LegalFeed.tsx`
- Create: `frontend/src/components/LegalFeedPersonalize.tsx`

**Interfaces:**
- Consumes: Task 12 API methods + `PRACTICE_AREAS`, `LegalFeedItem`, `LegalFeedPreference`.

- [ ] **Step 1: Create the Personalize panel**

```tsx
// frontend/src/components/LegalFeedPersonalize.tsx
import { useEffect, useState } from 'react';
import { api, PRACTICE_AREAS, LegalFeedPreference } from '../api';

export default function LegalFeedPersonalize({
  courts, onClose, onSaved,
}: { courts: string[]; onClose: () => void; onSaved: () => void }) {
  const [topics, setTopics] = useState<string[]>([]);
  const [selCourts, setSelCourts] = useState<string[]>([]);
  const [phrases, setPhrases] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api.getLegalFeedPreferences().then((p) => {
      setTopics(Object.keys(p.topic_weights || {}));
      setSelCourts(p.courts || []);
      setPhrases((p.interest_phrases || []).join(', '));
    });
  }, []);

  const toggle = (list: string[], set: (v: string[]) => void, v: string) =>
    set(list.includes(v) ? list.filter((x) => x !== v) : [...list, v]);

  const save = async () => {
    setSaving(true);
    const pref: LegalFeedPreference = {
      topic_weights: Object.fromEntries(topics.map((t) => [t, 1.0])),
      courts: selCourts,
      interest_phrases: phrases.split(',').map((s) => s.trim()).filter(Boolean),
    };
    await api.putLegalFeedPreferences(pref);
    setSaving(false);
    onSaved();
    onClose();
  };

  return (
    <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-paper border border-rule rounded-lg p-6 max-w-lg w-full" onClick={(e) => e.stopPropagation()}>
        <h2 className="font-display text-xl text-ink mb-4">Personalize your feed</h2>

        <div className="eyebrow text-ink-faint mb-2">Practice areas</div>
        <div className="flex flex-wrap gap-2 mb-4">
          {PRACTICE_AREAS.map((t) => (
            <button key={t} onClick={() => toggle(topics, setTopics, t)}
              className={['text-xs px-2 py-1 rounded border',
                topics.includes(t) ? 'bg-oxblood text-white border-oxblood' : 'border-rule text-ink-soft'].join(' ')}>
              {t}
            </button>
          ))}
        </div>

        <div className="eyebrow text-ink-faint mb-2">Courts</div>
        <div className="flex flex-wrap gap-2 mb-4">
          {courts.map((c) => (
            <button key={c} onClick={() => toggle(selCourts, setSelCourts, c)}
              className={['text-xs px-2 py-1 rounded border',
                selCourts.includes(c) ? 'bg-oxblood text-white border-oxblood' : 'border-rule text-ink-soft'].join(' ')}>
              {c}
            </button>
          ))}
        </div>

        <div className="eyebrow text-ink-faint mb-2">Specific interests (comma-separated)</div>
        <input value={phrases} onChange={(e) => setPhrases(e.target.value)}
          placeholder="e.g. GST input credit, anticipatory bail"
          className="w-full border border-rule rounded px-3 py-1.5 text-sm bg-paper text-ink mb-4" />

        <div className="flex justify-end gap-2">
          <button onClick={onClose} className="text-sm text-ink-soft px-3 py-1.5">Cancel</button>
          <button onClick={save} disabled={saving}
            className="text-sm bg-oxblood text-white rounded px-3 py-1.5 disabled:opacity-50">
            {saving ? 'Saving…' : 'Save'}
          </button>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Rewrite `LegalFeed.tsx`**

Replace the page so it: fetches courts from the API (fixing #1), shows a "For you" section above "Latest", renders `headline`/`tldr`/`image_url`, and opens the Personalize panel.

```tsx
import { useEffect, useState } from 'react';
import { api, LegalFeedItem } from '../api';
import Pagination from '../components/Pagination';
import LegalFeedPersonalize from '../components/LegalFeedPersonalize';

type Tab = 'judgement' | 'news';
const TABS: { key: Tab; label: string }[] = [
  { key: 'judgement', label: 'Judgements' },
  { key: 'news', label: 'Legal News' },
];
const PAGE_SIZE = 20;

function Card({ item }: { item: LegalFeedItem }) {
  return (
    <li className="border border-rule rounded-lg p-4 bg-paper flex gap-4">
      {item.image_url ? (
        <img src={item.image_url} alt="" loading="lazy"
          className="w-24 h-24 object-cover rounded flex-shrink-0"
          onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = 'none'; }} />
      ) : (
        <div className="w-24 h-24 rounded flex-shrink-0 bg-rule/40 flex items-center justify-center text-2xs text-ink-faint text-center px-1">
          {item.court || item.source_name}
        </div>
      )}
      <div className="min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <span className="eyebrow text-ink-faint">{item.source_name}</span>
          {item.court && <span className="text-2xs text-ink-muted">· {item.court}</span>}
          {item.published_at && (
            <span className="text-2xs text-ink-muted ml-auto">
              {new Date(item.published_at).toLocaleDateString()}
            </span>
          )}
        </div>
        <h3 className="text-ink font-medium mb-1">{item.headline || item.title}</h3>
        {(item.tldr || item.summary) && (
          <p className="text-sm text-ink-soft line-clamp-3 mb-2">{item.tldr || item.summary}</p>
        )}
        <a href={item.source_url} target="_blank" rel="noopener noreferrer"
          className="text-sm text-oxblood hover:underline">Read at source ↗</a>
      </div>
    </li>
  );
}

export default function LegalFeed() {
  const [tab, setTab] = useState<Tab>('judgement');
  const [court, setCourt] = useState('');
  const [courts, setCourts] = useState<string[]>([]);
  const [forYou, setForYou] = useState<LegalFeedItem[]>([]);
  const [items, setItems] = useState<LegalFeedItem[]>([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showPanel, setShowPanel] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => { api.getLegalFeedCourts().then(setCourts).catch(() => setCourts([])); }, []);

  useEffect(() => {
    api.getLegalFeedForYou({ type: tab, limit: 6 }).then(setForYou).catch(() => setForYou([]));
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

  return (
    <div className="p-8 max-w-4xl mx-auto">
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

      {forYou.length > 0 && (
        <section className="mb-8">
          <div className="eyebrow text-ink-faint mb-3">For you</div>
          <ul className="space-y-4">{forYou.map((i) => <Card key={`fy-${i.id}`} item={i} />)}</ul>
        </section>
      )}

      <div className="flex items-center justify-between mb-3">
        <div className="eyebrow text-ink-faint">Latest</div>
        {courts.length > 0 && (
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

      <ul className="space-y-4">{items.map((i) => <Card key={i.id} item={i} />)}</ul>

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

Run: `cd frontend && npm run build && npm run lint -- --max-warnings 0`
Expected: both succeed

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/LegalFeed.tsx frontend/src/components/LegalFeedPersonalize.tsx
git commit -m "feat(legal-feed): for-you shelf, personalize panel, images, full court list"
```

---

### Task 14: Env documentation + ops runbook

**Files:**
- Modify: `backend/.env.example`
- Modify: `docs/superpowers/legal-feed-ops.md`

- [ ] **Step 1: Document env vars**

Append to `backend/.env.example` under a "# Legal Feed enrichment (OpenAI)" heading:

```
# Legal Feed enrichment (OpenAI). If unset, ingestion still runs but items are
# not enriched (no headline/tldr/topics/importance/embedding).
OPENAI_API_KEY=
LEGAL_FEED_ENRICH_MODEL=gpt-4o-mini
LEGAL_FEED_EMBED_MODEL=text-embedding-3-small
```

- [ ] **Step 2: Update the runbook**

In `docs/superpowers/legal-feed-ops.md`, add a "## Enrichment & personalization" section documenting: enrichment runs automatically during each ingest for new items; use **"Enrich backlog"** in `/admin` to enrich already-ingested items after first enabling OpenAI; personalization is per-user via the in-app **Personalize** panel; failures are visible as `enrich_failed` in run results and retried on subsequent runs.

- [ ] **Step 3: Run the full backend suite**

Run: `cd backend && python -m pytest -q`
Expected: all legal-feed + send tests pass (the 3 pre-existing `tests/test_api.py` failures targeting `/api/clients` are unrelated and may remain).

- [ ] **Step 4: Commit**

```bash
git add backend/.env.example docs/superpowers/legal-feed-ops.md
git commit -m "docs(legal-feed): document enrichment env vars and ops"
```

---

## Self-Review

**Spec coverage:**
- Enrichment pass (content-type-aware, OpenAI, best-effort) → Tasks 5, 6 ✓
- Schema (item fields, run counters, preference table) → Task 2 ✓
- Two-tier personalization (taxonomy macro + interest embedding micro) → Tasks 7, 8 ✓
- "For you" + "Latest" layout, cold-start fallback → Tasks 8, 13 ✓
- Embeddings as JSON + Python cosine behind `rank_by_similarity` → Task 4 ✓
- Images (hotlink + fallback) → Tasks 3, 13 ✓
- Provider/config via env, graceful degradation → Tasks 5, 14 ✓
- Backlog backfill as deliberate admin action → Tasks 6, 10 ✓
- Output validation (taxonomy, clamp, no judgement tldr) → Task 5 ✓
- embed_model stamp → Tasks 2, 5, 7 ✓
- PII boundary (only RSS title/summary sent) → Task 5 (enforced by construction) ✓
- #1 court filter → Tasks 8, 9, 13 ✓
- #2 admin per-source counts → Task 10 ✓
- #4 invoice CC (firm_email, skip-if-equal/missing) → Task 11 ✓

**Placeholder scan:** No TODO/TBD; all code blocks complete. The only soft references are to existing test helpers (auth/admin headers) in Tasks 9–10, with explicit instructions to mirror the file's current pattern if absent.

**Type consistency:** `enrich_item(item, client)`, `rank_by_similarity(items, interest_embedding, now)`, `query_for_you(user_id, content_type, limit, window_days, now)`, `upsert_preference(user_id, topic_weights, courts, interest_phrases, client)`, `enrich_backlog(limit, client)` are used consistently across tasks. `embed_model` attribute on clients is read identically in Tasks 5 and 7. `inserted_ids` is added in Task 6 and stripped before persisting.
