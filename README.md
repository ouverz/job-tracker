# Job Tracker

Local job aggregator and CRM for AI/Data/Analytics Engineering roles in Germany / DACH.

## What it does

- **Scrapes** jobs from LinkedIn, Indeed, StepStone, Arbeitnow, Jobware on demand
- **Filters** by status, source, employment type, remote/hybrid, free text search
- **CRM**: track each role through `new → pending → applied / rejected / archived`, add notes
- **ATS scoring** *(requires Anthropic API key)*: compares job JD to your CV and returns a 0–100 compatibility score with skill, experience, language, and location breakdown scores, plus strengths, gaps, and a plain-English rationale. Scoring is candidate-aware: hard penalties for roles requiring German B2+, or on-site/hybrid offices >45 min by train from Frankfurt am Main

## Quick start

```bash
cd job-tracker
./start.sh           # creates venv, installs deps, starts both servers
```

Open **http://localhost:5173**

`start.sh` is fully automated — no manual pip/npm steps needed.

## Setup

**Required:** Python 3.11+, Node 18+

**For ATS scoring only** — add your Anthropic API key to `.env`:
```
ANTHROPIC_API_KEY=sk-ant-...
```
Then paste your CV as plain text into `cv.txt`. The rest of the app works without this.

## Architecture

```
backend/   Python 3.11 · FastAPI · SQLite (data/jobs.db)
  app/
    main.py              FastAPI app, CORS, DB init
    database.py          sqlite3 connection + schema
    config.py            settings via .env
    api/
      jobs.py            CRUD, filtering, stats
      scraping.py        trigger runs, SSE progress stream
      scoring.py         single + batch CV scoring
    scrapers/
      arbeitnow.py       public REST API (no auth needed)
      jobspy_scraper.py  LinkedIn + Indeed via python-jobspy
      stepstone.py       HTTP scraping with BeautifulSoup
      jobware.py         HTTP scraping with BeautifulSoup
      runner.py          orchestrates all scrapers, dedup, persists to DB
    services/
      scoring.py         Anthropic API call with tool_use for structured output

frontend/  React 18 · Vite · Tailwind CSS · TanStack Query
  src/
    App.jsx              root — filter state, selected job, scrape trigger
    components/
      Header.jsx         stats bar + Run Pipeline button
      FilterBar.jsx      status/source/type/remote chips + search input
      jobs/
        JobTable.jsx     sortable table with inline status badges
        JobDrawer.jsx    slide-in panel — full JD, ATS score, notes, status
        StatusBadge.jsx  colour-coded status/source/type badges
        ScoreBar.jsx     visual 0–100 score bar
      scraping/
        ScrapeModal.jsx  live per-source progress via SSE
    api/client.js        typed fetch wrapper for all API calls
```

## API (port 8000)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/jobs` | list with filters: status, source, employment_type, remote_type, q, sort, order |
| GET | `/api/jobs/{id}` | full job including description |
| PATCH | `/api/jobs/{id}` | update status, notes, applied_at |
| DELETE | `/api/jobs/{id}` | remove job |
| GET | `/api/jobs/stats` | counts by status and source |
| POST | `/api/scraping/run` | trigger pipeline (async, returns run_id) |
| GET | `/api/scraping/runs/{id}/stream` | SSE stream of live scraping progress |
| POST | `/api/scoring/jobs/{id}` | score one job against CV (requires API key) |
| POST | `/api/scoring/batch` | score all unscored jobs in background (requires API key) |

Interactive docs: **http://localhost:8000/docs**

## Search config

Edit `backend/app/config.py` to change roles, location, or per-source job limits:

```python
search_roles = ["AI Engineer", "Data Engineer", "Analytics Engineer"]
search_location = "Germany"
max_jobs_per_source = 50
```

## Scraping notes

- **Arbeitnow**: free public API, best German coverage, no rate limits
- **LinkedIn + Indeed**: via `python-jobspy`; limited to ~30 results per role to avoid blocks
- **StepStone / Jobware**: HTML scraping with polite delays; may return fewer results if layouts change
- All sources deduplicate by URL — re-running the pipeline won't create duplicates
