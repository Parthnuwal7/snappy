# Deploying the Snappy Backend to Cloud Run

## TL;DR

```bash
# from repo root (C:\Users\Lenovo\snappy)
gcloud run deploy snappy-backend --source backend --region asia-northeast1
```

`--source` controls **what gets uploaded**, not your current folder. Only the
directory you point `--source` at is sent to Cloud Build. So both of these
upload **only `backend/`**:

```bash
# from repo root
gcloud run deploy snappy-backend --source backend --region asia-northeast1

# from inside backend/
gcloud run deploy snappy-backend --source . --region asia-northeast1
```

Either way `frontend/`, `website/`, and root files are **not** uploaded —
they're outside the source dir.

## Which Dockerfile gets used (important)

Cloud Build looks for a `Dockerfile` *inside the source dir*, so pointing
`--source` at `backend/` uses **`backend/Dockerfile`** — the self-contained one
that does `COPY . .` (build context = backend). That's the correct pairing.

- ✅ `--source backend` → uses `backend/Dockerfile` (context = backend) — correct
- ❌ root `Dockerfile` + `--source backend` → fails: it expects context = repo
  root and does `COPY backend/ ./`, but there's no `backend/` subfolder inside
  the uploaded context.

Don't mix the two Dockerfiles. Use `--source backend` (what the `backend/Dockerfile`
header documents).

## Two checks before you fire it

1. **`.gcloudignore`** — make sure local `backend\venv\` is excluded, or it
   bloats the upload. gcloud honors `.gcloudignore`, or falls back to
   `.gitignore` (where `venv/` is presumably already ignored). If neither
   excludes it, add a `.gcloudignore` with `venv/`.
2. **Region** — confirm `snappy-backend` already lives in `asia-northeast1`
   (`gcloud run services list`) so you deploy a new *revision* rather than
   spinning up a second service in the wrong region.

## Prerequisite: Supabase migrations

Apply migrations **013–022** on Supabase **before** the deploy (manual step).
Note **021** (merge_writing) and **022** (slim_case_schema) are **destructive**
— they drop old tables inside a backfill transaction. Deploy the matching
backend revision promptly after applying those two so the running code matches
the schema.

## Notes

- Env vars persist across Cloud Run revisions — you don't re-supply them on each
  deploy.
- `backend/render.yaml` is a leftover Render.com blueprint, **not** the prod
  path. Ignore it.
- gunicorn runs `app.main:create_app()` with `--workers 2 --threads 4
  --timeout 120`; keep Cloud Run `--concurrency` in sync (8).
