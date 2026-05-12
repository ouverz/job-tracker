# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Context Resolution Order

When starting any task, resolve context in this order before writing any code or making any assumptions:

1. **Read these MD files first** — they are the authoritative source of truth for this project:
   - `CLAUDE.md` (this file) — working conventions and rules
   - `PROJECT_PLAN.md` — build status, feature list, full file structure
   - `backend/app/scrapers/README.md` — active and dead scrapers
   - `backend/app/api/README.md` — all API routes and their behaviour
   - `backend/app/services/README.md` — business logic layer

2. **Use conversation context** — any files, outputs, or explanations the user has already provided in the current session.

3. **Search or ask** — if the above two sources don't provide enough context:
   - Use `Grep` / `Glob` / `Read` to look up the relevant file or symbol directly.
   - If still unclear, ask the user a single focused question rather than guessing or making broad assumptions.

Never assume a scraper, route, or feature exists (or doesn't) without checking the MD files or the code first.

## Project Overview

**Job Tracker** is a personal job-search dashboard: a FastAPI backend + React/Vite frontend. It scrapes Data Engineering job postings, scores them against a CV using Claude AI, and tracks application status through a Kanban/table UI.

## Running the App

```bash
# Start both backend and frontend
bash start.sh

# Backend only (from repo root)
cd backend && .venv/bin/uvicorn app.main:app --reload --port 8000

# Frontend only (from repo root)
cd frontend && npm run dev
```

## Architecture

### Backend (`backend/app/`)

- **`main.py`** — FastAPI app, CORS, scheduler (daily 08:00 scrape), router registration
- **`database.py`** — SQLite via `db()` context manager; `init_db()` runs schema + idempotent migrations
- **`schemas.py`** — Pydantic models for all request/response types
- **`config.py`** — env var config (DB_PATH, API keys)
- **`api/`** — route handlers (one file per domain)
- **`services/`** — business logic called by routers
- **`scrapers/`** — per-source scraper classes + pipeline runner

### Frontend (`frontend/src/`)

- **`api/client.js`** — single `api` object; all backend calls go through `request()` helper
- **`App.jsx`** — top-level routing and layout
- **`components/`** — React components; job-specific ones live in `components/jobs/`

### Key patterns

- DB access: always use `with db() as conn:` from `database.py`
- New API routes: create `backend/app/api/<domain>.py`, register router in `main.py`
- New services: create `backend/app/services/<domain>.py`, import in the corresponding API file
- Frontend data fetching: React Query (`useQuery` / `useMutation`) — see `JobDrawer.jsx` as reference
- Frontend API calls: add methods to the `api` object in `client.js`

## Key Environment Variables

```
DB_PATH=backend/data/jobs.db
ANTHROPIC_API_KEY=sk-...      # required for CV scoring
```

## Documentation Rules

**These rules must be followed every time a task is completed:**

1. **`PROJECT_PLAN.md`** (root) is the master overview — update the Build Status table whenever a component moves from ⏳ TODO to ✅ Done. Also update the File Structure section if new files/folders are added.

2. **Per-folder `README.md`** — the folders below each have a `README.md` explaining what each file does and how the pieces connect. When files are added to one of these folders, update that folder's `README.md` in the same task.

   Current folder READMEs:
   - `backend/app/api/README.md`
   - `backend/app/services/README.md`
   - `backend/app/scrapers/README.md`
   - `frontend/src/components/README.md`

   When a new top-level folder is created, create its `README.md` immediately.

3. **`README.md`** (root) is user-facing — keep setup instructions, env vars, and feature list up to date when new capabilities are added.

4. **All three documents must be updated in the same task as the code change** — never defer documentation to a later step.
