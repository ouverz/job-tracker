"""jobware.de scraper — DACH job board via internal JSON API.

API endpoint discovered 2026-04: GET /api/d48b2/xnfwe?jw_jobname={term}&jw_result_count=50
Returns job listings with title, company, location, date, jobtypes, task (description),
and salary in a single call. No detail-page fetch required.

URL construction:
  API field : business-analyst-w-m-d.1936892405.html
  Canonical : https://www.jobware.de/job/business-analyst-w-m-d-1936892405
"""

import re
import time
import random
from datetime import datetime, timezone
from typing import Optional

import httpx

from .base import BaseScraper, JobPosting, is_too_old

BASE_URL = "https://www.jobware.de"
API_PATH = "/api/d48b2/xnfwe"
JOB_BASE = f"{BASE_URL}/job/"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
    "Referer": "https://www.jobware.de/",
}

DACH_COUNTRY_CODES = {"DE", "AT", "CH"}

# Broader search terms work better with Jobware's own relevance engine.
# Listing results are already filtered by Jobware — we just deduplicate across terms.
SEARCH_TERMS = [
    "Data Engineer",
    "AI Engineer",
    "Machine Learning Engineer",
    "Analytics Engineer",
    "Data Scientist",
    "Data Architect",
    "MLOps",
]


def _build_job_url(url_field: str) -> str:
    """Convert API url field to canonical Jobware job URL.

    API field:  business-analyst-w-m-d.1936892405.html
    Canonical:  https://www.jobware.de/job/business-analyst-w-m-d-1936892405
    """
    slug = re.sub(r"\.html$", "", url_field)  # strip .html suffix
    slug = slug.replace(".", "-")  # dot before numeric ID → hyphen
    return f"{JOB_BASE}{slug}"


def _parse_employment_type(jobtypes: list) -> str:
    names = " ".join(jt.get("name", "").lower() for jt in jobtypes)
    if any(
        w in names for w in ["freelance", "freiberuflich", "selbständig", "interim"]
    ):
        return "freelance"
    return "permanent"


def _parse_remote_type(jobtypes: list) -> str:
    names = " ".join(jt.get("name", "").lower() for jt in jobtypes)
    if "remote" in names:
        return "remote"
    if "homeoffice" in names:
        return "hybrid"
    return "onsite"


def _parse_salary(salary: Optional[dict]) -> Optional[str]:
    if not salary or not salary.get("from"):
        return None
    low = salary["from"]
    high = salary.get("to")
    return f"€{low}–€{high}" if high else f"€{low}+"


def _is_dach(item: dict) -> bool:
    """True if any locationInfo is in DE/AT/CH, or the location string implies DACH/remote."""
    for loc in item.get("locationInfos", []):
        if loc.get("iso2CountryCode") in DACH_COUNTRY_CODES:
            return True
    loc_str = item.get("location", "").lower()
    return any(
        w in loc_str
        for w in [
            "germany",
            "deutschland",
            "austria",
            "österreich",
            "switzerland",
            "schweiz",
            "remote",
        ]
    )


class JobwareScraper(BaseScraper):
    """Scrapes jobware.de via their internal listing API."""

    def scrape(self) -> list[JobPosting]:
        results: list[JobPosting] = []
        seen_urls: set[str] = set()

        with httpx.Client(timeout=20, headers=HEADERS, follow_redirects=True) as client:
            for term in SEARCH_TERMS:
                try:
                    time.sleep(random.uniform(1.5, 3.0))
                    resp = client.get(
                        f"{BASE_URL}{API_PATH}",
                        params={"jw_jobname": term, "jw_result_count": 50},
                    )
                    if resp.status_code == 403:
                        print(
                            f"[jobware] 403 on term '{term}' — API may require session cookie"
                        )
                        continue
                    resp.raise_for_status()
                    data = resp.json()
                except Exception as e:
                    print(f"[jobware] Error fetching '{term}': {e}")
                    continue

                items = data.get("data", [])
                for item in items:
                    try:
                        url_field = item.get("url", "")
                        if not url_field:
                            continue

                        job_url = _build_job_url(url_field)
                        if job_url in seen_urls:
                            continue

                        if not _is_dach(item):
                            continue

                        # date is Unix milliseconds
                        posted_at: Optional[datetime] = None
                        ts_ms = item.get("date")
                        if ts_ms:
                            posted_at = datetime.fromtimestamp(
                                ts_ms / 1000, tz=timezone.utc
                            ).replace(tzinfo=None)

                        if is_too_old(posted_at):
                            continue

                        seen_urls.add(job_url)

                        jobtypes = item.get("jobtypes", [])

                        results.append(
                            JobPosting(
                                source="jobware",
                                url=job_url,
                                title=item.get("title", ""),
                                company=item.get("advertiser", {}).get("name") or None,
                                location=item.get("location") or None,
                                employment_type=_parse_employment_type(jobtypes),
                                remote_type=_parse_remote_type(jobtypes),
                                salary_raw=_parse_salary(item.get("salary")),
                                description=item.get("task") or None,
                                posted_at=posted_at,
                                external_id=str(item["id"]) if item.get("id") else None,
                            )
                        )
                    except Exception:
                        continue

        print(
            f"[jobware] {len(results)} DACH jobs across {len(SEARCH_TERMS)} search terms"
        )
        return results
