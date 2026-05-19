# Contributing

Thanks for your interest. This is a personal project shared to help others — contributions that improve generalisability, fix bugs, or add scrapers for new job boards are very welcome.

## Local development setup

```bash
# 1. Clone and enter the repo
git clone https://github.com/<your-username>/job-tracker.git
cd job-tracker

# 2. Copy and edit environment config
cp .env.example .env
# Set ANTHROPIC_API_KEY if you want ATS scoring
# Set CANDIDATE_LOCATION, CANDIDATE_MAX_COMMUTE_MIN, CANDIDATE_LANGUAGE_REQUIREMENT

# 3. Start in dev mode (hot-reload on both frontend and backend)
./start.sh --dev
```

**Requirements:** Python 3.11+, Node 18+

## Running tests

```bash
cd backend
.venv/bin/pytest tests/ -v
```

## Project structure

```
backend/app/
  scrapers/   — one file per job board; runner.py orchestrates all of them
  api/        — FastAPI route handlers (one file per resource domain)
  services/   — business logic (scoring, enrichment, title filtering)
  database.py — SQLite schema + migrations
frontend/src/
  components/ — React components; job-specific ones in components/jobs/
  api/client.js — all backend calls go through the api object here
```

## Adding a new job board scraper

1. Create `backend/app/scrapers/<source_name>.py`
2. Subclass `BaseScraper` from `base.py` and implement `scrape() -> list[JobPosting]`
3. Register it in `runner.py` — add to the `scrapers` list in `run_scraping_pipeline()`
4. Add a row to `backend/app/scrapers/README.md`

```python
# Minimal scraper skeleton
from .base import BaseScraper, JobPosting

class MyBoardScraper(BaseScraper):
    def scrape(self) -> list[JobPosting]:
        jobs = []
        # fetch and parse jobs here
        # return a list of JobPosting dataclass instances
        return jobs
```

Look at `arbeitnow.py` (REST API) or `jobware.py` (JSON API) as clean reference implementations.

## Pull request guidelines

- One feature or fix per PR
- Scraper PRs should include a brief note on what the source is and how the scraper works (pagination, rate limiting approach)
- If a scraper relies on undocumented internal APIs or fragile CSS selectors, note that clearly in the PR description
- Keep the PR description honest about limitations (e.g. "may break if the site changes its layout")

## Reporting broken scrapers

Open an issue with the scraper name and the error message you see. HTML-scraping scrapers break when sites redesign — this is expected. PRs to fix them are very welcome.
