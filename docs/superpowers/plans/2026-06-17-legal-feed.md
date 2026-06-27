# Legal Feed (Sub-project 1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a legal updates feed (Judgements + Legal News tabs) to Snappy, fed by a scheduled RSS ingestion pipeline, with an operator-only admin panel for monitoring and control.

**Architecture:** A Cloud Scheduler job calls a secret-protected Flask endpoint twice a day. The handler reads enabled feeds from a `legal_feed_sources` registry, fetches+parses each RSS feed, dedupes by a unique key, and stores normalized items (headline + summary + link-out, no full text) in `legal_feed_items`. Each run is logged to `legal_feed_runs`. Authenticated users read the feed via a paginated API; a new React page renders tabs + a court filter. The existing server-rendered `/admin` panel gains a Legal Feed area for status, manual triggering, source management, moderation, and an ordering knob.

**Tech Stack:** Flask 3 + Flask-SQLAlchemy 2.0 (ORM against Supabase Postgres via `DATABASE_URL`), `feedparser` (new dep) for RSS, pytest (in-memory SQLite), React 18 + react-router-dom 6 + Tailwind + lucide-react.

## Global Constraints

- **Data layer is SQLAlchemy ORM**, not the Supabase REST client. New tables are `db.Model` classes in `backend/app/models/models.py`, imported in `create_app()` so `db.create_all()` builds them. Match existing style: integer PKs, `String` columns for enum-like fields (e.g. `status`), `datetime.utcnow` defaults, a `to_dict()` method per model.
- **API prefix is `/api/v1`**; the user-facing feed blueprint mounts there. The admin blueprint stays at `/admin`.
- **No full text.** Store only `title` + `summary` + `source_url` + metadata. Never store or render full judgement/article bodies or PDFs.
- **Auth:** user-facing read endpoint uses `@jwt_required` (from `app.middleware.jwt_auth`). The ingest endpoint uses a shared-secret header. Admin endpoints use `@requires_admin_auth` (HTTP Basic Auth).
- **Admin credentials come from env vars** `ADMIN_PASSWORD` (required) and `ADMIN_USERNAME` (optional, default `admin`). `/admin` must refuse to serve if `ADMIN_PASSWORD` is unset. No hardcoded credentials.
- **Ingest secret** env var: `LEGAL_FEED_INGEST_SECRET` (required for ingest endpoint to function).
- **Git:** Do NOT run `git commit`/`git push`/`git add` — the repo owner (Parth) performs all git operations himself. Every "Checkpoint" step means: stop, report what changed, and let Parth review/commit before continuing. Never invoke git.
- **Backend tests:** `cd backend && python -m pytest <path> -v`. Frontend has no unit-test runner; verify with `cd frontend && npm run build` (runs `tsc` then vite build) and `npm run lint`.

---

### Task 1: Data model — registry, items, runs, settings

**Files:**
- Modify: `backend/app/models/models.py` (append four models)
- Modify: `backend/app/main.py:55-61` (import new models inside the `app_context()` block so `db.create_all()` builds them)
- Test: `backend/tests/test_legal_feed_models.py`

**Interfaces:**
- Produces:
  - `LegalFeedSource(id:int, name:str, content_type:str, court:str|None, kind:str, feed_url:str, enabled:bool, weight:int, created_at:datetime)` with `.to_dict()`
  - `LegalFeedItem(id:int, source_id:int, content_type:str, title:str, summary:str|None, source_url:str, source_name:str, court:str|None, published_at:datetime|None, ingested_at:datetime, hidden:bool, dedup_key:str unique)` with `.to_dict()`
  - `LegalFeedRun(id:int, started_at:datetime, finished_at:datetime|None, trigger:str, status:str, total_ingested:int, results:list)` with `.to_dict()`
  - `LegalFeedSetting(id:int, ordering_mode:str)` with `.to_dict()`
  - Allowed values (documented, enforced in app code not DB): `content_type ∈ {judgement, news, notice}`; `kind ∈ {rss, scrape}`; `trigger ∈ {scheduled, manual}`; `status ∈ {success, partial, failed}`; `ordering_mode ∈ {recency, weighted}`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_legal_feed_models.py
from datetime import datetime
from app.models.models import (
    db, LegalFeedSource, LegalFeedItem, LegalFeedRun, LegalFeedSetting,
)


def test_create_source_and_item(db):
    src = LegalFeedSource(
        name='Indian Kanoon — Supreme Court', content_type='judgement',
        court='Supreme Court', kind='rss',
        feed_url='https://indiankanoon.org/feeds/latest/supremecourt/',
        enabled=True, weight=10,
    )
    db.session.add(src)
    db.session.commit()

    item = LegalFeedItem(
        source_id=src.id, content_type='judgement', title='ABC v. State',
        summary='A summary', source_url='https://example.com/1',
        source_name=src.name, court='Supreme Court',
        published_at=datetime(2026, 6, 17), hidden=False, dedup_key='abc123',
    )
    db.session.add(item)
    db.session.commit()

    fetched = LegalFeedItem.query.filter_by(dedup_key='abc123').first()
    assert fetched.title == 'ABC v. State'
    assert fetched.to_dict()['court'] == 'Supreme Court'
    assert src.to_dict()['feed_url'].endswith('/supremecourt/')


def test_run_and_setting(db):
    run = LegalFeedRun(started_at=datetime(2026, 6, 17), trigger='manual',
                       status='success', total_ingested=3,
                       results=[{'source_id': 1, 'fetched': 5, 'inserted': 3, 'error': None}])
    db.session.add(run)
    setting = LegalFeedSetting(id=1, ordering_mode='recency')
    db.session.add(setting)
    db.session.commit()

    assert LegalFeedRun.query.first().to_dict()['results'][0]['inserted'] == 3
    assert LegalFeedSetting.query.get(1).ordering_mode == 'recency'
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_legal_feed_models.py -v`
Expected: FAIL with `ImportError: cannot import name 'LegalFeedSource'`.

- [ ] **Step 3: Append the models to `backend/app/models/models.py`**

```python
class LegalFeedSource(db.Model):
    """A feed the ingestion pipeline polls. Config-driven source registry."""
    __tablename__ = 'legal_feed_sources'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    content_type = db.Column(db.String(20), nullable=False)  # judgement|news|notice
    court = db.Column(db.String(100))
    kind = db.Column(db.String(20), nullable=False, default='rss')  # rss|scrape
    feed_url = db.Column(db.String(500), nullable=False, unique=True)
    enabled = db.Column(db.Boolean, nullable=False, default=True)
    weight = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id, 'name': self.name, 'content_type': self.content_type,
            'court': self.court, 'kind': self.kind, 'feed_url': self.feed_url,
            'enabled': self.enabled, 'weight': self.weight,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class LegalFeedItem(db.Model):
    """A single feed entry: headline + summary + link-out. No full text."""
    __tablename__ = 'legal_feed_items'

    id = db.Column(db.Integer, primary_key=True)
    source_id = db.Column(db.Integer, db.ForeignKey('legal_feed_sources.id'), index=True)
    content_type = db.Column(db.String(20), nullable=False, index=True)
    title = db.Column(db.Text, nullable=False)
    summary = db.Column(db.Text)
    source_url = db.Column(db.String(1000), nullable=False)
    source_name = db.Column(db.String(200), nullable=False)
    court = db.Column(db.String(100), index=True)
    published_at = db.Column(db.DateTime, index=True)
    ingested_at = db.Column(db.DateTime, default=datetime.utcnow)
    hidden = db.Column(db.Boolean, nullable=False, default=False)
    dedup_key = db.Column(db.String(64), nullable=False, unique=True, index=True)

    def to_dict(self):
        return {
            'id': self.id, 'content_type': self.content_type, 'title': self.title,
            'summary': self.summary, 'source_url': self.source_url,
            'source_name': self.source_name, 'court': self.court,
            'published_at': self.published_at.isoformat() if self.published_at else None,
            'ingested_at': self.ingested_at.isoformat() if self.ingested_at else None,
            'hidden': self.hidden,
        }


