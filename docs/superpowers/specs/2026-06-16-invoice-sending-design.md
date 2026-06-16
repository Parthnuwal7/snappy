# Invoice Sending (WhatsApp + Email) — Design Spec

**Date:** 2026-06-16
**Status:** Approved design, pending spec review → implementation plan
**Owner:** Parth

## Goal

Add a distribution layer to Snappy so a user can send a finished invoice to their
client over **WhatsApp** or **email**, directly from the app. Today invoices can be
created and rendered to PDF, but there is no way to deliver them.

## Decisions (locked)

| Area | Decision |
| --- | --- |
| WhatsApp delivery | **Deep-link** (`wa.me` click-to-chat). Server builds a pre-filled message + link; user taps send in their own WhatsApp. Free, no Meta approval. Cannot be automated. |
| Email delivery | **Server-sent via Resend** transactional API, PDF attached. |
| Shareable link | **HMAC-signed link** encoding `user_id` + `invoice_id` → opens a **hosted public invoice page**; PDF regenerated on demand. No file storage. |
| Send trigger (v1) | **Manual only** — a "Send" button per invoice. (Auto-send recurring is out of scope.) |
| Send tracking | Record `sent_at` + `sent_channel`; flip `draft → sent`; never touch `paid`/`void`. |
| Message content | **Per-firm editable templates** (saved defaults) **+ per-send override** in the Send dialog. |
| Email sender identity | From `invoices@snappyco.org` (display name = firm name), **reply-to = firm email**. One verified domain, not one per firm. |
| Email transport | Pluggable `EmailTransport` interface. `ResendTransport` is v1; `GmailOAuthTransport` is **Phase 2** (documented below, not built). |

## Non-goals (v1)

- Automated / scheduled sending (recurring auto-email).
- Per-firm domain verification.
- Gmail OAuth ("send from your own Gmail") — designed-for, but Phase 2.
- Delivery/open tracking, retries, full send history/audit log.
- "Pay now" on the hosted page (the page is structured to host it later).

## Architecture

### 1. Shareable link + hosted invoice page

The backbone both channels depend on. WhatsApp cannot attach a file, so the client
must receive a **link**; email points at the same link for consistency.

- **Signed link, stateless, no storage.** Token = `user_id` + `invoice_id` + a short
  **HMAC-SHA256 signature** derived from a server secret (`INVOICE_LINK_SECRET`).
  This makes links **unforgeable** — raw `user_id/invoice_number` would be enumerable
  because invoice numbers run sequentially (`INV/0001`, `INV/0002`, …).
  - Link shape: `{PUBLIC_BASE_URL}/i/{user_id}/{invoice_id}/{sig}`
  - `sig = hmac_sha256(INVOICE_LINK_SECRET, f"{user_id}:{invoice_id}")` → hex, truncated
    (e.g. first 32 chars). Verified with constant-time comparison.
- **Public backend endpoints (no JWT):**
  - `GET /api/v1/public/invoices/<int:user_id>/<int:invoice_id>?sig=…`
    Verifies sig. Returns a **safe public subset**: firm name/logo/contact, client name,
    line items, subtotal/tax/total, invoice number, dates, status, UPI/bank for payment.
    Bad/missing sig → `403`. Voided invoice → `404` (or "no longer available").
  - `GET /api/v1/public/invoices/<int:user_id>/<int:invoice_id>/pdf?sig=…`
    Verifies sig, regenerates the PDF on demand via `generate_pdf_with_template`,
    streams `application/pdf`.
- **Hosted page (frontend):** new public route `/i/:userId/:invoiceId/:sig`, rendered
  **outside the authenticated app shell**. Shows a clean invoice view + a **Download PDF**
  button. This is what the client sees when they tap the link, and the natural future
  home for a "Pay now" button.
- **Exposure note:** anyone with the link can view the invoice (by design — it is a
  share link). The HMAC stops *enumeration/guessing*, not link forwarding. Acceptable
  for v1; optional expiry can be added later by including a timestamp in the signed payload.

### 2. Email delivery (Resend)

- New service `app/services/email_service.py`:
  - `EmailTransport` interface: `send(to, subject, html, pdf_bytes, pdf_name, reply_to, from_name) -> result`.
  - `ResendTransport` implements it using the Resend Python SDK + `RESEND_API_KEY`.
  - `send_invoice_email(invoice, firm, client, subject, body, pdf_bytes, link)` composes
    and dispatches via the configured transport.
- **From identity:** `"{firm_name} <invoices@snappyco.org>"`, **reply-to = `firm.firm_email`**.
  One verified domain (`snappyco.org`) covers all firms.
- Attaches the freshly rendered PDF and includes the hosted link in the body.
- Recipient = `client.email`. If missing, the Send dialog blocks the email channel.

### 3. WhatsApp delivery (deep-link)

- Server **never sends**. It builds:
  `https://wa.me/<phone_e164>?text=<url-encoded message including the hosted link>`
  and returns it; the frontend `window.open`s it → user's WhatsApp opens with the client
  and message pre-filled; user taps send.
- **Phone normalization** helper → E.164. Strip spaces/dashes/`+`; if no country code,
  default `+91` (India). If `client.phone` is missing/unparseable, the Send dialog blocks
  the WhatsApp channel with a clear message.

### 4. Send orchestration

- New service `app/services/send_service.py`:
  - Renders the message from the (firm template or per-send override) via the placeholder
    formatter.
  - For **email**: builds link, regenerates PDF, calls `send_invoice_email`.
  - For **whatsapp**: builds link + `wa.me` URL, returns it.
  - On success: records `sent_at = now`, `sent_channel = channel`; if `status == 'draft'`,
    sets `status = 'sent'`.
