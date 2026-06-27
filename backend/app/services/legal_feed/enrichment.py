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
    """Enrich one NEWS item in place. Returns True on success, False otherwise.

    Judgements are intentionally NOT enriched for now (handled later) — callers
    should not select them, but this guard keeps it safe if they do.
    """
    if item.content_type != 'news':
        return False
    user = f"Title: {item.title}\nSummary: {item.summary or ''}"
    try:
        parsed = json.loads(client.complete(_NEWS_SYSTEM, user))
        if not isinstance(parsed, dict):
            return False
        topics = normalize_topics(parsed.get('topics'))
        importance = _clamp_importance(parsed.get('importance'))
        embed_text = f"{parsed.get('headline') or item.title}\n{parsed.get('tldr') or ''}\n{item.summary or ''}"
        embedding = client.embed(embed_text)
    except Exception:
        return False

    item.headline = (parsed.get('headline') or '').strip() or None
    item.tldr = (parsed.get('tldr') or '').strip() or None
    item.topics = topics
    item.importance = importance
    item.embedding = embedding
    item.embed_model = getattr(client, 'embed_model', DEFAULT_EMBED_MODEL)
    item.enriched_at = datetime.utcnow()
    return True
