# Writing / Drafting Editor — Design Spec (Sub-project C)

**Date:** 2026-06-26
**Status:** Approved (design) → implementation (phase C1)
**Editor decision:** Embedded **TipTap** (ProseMirror). Not Google Docs API (which is plumbing, not an embeddable editor) and not a self-hosted Office server (heavy ops; blocks merge-fields/AI).

## Goal

A native drafting workspace: reusable **templates** with merge-field tokens, **drafts** (case-linkable, born blank or from a template), and a capable rich-text editor. Phase C1 ships the editor + templates + drafts + load-template-as-draft + merge-fields + PDF export. Phase C2 (later) adds AI-assist, DOCX export, and save-to-case-vault.

## Entities

- **Template** — `firm_id, created_by_user_id, name, category, body (HTML), created_at, updated_at`. `category` ∈ {wakalatnama, notice, application, other}. Plus a code catalog of **built-in starter templates** (wakalatnama, legal notice) so drafting works on day one.
- **Draft** — `firm_id, created_by_user_id, title, body (HTML), case_file_id? (link), template_id? (origin), created_at, updated_at`. `to_dict` includes `case_number`/`case_title` when linked.

## Merge fields

A catalog (`app/writing/merge.py`) of `{token, label, source}` — e.g. `{{petitioner}}`, `{{respondent}}`, `{{court}}`, `{{case_number}}` (court case no.), `{{file_number}}` (CF no.), `{{client}}`, `{{matter}}`, `{{date}}`. The editor's **Insert field** menu lists them. **Fill from case** (client-side) resolves each `source` against the draft's linked case (parties by role, court, numbers, client, today) and replaces tokens in the editor content. Tokens are plain text, so unfilled tokens are harmless.

## API (single `writing` blueprint, `/api/v1`)

- `GET /writing/meta` → `{ merge_fields, template_categories, builtin_templates }`.
- Templates: `GET /templates`, `POST /templates`, `GET/PATCH/DELETE /templates/<id>`.
- Drafts: `GET /drafts?case_file_id=`, `POST /drafts`, `GET/PATCH/DELETE /drafts/<id>`.

## RBAC

- `templates` module: Owner auto; **Partner CRUD**; Associate/Staff **read** (templates are firm config).
- `drafts` module: Owner auto; **Partner/Associate/Staff CRUD** (everyone drafts).

## Frontend

- **Deps:** TipTap — `@tiptap/react`, `@tiptap/starter-kit`, `@tiptap/extension-underline`, `@tiptap/extension-link`, `@tiptap/extension-text-align`, `@tiptap/extension-highlight`, table extensions.
- **`components/Editor.tsx`** — TipTap editor + toolbar (headings, B/I/U, lists, align, link, table, highlight) + an Insert-field dropdown. Controlled via `content`/`onChange`.
- **`pages/Writing.tsx`** — replaces the placeholder; subtabs **Templates · Drafts**. Drafts list + "New draft" (blank or from a template/built-in). Templates list + "New template".
- **`pages/DraftEditor.tsx`** (`/writing/draft/:id`, `:id='new'`) — title, case-link select, the editor, Insert-field, **Fill from case**, Save, **Export PDF**.
- **`pages/TemplateEditor.tsx`** (`/writing/template/:id`) — name, category, the editor, Save.
- **Export PDF** — Save then open a chrome-free print route `/print/draft/:id` that renders the saved HTML and auto-prints (reuses the cause-list print pattern).
- `api.ts` — `Template`/`Draft` types + CRUD methods + `getWritingMeta`.

## Routing

Add under the Layout: `/writing` (Writing), `/writing/draft/:id`, `/writing/template/:id`. Add a chrome-free sibling `/print/draft/:id` (ProtectedRoute, outside Layout).

## Migration

`019_writing.sql` — `templates` + `drafts` tables (additive).

## Out of scope (C2)

AI-assist (LLM endpoint + inline UX), DOCX export, save-draft-to-case-vault (CaseDocument) + surfacing drafts in the case file, real-time collaboration, pagination.

## Testing

Backend: pytest — model `to_dict`, RBAC grants, templates/drafts CRUD + firm isolation + `case_file_id` filter, writing meta. Frontend: `npm run build` clean (after installing TipTap deps). Migration 019 for Parth.
