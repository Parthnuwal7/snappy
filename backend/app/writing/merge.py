"""Merge-field catalog. `source` is resolved client-side against the linked case."""
MERGE_FIELDS = [
    {"token": "{{petitioner}}", "label": "Petitioner / Plaintiff", "source": "petitioner"},
    {"token": "{{respondent}}", "label": "Respondent / Defendant", "source": "respondent"},
    {"token": "{{court}}",       "label": "Court",                  "source": "court"},
    {"token": "{{case_number}}", "label": "Court case no.",         "source": "court_case_number"},
    {"token": "{{file_number}}", "label": "File no. (CF)",          "source": "case_number"},
    {"token": "{{client}}",      "label": "Client",                 "source": "client_name"},
    {"token": "{{matter}}",      "label": "Matter title",           "source": "title"},
    {"token": "{{date}}",        "label": "Today's date",           "source": "today"},
]
TEMPLATE_CATEGORIES = [
    {"key": "wakalatnama", "label": "Wakalatnama"},
    {"key": "notice",      "label": "Legal notice"},
    {"key": "application", "label": "Application"},
    {"key": "other",       "label": "Other"},
]
