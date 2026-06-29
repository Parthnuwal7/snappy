# SNAPPY — Legal Practice CRM & Billing for Indian Advocates

[![License](https://img.shields.io/badge/License-Dual-blue.svg)](LICENSE)
[![Live](https://img.shields.io/badge/Status-Live-brightgreen)]()

> A full-stack practice-management platform for Indian advocates and small law
> firms — case management, a documents & evidence vault, a day planner, a
> drafting workspace, a legal news feed, and billing — built with **React**,
> **Flask**, and **Supabase**, running in production on **Google Cloud Run**.

Snappy began as a billing app and grew into a multi-tenant Legal CRM. Firms
onboard, invite their team under role-based permissions, run their matters from
intake to hearing, draft documents, store evidence, and bill clients — all in
one workspace.

## 🎯 Project Highlights

| Aspect | Details |
|--------|---------|
| **Type** | Multi-tenant SaaS — Legal CRM + Billing |
| **Status** | ✅ In production (live) |
| **Tenancy** | Firm-scoped data isolation with role-based access control (RBAC) |
| **Deployment** | GitHub → Vercel (frontend) + Cloud Run (backend) + Supabase |
| **Test suite** | ~330 backend tests (pytest), green |

## ✨ Key Features

### Practice management
- 🗂️ **Case files** — matters with a Kanban board, a searchable Vault list, and a Calendar, plus a stage taxonomy from intake to disposal
- 📥 **Leads / intake** — capture enquiries and convert them into matters
- 📅 **Day planner** — tasks (day / week / month views) and a one-click printable **cause-list**
- 🗒️ **Case record** — notes, hearings/events, expenses, parties, and a progression timeline

### Documents & drafting
- 🔒 **Documents & Evidence Vault** — uploads in a private Supabase Storage bucket, served via short-lived signed URLs; exhibit register with marks
- ✍️ **Writing workspace** — a TipTap rich-text editor with reusable templates, drafts, case **merge-fields**, and PDF export

### Knowledge & billing
- 📰 **Legal news feed** — RSS ingestion (LiveLaw, Bar & Bench) with LLM enrichment (headline / TL;DR / topics) and a personalised "For you" ranking
- 📄 **Billing & invoicing** — invoice lifecycle, line-items, recurring schedules, professional PDF generation, and public shareable invoice links
- 👥 **Clients** — contact database with fuzzy search
- 📊 **Reports** — revenue trends, invoice aging, and firm analytics

### Firm & team
- 🏢 **Firm tenancy** — every record scoped to a firm; users belong to exactly one firm with one role
- 🛡️ **RBAC** — a permission catalogue with system + custom roles (Owner / Partner / Associate / Staff)
- 📨 **Invites & onboarding** — email invitations, a minimal first-run gate, and a progressive "finish setting up" checklist

## 🛠️ Tech Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | React 18 + TypeScript + Vite |
| **Styling** | Tailwind CSS |
| **Server state** | TanStack Query (React Query) |
| **Rich-text editor** | TipTap 2 |
| **Backend** | Flask 3 (Python 3.11) + Gunicorn |
| **ORM** | SQLAlchemy 2 |
| **Database** | PostgreSQL (Supabase) |
| **Auth** | Supabase Auth (JWT, HS256) |
| **File storage** | Supabase Storage (private buckets + signed URLs) |
| **PDF engine** | ReportLab |
| **Search** | RapidFuzz |
| **News ingestion** | feedparser + LLM enrichment |
| **Frontend hosting** | Vercel |
| **Backend hosting** | Google Cloud Run (Docker) |
| **Uptime** | Cloud Scheduler keepalive |

## 🧱 Architecture

```
React SPA (Vercel)
   │  HTTPS, Supabase JWT in Authorization header
   ▼
Flask REST API (Cloud Run, Gunicorn)
   ├── JWT middleware → firm context + RBAC permission checks
   ├── /api/v1/...  case files · documents · leads · tasks · writing
   │                invoices · clients · analytics · legal-feed · firm/roles/invites
   ▼
Supabase
   ├── PostgreSQL   (all tenant data, scoped by firm_id)
   ├── Auth         (user identity, JWT issuance)
   └── Storage      (case-documents [private], logo/signature/qr, backups)

Cloud Scheduler ──► /keepalive (prevents free-tier idle pause)
                └─► /api/v1/legal-feed/ingest (periodic news ingestion)
```

### Multi-tenancy & RBAC
- Every authenticated request resolves the caller's **firm** and **role** from their Supabase identity.
- All queries are scoped by `firm_id`; tenant isolation is enforced in the application layer.
- Endpoints are gated by a **permission catalogue** (e.g. `members.invite`, `cases.write`); the `Owner` system role resolves to all permissions.
- The backend uses the Supabase **service-role key** for Storage, so object access is mediated entirely by the API (firm-ownership checks + signed URLs), not by Storage RLS.

## 📁 Project Structure

```
snappy/
├── backend/                  # Flask REST API (Cloud Run)
│   ├── app/
│   │   ├── api/              # Route handlers (auth, case_files, case_documents,
│   │   │                     #   leads, tasks, writing, invoices, clients,
│   │   │                     #   analytics, legal_feed, firm, roles, invites …)
│   │   ├── models/           # SQLAlchemy ORM models (auth, case, lead, task, writing …)
│   │   ├── services/         # Business logic (document_storage, firm_service,
│   │   │                     #   invite_service, pdf_*, legal_feed/* …)
│   │   ├── middleware/        # JWT auth + firm-context / permission checks
│   │   ├── rbac/             # Permission catalogue + default roles
│   │   └── utils/            # Pagination and helpers
│   ├── migrations/           # Numbered SQL migrations (applied manually on Supabase)
│   ├── tests/                # pytest suite (~330 tests)
│   └── Dockerfile            # Cloud Run image (self-contained, context = backend/)
│
├── frontend/                 # React SPA (Vercel)
│   └── src/
│       ├── pages/            # Route components
│       ├── components/       # Reusable UI
│       ├── contexts/         # Auth context
│       └── api.ts            # Type-safe API client
│
├── docs/superpowers/         # Design specs & implementation plans
└── website/                  # Marketing site
```

## 🗄️ Database migrations

Schema changes are **numbered SQL files** in `backend/migrations/` (`001_…` →
`023_…`). They are applied **manually on Supabase** (e.g. via the SQL editor),
not by the application at runtime. The local test suite builds the schema
directly from the SQLAlchemy models against in-memory SQLite, so tests never
depend on a live database.

## 📦 Storage buckets (Supabase)

| Bucket | Visibility | Purpose |
|--------|------------|---------|
| `case-documents` | **Private** | Case documents & evidence; downloaded via signed URLs |
| `logos`, `signatures`, `qr` | Private | Firm branding on invoices |
| `invoice-backups` / `snappy-backups` | Private | Backup archives |

Object paths in `case-documents` are keyed `{firm_id}/{case_file_id}/{uuid}.{ext}`.

## 🚀 Deployment

### Frontend — Vercel
- Auto-deploys on push to `main`; environment variables set in the Vercel dashboard.

### Backend — Google Cloud Run
- Containerised with the self-contained `backend/Dockerfile` (Gunicorn, app-factory `app.main:create_app()`).
- Deploy from the repo root, uploading only the backend folder:
  ```bash
  gcloud run deploy snappy-backend --source backend --region asia-northeast1
  ```
- Environment variables (`DATABASE_URL`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWT_SECRET`, …) persist across revisions.

### Supabase
- PostgreSQL + Auth + Storage. Apply any pending migrations before deploying a backend revision that reads new columns.

### Keepalive
- A Cloud Scheduler job pings `/keepalive` so the free-tier Supabase project never crosses the idle auto-pause threshold.

## 🧪 Testing

```bash
cd backend
python -m pytest -q
```

~330 tests run against an in-memory SQLite database (no external services
required). The suite covers auth/onboarding, firm tenancy & RBAC, case
management, the documents vault, the writing workspace, the legal feed
pipeline, and billing.

## 🔐 Security

- **Authentication** — Supabase-issued JWTs, HS256-verified on every request.
- **Authorization** — firm context + RBAC permission checks on protected endpoints.
- **Tenant isolation** — every query scoped by `firm_id`; users cannot reach another firm's data.
- **Storage** — private buckets; downloads only via short-lived signed URLs.
- **Resilience** — connection-pool pre-ping/recycle and bounded transaction windows on the ingestion path.

## 📝 License

Dual License — free for educational / non-commercial use. Commercial use
requires a paid license — see [LICENSE](LICENSE).

---

**Built by Parth Nuwal** | [GitHub](https://github.com/Parthnuwal7) | [LinkedIn](https://www.linkedin.com/in/parth-nuwal-9a81b9226)
