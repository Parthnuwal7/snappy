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
