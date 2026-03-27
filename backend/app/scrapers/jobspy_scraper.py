"""LinkedIn and Indeed scraper using python-jobspy library."""
import re
from datetime import datetime
from typing import Optional

from .base import BaseScraper, JobPosting, is_too_old

try:
    from jobspy import scrape_jobs
    JOBSPY_AVAILABLE = True
except ImportError:
    JOBSPY_AVAILABLE = False


def _detect_remote(title: str, description: str, location: str) -> str:
    combined = f"{title} {description[:500]} {location}".lower()
    if "remote" in combined:
        return "remote"
    if "hybrid" in combined:
        return "hybrid"
    return "onsite"


def _detect_employment_type(title: str, description: str) -> str:
    combined = f"{title} {description[:500]}".lower()
    if any(w in combined for w in ["freelance", "freiberuflich", "contract", "selbständig"]):
        return "freelance"
    return "permanent"


def _to_datetime(val) -> Optional[datetime]:
    if val is None:
        return None
    if isinstance(val, datetime):
        return val
    try:
        return datetime.fromisoformat(str(val))
    except Exception:
        return None


class JobSpyScraper(BaseScraper):
    """Scrapes LinkedIn and Indeed via python-jobspy."""

    SITES = ["linkedin", "indeed"]

    def scrape(self) -> list[JobPosting]:
        if not JOBSPY_AVAILABLE:
            raise RuntimeError("python-jobspy not installed. Run: pip install python-jobspy")

        results: list[JobPosting] = []
        seen_urls: set[str] = set()

        for role in self.roles:
            for site in self.SITES:
                try:
                    kwargs = dict(
                        site_name=[site],
                        search_term=role,
                        location="Germany",
                        results_wanted=50,
                        hours_old=336,  # last 14 days
                    )
                    if site == "linkedin":
                        kwargs["linkedin_fetch_description"] = True
                    if site == "indeed":
                        kwargs["country_indeed"] = "germany"
                    df = scrape_jobs(**kwargs)
                    if df is None or df.empty:
                        continue

                    for _, row in df.iterrows():
                        url = str(row.get("job_url", "")).strip()
                        if not url or url in seen_urls:
                            continue

                        posted_at = _to_datetime(row.get("date_posted"))
                        if is_too_old(posted_at):
                            continue

                        seen_urls.add(url)

                        title = str(row.get("title", "")).strip()
                        description = str(row.get("description", "") or "")
                        location = str(row.get("location", "") or "")

                        results.append(JobPosting(
                            source=site,
                            url=url,
                            title=title,
                            company=str(row.get("company", "") or "").strip() or None,
                            location=location or None,
                            employment_type=_detect_employment_type(title, description),
                            remote_type=_detect_remote(title, description, location),
                            salary_raw=str(row.get("min_amount", "") or "").strip() or None,
                            description=description or None,
                            posted_at=posted_at,
                            external_id=str(row.get("id", "") or "").strip() or None,
                        ))
                except Exception as e:
                    # Don't fail all sources if one role/site combination fails
                    print(f"[jobspy] Error scraping {site}/{role}: {e}")
                    continue

        return results
