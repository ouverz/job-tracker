# Job Tracker

Local job aggregator and CRM for AI/Data/Analytics Engineering roles — primarily DACH.

## What it does

- **Multi-source scraping**: Arbeitnow, LinkedIn, Indeed, StepStone, Jobware, Hays, yer.de, Orange Quarter — concurrent, deduplicated on every run
- **Filtering**: status, source, employment type, remote/hybrid, location, score range, free-text search, starred
- **CRM pipeline**: track roles through `new → pending → applied / rejected / archived`, add notes, set follow-up reminders, star shortlisted roles
- **Networking**: track contacts per job, log outreach, generate LinkedIn recruiter search links
- **ATS scoring** *(requires Anthropic API key)*: scores each JD against your CV using Claude, returning a 0–100 match with skill, experience, language, and location sub-scores plus strengths, gaps, and a plain-English rationale. Candidate constraints (target location, language requirements) are configurable in `backend/app/services/scoring.py`
- **Batch scoring**: score all unscored jobs in the background with a single click
- **CV upload**: upload a PDF or DOCX through the UI; text is extracted and stored as `cv.txt`
- **Skills gap analysis**: aggregates gaps and strengths across all scored jobs — filterable by min score and status
- **Weekly activity log**: set weekly targets (applications, outreach, LinkedIn posts, interviews, GitHub commits) and track actuals; applications sent and network reconnects auto-populate from your data
- **KPI dashboard**: applied/rejected bar charts (last 30 days) and summary stat cards
- **Auto-archive**: `new` jobs older than 14 days are archived daily at 09:00
- **Description backfill**: fetch missing job descriptions for StepStone, LinkedIn, and Indeed jobs in the background
- **Bulk operations**: bulk status update, title-based bulk archiving

## Quick start

```bash
cd job-tracker
./start.sh           # creates venv, installs deps, starts both servers
```

Open **http://localhost:5173**

`start.sh` is fully automated — no manual pip/npm steps needed.

## Setup

**Required:** Python 3.11+, Node 18+

**For ATS scoring** — add your Anthropic API key to `.env`:
```
ANTHROPIC_API_KEY=sk-ant-...
```

Upload your CV via the UI (Header → "Upload CV" — accepts PDF or DOCX). Alternatively, paste it as plain text into `cv.txt` at the project root. The rest of the app works without a CV.

**Candidate constraints** for scoring (target location, commute radius, language requirements) are hardcoded in `backend/app/services/scoring.py` — edit the `SYSTEM_PROMPT` to match your profile.

**Search config** — edit `backend/app/config.py` to change roles, location, or per-source limits:

```python
search_roles = ["AI Engineer", "Data Engineer", "Analytics Engineer"]
search_location = "Germany"
max_jobs_per_source = 50
```

## Architecture

