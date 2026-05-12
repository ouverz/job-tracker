# `backend/app/scrapers/`

Per-source scraper classes and the pipeline runner that orchestrates them. Each scraper produces a list of `JobPosting` objects; the runner deduplicates and persists them.

---

## Active scrapers

| File | Source | Notes |
|------|--------|-------|
| `arbeitnow.py` | Arbeitnow | Public JSON API |
| `jobspy_scraper.py` | LinkedIn + Indeed | Uses the `jobspy` library; two sources in one scraper |
| `jobware.py` | Jobware | Internal JSON API (`/api/d48b2/xnfwe`); description included in listing response |
| `stepstone.py` | StepStone | HTML scraping with BeautifulSoup |
| `hays.py` | Hays DACH | HTML scraping |
| `yer.py` | yer.de | HTML scraping |
| `orange_quarter.py` | Orange Quarter | HTML scraping |

---

## Core files

### `base.py`
- `JobPosting` — dataclass with all fields a scraper may produce (`source`, `url`, `title`, `company`, `location`, `employment_type`, `remote_type`, `salary_raw`, `description`, `posted_at`, `external_id`).
- `BaseScraper` — abstract base class. Subclasses implement `scrape() -> list[JobPosting]`. The `run_safe()` method wraps `scrape()` in a try/except and returns `(jobs, error_string_or_None)`.

### `runner.py`
Orchestrates the full pipeline: launches scrapers concurrently, deduplicates results, and writes to the DB.

**Deduplication** — three strategies applied in order:
1. **URL uniqueness** — enforced by a `UNIQUE` constraint on `jobs.url` via `INSERT OR IGNORE`. Catches the same posting reappearing on the same source.
2. **`content_hash`** (normalized title + company) — catches the same role posted across multiple sources with identical titles (e.g. StepStone and Arbeitnow both list "Data Engineer @ Acme"). Only active when company is known.
3. **Fuzzy company prefix** — catches minor company name variants between sources (e.g. "WashTec AG" vs "WashTec Cleaning Technology"). Same title hash, but the normalized company names share a common prefix.

**`_upsert_jobs(jobs)`** — inserts new jobs and, for URL-colliding rows that already exist, backfills the description if the new scrape captured it and the DB row is still empty.

**Threading** — a module-level `_db_write_lock` serialises concurrent upsert calls from the `ThreadPoolExecutor` that runs scrapers in parallel.

### `filters.py`
Post-scrape filters applied to every scraper's output before DB insertion (e.g. minimum description length, location sanity checks).

### `utils.py`
Shared helper utilities (HTML cleaning, date parsing, salary normalisation).

---

## Dead scrapers (removed 2026-03)

The following sources are either JS-rendered or no longer accessible:

| Scraper | Reason |
|---------|--------|
| `thryve.py` | Domain changed to thryve.health; no accessible DE data jobs |
| `deeprec.py` | JS SPA, no public API |
| `xcede.py` | JS SPA, no public API |
| `peritus.py` | Wix JS site, only ~10 jobs, no accessible card structure |
| `redrecruitment.py` | No actual job listings on their page |