class LegalFeedRun(db.Model):
    """Audit log of one ingestion run, for the admin status view."""
    __tablename__ = 'legal_feed_runs'

    id = db.Column(db.Integer, primary_key=True)
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    finished_at = db.Column(db.DateTime)
    trigger = db.Column(db.String(20), nullable=False)  # scheduled|manual
    status = db.Column(db.String(20), nullable=False, default='success')
    total_ingested = db.Column(db.Integer, nullable=False, default=0)
    results = db.Column(db.JSON, default=list)  # [{source_id, fetched, inserted, error}]

    def to_dict(self):
        return {
            'id': self.id,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'finished_at': self.finished_at.isoformat() if self.finished_at else None,
            'trigger': self.trigger, 'status': self.status,
            'total_ingested': self.total_ingested, 'results': self.results or [],
        }


class LegalFeedSetting(db.Model):
    """Singleton (id=1) holding the global feed ordering mode."""
    __tablename__ = 'legal_feed_settings'

    id = db.Column(db.Integer, primary_key=True)
    ordering_mode = db.Column(db.String(20), nullable=False, default='recency')  # recency|weighted

    def to_dict(self):
        return {'id': self.id, 'ordering_mode': self.ordering_mode}
```

- [ ] **Step 4: Register the models for table creation**

In `backend/app/main.py`, inside the `with app.app_context():` block (around line 57-60), add an import next to the existing model imports so `db.create_all()` sees them:

```python
        from app.models.models import (
            LegalFeedSource, LegalFeedItem, LegalFeedRun, LegalFeedSetting,
        )  # ensure legal feed tables are created
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_legal_feed_models.py -v`
Expected: PASS (2 passed).

- [ ] **Step 6: Checkpoint** — report the four new models + main.py import; let Parth review/commit.

---

### Task 2: Dedup key utility

**Files:**
- Create: `backend/app/utils/legal_feed_dedup.py`
- Test: `backend/tests/test_legal_feed_dedup.py`

**Interfaces:**
- Produces: `compute_dedup_key(source_url: str | None, source_name: str, title: str) -> str` — returns a 64-char SHA-256 hex digest. Uses normalized `source_url` when truthy, else `source_name|title` normalized.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_legal_feed_dedup.py
from app.utils.legal_feed_dedup import compute_dedup_key


def test_same_url_same_key():
    a = compute_dedup_key('https://x.com/1', 'LiveLaw', 'Title A')
    b = compute_dedup_key('https://X.com/1 ', 'LiveLaw', 'Different title')
    assert a == b  # URL drives the key; normalization ignores case/whitespace


def test_different_url_different_key():
    a = compute_dedup_key('https://x.com/1', 'LiveLaw', 'T')
    b = compute_dedup_key('https://x.com/2', 'LiveLaw', 'T')
    assert a != b


def test_fallback_to_source_and_title_when_no_url():
    a = compute_dedup_key(None, 'SC', 'Order of the day')
    b = compute_dedup_key('', 'sc', 'order of the day ')
    assert a == b
    assert len(a) == 64
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_legal_feed_dedup.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement**

```python
# backend/app/utils/legal_feed_dedup.py
"""Exact-dedup key for legal feed items."""
import hashlib
import re


def _norm(value: str) -> str:
    return re.sub(r'\s+', ' ', (value or '').strip().lower())


def compute_dedup_key(source_url, source_name, title) -> str:
    if source_url and source_url.strip():
        basis = _norm(source_url)
    else:
        basis = f"{_norm(source_name)}|{_norm(title)}"
    return hashlib.sha256(basis.encode('utf-8')).hexdigest()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_legal_feed_dedup.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Checkpoint** — report the new util; let Parth review/commit.

---

### Task 3: RSS fetcher (network fetch + pure parse)

**Files:**
- Create: `backend/app/services/legal_feed/__init__.py` (empty)
- Create: `backend/app/services/legal_feed/rss.py`
- Modify: `backend/requirements.txt` (add `feedparser==6.0.11`)
- Test: `backend/tests/test_legal_feed_rss.py`
- Test fixture: `backend/tests/fixtures/sample_feed.xml`

**Interfaces:**
- Produces:
  - `fetch_raw(url: str) -> str` — HTTP GET the feed, return body text (network; not unit-tested directly).
  - `parse_feed(raw: str) -> list[dict]` — pure; returns items `{'title': str, 'summary': str|None, 'source_url': str, 'published_at': datetime|None}`. Skips entries with no title or no link.

- [ ] **Step 1: Add the dependency**

In `backend/requirements.txt`, under `# Utils`, add:

```
feedparser==6.0.11
```

Then install: `cd backend && pip install feedparser==6.0.11`

- [ ] **Step 2: Create the test fixture**

```xml
<!-- backend/tests/fixtures/sample_feed.xml -->
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Sample Court Feed</title>
    <item>
      <title>Alpha v. Beta</title>
      <link>https://indiankanoon.org/doc/111/</link>
      <description>Summary of Alpha v. Beta judgement.</description>
      <pubDate>Tue, 17 Jun 2026 10:00:00 +0530</pubDate>
    </item>
    <item>
      <title>Gamma v. Delta</title>
      <link>https://indiankanoon.org/doc/222/</link>
      <description>Summary of Gamma v. Delta.</description>
      <pubDate>Mon, 16 Jun 2026 09:00:00 +0530</pubDate>
    </item>
    <item>
      <title>No Link Item</title>
      <description>Should be skipped because it has no link.</description>
    </item>
  </channel>
</rss>
```

- [ ] **Step 3: Write the failing test**

```python
# backend/tests/test_legal_feed_rss.py
import os
from datetime import datetime
from app.services.legal_feed import rss

FIXTURE = os.path.join(os.path.dirname(__file__), 'fixtures', 'sample_feed.xml')


def _raw():
    with open(FIXTURE, 'r', encoding='utf-8') as f:
        return f.read()


def test_parse_feed_returns_normalized_items():
    items = rss.parse_feed(_raw())
    assert len(items) == 2  # third entry skipped (no link)
    first = items[0]
    assert first['title'] == 'Alpha v. Beta'
    assert first['source_url'] == 'https://indiankanoon.org/doc/111/'
    assert 'Alpha' in first['summary']
    assert isinstance(first['published_at'], datetime)


def test_parse_feed_handles_empty():
    assert rss.parse_feed('') == []
```

- [ ] **Step 4: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_legal_feed_rss.py -v`
Expected: FAIL with `ModuleNotFoundError: app.services.legal_feed`.

- [ ] **Step 5: Implement**

```python
# backend/app/services/legal_feed/rss.py
"""RSS fetching and parsing for the legal feed pipeline.

Split into a network half (fetch_raw) and a pure half (parse_feed) so the
parser can be unit-tested against a fixture without hitting the network.
"""
import time
from datetime import datetime

import feedparser
import requests

USER_AGENT = 'SnappyLegalFeed/1.0 (+https://snappy.app)'
TIMEOUT_SECONDS = 30


def fetch_raw(url: str) -> str:
    resp = requests.get(url, headers={'User-Agent': USER_AGENT}, timeout=TIMEOUT_SECONDS)
    resp.raise_for_status()
    return resp.text