- **Endpoint:** `POST /api/v1/invoices/<int:id>/send`
  - Body: `{ "channel": "email" | "whatsapp", "subject"?: str, "body"?: str }`
    (`subject`/`body` are the per-send overrides from the dialog; absent → render from firm template).
  - `email` → sends, records sent, returns `{ status, sent_at, sent_channel }`.
  - `whatsapp` → records sent (best-effort — we cannot confirm the user actually tapped
    send), returns `{ whatsapp_url, status, sent_at, sent_channel }`.
  - Validation: recipient present for the chosen channel, invoice belongs to user, not void.

### 5. Send tracking

- Migration adds `invoices.sent_at TIMESTAMP NULL`, `invoices.sent_channel VARCHAR(20) NULL`.
- On send: set both; `draft → sent`; never change `paid`/`void`. `'sent'` is app-level only
  (status is free-form varchar, no DB enum/constraint).
- `Invoice.to_dict` returns `sent_at`, `sent_channel`.
- Frontend: "Sent {date} via {channel}" badge in InvoiceList + invoice detail; status filter
  learns `sent`.

### 6. Message templates (per-firm + per-send override)

- New `FirmDetails` columns (all `TEXT NULL`, fall back to built-in defaults when null):
  `email_subject_template`, `email_body_template`, `whatsapp_template`.
- **Placeholders:** `{client_name} {invoice_number} {firm_name} {total} {due_date} {invoice_link}`.
  Rendered by a small **safe formatter** (unknown placeholders left intact or blank — never
  raises `KeyError`).
- **Built-in defaults** (used when a firm template is null), e.g.:
  - Email subject: `Invoice {invoice_number} from {firm_name}`
  - Email body: greeting + "Please find invoice {invoice_number} for {total}, due {due_date}.
    View it here: {invoice_link}" + sign-off.
  - WhatsApp: `Hi {client_name}, here's invoice {invoice_number} for {total} (due {due_date}): {invoice_link}`
- **Settings UI:** new "Messages" section to edit the three templates (saved to FirmDetails).
- **Send dialog:** pre-fills subject/body (email) or text (whatsapp) from the rendered firm
  template; user can tweak before sending; edited values posted to `/send`.

### 7. Frontend

- **Send button** on each invoice (InvoiceList row action + invoice detail) → **Send dialog**:
  - Channel tabs: WhatsApp / Email.
  - Editable message preview (pre-filled per §6).
  - Shows recipient (`client.email` / `client.phone`); warns + disables a channel if its
    contact field is missing.
  - Email → `POST /send`, toast success/failure.
  - WhatsApp → `POST /send`, receive `whatsapp_url`, `window.open` it, toast.
- **Public hosted invoice page** — new route/component, no auth, no app shell.
- `api.ts`: add `sendInvoice(id, payload)` and public fetchers (`getPublicInvoice`,
  `publicPdfUrl`).

### 8. Config, migration, tests

- **New env / secrets** (added to `.env.example` + Cloud Run):
  - `RESEND_API_KEY` — Resend API key.
  - `INVOICE_LINK_SECRET` — HMAC secret for signed links.
  - `EMAIL_FROM` — verified sender, default `invoices@snappyco.org`.
  - `PUBLIC_BASE_URL` — base for building links (Vercel URL now; `snappyco.org` later).
- **Migration `007_invoice_sending.sql`** (matches existing migration style):
  - `invoices`: `sent_at`, `sent_channel`.
  - `firm_details`: `email_subject_template`, `email_body_template`, `whatsapp_template`.
  - Models + `to_dict` updated accordingly.
- **Tests** (SQLite-compatible, in-memory):
  - HMAC sign/verify roundtrip; tampered/short sig rejected.
  - Template rendering with all placeholders; null-template fallback to defaults; unknown
    placeholder does not raise.
  - Phone → E.164 normalization (with/without country code, with separators, invalid).
  - `POST /send` email path (Resend mocked): records `sent_at`/`sent_channel`, flips
    `draft → sent`, leaves `paid` unchanged; blocks when `client.email` missing.
  - `POST /send` whatsapp path: returns `whatsapp_url`, records sent; blocks when phone missing.
  - Public endpoint: `200` + safe subset on valid sig; `403` on bad sig; `404` on void.

## Phase 2 — "Connect Gmail" (documented, not built)

Some firms will want invoices to come from **their own** email address, not the shared
`snappyco.org`. The only legitimate way to send "from `name@gmail.com`" is Google's Gmail
API via OAuth (a third-party provider cannot authorize Gmail's SPF/DKIM).

- Add a `GmailOAuthTransport implements EmailTransport`, selected per-firm when the firm has
  connected Google.
- Requires: per-firm OAuth (`gmail.send` scope), encrypted token storage + refresh, Google
  app **verification** (security review) before >100 users.
- v1 leaves the seam: `email_service` already dispatches through `EmailTransport`, and the
  firm record can later carry a `email_transport` preference (`resend` | `gmail`). No v1
  rework needed.

## Build order

Each step is independently shippable and testable:

1. **§1** signed link + public endpoints + hosted page.
2. **§2 / §3** email (Resend) + WhatsApp deep-link transports.
3. **§4 / §5** send orchestration + endpoint + sent tracking.
4. **§6** templates (defaults, firm storage, settings UI, dialog pre-fill).
5. **§7** Send dialog + InvoiceList polish.

## Open setup task (not code)

- Verify `snappyco.org` in Resend (add SPF/DKIM TXT records to the domain's DNS) before
  sending to real recipients. Until then, build/test against the Resend sandbox
  (`onboarding@resend.dev`, which only delivers to the account owner's email).
