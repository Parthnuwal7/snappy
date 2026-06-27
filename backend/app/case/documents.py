"""Document vault catalog: fixed doc-type vocabulary + upload constraints."""

DOC_TYPES = [
    {"key": "pleading",       "label": "Pleading"},
    {"key": "wakalatnama",    "label": "Wakalatnama"},
    {"key": "evidence",       "label": "Evidence / Exhibit"},
    {"key": "order",          "label": "Order / Judgment"},
    {"key": "correspondence", "label": "Correspondence"},
    {"key": "draft",          "label": "Draft"},
    {"key": "other",          "label": "Other"},
]
DOC_TYPE_KEYS = {d["key"] for d in DOC_TYPES}
DEFAULT_DOC_TYPE = "other"

MAX_DOCUMENT_BYTES = 25 * 1024 * 1024  # 25 MB
ALLOWED_EXTENSIONS = {"pdf", "jpg", "jpeg", "png", "doc", "docx", "xls", "xlsx", "txt"}


def is_valid_doc_type(key):
    return key in DOC_TYPE_KEYS


def extension_of(filename):
    return filename.rsplit(".", 1)[1].lower() if "." in filename else ""


def is_allowed_filename(filename):
    return extension_of(filename) in ALLOWED_EXTENSIONS
