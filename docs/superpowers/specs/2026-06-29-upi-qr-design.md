# Dynamic UPI QR on Invoices — Design

**Date:** 2026-06-29
**Status:** Approved (pending spec review)

## Goal

Replace the static, user-uploaded UPI QR image with a **per-invoice generated
QR** that embeds an NPCI UPI deep link carrying the exact amount and invoice
number, so a payer scans and pays the precise bill without manual entry.

## Background — current state

- The QR today is a static image the user uploads to Supabase Storage
  (bucket `qr-codes`), fetched per-invoice via `get_supabase_image(user_id,
  'qr')` and embedded in the PDF. Same sticker on every invoice; no amount, no
  reference.
- **Source of truth for bank/UPI data is the `BankAccount` table**
  (`app/models/auth.py`, user-scoped, `is_default=True`), NOT `FirmDetails`.
  `FirmDetails` has no bank fields. The frontend `firm` object only appears to
  carry `upi_id` because `/firm` GET and `/auth/me` merge the default
  `BankAccount` fields in.
- Two PDF footer renderers in `app/services/pdf_templates.py` render the QR —
  one historically via `firm.upi_qr_path` (file path), one via the Supabase
  `qr_bytes`. Both fall back to a placeholder/bank-text block when absent.
- No QR library exists in either backend or frontend.

## NPCI UPI deep link

```
upi://pay?pa={UPI_ID}&pn={PAYEE_NAME}&am={AMOUNT}&cu=INR&tn={NOTE}&tr={INVOICE_NO}
```

| Param | Meaning | Source |
|-------|---------|--------|
| `pa` | Payee address (VPA / UPI ID) | `BankAccount.upi_id` (mandatory) |
| `pn` | Payee name | `BankAccount.upi_payee_name` (mandatory, new) |
| `am` | Amount (locks the amount in payer's app) | invoice total, 2 decimals; **omitted when ≤ 0** |
| `cu` | Currency | always `INR` |
| `tn` | Transaction note | `{upi_note} — {invoice_no}` or just `{invoice_no}` |
| `tr` | Tracking reference | invoice number |

## Decisions (locked)

1. **Payee name** = dedicated `BankAccount.upi_payee_name` field, distinct from
   bank `account_holder_name`.
2. **Note (`tn`)** = auto, prefixed by user default: `f"{upi_note} — {invoice_no}"`,
   falling back to `invoice_no` when no default note is set.
3. **Web rendering** = backend returns the `upi://` string in JSON; the frontend
   draws the QR from that string with a JS QR lib. The backend separately renders
   the QR into the PDF from the same string builder (single source for the
   *string*, two renderers for the *image*).
4. **Required gate** = required at banking save (frontend + backend 400 when
   saving banking without `upi_id` + `upi_payee_name`). The minimal name-only
   onboarding gate is unchanged.
5. **`upi_qr_path`** = dropped in the migration (genuinely dead after this).

## Architecture

### Data model — migration `024_upi_qr.sql` (manual apply on Supabase)

```sql
ALTER TABLE bank_accounts ADD COLUMN IF NOT EXISTS upi_payee_name VARCHAR(200);
ALTER TABLE bank_accounts ADD COLUMN IF NOT EXISTS upi_note       VARCHAR(120);
ALTER TABLE bank_accounts DROP COLUMN IF EXISTS upi_qr_path;
```

Model (`app/models/auth.py` `BankAccount`): add `upi_payee_name`, `upi_note`;
remove `upi_qr_path` column + its `to_dict()` key.

### Backend service — `app/services/upi.py` (new, focused unit)

- `build_upi_uri(upi_id, payee_name, amount=None, note=None, invoice_no=None) -> str`
  - Returns `upi://pay?…` with params URL-encoded via `urllib.parse.urlencode`.
  - `pa`, `pn`, `cu=INR` always; `am` only when `amount` is set and `> 0`,
    formatted `f"{amount:.2f}"`; `tn` only when `note`; `tr` only when `invoice_no`.
  - Returns empty string `""` when `upi_id` is falsy (caller treats as "no QR").
- `compose_note(upi_note, invoice_no) -> str`
  - `f"{upi_note} — {invoice_no}"` when `upi_note` set, else `invoice_no`.
- `qr_png(uri) -> bytes` — render PNG via **`segno`** (pure-Python, no Pillow).

Add `segno` to `backend/requirements.txt`.

### Wiring

- **`pdf_templates.py`** (both footer renderers): build the URI from the
  invoice's `bank.upi_id`, `bank.upi_payee_name`, invoice total, and
  `compose_note(bank.upi_note, invoice.invoice_number)`; render with `qr_png`
  and embed. **Keep the existing fallback to the bank-details text block when
  `upi_id` is empty.** Remove the `get_supabase_image('qr')` / `upi_qr_path`
  image paths.
- **`public.py` `_public_dict`**: add `payment.upi_uri` (built from the bank +
  invoice). Empty string when no `upi_id`.
- **Invoice JSON consumed by the on-screen `InvoicePreview`**: expose `upi_uri`
  the same way.
- **`storage.py`**: remove the `qr` bucket entry and the `qr` handling from
  upload / delete / signed-url / precache (and the precache loop list).
- **`pdf_templates.py` shell cache**: drop `qr_bytes` prefetch.

### Frontend

- **`pages/Settings.tsx` → Payment section:** add **UPI payee name** (required)
  and **Default payment note** (optional) inputs bound to `upi_payee_name` /
  `upi_note`; **remove** the `<ImageUpload type="qr">` tile (and its mention in
  the Branding heading + backup copy).
- **Banking save (Settings + `SetupChecklist`):** block save and surface an
  error when `upi_id` or `upi_payee_name` is blank; backend returns 400 on the
  same condition.
- **`api.ts`:** drop `qr` from the image-upload type union.
- **`components/InvoicePreview.tsx` + `pages/PublicInvoice.tsx`:** render the QR
  from `upi_uri` using **`qrcode.react`**, labelled "Scan to pay ₹{amount}".
  Render nothing when `upi_uri` is empty.

### Pre-work

Resolve the existing git merge-conflict markers in `backend/app/api/auth.py`
(`<<<<<<< Updated upstream` / `=======` / `>>>>>>> Stashed changes`) before
editing the `/me`, `/firm`, and onboarding handlers there. Confirm the intended
resolution with the user.

## Error handling

- No `upi_id` → `build_upi_uri` returns `""`; PDF falls back to bank-text block,
  web pages render no QR. No error surfaced.
- Amount ≤ 0 (draft / zero) → QR generated without `am` so a payer can still
  enter an open amount.
- Special characters in payee name / note → URL-encoded by `urlencode`.

## Testing

**Backend (`tests/`):**
- `build_upi_uri`: full param set present & correctly ordered/encoded; `am`
  formatted to 2 decimals; `am` omitted when amount is 0/None; `cu=INR` always;
  returns `""` when `upi_id` blank.
- `compose_note`: prefix + invoice number; invoice number alone when no default.
- `qr_png`: returns non-empty bytes beginning with the PNG signature.
- `_public_dict`: includes `payment.upi_uri`; empty when no bank `upi_id`.
- PDF generation: produces output both with `upi_id` (QR path) and without
  (fallback path) — no exceptions.
- Banking save: 400 when `upi_id` / `upi_payee_name` missing.

**Frontend:** `npm run build` clean.

## Out of scope

- Merging `firm_details` into `firms` (the broader R3 refactor).
- Multiple bank accounts per invoice / choosing a non-default account.
- Partial-payment-aware `am` (uses invoice total; partial-payment ledger is a
  separate effort).
