"""Orchestrates all scrapers, deduplicates results, and persists to DB."""

import hashlib
import re
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Optional

_db_write_lock = threading.Lock()  # serialise concurrent upserts across scraper threads

from ..database import db
from ..scrapers import (
    ArbeitnowScraper,
    JobSpyScraper,
    JobwareScraper,
    StepStoneScraper,
    YerScraper,
    HaysScraper,
    OrangeQuarterScraper,
)
from ..scrapers.base import JobPosting
from ..scrapers.filters import apply_filters

# Dead/JS-rendered scrapers removed 2026-03:
#   thryve    — domain changed to thryve.health, no accessible DE data jobs
#   deeprec   — JS SPA, no public API
#   xcede     — JS SPA, no public API
#   peritus   — Wix JS site, only ~10 jobs, no accessible card structure
#   redrecruitment — no actual job listings on their page
# Jobware restored 2026-04: internal JSON API discovered at /api/d48b2/xnfwe

SCRAPER_MAP = {
    "arbeitnow": ArbeitnowScraper,
    "linkedin_indeed": JobSpyScraper,
    "jobware": JobwareScraper,
    "stepstone": StepStoneScraper,
    "yer": YerScraper,
    "hays": HaysScraper,
    "orange_quarter": OrangeQuarterScraper,
}

# Display names for UI (one entry per logical scraper)
SOURCE_LABELS = {
    "arbeitnow": "Arbeitnow",
    "linkedin_indeed": "LinkedIn + Indeed",
    "jobware": "Jobware",
    "stepstone": "StepStone",
    "yer": "yer.de",
    "hays": "Hays DACH",
    "orange_quarter": "Orange Quarter",
}


