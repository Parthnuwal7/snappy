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
