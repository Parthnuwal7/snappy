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
