"""Evidence exhibit register catalog: status vocabulary + producing-party
suggestions. Mirrors the court convention of marking exhibits (Ex. P-1 / D-1)
and tracking their admission."""

EXHIBIT_STATUSES = [
    {"key": "marked",   "label": "Marked"},
    {"key": "admitted", "label": "Admitted"},
    {"key": "objected", "label": "Objected"},
    {"key": "denied",   "label": "Denied"},
]
EXHIBIT_STATUS_KEYS = {s["key"] for s in EXHIBIT_STATUSES}
DEFAULT_EXHIBIT_STATUS = "marked"

EXHIBIT_PARTIES = [
    {"key": "petitioner", "label": "Petitioner / Plaintiff"},
    {"key": "respondent", "label": "Respondent / Defendant"},
    {"key": "court",      "label": "Court"},
]


def is_valid_exhibit_status(key):
    return key in EXHIBIT_STATUS_KEYS