def _parse_date(entry):
    parsed = entry.get('published_parsed') or entry.get('updated_parsed')
    if parsed:
        return datetime.fromtimestamp(time.mktime(parsed))
    return None


def parse_feed(raw: str) -> list:
    feed = feedparser.parse(raw)
    items = []
    for entry in feed.entries:
        title = (entry.get('title') or '').strip()
        link = (entry.get('link') or '').strip()
        if not title or not link:
            continue
        items.append({
            'title': title,
            'summary': (entry.get('summary') or '').strip() or None,
            'source_url': link,
            'published_at': _parse_date(entry),
        })
    return items
```

- [ ] **Step 6: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_legal_feed_rss.py -v`
Expected: PASS (2 passed).

- [ ] **Step 7: Checkpoint** — report the rss module + feedparser dep; let Parth review/commit.

---

### Task 4: Source registry seeding (v1 sources)

**Files:**
- Create: `backend/app/services/legal_feed/seed.py`
- Test: `backend/tests/test_legal_feed_seed.py`

**Interfaces:**
- Consumes: `LegalFeedSource` (Task 1).
- Produces: `seed_sources() -> int` — inserts any v1 source whose `feed_url` is not already present; returns count inserted. Idempotent.

> **External-URL verification (do this once during implementation):** the Indian Kanoon judgement feed URLs are confirmed (pattern `https://indiankanoon.org/feeds/latest/<slug>/`). The two **news** feed URLs below are best-known and MUST be opened in a browser to confirm they return a valid RSS/Atom document before relying on them; if a URL 404s or returns HTML, correct it (check the outlet's site for its RSS link) and update the seed list. This is a verification step, not a code placeholder — ship real URLs.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_legal_feed_seed.py
from app.models.models import LegalFeedSource
from app.services.legal_feed.seed import seed_sources


def test_seed_inserts_v1_sources(db):
    inserted = seed_sources()
    assert inserted == 11
    assert LegalFeedSource.query.count() == 11
    # 9 judgement feeds + 2 news feeds
    assert LegalFeedSource.query.filter_by(content_type='judgement').count() == 9
    assert LegalFeedSource.query.filter_by(content_type='news').count() == 2


def test_seed_is_idempotent(db):
    seed_sources()
    second = seed_sources()
    assert second == 0
    assert LegalFeedSource.query.count() == 11
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_legal_feed_seed.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement**

```python
# backend/app/services/legal_feed/seed.py
"""Seed the v1 legal feed source registry. Idempotent (keyed on feed_url)."""
from app.models.models import db, LegalFeedSource

IK = 'https://indiankanoon.org/feeds/latest/'

V1_SOURCES = [
    # Judgements — Indian Kanoon RSS (slugs verified against indiankanoon.org/feeds/)
    ('Indian Kanoon — Supreme Court', 'judgement', 'Supreme Court', IK + 'supremecourt/', 10),
    ('Indian Kanoon — Delhi HC',      'judgement', 'Delhi HC',      IK + 'delhi/',        5),
    ('Indian Kanoon — Bombay HC',     'judgement', 'Bombay HC',     IK + 'bombay/',       5),
    ('Indian Kanoon — Madras HC',     'judgement', 'Madras HC',     IK + 'chennai/',      5),
    ('Indian Kanoon — Calcutta HC',   'judgement', 'Calcutta HC',   IK + 'kolkata/',      5),
    ('Indian Kanoon — Karnataka HC',  'judgement', 'Karnataka HC',  IK + 'karnataka/',    5),
    ('Indian Kanoon — Rajasthan HC',  'judgement', 'Rajasthan HC',  IK + 'jaipur/',       6),
    ('Indian Kanoon — ITAT',          'judgement', 'ITAT',          IK + 'itat/',         3),
    ('Indian Kanoon — NGT',           'judgement', 'NGT',           IK + 'greentribunal/', 3),
    # News — VERIFY these URLs in a browser before relying on them (see note above)
    ('LiveLaw',     'news', None, 'https://www.livelaw.in/rss/', 4),
    ('Bar & Bench', 'news', None, 'https://www.barandbench.com/feed', 4),
]


def seed_sources() -> int:
    inserted = 0
    for name, content_type, court, feed_url, weight in V1_SOURCES:
        exists = LegalFeedSource.query.filter_by(feed_url=feed_url).first()
        if exists:
            continue
        db.session.add(LegalFeedSource(
            name=name, content_type=content_type, court=court,
            kind='rss', feed_url=feed_url, enabled=True, weight=weight,
        ))
        inserted += 1
    db.session.commit()
    return inserted


if __name__ == '__main__':
    # One-off operational seeding: `cd backend && python -m app.services.legal_feed.seed`
    from app.main import create_app
    app = create_app()
    with app.app_context():
        n = seed_sources()
        print(f'Seeded {n} new legal feed source(s).')
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_legal_feed_seed.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Checkpoint** — report seed module + the verification note for the two news URLs; let Parth review/commit.

---

### Task 5: Ingestion service (orchestration + run logging)

**Files:**
- Create: `backend/app/services/legal_feed/ingest.py`
- Test: `backend/tests/test_legal_feed_ingest.py`

**Interfaces:**
- Consumes: `LegalFeedSource`, `LegalFeedItem`, `LegalFeedRun` (Task 1); `compute_dedup_key` (Task 2); `rss.fetch_raw`, `rss.parse_feed` (Task 3).
- Produces: `run_ingestion(trigger: str) -> dict` — runs all enabled sources, dedupes, inserts new items, writes a `LegalFeedRun`, returns `run.to_dict()`. Status: `success` (no source errored), `partial` (some errored, ≥1 ok), `failed` (all errored).

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_legal_feed_ingest.py
from app.models.models import db, LegalFeedSource, LegalFeedItem, LegalFeedRun
from app.services.legal_feed import rss
from app.services.legal_feed.ingest import run_ingestion

SAMPLE = """<?xml version="1.0"?><rss version="2.0"><channel>
<item><title>Case One</title><link>https://ik.org/doc/1/</link>
<description>Sum 1</description><pubDate>Tue, 17 Jun 2026 10:00:00 +0530</pubDate></item>
</channel></rss>"""


def _add_source(name='SC', url='https://ik.org/feeds/sc/', enabled=True):
    s = LegalFeedSource(name=name, content_type='judgement', court='Supreme Court',
                        kind='rss', feed_url=url, enabled=enabled, weight=10)
    db.session.add(s)
    db.session.commit()
    return s


def test_ingestion_inserts_and_logs_run(db, monkeypatch):
    _add_source()
    monkeypatch.setattr(rss, 'fetch_raw', lambda url: SAMPLE)

    result = run_ingestion('manual')

    assert result['status'] == 'success'
    assert result['total_ingested'] == 1
    assert LegalFeedItem.query.count() == 1
    assert LegalFeedRun.query.count() == 1
    item = LegalFeedItem.query.first()
    assert item.source_name == 'SC'
    assert item.court == 'Supreme Court'


def test_ingestion_is_idempotent(db, monkeypatch):
    _add_source()
    monkeypatch.setattr(rss, 'fetch_raw', lambda url: SAMPLE)
    run_ingestion('manual')
    run_ingestion('manual')
    assert LegalFeedItem.query.count() == 1  # second run dedupes


def test_ingestion_partial_when_one_source_fails(db, monkeypatch):
    _add_source(name='Good', url='https://ik.org/feeds/good/')
    _add_source(name='Bad', url='https://ik.org/feeds/bad/')

    def fake_fetch(url):
        if 'bad' in url:
            raise RuntimeError('boom')
        return SAMPLE

    monkeypatch.setattr(rss, 'fetch_raw', fake_fetch)
    result = run_ingestion('scheduled')

    assert result['status'] == 'partial'
    assert result['total_ingested'] == 1
    errors = [r for r in result['results'] if r['error']]
    assert len(errors) == 1
    assert 'boom' in errors[0]['error']


def test_ingestion_disabled_source_skipped(db, monkeypatch):
    _add_source(enabled=False)
    monkeypatch.setattr(rss, 'fetch_raw', lambda url: SAMPLE)
    result = run_ingestion('manual')
    assert result['total_ingested'] == 0
    assert LegalFeedItem.query.count() == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_legal_feed_ingest.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement**

```python
# backend/app/services/legal_feed/ingest.py
"""Orchestrates one ingestion run across all enabled sources."""
from datetime import datetime

from app.models.models import db, LegalFeedSource, LegalFeedItem, LegalFeedRun
from app.utils.legal_feed_dedup import compute_dedup_key
from app.services.legal_feed import rss

# Fetchers keyed by source.kind. v1 ships RSS only.
FETCHERS = {'rss': rss}


def _ingest_source(source) -> dict:
    result = {'source_id': source.id, 'fetched': 0, 'inserted': 0, 'error': None}
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
            db.session.add(LegalFeedItem(
                source_id=source.id, content_type=source.content_type,
                title=it['title'], summary=it.get('summary'),
                source_url=it['source_url'], source_name=source.name,
                court=source.court, published_at=it.get('published_at'),
                hidden=False, dedup_key=key,
            ))
            result['inserted'] += 1
        db.session.commit()
    except Exception as exc:  # one bad source must not abort the run
        db.session.rollback()
        result['error'] = str(exc)
    return result


def run_ingestion(trigger: str) -> dict:
    run = LegalFeedRun(started_at=datetime.utcnow(), trigger=trigger,
                       status='success', total_ingested=0, results=[])
    db.session.add(run)
    db.session.commit()

    sources = LegalFeedSource.query.filter_by(enabled=True).all()
    results = [_ingest_source(s) for s in sources]

    error_count = sum(1 for r in results if r['error'])
    if error_count == 0:
        status = 'success'
    elif error_count == len(results):
        status = 'failed'
    else:
        status = 'partial'

    run.finished_at = datetime.utcnow()
    run.total_ingested = sum(r['inserted'] for r in results)
    run.status = status
    run.results = results
    db.session.commit()
    return run.to_dict()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_legal_feed_ingest.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Checkpoint** — report ingestion service; let Parth review/commit.

---

### Task 6: Read query + user-facing API (feed + ingest endpoints)

**Files:**
- Create: `backend/app/services/legal_feed/query.py`
- Create: `backend/app/api/legal_feed.py`
- Modify: `backend/app/main.py` (import `legal_feed` in the api import line ~12; register blueprint at `/api/v1` ~line 75)
- Test: `backend/tests/test_legal_feed_api.py`

**Interfaces:**
- Consumes: `LegalFeedItem`, `LegalFeedSource`, `LegalFeedSetting` (Task 1); `run_ingestion` (Task 5); pagination util (`get_pagination_args`, `paginate_query`).
- Produces:
  - `get_ordering_mode() -> str` — reads/creates the `LegalFeedSetting` singleton, returns `recency` or `weighted`.
  - `query_feed(content_type=None, court=None, page=1, page_size=50) -> dict` — pagination envelope `{data, total, page, page_size, total_pages}`, excludes hidden, ordered per mode.
  - Blueprint `bp` with `GET /legal-feed` (`@jwt_required`) and `POST /legal-feed/ingest` (secret header `X-Ingest-Secret`).

- [ ] **Step 1: Write the failing test** (query function + ingest endpoint; the authed GET is covered via the query function since tests can't mint a Supabase JWT)

```python
# backend/tests/test_legal_feed_api.py
import os
from datetime import datetime
from app.models.models import db, LegalFeedSource, LegalFeedItem, LegalFeedSetting
from app.services.legal_feed.query import query_feed, get_ordering_mode


def _src(name, court, weight):
    s = LegalFeedSource(name=name, content_type='judgement', court=court,
                        kind='rss', feed_url=f'https://x/{name}', enabled=True, weight=weight)
    db.session.add(s); db.session.commit(); return s


def _item(src, title, ct='judgement', court='Supreme Court', when=None, hidden=False, key=None):
    db.session.add(LegalFeedItem(
        source_id=src.id, content_type=ct, title=title, summary='s',
        source_url=f'https://x/{title}', source_name=src.name, court=court,
        published_at=when or datetime(2026, 6, 1), hidden=hidden, dedup_key=key or title))
    db.session.commit()


def test_query_filters_by_type_and_court(db):
    s = _src('SC', 'Supreme Court', 10)
    _item(s, 'J1', ct='judgement', court='Supreme Court')
    _item(s, 'N1', ct='news', court=None)
    _item(s, 'J2', ct='judgement', court='Delhi HC')

    res = query_feed(content_type='judgement')
    assert res['total'] == 2
    res2 = query_feed(content_type='judgement', court='Delhi HC')
    assert res2['total'] == 1
    assert res2['data'][0]['title'] == 'J2'


def test_query_excludes_hidden(db):
    s = _src('SC', 'Supreme Court', 10)
    _item(s, 'Visible')
    _item(s, 'Gone', hidden=True, key='gone')
    res = query_feed()
    titles = [d['title'] for d in res['data']]
    assert 'Visible' in titles and 'Gone' not in titles


def test_query_recency_ordering(db):
    s = _src('SC', 'Supreme Court', 10)
    _item(s, 'Older', when=datetime(2026, 1, 1), key='o')
    _item(s, 'Newer', when=datetime(2026, 6, 1), key='n')
    res = query_feed()
    assert res['data'][0]['title'] == 'Newer'


def test_query_weighted_ordering(db):
    high = _src('HighWeight', 'Supreme Court', 100)
    low = _src('LowWeight', 'Delhi HC', 1)
    _item(low, 'FromLow', when=datetime(2026, 6, 2), key='low')
    _item(high, 'FromHigh', when=datetime(2026, 1, 1), key='high')
    db.session.add(LegalFeedSetting(id=1, ordering_mode='weighted')); db.session.commit()

    res = query_feed()
    assert get_ordering_mode() == 'weighted'
    assert res['data'][0]['title'] == 'FromHigh'  # weight beats recency


def test_ingest_endpoint_requires_secret(client, monkeypatch):
    monkeypatch.setenv('LEGAL_FEED_INGEST_SECRET', 'topsecret')
    # missing header
    assert client.post('/api/v1/legal-feed/ingest').status_code == 401
    # wrong header
    assert client.post('/api/v1/legal-feed/ingest',
                       headers={'X-Ingest-Secret': 'nope'}).status_code == 401
    # correct header
    ok = client.post('/api/v1/legal-feed/ingest',
                     headers={'X-Ingest-Secret': 'topsecret'})
    assert ok.status_code == 200
    assert ok.get_json()['trigger'] == 'scheduled'
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_legal_feed_api.py -v`
Expected: FAIL with `ModuleNotFoundError: app.services.legal_feed.query`.

- [ ] **Step 3: Implement the query module**

```python
# backend/app/services/legal_feed/query.py
"""Read-side query logic for the legal feed (testable without HTTP/JWT)."""
from sqlalchemy import func

from app.models.models import db, LegalFeedItem, LegalFeedSource, LegalFeedSetting
from app.utils.pagination import paginate_query


def get_ordering_mode() -> str:
    setting = LegalFeedSetting.query.get(1)
    if setting is None:
        setting = LegalFeedSetting(id=1, ordering_mode='recency')
        db.session.add(setting)
        db.session.commit()
    return setting.ordering_mode


def query_feed(content_type=None, court=None, page=1, page_size=50) -> dict:
    q = LegalFeedItem.query.filter_by(hidden=False)
    if content_type:
        q = q.filter_by(content_type=content_type)
    if court:
        q = q.filter_by(court=court)

    recency = func.coalesce(LegalFeedItem.published_at, LegalFeedItem.ingested_at).desc()
    if get_ordering_mode() == 'weighted':
        q = (q.join(LegalFeedSource, LegalFeedItem.source_id == LegalFeedSource.id)
              .order_by(LegalFeedSource.weight.desc(), recency))
    else:
        q = q.order_by(recency)

    return paginate_query(q, page, page_size, lambda i: i.to_dict())
```

- [ ] **Step 4: Implement the API blueprint**

```python
# backend/app/api/legal_feed.py
"""User-facing legal feed API + scheduler ingest endpoint."""
import os
from flask import Blueprint, request, jsonify

from app.middleware.jwt_auth import jwt_required
from app.utils.pagination import pagination_requested, get_pagination_args
from app.services.legal_feed.query import query_feed
from app.services.legal_feed.ingest import run_ingestion

bp = Blueprint('legal_feed', __name__)


@bp.route('/legal-feed', methods=['GET'])
@jwt_required
def get_feed():
    if pagination_requested():
        page, page_size = get_pagination_args()
    else:
        page, page_size = 1, 50
    return jsonify(query_feed(
        content_type=request.args.get('type'),
        court=request.args.get('court'),
        page=page, page_size=page_size,
    ))


@bp.route('/legal-feed/ingest', methods=['POST'])
def ingest():
    secret = os.getenv('LEGAL_FEED_INGEST_SECRET')
    if not secret or request.headers.get('X-Ingest-Secret') != secret:
        return jsonify({'error': 'unauthorized'}), 401
    return jsonify(run_ingestion('scheduled'))
```

- [ ] **Step 5: Register the blueprint in `backend/app/main.py`**

Add `legal_feed` to the api import (line ~12):

```python
from app.api import (invoices, clients, analytics, import_csv, backup, auth,
                     admin, items, storage, recurring, public, legal_feed)
```

Register near the other `/api/v1` blueprints (after line ~75):

```python
    app.register_blueprint(legal_feed.bp, url_prefix='/api/v1')
```

- [ ] **Step 6: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_legal_feed_api.py -v`
Expected: PASS (5 passed).

- [ ] **Step 7: Checkpoint** — report query module + API blueprint + registration; let Parth review/commit.

---

### Task 7: Admin auth hardening (env-var credentials)

**Files:**
- Modify: `backend/app/api/admin.py:10-16` (replace hardcoded creds with env reads; refuse if unset)
- Test: `backend/tests/test_admin_auth.py`

**Interfaces:**
- Modifies: `check_admin_auth(username, password) -> bool` now reads `ADMIN_USERNAME` (default `admin`) and `ADMIN_PASSWORD` (no default) from env at call time, with constant-time comparison; returns `False` if `ADMIN_PASSWORD` unset.
- Produces: `GET /admin/` returns 503 if `ADMIN_PASSWORD` unset; otherwise 401 without/with-wrong Basic Auth, 200 with correct.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_admin_auth.py
import base64


def _basic(user, pw):
    raw = base64.b64encode(f'{user}:{pw}'.encode()).decode()
    return {'Authorization': f'Basic {raw}'}


def test_admin_refuses_when_password_unset(client, monkeypatch):
    monkeypatch.delenv('ADMIN_PASSWORD', raising=False)
    resp = client.get('/admin/')
    assert resp.status_code == 503


def test_admin_requires_correct_credentials(client, monkeypatch):
    monkeypatch.setenv('ADMIN_PASSWORD', 'secretpw')
    assert client.get('/admin/').status_code == 401
    assert client.get('/admin/', headers=_basic('admin', 'wrong')).status_code == 401
    assert client.get('/admin/', headers=_basic('admin', 'secretpw')).status_code == 200
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_admin_auth.py -v`
Expected: FAIL — with hardcoded creds, the "refuses when unset" test gets 401 (or 200), not 503.

- [ ] **Step 3: Implement** — replace lines 10-16 of `backend/app/api/admin.py`:

```python
# Admin credentials come from environment. ADMIN_PASSWORD is required; the
# panel refuses to serve if it is unset (no insecure default).
import os
import hmac


def _admin_password():
    return os.getenv('ADMIN_PASSWORD')


def _admin_username():
    return os.getenv('ADMIN_USERNAME', 'admin')


def check_admin_auth(username, password):
    """Constant-time credential check. False if ADMIN_PASSWORD is unset."""
    expected_pw = _admin_password()
    if not expected_pw:
        return False
    user_ok = hmac.compare_digest(username or '', _admin_username())
    pw_ok = hmac.compare_digest(password or '', expected_pw)
    return user_ok and pw_ok
```

Then update the `requires_admin_auth` decorator (around line 26-34) so a missing password yields 503 rather than an unwinnable auth prompt:

```python
def requires_admin_auth(f):
    """Decorator for routes requiring admin authentication."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not _admin_password():
            return make_response('Admin panel disabled: ADMIN_PASSWORD not set', 503)
        auth = request.authorization
        if not auth or not check_admin_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_admin_auth.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Checkpoint** — report the credential hardening (note: this changes prod behaviour — `ADMIN_PASSWORD` must be set in the deployment env or `/admin` returns 503); let Parth review/commit.

---

### Task 8: Admin Legal Feed endpoints + panel section

**Files:**
- Modify: `backend/app/api/admin.py` (add endpoints + extend the HTML panel)
- Test: `backend/tests/test_admin_legal_feed.py`

**Interfaces:**
- Consumes: `requires_admin_auth` (Task 7); models (Task 1); `run_ingestion` (Task 5); `seed_sources` (Task 4).
- Produces (all under `/admin/api/legal-feed`, all `@requires_admin_auth`):
  - `GET /runs` → `{runs: [...]}` (latest 20 `LegalFeedRun`, newest first)
  - `POST /run` → `run_ingestion('manual')` result
  - `POST /seed` → `{inserted: int}`
  - `GET /sources` → `{sources: [...]}`
  - `POST /sources` → create from JSON `{name, content_type, court, feed_url, weight}` → 201 source dict
  - `PUT /sources/<id>` → patch `enabled`/`weight`/`court` → source dict
  - `GET /items?limit=` → `{items: [...]}` (latest, includes hidden)
  - `POST /items/<id>/hide` → toggle/set `hidden` from JSON `{hidden: bool}` → item dict
  - `GET /settings` / `PUT /settings` → `{ordering_mode}` (PUT validates value ∈ {recency, weighted})

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_admin_legal_feed.py
import base64
import pytest
from app.models.models import db, LegalFeedSource, LegalFeedItem


def _h(monkeypatch):
    monkeypatch.setenv('ADMIN_PASSWORD', 'pw')
    raw = base64.b64encode(b'admin:pw').decode()
    return {'Authorization': f'Basic {raw}'}


def test_sources_crud_and_seed(client, monkeypatch):
    h = _h(monkeypatch)
    # seed
    seeded = client.post('/admin/api/legal-feed/seed', headers=h)
    assert seeded.status_code == 200
    assert seeded.get_json()['inserted'] == 11
    # list
    listing = client.get('/admin/api/legal-feed/sources', headers=h)
    assert len(listing.get_json()['sources']) == 11
    # create
    created = client.post('/admin/api/legal-feed/sources', headers=h, json={
        'name': 'The Leaflet', 'content_type': 'news', 'court': None,
        'feed_url': 'https://theleaflet.in/feed/', 'weight': 2})
    assert created.status_code == 201
    sid = created.get_json()['id']
    # disable it
    upd = client.put(f'/admin/api/legal-feed/sources/{sid}', headers=h,
                     json={'enabled': False})
    assert upd.get_json()['enabled'] is False


def test_settings_validation(client, monkeypatch):
    h = _h(monkeypatch)
    assert client.get('/admin/api/legal-feed/settings', headers=h).get_json()['ordering_mode'] == 'recency'
    ok = client.put('/admin/api/legal-feed/settings', headers=h, json={'ordering_mode': 'weighted'})
    assert ok.get_json()['ordering_mode'] == 'weighted'
    bad = client.put('/admin/api/legal-feed/settings', headers=h, json={'ordering_mode': 'bogus'})
    assert bad.status_code == 400


def test_item_moderation(client, monkeypatch):
    h = _h(monkeypatch)
    src = LegalFeedSource(name='SC', content_type='judgement', court='SC',
                          kind='rss', feed_url='https://x/sc', enabled=True, weight=1)
    db.session.add(src); db.session.commit()
    it = LegalFeedItem(source_id=src.id, content_type='judgement', title='T',
                       summary='s', source_url='https://x/1', source_name='SC',
                       court='SC', hidden=False, dedup_key='k1')
    db.session.add(it); db.session.commit()

    resp = client.post(f'/admin/api/legal-feed/items/{it.id}/hide', headers=h,
                       json={'hidden': True})
    assert resp.status_code == 200
    assert resp.get_json()['hidden'] is True


def test_endpoints_reject_without_auth(client, monkeypatch):
    monkeypatch.setenv('ADMIN_PASSWORD', 'pw')
    assert client.get('/admin/api/legal-feed/runs').status_code == 401
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_admin_legal_feed.py -v`
Expected: FAIL with 404s (endpoints not defined).

- [ ] **Step 3: Implement the endpoints** — append to `backend/app/api/admin.py`:

```python
from app.models.models import (
    LegalFeedSource, LegalFeedItem, LegalFeedRun, LegalFeedSetting,
)
from app.services.legal_feed.ingest import run_ingestion
from app.services.legal_feed.seed import seed_sources
from app.services.legal_feed.query import get_ordering_mode

ALLOWED_ORDERING = {'recency', 'weighted'}


@bp.route('/api/legal-feed/runs', methods=['GET'])
@requires_admin_auth
def lf_runs():
    runs = LegalFeedRun.query.order_by(LegalFeedRun.id.desc()).limit(20).all()
    return jsonify({'runs': [r.to_dict() for r in runs]})


@bp.route('/api/legal-feed/run', methods=['POST'])
@requires_admin_auth
def lf_run_now():
    return jsonify(run_ingestion('manual'))


@bp.route('/api/legal-feed/seed', methods=['POST'])
@requires_admin_auth
def lf_seed():
    return jsonify({'inserted': seed_sources()})


@bp.route('/api/legal-feed/sources', methods=['GET'])
@requires_admin_auth
def lf_sources():
    sources = LegalFeedSource.query.order_by(LegalFeedSource.id).all()
    return jsonify({'sources': [s.to_dict() for s in sources]})


@bp.route('/api/legal-feed/sources', methods=['POST'])
@requires_admin_auth
def lf_create_source():
    data = request.get_json() or {}
    if not data.get('name') or not data.get('feed_url') or not data.get('content_type'):
        return jsonify({'error': 'name, feed_url and content_type are required'}), 400
    src = LegalFeedSource(
        name=data['name'], content_type=data['content_type'],
        court=data.get('court'), kind=data.get('kind', 'rss'),
        feed_url=data['feed_url'], enabled=data.get('enabled', True),
        weight=int(data.get('weight', 0)),
    )
    db.session.add(src)
    db.session.commit()
    return jsonify(src.to_dict()), 201


@bp.route('/api/legal-feed/sources/<int:source_id>', methods=['PUT'])
@requires_admin_auth
def lf_update_source(source_id):
    src = LegalFeedSource.query.get_or_404(source_id)
    data = request.get_json() or {}
    if 'enabled' in data:
        src.enabled = bool(data['enabled'])
    if 'weight' in data:
        src.weight = int(data['weight'])
    if 'court' in data:
        src.court = data['court']
    db.session.commit()
    return jsonify(src.to_dict())


@bp.route('/api/legal-feed/items', methods=['GET'])
@requires_admin_auth
def lf_items():
    limit = min(request.args.get('limit', default=50, type=int) or 50, 200)
    items = LegalFeedItem.query.order_by(LegalFeedItem.id.desc()).limit(limit).all()
    return jsonify({'items': [i.to_dict() for i in items]})


@bp.route('/api/legal-feed/items/<int:item_id>/hide', methods=['POST'])
@requires_admin_auth
def lf_hide_item(item_id):
    item = LegalFeedItem.query.get_or_404(item_id)
    data = request.get_json() or {}
    item.hidden = bool(data.get('hidden', True))
    db.session.commit()
    return jsonify(item.to_dict())


@bp.route('/api/legal-feed/settings', methods=['GET'])
@requires_admin_auth
def lf_get_settings():
    return jsonify({'ordering_mode': get_ordering_mode()})


@bp.route('/api/legal-feed/settings', methods=['PUT'])
@requires_admin_auth
def lf_put_settings():
    data = request.get_json() or {}
    mode = data.get('ordering_mode')
    if mode not in ALLOWED_ORDERING:
        return jsonify({'error': f'ordering_mode must be one of {sorted(ALLOWED_ORDERING)}'}), 400
    setting = LegalFeedSetting.query.get(1)
    if setting is None:
        setting = LegalFeedSetting(id=1, ordering_mode=mode)
        db.session.add(setting)
    else:
        setting.ordering_mode = mode
    db.session.commit()
    return jsonify(setting.to_dict())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_admin_legal_feed.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Add a Legal Feed section to the admin HTML panel**

In `backend/app/api/admin.py`, inside `ADMIN_PANEL_HTML`, add a new card after the Users card (before `</div>` that closes `.container`). Keep it consistent with the existing inline style:

```html
        <div class="card">
            <h2>Legal Feed</h2>
            <div id="lfMessage" class="message"></div>
            <button class="btn" onclick="lfRunNow()">Run ingestion now</button>
            <button class="btn" onclick="lfSeed()" style="margin-left:8px;">Seed v1 sources</button>
            <button class="btn" onclick="lfLoad()" style="margin-left:8px;">Refresh</button>

            <h3 style="margin-top:24px;">Ordering mode</h3>
            <select id="lfMode" onchange="lfSetMode()">
                <option value="recency">Recency (newest first)</option>
                <option value="weighted">Weighted (by source priority)</option>
            </select>

            <h3 style="margin-top:24px;">Latest runs</h3>
            <table><thead><tr><th>Started</th><th>Trigger</th><th>Status</th><th>Ingested</th></tr></thead>
                <tbody id="lfRuns"><tr><td colspan="4">—</td></tr></tbody></table>

            <h3 style="margin-top:24px;">Sources</h3>
            <table><thead><tr><th>Name</th><th>Type</th><th>Court</th><th>Enabled</th><th>Weight</th><th></th></tr></thead>
                <tbody id="lfSources"><tr><td colspan="6">—</td></tr></tbody></table>
        </div>
```

Add the matching JS before the closing `</script>` (reuse the existing `showMessage` helper):

```javascript
        async function lfLoad() {
            const runs = await (await fetch('/admin/api/legal-feed/runs')).json();
            document.getElementById('lfRuns').innerHTML = (runs.runs || []).map(r =>
                `<tr><td>${r.started_at || '-'}</td><td>${r.trigger}</td><td>${r.status}</td><td>${r.total_ingested}</td></tr>`
            ).join('') || '<tr><td colspan="4">No runs yet</td></tr>';

            const s = await (await fetch('/admin/api/legal-feed/sources')).json();
            document.getElementById('lfSources').innerHTML = (s.sources || []).map(src =>
                `<tr><td>${src.name}</td><td>${src.content_type}</td><td>${src.court || '-'}</td>
                 <td>${src.enabled ? 'Yes' : 'No'}</td><td>${src.weight}</td>
                 <td><button class="btn btn-small" onclick="lfToggle(${src.id}, ${!src.enabled})">${src.enabled ? 'Disable' : 'Enable'}</button></td></tr>`
            ).join('') || '<tr><td colspan="6">No sources — click "Seed v1 sources"</td></tr>';

            const set = await (await fetch('/admin/api/legal-feed/settings')).json();
            document.getElementById('lfMode').value = set.ordering_mode;
        }
        async function lfRunNow() {
            const r = await (await fetch('/admin/api/legal-feed/run', {method:'POST'})).json();
            showMessage('lfMessage', `Run ${r.status}: ${r.total_ingested} new item(s)`, 'success');
            lfLoad();
        }
        async function lfSeed() {
            const r = await (await fetch('/admin/api/legal-feed/seed', {method:'POST'})).json();
            showMessage('lfMessage', `Seeded ${r.inserted} source(s)`, 'success');
            lfLoad();
        }
        async function lfToggle(id, enabled) {
            await fetch(`/admin/api/legal-feed/sources/${id}`, {method:'PUT',
                headers:{'Content-Type':'application/json'}, body: JSON.stringify({enabled})});
            lfLoad();
        }
        async function lfSetMode() {
            const ordering_mode = document.getElementById('lfMode').value;
            await fetch('/admin/api/legal-feed/settings', {method:'PUT',
                headers:{'Content-Type':'application/json'}, body: JSON.stringify({ordering_mode})});
            showMessage('lfMessage', `Ordering set to ${ordering_mode}`, 'success');
        }
        lfLoad();
```

- [ ] **Step 6: Manual verification of the panel**

With `ADMIN_PASSWORD` set, run the backend (`cd backend && python -m app.main`), open `http://localhost:5000/admin/`, authenticate, and confirm: the Legal Feed card renders, "Seed v1 sources" adds 11 sources, "Run ingestion now" reports a run, the ordering dropdown saves. (Network calls to live RSS may fail locally — a `partial`/`failed` status here is acceptable; the point is the panel wiring.)

- [ ] **Step 7: Checkpoint** — report admin endpoints + panel section; let Parth review/commit.

---

### Task 9: Frontend API client additions

**Files:**
- Modify: `frontend/src/api.ts` (add type, endpoint, fetch function)

**Interfaces:**
- Produces:
  - `interface LegalFeedItem { id:number; content_type:'judgement'|'news'|'notice'; title:string; summary?:string; source_url:string; source_name:string; court?:string; published_at?:string; ingested_at?:string; }`
  - `API_ENDPOINTS.legalFeed: string`
  - `api.getLegalFeed(params: { page:number; page_size?:number; type?:string; court?:string }) => Promise<Paginated<LegalFeedItem>>`

- [ ] **Step 1: Add the endpoint constant** — in `API_ENDPOINTS` (after `recurring:` line ~37):

```typescript
  legalFeed: `${API_BASE_URL}/legal-feed`,
```

- [ ] **Step 2: Add the interface** — after the `Item` interface (~line 74):

```typescript
export interface LegalFeedItem {
  id: number;
  content_type: 'judgement' | 'news' | 'notice';
  title: string;
  summary?: string;
  source_url: string;
  source_name: string;
  court?: string;
  published_at?: string;
  ingested_at?: string;
}
```

- [ ] **Step 3: Add the fetch function** — inside the `api` object (e.g. after the recurring functions ~line 439):

```typescript
  // Legal Feed
  getLegalFeed: (params: { page: number; page_size?: number; type?: string; court?: string }) => {
    const q = new URLSearchParams();
    q.append('page', String(params.page));
    q.append('page_size', String(params.page_size ?? 20));
    if (params.type) q.append('type', params.type);
    if (params.court) q.append('court', params.court);
    return fetchAPI<Paginated<LegalFeedItem>>(`${API_ENDPOINTS.legalFeed}?${q}`);
  },
```

- [ ] **Step 4: Verify it compiles**

Run: `cd frontend && npm run build`
Expected: build succeeds (tsc finds no type errors). If it fails, fix the type/usage before continuing.

- [ ] **Step 5: Checkpoint** — report api.ts additions; let Parth review/commit.

---

### Task 10: Frontend Legal Feed page + route + nav

**Files:**
- Create: `frontend/src/pages/LegalFeed.tsx`
- Modify: `frontend/src/App.tsx` (import + route)
- Modify: `frontend/src/components/Layout.tsx` (nav entry)
- Modify: `frontend/src/components/Pagination.tsx` — **only read it first** to match its props; do not change it.

**Interfaces:**
- Consumes: `api.getLegalFeed`, `LegalFeedItem`, `Paginated` (Task 9); existing `Pagination` component.

- [ ] **Step 1: Read the existing `Pagination` component** to learn its exact props.

Run: open `frontend/src/components/Pagination.tsx` and note the prop names (e.g. `page`, `totalPages`, `onPageChange`). Use those exact names in Step 2. Also skim `frontend/src/pages/Items.tsx` for the established page layout/heading/loading patterns and Tailwind tokens (`text-ink`, `bg-paper`, `border-rule`, `eyebrow`, `oxblood`).

- [ ] **Step 2: Create the page** (adjust the `<Pagination .../>` props to match what Step 1 found; the rest is self-contained):

```tsx
// frontend/src/pages/LegalFeed.tsx
import { useEffect, useState } from 'react';
import { api, LegalFeedItem } from '../api';
import Pagination from '../components/Pagination';

type Tab = 'judgement' | 'news';

const TABS: { key: Tab; label: string }[] = [
  { key: 'judgement', label: 'Judgements' },
  { key: 'news', label: 'Legal News' },
];

export default function LegalFeed() {
  const [tab, setTab] = useState<Tab>('judgement');
  const [court, setCourt] = useState<string>('');
  const [items, setItems] = useState<LegalFeedItem[]>([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Court options come from the judgement items currently loaded.
  const courts = Array.from(
    new Set(items.map((i) => i.court).filter((c): c is string => !!c)),
  ).sort();

  useEffect(() => {
    setLoading(true);
    setError(null);
    api
      .getLegalFeed({ page, type: tab, court: court || undefined, page_size: 20 })
      .then((res) => {
        setItems(res.data);
        setTotalPages(res.total_pages || 1);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [tab, court, page]);

  const switchTab = (next: Tab) => {
    setTab(next);
    setCourt('');
    setPage(1);
  };

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <div className="eyebrow text-ink-faint mb-1">Library</div>
      <h1 className="font-display text-3xl text-ink mb-6">Legal Feed</h1>

      <div className="flex items-center gap-6 border-b border-rule mb-5">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => switchTab(t.key)}
            className={[
              'pb-2 text-sm font-medium transition-colors -mb-px border-b-2',
              tab === t.key
                ? 'text-oxblood border-oxblood'
                : 'text-ink-soft border-transparent hover:text-ink',
            ].join(' ')}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'judgement' && courts.length > 0 && (
        <select
          value={court}
          onChange={(e) => {
            setCourt(e.target.value);
            setPage(1);
          }}
          className="mb-5 border border-rule rounded px-3 py-1.5 text-sm bg-paper text-ink"
        >
          <option value="">All courts</option>
          {courts.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
      )}

      {loading && <p className="text-ink-muted text-sm">Loading…</p>}
      {error && <p className="text-oxblood text-sm">Failed to load: {error}</p>}
      {!loading && !error && items.length === 0 && (
        <p className="text-ink-muted text-sm">No items yet. Check back soon.</p>
      )}

      <ul className="space-y-4">
        {items.map((item) => (
          <li key={item.id} className="border border-rule rounded-lg p-4 bg-paper">
            <div className="flex items-center gap-2 mb-1">
              <span className="eyebrow text-ink-faint">{item.source_name}</span>
              {item.court && (
                <span className="text-2xs text-ink-muted">· {item.court}</span>
              )}
              {item.published_at && (
                <span className="text-2xs text-ink-muted ml-auto">
                  {new Date(item.published_at).toLocaleDateString()}
                </span>
              )}
            </div>
            <h3 className="text-ink font-medium mb-1">{item.title}</h3>
            {item.summary && (
              <p className="text-sm text-ink-soft line-clamp-3 mb-2">{item.summary}</p>
            )}
            <a
              href={item.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-oxblood hover:underline"
            >
              Read at source ↗
            </a>
          </li>
        ))}
      </ul>

      {totalPages > 1 && (
        <div className="mt-6">
          <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 3: Add the route** in `frontend/src/App.tsx` — import near the other page imports:

```tsx
import LegalFeed from './pages/LegalFeed';
```

and add a route inside the protected `Layout` block (next to `items`):

```tsx
            <Route path="legal-feed" element={<LegalFeed />} />
```

- [ ] **Step 4: Add the nav entry** in `frontend/src/components/Layout.tsx` — import an icon (extend the existing `lucide-react` import) and add to `NAV_SECONDARY` (or a new group). Using `Scale`:

```tsx
// add Scale to the lucide-react import:
import { LayoutDashboard, FileText, Users, Package, BarChart3, Settings as SettingsIcon, LogOut, Scale } from 'lucide-react';

// add to NAV_SECONDARY array:
  { name: 'Legal Feed', path: '/legal-feed', Icon: Scale },
```

- [ ] **Step 5: Verify build + lint**

Run: `cd frontend && npm run build`
Expected: succeeds. Then `npm run lint` — fix any new warnings/errors in the files you touched (lint is `--max-warnings 0`).

- [ ] **Step 6: Manual verification**

Run the frontend (`cd frontend && npm run dev`) against a backend that has seeded sources and at least one ingestion run. Log in, click "Legal Feed" in the sidebar, confirm tabs switch, the court dropdown filters, cards render with working "Read at source" links, and pagination works.

- [ ] **Step 7: Checkpoint** — report page + route + nav; let Parth review/commit.

---

### Task 11: Configuration & operations (env vars, scheduler)

**Files:**
- Modify: `backend/.env.example` (add the three new vars; create the file if it doesn't exist)
- Create: `docs/superpowers/legal-feed-ops.md` (operator runbook)

**Interfaces:** none (documentation/config only).

- [ ] **Step 1: Add env vars to `backend/.env.example`**

Append (read the file first to match its formatting; if it does not exist, create it with these lines):

```
# Admin panel (server-rendered at /admin). ADMIN_PASSWORD is REQUIRED —
# /admin returns 503 if it is unset. ADMIN_USERNAME defaults to "admin".
ADMIN_USERNAME=admin
ADMIN_PASSWORD=change-me-strong-password

# Shared secret the Cloud Scheduler job sends as the X-Ingest-Secret header
# when calling POST /api/v1/legal-feed/ingest. Required for ingestion to run.
LEGAL_FEED_INGEST_SECRET=change-me-random-secret
```

- [ ] **Step 2: Write the operator runbook** `docs/superpowers/legal-feed-ops.md`:

```markdown
# Legal Feed — Operations

## One-time setup
1. Set env vars in the Cloud Run service: `ADMIN_PASSWORD`, optionally
   `ADMIN_USERNAME`, and `LEGAL_FEED_INGEST_SECRET`.
2. Seed the source registry once: open `/admin`, authenticate, click
   **"Seed v1 sources"** (or run `cd backend && python -m app.services.legal_feed.seed`).
3. Verify the two news feed URLs (LiveLaw, Bar & Bench) return valid RSS; fix in
   the admin Sources table if needed.

## Scheduled ingestion (2×/day)
Create a Cloud Scheduler job (set the two times you want, e.g. 08:00 and 18:00 IST):

    Method:  POST
    URL:     https://<cloud-run-host>/api/v1/legal-feed/ingest
    Header:  X-Ingest-Secret: <LEGAL_FEED_INGEST_SECRET>
    Body:    (empty)

## Monitoring
- `/admin` → Legal Feed card shows recent runs (status, items ingested) and
  per-source results. Use "Run ingestion now" to test on demand.

## Tuning the feed
- Enable/disable sources and add new RSS feeds in the Sources table.
- Switch ordering between "Recency" and "Weighted" (uses per-source weight).
```

- [ ] **Step 3: Verify full backend test suite still passes**

Run: `cd backend && python -m pytest tests/ -v`
Expected: all legal-feed tests pass. (Pre-existing unrelated tests in `tests/test_api.py` that target `/api/clients` may already be failing before this work — note their status but do not fix them here; they are out of scope.)

- [ ] **Step 4: Checkpoint** — report env example + runbook; confirm the scheduler is Parth's manual step (he sets the two daily times); let Parth review/commit.

---

## Self-Review

**1. Spec coverage:**
- Ingestion pipeline (2×/day, scheduler→endpoint) → Tasks 5, 6, 11 ✓
- Config-driven source registry → Tasks 1, 4, 8 ✓
- Exact dedup (idempotent) → Tasks 2, 5 ✓
- Read API (type tabs, court filter, pagination, hidden excluded, ordering modes) → Task 6 ✓
- Frontend feed page + nav (two tabs, dropdown, cards, link-out) → Tasks 9, 10 ✓
- Admin panel (status, run-now, source mgmt, moderation, Feed Algorithm ordering) → Task 8 ✓
- Admin auth hardening (env creds, refuse if unset) → Task 7 ✓
- Run logging / partial-failure handling → Tasks 1, 5 ✓
- No full text (headline+summary+link only) → enforced by model + parser (Tasks 1, 3) ✓
- Notices tab deferred → not built; `content_type` enum reserves `notice` (Task 1) ✓
- Three tables + ordering setting → Task 1 (added a 4th small `legal_feed_settings` singleton for the ordering knob, which the spec described under Feed Algorithm but did not give storage for; noted as a minor, bounded addition) ✓

**2. Placeholder scan:** No "TBD"/"implement later". The only deferred-to-runtime item is verifying the two external news-feed URLs (Task 4 Step 5 / Task 11 Step 1) — that is an external-resource verification instruction with real default URLs shipped, not a code placeholder.

**3. Type consistency:** `compute_dedup_key(source_url, source_name, title)` consistent across Tasks 2/5. `run_ingestion(trigger)->dict` consistent Tasks 5/6/8. `query_feed(content_type, court, page, page_size)` and `get_ordering_mode()` consistent Tasks 6/8. Model field names (`feed_url`, `content_type`, `ordering_mode`, `hidden`, `weight`) consistent across backend tasks and the frontend `LegalFeedItem` (Tasks 9/10). Admin endpoint paths consistent between Task 8 impl and its tests.
