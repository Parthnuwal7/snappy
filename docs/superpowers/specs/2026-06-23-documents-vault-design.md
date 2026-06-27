# Documents & Evidence Vault — Design Spec

**Status:** Approved (brainstorming) — ready for implementation planning
**Date:** 2026-06-23
**Sub-project:** 3 of the Snappy Legal CRM (builds on sub-project 2, the Case File spine)

## Purpose

Give each case file a digital record vault: upload, organize, and retrieve the
documents a matter accumulates — pleadings, the wakalatnama, evidence/exhibits,
orders, correspondence, drafts. Documents hang off `case_file_id` and may
optionally be tied to a `case_events` timeline step, so the "open the file"
view can show what was filed on a given date.

## Guiding constraints

- **Solo-first, RBAC-only** access — a new `documents` permission module (CRUD),
  firm-wide, consistent with case files. No per-matter walls.
- **Reuse the existing storage pattern**: private Supabase buckets, upload by
  path, download via short-lived signed URLs (see `app/api/storage.py`).
- File bytes live in Supabase Storage; **metadata lives in Postgres**.
- Storage access goes through a thin, monkeypatchable service so the API is
  testable on in-memory SQLite without Supabase (same pattern as
  `invite_service.supabase_email_inviter`).
- Migration delivered as SQL (`011`) for Parth to apply manually; the
  `case-documents` bucket is created manually in the Supabase dashboard.
- **Git:** Parth handles commits. End each task at a green test/build run.

## Decisions (from brainstorming)

1. A document belongs to a **case file**, with an **optional** link to a
   timeline step (`event_id`).
2. **No version chains** — each upload is its own document row (name them
   "Petition v2"). Replace = delete + re-upload.
3. **`doc_type` field** (fixed vocabulary) + **≤ 25 MB** + common legal formats.
   "Evidence" is a `doc_type` value, not a separate table.

## Data model — `case_documents`

New model in `app/models/case.py` (case concerns stay in one file).

| Column | Type | Notes |
|---|---|---|
| `id` | Integer PK | |
| `firm_id` | FK `firms.id`, index | access scope |
| `case_file_id` | FK `case_files.id`, index, **cascade delete** | owner |
| `event_id` | FK `case_events.id`, nullable, index | optional timeline-step link |
| `uploaded_by_user_id` | FK `users.id` | attribution |
| `title` | String(300), not null | display name |
| `doc_type` | String(40), not null, default `other` | fixed vocabulary (below) |
| `file_name` | String(300) | original upload filename |
| `mime_type` | String(120) | |
| `size_bytes` | Integer | |
| `storage_path` | String(500) | bucket key; **never serialized** |
| `description` | Text | optional |
| `created_at` | DateTime | |

`to_dict()` returns all fields **except `storage_path`** (internal). Download is
a separate signed-URL endpoint.

When a `case_event` is deleted, its documents are **not** deleted — their
`event_id` is set NULL (the file still belongs to the case). When a `case_file`
is deleted, its documents cascade (rows) and the API best-effort removes the
storage objects.

## Catalog — `app/case/documents.py`

```python
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

def is_valid_doc_type(key): ...
def is_allowed_filename(filename): ...  # extension in ALLOWED_EXTENSIONS
```

`doc_types` is added to the existing `GET /case-files/meta` payload.

## Storage service — `app/services/document_storage.py`

Bucket: `case-documents` (private). Object key: `{firm_id}/{case_file_id}/{uuid4}.{ext}`
— namespaced by firm + case so nothing collides or leaks across firms.

Module-level functions (monkeypatched in tests):

```python
BUCKET = "case-documents"

def put_object(storage_path, data: bytes, content_type) -> None
def signed_url(storage_path, ttl=3600) -> str
def remove_object(storage_path) -> None
def build_storage_path(firm_id, case_file_id, ext) -> str   # uuid-based key
```

Each raises `StorageError` (or returns a 503-mapped error) if Supabase isn't
configured. They wrap `get_supabase_client().storage.from_(BUCKET)...`.

## RBAC — new `documents` module

Add to `MODULES` in `app/rbac/permissions.py`: `{"key": "documents", "label":
"Documents", "actions": CRUD}`. Owner resolves to all permissions
automatically. Default grants: **Partner** CRUD; **Associate** create/read/update;
**Staff** create/read (delete reserved for seniors).

## API — `app/api/case_documents.py` (firm-scoped, `/api/v1`)

| Method & path | Permission | Purpose |
|---|---|---|
| `GET /case-files/<case_id>/documents` | `documents.read` | list (filter `doc_type`, `event_id`) |
| `POST /case-files/<case_id>/documents` | `documents.create` | multipart upload (`file` + `title` + `doc_type` + `description` + optional `event_id`) |
| `GET /case-documents/<doc_id>/download` | `documents.read` | `{ "url": signed-url }` |
| `PATCH /case-documents/<doc_id>` | `documents.update` | edit metadata (title / doc_type / description / event_id) |
| `DELETE /case-documents/<doc_id>` | `documents.delete` | delete row + storage object |

Validation: title required; `doc_type` must be valid (defaults to `other`);
filename extension in `ALLOWED_EXTENSIONS`; size ≤ `MAX_DOCUMENT_BYTES`; an
`event_id`, if given, must belong to the same case. All `<id>` lookups filter
by `firm_id` → 404 across firms. Upload returns 503 if storage unconfigured.

## Frontend

- **`api.ts`**: `CaseDocument` type + `getCaseDocuments`, `uploadCaseDocument`
  (FormData, like `uploadImage`), `getDocumentDownloadUrl`, `updateCaseDocument`,
  `deleteCaseDocument`; `doc_types` added to `CaseMeta`.
- **`CaseDetail.tsx`**: a **Documents panel** — list rows (title, doc-type
  badge, size, date, uploader), an upload control (file picker + title +
  doc-type select), download (open signed URL in new tab), edit metadata, delete
  (gated by `documents.delete`). Controls gated via `usePermissions`.
- Timeline steps may show their linked documents (filter by `event_id`); full
  per-step attach UI can come incrementally.

## Testing

- **Models**: `case_documents` cascade on case delete; `event_id` set-null on
  event delete; `to_dict` omits `storage_path`; `is_valid_doc_type`/
  `is_allowed_filename`.
- **API** (fake `document_storage` via monkeypatch): upload → row created +
  `put_object` called with namespaced path; oversize → 400; disallowed
  extension → 400; bad `doc_type` → 400; `event_id` from another case → 400;
  download → returns `signed_url`; delete → row gone + `remove_object` called;
  cross-firm read/download/delete → 404; missing storage config → 503.
- **RBAC**: a role without `documents.read` → 403.
- **Frontend**: `npm run build` typechecks clean.

## Migration `011` + manual bucket

`backend/migrations/011_case_documents.sql` — additive: `CREATE TABLE
case_documents` with FKs (case_file_id cascade; event_id ON DELETE SET NULL) and
indexes. **Manual:** create a private `case-documents` bucket in the Supabase
dashboard. Permissions need no migration (Owners dynamic; others via Roles
editor).

## Seam for later

The `event_id` link is the hook for sub-project 2's timeline to surface a step's
documents, and for future drafting/AI (sub-project 4) to write generated drafts
straight into the vault.