def _normalize_title(title: str) -> str:
    """Lowercase, strip gender markers and punctuation for dedup comparison."""
    t = title.lower()
    t = re.sub(
        r"\s*\(m/w/d\)|\s*\(w/m/d\)|\s*\(m/f/d\)|\s*\(all genders?\)|\s*\(gn\)|\s*\(f/m/d\)",
        "",
        t,
    )
    t = re.sub(r"[^\w\s]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def _normalize_company(company: str) -> str:
    """Lowercase, strip common legal suffixes for dedup comparison."""
    c = company.lower()
    c = re.sub(r"\b(gmbh|ag|se|kg|mbh|co\.?\s*kg|inc\.?|ltd\.?|llc|s\.a\.?)\b", "", c)
    c = re.sub(r"[^\w\s]", " ", c)
    return re.sub(r"\s+", " ", c).strip()


def _content_hash(
    title: str, company: Optional[str], location: Optional[str] = None
) -> str:
    """Hash of normalized title + company (location excluded to handle format variants).
    Used for cross-source deduplication.
    """
    raw = f"{_normalize_title(title)}|{_normalize_company(company or '')}"
    return hashlib.md5(raw.encode()).hexdigest()


def _title_hash(title: str) -> str:
    """Hash of normalized title only, for fuzzy cross-source dedup."""
    return hashlib.md5(_normalize_title(title).encode()).hexdigest()


def _companies_overlap(a: str, b: str) -> bool:
    """True if one normalized company name is a prefix of the other.
    Catches cases like 'washtec' vs 'washtec cleaning' where one source
    uses the legal entity name and another uses the trading/full name.
    """
    if not a or not b:
        return False
    shorter, longer = (a, b) if len(a) <= len(b) else (b, a)
    return longer.startswith(shorter)


def _upsert_jobs(jobs: list[JobPosting]) -> int:
    """Insert new jobs (skip duplicates by URL or title+company). Returns count of new jobs."""
    new_count = 0
    with db() as conn:
        for job in jobs:
            content_hash = _content_hash(job.title, job.company)
            th = _title_hash(job.title)

            # Three-layer dedup strategy, applied in order of strictness:
            #  1. URL uniqueness — enforced by the UNIQUE constraint on jobs.url via INSERT OR IGNORE.
            #     Catches the same posting reappearing on the same source.
            #  2. content_hash (title+company) — catches the same role posted across multiple
            #     sources with identical titles (e.g. StepStone and Arbeitnow both list "Data
            #     Engineer @ Acme"). Only active when company is known.
            #  3. Fuzzy company prefix — catches minor company name variants between sources
            #     (e.g. "WashTec AG" vs "WashTec Cleaning Technology"). Same title hash, but
            #     the normalized company names share a common prefix.
            if job.company:
                existing = conn.execute(
                    "SELECT id FROM jobs WHERE content_hash = ?", (content_hash,)
                ).fetchone()
                if existing:
                    continue

                # Fuzzy company dedup: same title, company names share a common prefix.
                # Catches e.g. "WashTec AG" (→ "washtec") vs "WashTec Cleaning" (→ "washtec cleaning").
                norm_co = _normalize_company(job.company)
                candidates = conn.execute(
                    "SELECT company FROM jobs WHERE title_hash = ? AND company IS NOT NULL",
                    (th,),
                ).fetchall()
                if any(
                    _companies_overlap(norm_co, _normalize_company(r["company"]))
                    for r in candidates
                ):
                    continue

            cursor = conn.execute(
                """
                INSERT OR IGNORE INTO jobs
                    (source, url, title, company, location, employment_type, remote_type,
                     salary_raw, description, posted_at, content_hash, title_hash, external_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job.source,
                    job.url,
                    job.title,
                    job.company,
                    job.location,
                    job.employment_type,
                    job.remote_type,
                    job.salary_raw,
                    job.description,
                    job.posted_at.isoformat() if job.posted_at else None,
                    content_hash,
                    th,
                    job.external_id,
                ),
            )
            if cursor.rowcount > 0:
                new_count += 1
            elif job.description:
                conn.execute(
                    "UPDATE jobs SET description = ? WHERE url = ? AND (description IS NULL OR description = '')",
                    (job.description, job.url),
                )
    return new_count


def _update_run_detail(run_id: int, source: str, **kwargs):
    with db() as conn:
        sets = ", ".join(f"{k} = ?" for k in kwargs)
        vals = list(kwargs.values()) + [run_id, source]
        conn.execute(
            f"UPDATE scraping_run_details SET {sets} WHERE run_id = ? AND source = ?",
            vals,
        )


def _run_one(source_key: str, ScraperClass, run_id: int) -> tuple[str, int, bool]:
    """Run a single scraper inside a thread pool worker. Returns (source_key, new_count, had_error)."""
    _update_run_detail(
        run_id, source_key, status="running", started_at=datetime.utcnow().isoformat()
    )
    try:
        scraper = ScraperClass()
        jobs, error = scraper.run_safe()
        jobs = apply_filters(jobs) if jobs else jobs
        with _db_write_lock:
            new_count = _upsert_jobs(jobs) if jobs else 0

        if error:
            _update_run_detail(
                run_id,
                source_key,
                status="failed",
                jobs_found=len(jobs),
                jobs_new=new_count,
                error_msg=error[:500],
                finished_at=datetime.utcnow().isoformat(),
            )
            return source_key, new_count, True
        else:
            _update_run_detail(
                run_id,
                source_key,
                status="done",
                jobs_found=len(jobs),
                jobs_new=new_count,
                finished_at=datetime.utcnow().isoformat(),
            )
            return source_key, new_count, False
    except Exception as e:
        _update_run_detail(
            run_id,
            source_key,
            status="failed",
            error_msg=str(e)[:500],
            finished_at=datetime.utcnow().isoformat(),
        )
        return source_key, 0, True


def run_scraping_pipeline(run_id: int, sources: Optional[list[str]] = None):
    """Run scrapers concurrently. Updates scraping_run_details as each finishes."""
    active_scrapers = {
        k: v for k, v in SCRAPER_MAP.items() if sources is None or k in sources
    }

    # Initialise detail rows
    with db() as conn:
        for source_key in active_scrapers:
            conn.execute(
                "INSERT INTO scraping_run_details (run_id, source, status) VALUES (?, ?, 'pending')",
                (run_id, source_key),
            )

    total_new = 0
    any_error = False

    with ThreadPoolExecutor(max_workers=len(active_scrapers)) as pool:
        futures = {
            pool.submit(_run_one, key, cls, run_id): key
            for key, cls in active_scrapers.items()
        }
        for future in as_completed(futures):
            _, new_count, had_error = future.result()
            total_new += new_count
            if had_error:
                any_error = True

    final_status = "failed" if any_error and total_new == 0 else "completed"
    with db() as conn:
        conn.execute(
            "UPDATE scraping_runs SET status = ?, finished_at = ? WHERE id = ?",
            (final_status, datetime.utcnow().isoformat(), run_id),
        )


def start_pipeline_thread(
    run_id: int, sources: Optional[list[str]] = None
) -> threading.Thread:
    t = threading.Thread(
        target=run_scraping_pipeline, args=(run_id, sources), daemon=True
    )
    t.start()
    return t
