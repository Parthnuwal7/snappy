"""Code-defined case workflow catalog: kanban stages + timeline step kinds.

Stages drive the kanban columns in display order. A case is closed when its
stage is "closed" — there is no separate status field. Kinds classify timeline
(case_events) steps. Both are extended here without a schema change.
"""

STAGES = [
    {"key": "engaged",           "label": "Engaged"},
    {"key": "notice",            "label": "Notice"},
    {"key": "filed",             "label": "Filed"},
    {"key": "hearings_evidence", "label": "Hearings & Evidence"},
    {"key": "arguments",         "label": "Arguments"},
    {"key": "judgment",          "label": "Judgment"},
    {"key": "closed",            "label": "Closed"},
]

STAGE_KEYS = {s["key"] for s in STAGES}
DEFAULT_STAGE = "engaged"

EVENT_KINDS = ["note", "filing", "hearing", "order", "step"]

PRIORITIES = [
    {"key": "low",    "label": "Low"},
    {"key": "normal", "label": "Normal"},
    {"key": "high",   "label": "High"},
    {"key": "urgent", "label": "Urgent"},
]
PRIORITY_KEYS = {p["key"] for p in PRIORITIES}
DEFAULT_PRIORITY = "normal"

# Maps the pre-2026-06-25 stage keys to the current taxonomy. Mirrored by
# migrations/013_stage_taxonomy_remap.sql. Keys that did not change still
# appear so the mapping is total.
LEGACY_STAGE_REMAP = {
    "intake":         "engaged",
    "drafting":       "notice",
    "filed":          "filed",
    "in_hearing":     "hearings_evidence",
    "awaiting_order": "judgment",
    "closed":         "closed",
}

# Per-stage guidance for the case-file "This stage" rail. `available` is False
# for actions whose feature ships in a later plan (record proceedings = Plan 6,
# mark exhibit = Plan 5, drafting = Plan 7); those render as muted hints.
STAGE_GUIDES = {
    "engaged": {
        "focus": "Record the facts and sign the wakalatnama.",
        "actions": [
            {"key": "note", "label": "Add facts / note", "available": True},
            {"key": "new_draft", "label": "Draft wakalatnama", "available": False},
        ],
    },
    "notice": {
        "focus": "Draft and send the legal notice.",
        "actions": [
            {"key": "new_draft", "label": "Draft legal notice", "available": False},
            {"key": "note", "label": "Record notice sent", "available": True},
        ],
    },
    "filed": {
        "focus": "Petition filed — track show-cause and replies.",
        "actions": [
            {"key": "record_proceedings", "label": "Record proceedings", "available": True},
            {"key": "add_party", "label": "Add a party", "available": True},
            {"key": "documents", "label": "File a document", "available": True},
        ],
    },
    "hearings_evidence": {
        "focus": "Mark evidence, log cross-examination, track dates.",
        "actions": [
            {"key": "record_proceedings", "label": "Record proceedings", "available": True},
            {"key": "mark_exhibit", "label": "Mark an exhibit", "available": True},
            {"key": "note", "label": "Log cross-examination", "available": True},
        ],
    },
    "arguments": {
        "focus": "Final hearing and arguments.",
        "actions": [
            {"key": "record_proceedings", "label": "Record proceedings", "available": True},
            {"key": "note", "label": "Add a note", "available": True},
        ],
    },
    "judgment": {
        "focus": "Judgment reserved or delivered.",
        "actions": [
            {"key": "record_proceedings", "label": "Record proceedings", "available": True},
            {"key": "note", "label": "Record judgment", "available": True},
            {"key": "documents", "label": "Upload the order", "available": True},
        ],
    },
    "closed": {
        "focus": "Disposed — raise the bill and plan the next course.",
        "actions": [
            {"key": "raise_bill", "label": "Raise a bill", "available": True},
            {"key": "note", "label": "Record future course", "available": True},
        ],
    },
}

_STAGE_ORDER = [s["key"] for s in STAGES]
STAGE_FLOW = {
    key: (_STAGE_ORDER[i + 1] if i + 1 < len(_STAGE_ORDER) else None)
    for i, key in enumerate(_STAGE_ORDER)
}


def next_stage(key):
    return STAGE_FLOW.get(key)


HEARING_PURPOSES = [
    {"key": "framing",   "label": "Framing of issues"},
    {"key": "evidence",  "label": "Evidence"},
    {"key": "cross",     "label": "Cross-examination"},
    {"key": "arguments", "label": "Arguments"},
    {"key": "reply",     "label": "Reply / Rejoinder"},
    {"key": "orders",    "label": "Orders"},
    {"key": "misc",      "label": "Miscellaneous"},
]


def is_valid_stage(key):
    return key in STAGE_KEYS


def is_valid_event_kind(kind):
    return kind in EVENT_KINDS


def is_valid_priority(key):
    return key in PRIORITY_KEYS
