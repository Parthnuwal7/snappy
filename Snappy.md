produce a working repo that a developer can run locally and build cross-platform. Prioritize SPEED, clean keyboard-first UX, robust analytics, and small bundle size. Name the app SNAPPY.

Summary (one line)

Create SNAPPY — a local-first desktop billing app for lawyers (Tauri + React frontend + Flask backend) with SQLite for transactions, DuckDB for analytics, HTML→PDF invoice generation, CSV import, signature images, keyboard shortcuts, and automated CI builds.

High-level requirements / acceptance criteria

repo must build and run locally with one command (e.g., ./dev.sh or make dev) and expose clear run/build instructions in README.md.

Tauri + React UI must be production-ready and keyboard-first:

New Invoice form, Invoice List, Clients, Reports (analytics), Settings.

Keyboard shortcuts: Ctrl/Cmd+N (New Invoice), Ctrl/Cmd+S (Save), Ctrl/Cmd+E (Export PDF), Ctrl/Cmd+P (Print), Ctrl/Cmd+K (focus search).

Flask backend (local-only) must provide REST endpoints to:

CRUD clients, invoices, invoice lines, payments.

POST /generate_pdf (accept invoice_id or HTML and return PDF bytes).

/analytics endpoints that run DuckDB queries and return JSON results (monthly revenue, top clients, aging buckets).

/import/csv to map and import CSV invoices/clients.

/backup and /restore.

DBs:

SQLite snappy.db as source of truth for transactions.

DuckDB used by Flask for analytics (ingest or query SQLite/exported tables).

PDF generation:

Render invoice HTML in frontend; send HTML to Flask which uses WeasyPrint (preferred) or ReportLab to produce PDF.

PDFs must include header, invoice meta, table, totals, signature image, and total-in-words.

Provide a Tailwind-based invoice HTML template (editable).

Include sample data and seed script (10 clients, 20 invoices spanning 12 months).

Provide automated tests:

Unit tests for Flask endpoints (pytest).

Basic E2E script or instructions to simulate creating invoice & exporting PDF.

CI:

GitHub Actions to run lint (prettier/eslint for frontend, black/flake8 for backend), tests, and produce cross-platform Tauri builds (or at least build artifacts).

Documentation:

README.md with install/run/build/test steps for Linux/Windows/macOS.

Data model diagram (ASCII or image) and API spec (OpenAPI or simple markdown).

Licensing: MIT.

Tech stack (explicit)

Desktop wrapper: Tauri (use Rust backend only as packager; primary app logic goes in Python service).

Frontend: React (Vite), TypeScript, Tailwind CSS, React Hook Form, Zustand (or Redux toolkit) for state, React Query for async caching, Recharts for charts.

Backend: Flask (Python 3.11+), Uvicorn/Waitress for prod, flask-cli dev, gunicorn optional.

Databases: SQLite (transactions) via SQLAlchemy + Alembic migrations; DuckDB (analytics) via Python duckdb package.

PDF: WeasyPrint (HTML→PDF) as primary; fallback reportlab for programmatic PDF.

Packaging/Build: Tauri build pipeline, GitHub Actions for CI.

Tests: pytest + requests for API; optionally Playwright for E2E (optional but preferred).

CSV parsing: pandas for robust mapping & duckdb ingestion.

Fuzzy matching: rapidfuzz (client dedupe).

Optional: python-dotenv for config, sqlalchemy-utils if needed.

Repo layout (must create)
snappy/
├─ README.md
├─ package.json (frontend)
├─ tauri.conf.json
├─ src-tauri/ (tauri files)
├─ frontend/
│  ├─ vite.config.ts
│  ├─ src/
│  │  ├─ main.tsx
│  │  ├─ App.tsx
│  │  ├─ pages/
│  │  │  ├─ Dashboard.tsx
│  │  │  ├─ NewInvoice.tsx
│  │  │  ├─ InvoiceList.tsx
│  │  │  ├─ Clients.tsx
│  │  │  ├─ Reports.tsx
│  │  ├─ components/
│  │  │  ├─ InvoiceForm/
│  │  │  ├─ InvoiceTable.tsx
│  │  │  ├─ ClientSelect.tsx
│  │  ├─ templates/invoice.html (Tailwind-based)
│  ├─ tests/ (optional E2E)
├─ backend/
│  ├─ app/
│  │  ├─ main.py (Flask app)
│  │  ├─ api/
│  │  │  ├─ invoices.py
│  │  │  ├─ clients.py
│  │  │  ├─ analytics.py
│  │  │  ├─ import_csv.py
│  │  ├─ models/
│  │  │  ├─ models.py (SQLAlchemy)
│  │  ├─ services/
│  │  │  ├─ pdf_service.py
│  │  │  ├─ duckdb_service.py
│  │  │  ├─ backup_service.py
│  │  ├─ migrations/
│  ├─ requirements.txt
│  ├─ tests/
│  │  ├─ test_invoices.py
├─ scripts/
│  ├─ dev.sh (one-command dev runner)
│  ├─ seed_db.py
├─ .github/
│  ├─ workflows/ci.yml

Detailed feature spec (developer checklist)

Authentication & security

App is local-first; no remote auth by default.

Offer simple app-lock PIN in Settings (store salt+hash in SQLite).

