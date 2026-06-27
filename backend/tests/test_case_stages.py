from app.case.stages import (
    STAGES, STAGE_KEYS, DEFAULT_STAGE, EVENT_KINDS, LEGACY_STAGE_REMAP,
    STAGE_GUIDES, STAGE_FLOW, next_stage,
    is_valid_stage, is_valid_event_kind,
)


def test_stage_keys_in_lifecycle_order():
    keys = [s["key"] for s in STAGES]
    assert keys == ["engaged", "notice", "filed",
                    "hearings_evidence", "arguments", "judgment", "closed"]
    assert all("label" in s for s in STAGES)


def test_default_stage_is_engaged():
    assert DEFAULT_STAGE == "engaged"
    assert DEFAULT_STAGE in STAGE_KEYS


def test_stage_validation():
    assert is_valid_stage("filed")
    assert not is_valid_stage("teleported")


def test_event_kinds_and_validation():
    assert EVENT_KINDS == ["note", "filing", "hearing", "order", "step"]
    assert is_valid_event_kind("hearing")
    assert not is_valid_event_kind("smoke_signal")


def test_legacy_remap_targets_are_valid_stages():
    # Every legacy key must map to a key that exists in the new taxonomy.
    assert set(LEGACY_STAGE_REMAP) == {
        "intake", "drafting", "filed", "in_hearing", "awaiting_order", "closed"}
    for old, new in LEGACY_STAGE_REMAP.items():
        assert new in STAGE_KEYS
    assert LEGACY_STAGE_REMAP["intake"] == "engaged"
    assert LEGACY_STAGE_REMAP["in_hearing"] == "hearings_evidence"
    assert LEGACY_STAGE_REMAP["awaiting_order"] == "judgment"


def test_stage_guides_cover_every_stage():
    assert set(STAGE_GUIDES) == STAGE_KEYS
    for key, guide in STAGE_GUIDES.items():
        assert isinstance(guide["focus"], str) and guide["focus"]
        assert guide["actions"], f"{key} has no actions"
        for a in guide["actions"]:
            assert set(a) == {"key", "label", "available"}
            assert isinstance(a["available"], bool)


def test_next_stage_walks_the_lifecycle_and_ends_at_closed():
    assert next_stage("engaged") == "notice"
    assert next_stage("hearings_evidence") == "arguments"
    assert next_stage("closed") is None
    assert STAGE_FLOW["judgment"] == "closed"
    assert STAGE_FLOW["closed"] is None


def test_mark_exhibit_action_is_available():
    actions = {a["key"]: a for a in STAGE_GUIDES["hearings_evidence"]["actions"]}
    assert actions["mark_exhibit"]["available"] is True


def test_record_proceedings_available_in_court_stages():
    for stage in ("filed", "hearings_evidence", "arguments", "judgment"):
        actions = {a["key"]: a for a in STAGE_GUIDES[stage]["actions"]}
        assert actions["record_proceedings"]["available"] is True
