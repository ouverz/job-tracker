# `backend/app/api/`

Route handlers — one file per domain. Each module creates a FastAPI `APIRouter` that is registered in `main.py`. Business logic lives in `services/`; these files handle HTTP concerns only (request parsing, response shaping, error codes).

---

## Route files

### `jobs.py` — mount: `/api/jobs`

Core job CRUD and query surface.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/jobs` | List jobs with filtering, sorting, and pagination |
| `GET` | `/api/jobs/stats` | Aggregate counts by status and source |
| `GET` | `/api/jobs/kpi` | KPI dashboard data: daily applied/rejected, summary totals |
| `GET` | `/api/jobs/{job_id}` | Full job record |
| `PATCH` | `/api/jobs/{job_id}` | Update status, notes, applied_at, starred, follow_up_at |
| `PATCH` | `/api/jobs/batch-status` | Bulk status update for a list of job IDs |
| `DELETE` | `/api/jobs/{job_id}` | Hard-delete a job |

**Filter dimensions** on `GET /api/jobs`: `status` (comma-separated), `source`, `employment_type`, `remote_type`, `location`, `scraped_days`, `q` (full-text), `starred`, `exclude_starred`, `min_score`, `max_score`, `no_jd`. Sort by `scraped_at | cv_score | posted_at | created_at | title`.

---

### `scoring.py` — mount: `/api/scoring`

CV-to-JD ATS scoring via Claude (delegates to `services/scoring.py`).

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/scoring/jobs/{job_id}` | Score a single job synchronously |
| `POST` | `/api/scoring/batch` | Kick off background batch scoring; accepts optional `job_ids`, `status`, `min_score`, `max_score` filters |
| `GET` | `/api/scoring/batch/status` | Poll batch progress (`running`, `total`, `done`, `errors`) |

---

### `scraping.py` — mount: `/api/scraping`

Scraping pipeline control and progress streaming.

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/scraping/run` | Trigger a new scraping run (optional `sources` filter) |
| `GET` | `/api/scraping/runs` | List recent runs (default last 20) |
| `GET` | `/api/scraping/runs/latest` | Most recent run with per-source detail rows |
| `GET` | `/api/scraping/runs/{run_id}` | Specific run with detail rows |
| `GET` | `/api/scraping/runs/{run_id}/stream` | **SSE stream** — emits `source_update`, `run_update`, `done`, `timeout` events |

The SSE endpoint polls the DB every `SSE_POLL_INTERVAL_SEC` and emits events only when a source's state signature changes, up to `SSE_TIMEOUT_POLLS` polls (5 minutes).

---

### `contacts.py` — mount: `/api/jobs/{job_id}/contacts` and `/api/contacts`

Network contact tracking per job.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/jobs/{job_id}/search-links` | Generate LinkedIn/recruiter search URLs for the job's company |
| `GET` | `/api/jobs/{job_id}/contacts` | List contacts for a job |
| `POST` | `/api/jobs/{job_id}/contacts` | Add a new contact |
| `PATCH` | `/api/contacts/{contact_id}` | Update contact; auto-timestamps `reached_out_at` when `reached_out=true` |
| `DELETE` | `/api/contacts/{contact_id}` | Remove a contact |

---

### `cv.py` — mount: `/api/cv`

CV upload and status.

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/cv/upload` | Upload a PDF or DOCX; extracted text is saved as `cv.txt` |
| `GET` | `/api/cv/status` | Returns whether a CV is loaded and its char/word counts |

---

### `enrichment.py` — mount: `/api/enrichment`

Title-based archiving and description backfill.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/enrichment/title-filter-preview` | Dry-run: show which jobs would be archived or kept |
| `POST` | `/api/enrichment/title-filter-apply` | Archive jobs whose titles don't match keep patterns |
| `POST` | `/api/enrichment/backfill-descriptions` | Start background fetch of missing job descriptions |
| `GET` | `/api/enrichment/backfill-status` | Poll backfill progress |