Backups must be exportable and optionally encrypted (AES). Provide backup_service.encrypt_backup(passphrase).

Invoice numbering

Configurable in Settings: PREFIX, YEAR, PADDING.

Implement generator: LAW/2025/0001. Deleted invoices are voided — never reuse numbers.

New Invoice form UX

Autofill client via fuzzy search (RapidFuzz) while typing.

Short description (single line, max 120 chars; show char count).

Line items: supports adding commonly-used items quickly (remember last N).

Totals recalc as user types; tax broken out and total-in-words shown.

Auto-save draft on change.

Signature: allow upload PNG/JPEG; store path in DB.

Buttons: Save Draft, Save & Export PDF, Mark Paid.

Invoice List

Columns: InvoiceNo, Date, Client, ShortDesc, Amount, Status, Actions.

Filters: date range, client, status; search by invoice no or text.

Bulk export CSV / PDF.

Clients

CRUD modal, default tax percentage, notes, address, contact.

Import CSV mapping with fuzzy dedupe suggestions.

Reports

Monthly revenue (last 12 months — line chart)

Top 5 clients (bar chart)

Aging buckets (0-30 / 31-60 / 61+)

Invoice count & avg value

Provide raw-export buttons for each report.

CSV Import

UI to map CSV columns to DB fields (client_name, date, short_desc, item lines).

Preview parsed rows and duplicates detected; let user accept, skip, or merge.

Backup & Restore

Manual backup to a folder; option to auto-backup daily.

Encrypted export using password (AES-256).

Restore with validation and abort if DB schema mismatches.

Analytics architecture

Flask endpoint GET /analytics/monthly?start=yyyy-mm-dd&end=yyyy-mm-dd that:

Loads latest invoices table (via DuckDB ingestion of SQLite) and returns aggregated JSON.

Keep DuckDB queries parameterized and cached.

PDF generation

Frontend renders invoice HTML template with Tailwind classes.

Send the rendered HTML and invoice metadata to POST /generate_pdf.

Flask pdf_service uses WeasyPrint to produce PDF bytes and returns application/pdf.

Filename: SNAPPY_INV_<invoice_no>.pdf

Packaging

Tauri dev script spawns Flask server and runs Vite dev server. dev.sh orchestrates both.

Build script packages Flask assets (or bundle Python service with PyInstaller) and Tauri builds.

Testing

pytest tests for endpoints: create client, create invoice, generate PDF, analytics.

Linting configs and pre-commit hooks.

Internationalization & Currency

Default currency INR but make currency selectable. Display numbers with locale formatting.

Developer instructions for the coding agent

Start with a working minimal end-to-end flow: create invoice → save to SQLite → render HTML invoice → POST /generate_pdf → return PDF. Ensure the dev script runs it.

Commit frequently with clear messages. Provide a final PR/branch feature/snappy-initial with README that documents run steps.

Include seeded sample data and a demo script that demonstrates the main flows.

Provide a short developer guide (in docs/DEV_GUIDE.md) describing how the Flask ↔ Tauri communication works and how to build releases.

Ensure all secrets or keys are not committed. Use .env for configurable items and include .env.example.

Example API snippets (exact expected endpoints)
GET /api/clients
POST /api/clients
GET /api/clients/{id}
PUT /api/clients/{id}
DELETE /api/clients/{id}

GET /api/invoices
POST /api/invoices
GET /api/invoices/{id}
PUT /api/invoices/{id}
POST /api/invoices/{id}/mark_paid
POST /api/invoices/{id}/generate_pdf

POST /api/import/csv
POST /api/backup
POST /api/restore
GET  /api/analytics/monthly
GET  /api/analytics/top_clients
GET  /api/analytics/aging


Include OpenAPI/Swagger docs auto-generated for these endpoints.

Minimal frontend behavior to implement immediately

NewInvoice page with form that posts to /api/invoices.

InvoiceList page that fetches /api/invoices.

Generate PDF button that calls /api/invoices/{id}/generate_pdf and downloads the returned PDF.

Dashboard displaying /api/analytics/monthly and /api/analytics/top_clients.

Seed data & demo flow (must be included)

scripts/seed_db.py populates 10 realistic clients (names, addresses) and 20 invoices over the last 12 months of mixed paid/unpaid status.

scripts/demo.sh or Makefile target that runs through:

start backend

start frontend

create a new invoice via API script

generate its PDF and save to ./demo-output/

Priority list (what to deliver first)

Minimal E2E: New invoice → save → generate PDF → download.

Invoice list + client autocomplete + keyboard shortcuts.

DuckDB analytics endpoints (monthly & top clients).

CSV import & seed script.

Backup/restore & encryption.

Tests, CI, packaging.

Non-functional requirements & constraints

App must be offline-first (no remote servers).

Keep binary size small; avoid Electron.

Use accessible, keyboard-focusable components.

Provide clear error messages and validation.

No telemetry or analytics by default.

Final note (tone to agent)

Be pragmatic and iterative: deliver a small, solid core first (E2E invoice → PDF). Aim for excellent UX and speed. Comment code and include docstrings for backend functions. Use type annotations (TypeScript + Python). Keep commits atomic and descriptive. Name the project SNAPPY.