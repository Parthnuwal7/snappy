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


def test_judgement_is_not_enriched(db):
    item = _judgement()
    client = FakeClient(json.dumps({
        'headline': 'should be ignored', 'topics': ['Civil'], 'importance': 60,
    }))
    assert enrich_item(item, client) is False
    assert item.headline is None
    assert item.tldr is None
    assert item.topics is None
    assert item.importance is None
    assert item.enriched_at is None


def test_bad_json_is_a_failure(db):
    item = _news()
    assert enrich_item(item, FakeClient('not json')) is False
    assert item.enriched_at is None


def test_embed_text_uses_news_content(db):
    item = _news()
    client = FakeClient(json.dumps({'topics': ['Tax'], 'importance': 50}))
    enrich_item(item, client)
    # No headline in completion -> embed text falls back to the item title.
    assert 'Court rules on GST' in client.embed_calls[0]
