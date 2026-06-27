# DB Simplification — Design Spec

**Date:** 2026-06-26
**Status:** Approved (design) → implementation
**Goal:** Reduce table count by 4 (34 → 30) via structural merges, with **zero user-facing feature loss**. The `case_stage_changes` audit (Progression strip) is explicitly retained.

**Context:** Live billing data exists; user is taking a backup. Migrations are SQL files the user applies on the (backed-up) DB — no code path runs them.

## Refactors (in order; firms-merge last because it touches live billing)

### R1 — templates + drafts → `writing_documents`
One table with `kind ∈ {template, draft}`. Columns: `id, firm_id, created_by_user_id, kind, title, category (null for drafts), body, case_file_id (null for templates), created_at, updated_at`. (`drafts.template_id` is dropped — unused.)
- Model: replace `Template`/`Draft` with one `WritingDoc` (`writing_documents`).
- API: keep `/templates` and `/drafts` endpoints (compatibility) backed by the one table filtered by `kind`; `/templates` serializes `name = title`. RBAC modules `templates`/`drafts` unchanged.
- Migration `021`: create `writing_documents`; copy from `templates` (kind='template', title=name) and `drafts` (kind='draft'); drop `templates`, `drafts`.
- Frontend: unchanged (same endpoints, same `Template`/`Draft` shapes).

### R2 — case schema slim (keep progression)
- **case_parties → JSON.** Add `case_files.parties` (JSON list of `{name, role}`). `CaseFile.to_dict` reads it; `_set_parties` writes it. Drop `case_parties`.
- **case_exhibits → case_documents.** Add to `case_documents`: `is_exhibit (bool)`, `exhibit_mark`, `party`, `exhibit_status`, `hearing_event_id`; make `storage_path` **nullable** (fileless exhibits). The exhibits API operates on `case_documents WHERE is_exhibit`. Drop `case_exhibits`.
- **Keep `case_stage_changes`** (Progression strip).
- Migration `022`: add columns; copy `case_parties` into `case_files.parties`; copy `case_exhibits` into `case_documents` (is_exhibit=true); make storage_path nullable; drop `case_parties`, `case_exhibits`.

### R3 — firms + firm_details → `firms`
Move all `firm_details` config columns onto `firms` (address, email/phones, logo/signature, terms, invoice settings, email/whatsapp templates, default_template, invoice_prefix, default_tax_rate, currency, show_due_date, …). Drop `firm_details`.
- Model: fold `FirmDetails` fields into `Firm`; update all usages (onboarding, settings, invoice/PDF rendering, firm API).
- Migration `023`: add columns to `firms`; copy `firm_details` rows by `firm_id`; drop `firm_details`.
- **Live billing data** — apply on the backed-up DB; do this refactor last.

## Non-goals / kept

`legal_feed_settings`, `legal_feed_runs` kept (not selected). `case_expenses`, `case_notes`, `case_events`, `case_documents`, `leads`, `tasks`, `bank_accounts` kept. No feature removed.

## Testing

Backend pytest green after each refactor; frontend `npm run build` clean. Each refactor delivers a numbered migration SQL for the user.