```
backend/   Python 3.11 · FastAPI · SQLite (data/jobs.db)
  app/
    main.py              FastAPI app, CORS, scheduler, router registration
    database.py          SQLite via db() context manager; init_db() runs schema + migrations
    schemas.py           Pydantic request/response models
    config.py            env var config (DB_PATH, API keys, search settings)
    constants.py         tuneable limits (page size, SSE timeouts, batch workers)
    api/
      jobs.py            CRUD, filtering, pagination, bulk status, KPI
      scraping.py        trigger runs, SSE progress stream
      scoring.py         single + batch CV scoring
      contacts.py        per-job contact/network tracking
      cv.py              CV upload (PDF/DOCX) and status
      enrichment.py      title-based archiving, description backfill
      analysis.py        skills gap frequency aggregation
      activity_log.py    weekly activity targets and log
    scrapers/
      arbeitnow.py       public REST API
      jobspy_scraper.py  LinkedIn + Indeed via python-jobspy
      stepstone.py       HTML scraping
      jobware.py         internal JSON API
      hays.py            HTML scraping
      yer.py             HTML scraping
      orange_quarter.py  HTML scraping
      runner.py          concurrent orchestration, 3-strategy deduplication
      filters.py         post-scrape quality filters
    services/
      scoring.py         Anthropic API call with tool_use for structured output
      enrichment.py      description backfill (StepStone, LinkedIn, Indeed)
      title_filter.py    heuristic title-match archiving

frontend/  React 18 · Vite · Tailwind CSS · TanStack Query
  src/
    App.jsx              root — tab routing, filter state, SSE lifecycle
    api/client.js        central fetch wrapper for all API calls
    utils/dates.js       shared date formatting
    components/
      Header.jsx         stats bar, Run Pipeline, CV upload
      FilterBar.jsx      status/source/type/remote/score chips + search
      Dashboard.jsx      KPI bar charts + summary cards
      PipelineView.jsx   scraping run history + per-source progress
      GapAnalysis.jsx    strengths vs gaps frequency chart
      ActivityLog.jsx    weekly activity log with targets and actuals
      jobs/
        JobTable.jsx     sortable/paginated table, bulk select, starred
        JobDrawer.jsx    detail panel — JD, ATS score, notes, contacts, follow-up
        StatusBadge.jsx  colour-coded status/source/type badges
        ScoreBar.jsx     0–100 visual score bar
        NetworkSection.jsx  per-job contacts, outreach tracking, LinkedIn search
      scraping/
        ScrapeModal.jsx  live SSE progress modal
```

## API (port 8000)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/jobs` | List with filters: status, source, employment_type, remote_type, location, scraped_days, q, starred, min_score, max_score |
| GET | `/api/jobs/stats` | Counts by status and source |
| GET | `/api/jobs/kpi` | KPI data: daily applied/rejected, summary totals |
| GET | `/api/jobs/{id}` | Full job record |
| PATCH | `/api/jobs/{id}` | Update status, notes, applied_at, starred, follow_up_at |
| PATCH | `/api/jobs/batch-status` | Bulk status update for a list of job IDs |
| DELETE | `/api/jobs/{id}` | Remove job |
| POST | `/api/scraping/run` | Trigger pipeline (async, returns run_id) |
| GET | `/api/scraping/runs` | List recent runs |
| GET | `/api/scraping/runs/{id}/stream` | SSE stream of live scraping progress |
| POST | `/api/scoring/jobs/{id}` | Score one job against CV |
| POST | `/api/scoring/batch` | Batch-score jobs in background |
| GET | `/api/scoring/batch/status` | Poll batch progress |
| GET | `/api/jobs/{id}/contacts` | List contacts for a job |
| POST | `/api/jobs/{id}/contacts` | Add contact |
| PATCH | `/api/contacts/{id}` | Update contact |
| DELETE | `/api/contacts/{id}` | Remove contact |
| POST | `/api/cv/upload` | Upload CV (PDF or DOCX) |
| GET | `/api/cv/status` | CV load status and char/word counts |
| GET | `/api/enrichment/title-filter-preview` | Dry-run title-based archive |
| POST | `/api/enrichment/title-filter-apply` | Execute title-based archive |
| POST | `/api/enrichment/backfill-descriptions` | Start description backfill in background |
| GET | `/api/enrichment/backfill-status` | Poll backfill progress |
| GET | `/api/analysis/gaps` | Skills gap frequency aggregation across scored jobs |
| GET | `/api/activity-log` | Weekly activity log (targets + actuals) |
| PATCH | `/api/activity-log/{week}/{activity}` | Update target or actual for an activity |

Interactive docs: **http://localhost:8000/docs**

## Scraping notes

- **Arbeitnow**: free public API, best German coverage, no rate limits
- **LinkedIn + Indeed**: via `python-jobspy`; limited to ~30 results per role to avoid blocks
- **StepStone / Jobware**: HTML scraping with polite delays; may return fewer results if layouts change
- **Hays / yer.de / Orange Quarter**: specialist/agency sources; HTML scraping
- All sources deduplicate on URL, content hash, and fuzzy company name — re-running won't create duplicates
