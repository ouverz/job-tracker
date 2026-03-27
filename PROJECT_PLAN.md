# Project Plan — Job Tracker

## Overview

Job Tracker is a personal job-search dashboard that automates the discovery and scoring of Data Engineering roles. A FastAPI backend scrapes jobs from multiple sources, deduplicates them, and optionally scores each posting against a CV using Claude AI. A React/Vite frontend provides a filterable table, a detail drawer, a Kanban-style pipeline view, and a KPI dashboard to track application progress.

---

## Build Status

| Feature | Status | Notes |
|---------|--------|-------|
| Multi-source scraping (Arbeitnow, StepStone, LinkedIn/Indeed, Hays, yer, Orange Quarter) | ✅ Done | Concurrent via ThreadPoolExecutor |
| 3-strategy deduplication (URL, content_hash, fuzzy company) | ✅ Done | `scrapers/runner.py` |
| Scheduled daily scrape (08:00) | ✅ Done | APScheduler in `main.py` |
| Job filtering (status, source, type, location, score, text search) | ✅ Done | `api/jobs.py` dynamic query builder |
| CV upload (PDF/DOCX) | ✅ Done | `api/cv.py` + pypdf/python-docx |
| ATS scoring via Claude (single + batch) | ✅ Done | `services/scoring.py` |
| Score breakdown (skills, experience, language, location) | ✅ Done | Stored as JSON in `cv_score_breakdown` |
| Batch scoring background worker | ✅ Done | `services/scoring.py` thread |
| SSE scraping progress stream | ✅ Done | `api/scraping.py` state-signature diffing |
| Contact / network tracking per job | ✅ Done | `api/contacts.py` |
| Title-based bulk archiving | ✅ Done | `services/title_filter.py` |
| Description backfill (StepStone, LinkedIn) | ✅ Done | `services/enrichment.py` |
| KPI dashboard (applied/rejected charts) | ✅ Done | `api/jobs.py` `/kpi` endpoint + `Dashboard.jsx` |
| Follow-up reminders (overdue highlight) | ✅ Done | `JobDrawer.jsx` + `JobTable.jsx` |
| Bulk status update | ✅ Done | `JobTable.jsx` + `api/jobs.py` batch-status |
| Starred jobs | ✅ Done | Filter + star button in table |

---

## File Structure

```
job-tracker/
├── start.sh                         # Launch both services
├── PROJECT_PLAN.md                  # This file
├── README.md                        # User-facing setup guide
│
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI app, CORS, scheduler, router registration
│   │   ├── database.py              # SQLite via db() context manager; init_db()
│   │   ├── schemas.py               # Pydantic models
│   │   ├── config.py                # Env var config (DB_PATH, API keys)
│   │   ├── constants.py             # Magic constants (limits, timeouts, page size)
│   │   ├── api/                     # Route handlers (one file per domain)
│   │   │   ├── README.md
│   │   │   ├── jobs.py
│   │   │   ├── scoring.py
│   │   │   ├── scraping.py
│   │   │   ├── contacts.py
│   │   │   ├── cv.py
│   │   │   └── enrichment.py
│   │   ├── services/                # Business logic
│   │   │   ├── README.md
│   │   │   ├── scoring.py
│   │   │   ├── enrichment.py
│   │   │   └── title_filter.py
│   │   └── scrapers/                # Per-source scrapers + pipeline runner
│   │       ├── README.md
│   │       ├── base.py
│   │       ├── runner.py
│   │       ├── filters.py
│   │       ├── utils.py
│   │       ├── arbeitnow.py
│   │       ├── jobspy_scraper.py
│   │       ├── stepstone.py
│   │       ├── hays.py
│   │       ├── yer.py
│   │       └── orange_quarter.py
│   └── data/
│       └── jobs.db                  # SQLite database (gitignored)
│
└── frontend/
    └── src/
        ├── App.jsx                  # Top-level routing and layout
        ├── api/
        │   └── client.js            # Central api object; all fetch calls
        ├── utils/
        │   └── dates.js             # Shared date formatting utilities
        └── components/
            ├── README.md
            ├── Header.jsx
            ├── FilterBar.jsx
            ├── Dashboard.jsx
            ├── PipelineView.jsx
            ├── jobs/
            │   ├── JobTable.jsx
            │   ├── JobDrawer.jsx
            │   ├── ScoreBar.jsx
            │   ├── StatusBadge.jsx
            │   └── NetworkSection.jsx
            └── scraping/
                └── ScrapeModal.jsx
```
