# Deeper Case Record — Design Spec

**Status:** Approved (brainstorming) — ready for planning
**Date:** 2026-06-23
**Sub-project:** 3b of the Snappy Legal CRM (depth iteration on the Case File spine)

## Purpose

Make the case record substantial: a **stage-progression audit**, **fee & expense
tracking** that closes the billing loop, and a **tabbed detail layout** so the
case page stays navigable as depth grows. Builds directly on the Case File spine
and the existing invoice↔case link.

## Guiding constraints

- Firm-scoped (`firm_id`) + `created_by_user_id` attribution; RBAC-only access.
- Stage history is **auto-recorded**, read-only, gated by `case_files.read`.
- Expense writes gate on `case_files.update`; reads on `case_files.read` (no new
  RBAC module — expenses are case-record data).
- Money columns are `Numeric(12,2)`, serialized via `_money` (float) like
  invoices.
- Migration delivered as `012` SQL for Parth; **Do not run git commits**.

## Scope

1. **Stage history** — every stage change recorded.
2. **Fee & expense tracking** — `agreed_fee` on the case, an expense ledger, and
   a computed financial summary.
3. **Tabbed detail layout** — Overview · Timeline · Documents · Fees & Billing.

Out of scope (deferred): document checklist (fits sub-project 4 templates).

## Data model

### `case_stage_changes` (audit log)

| Column | Type | Notes |
|---|---|---|
| `id` | Integer PK | |
| `firm_id` | FK `firms.id`, index | scope |
| `case_file_id` | FK `case_files.id`, index, cascade | |
| `from_stage` | String(40), nullable | NULL = initial (on case creation) |
| `to_stage` | String(40) | |
| `changed_by_user_id` | FK `users.id` | |
| `changed_at` | DateTime, default utcnow, index | |

### `case_expenses` (ledger)

| Column | Type | Notes |
|---|---|---|
| `id` | Integer PK | |
| `firm_id` | FK `firms.id`, index | scope |
| `case_file_id` | FK `case_files.id`, index, cascade | |
| `expense_date` | Date | |
| `description` | String(300), not null | |
| `category` | String(40), default `misc` | from a small catalog |
| `amount` | Numeric(12,2) | `_money` on output |
| `created_by_user_id` | FK `users.id` | |
| `created_at` | DateTime | |

### `case_files` (modified)

Add `agreed_fee` (`Numeric(12,2)`, nullable) — the quoted engagement fee.

## Catalog — `app/case/expenses.py`

```python
EXPENSE_CATEGORIES = [
    {"key": "court_fee",     "label": "Court fee"},
    {"key": "filing",        "label": "Filing / registry"},
    {"key": "travel",        "label": "Travel"},
    {"key": "professional",  "label": "Professional / counsel"},
    {"key": "misc",          "label": "Miscellaneous"},
]
EXPENSE_CATEGORY_KEYS = {c["key"] for c in EXPENSE_CATEGORIES}
DEFAULT_EXPENSE_CATEGORY = "misc"
def is_valid_expense_category(key): ...
```

Added to `GET /case-files/meta` as `expense_categories`.

## Stage-change recording

A helper `record_stage_change(case_file, from_stage, to_stage, user_id)` adds a
`CaseStageChange`. Called from:
- **create case** → `from_stage=None, to_stage=<initial>`.
- **update case** when `stage` is in the payload and actually changes.
- **move case** when the stage actually changes.

The recording reads `g.user.id` for `changed_by_user_id`.

## Financial summary

`GET /case-files/<id>/financials` (`case_files.read`) returns:

```json
{
  "agreed_fee": 50000.0,
  "total_expenses": 3200.0,
  "total_invoiced": 41000.0,
  "total_paid": 25000.0,
  "outstanding": 16000.0
}
```

- `total_expenses` = sum of the case's `case_expenses.amount`.
- `total_invoiced` = sum of `invoices.total` where `case_file_id == id`.
- `total_paid` = same, filtered `status == 'paid'`.
- `outstanding` = `total_invoiced − total_paid`.

## API (firm-scoped, `/api/v1`)

| Method & path | Permission | Purpose |
|---|---|---|
| `GET /case-files/<id>/stage-history` | `case_files.read` | progression log (oldest→newest) |
| `GET /case-files/<id>/financials` | `case_files.read` | summary above |
| `GET /case-files/<id>/expenses` | `case_files.read` | list |
| `POST /case-files/<id>/expenses` | `case_files.update` | add `{expense_date, description, category, amount}` |
| `PATCH /case-expenses/<id>` | `case_files.update` | edit |
| `DELETE /case-expenses/<id>` | `case_files.update` | remove |

`agreed_fee` is accepted on case create/update and returned in `CaseFile.to_dict`.
All `<id>` lookups filter by `firm_id` → 404 across firms.

## Frontend

- **`api.ts`**: types `CaseStageChange`, `CaseExpense`, `CaseFinancials`;
  `CaseFile` gains `agreed_fee`; `CaseMeta` gains `expense_categories`; methods
  `getStageHistory`, `getCaseFinancials`, `getCaseExpenses`, `addCaseExpense`,
  `updateCaseExpense`, `deleteCaseExpense`.
- **`CaseDetail.tsx`** restructured into **tabs**:
  - **Overview** — facts grid, description, parties, and the **progression**
    (stage history) strip.
  - **Timeline** — the existing diary.
  - **Documents** — the existing vault panel.
  - **Fees & Billing** — financial summary cards, the expense ledger
    (add/edit/delete), and linked invoices (with the "New invoice" shortcut).
  - The edit modal gains an **agreed fee** field.

## Testing

- **Models**: stage-change + expense `to_dict`/`_money`; cascade on case delete.
- **Catalog**: `is_valid_expense_category`.
- **API**: stage history recorded on create + on stage change (PATCH) + on move
  (and *not* recorded when stage is unchanged); expenses CRUD; financials
  computation (expenses + invoiced + paid + outstanding); `agreed_fee` persists;
  meta `expense_categories`; cross-firm 404 on stage-history/expenses/financials.
- **Frontend**: `npm run build` typechecks clean.

## Migration `012`

`backend/migrations/012_case_record_depth.sql` — additive: `ALTER TABLE
case_files ADD COLUMN agreed_fee NUMERIC(12,2)`; `CREATE TABLE
case_stage_changes`, `case_expenses` (FKs cascade, indexes). No backfill.
