import httpx
import time
from .base import BaseScraper, JobPosting, is_too_old
from datetime import datetime
import re

# Keywords matched against job title (substring match, case-insensitive)
ROLE_KEYWORDS = [
    # AI / ML
    "ai engineer",
    "ai architect",
    "ai developer",
    "artificial intelligence",
    "machine learning",
    "ml engineer",
    "mlops",
    "ml ops",
    "llm",
    "nlp",
    "generative ai",
    "gen ai",
    "deep learning",
    "ki-ingenieur",
    "ki engineer",  # German: KI = AI
    # Data Engineering
    "data engineer",
    "data architect",
    "data platform",
    "data infrastructure",
    "data pipeline",
    "etl engineer",
    "databricks engineer",
    "big data",
    "dataops",
    "data ops",
    # Analytics
    "analytics engineer",
    "analytics architect",
    "dbt",
    "data analyst",
    "bi engineer",
    "bi developer",
    # Data Science
    "data scientist",
]


def _is_relevant(title: str) -> bool:
    # Arbeitnow is a DACH-focused board — no location check needed.
    # Only filter on role keywords matched against the title.
    return any(kw in title.lower() for kw in ROLE_KEYWORDS)


def _parse_employment_type(job: dict) -> str:
    types = job.get("job_types", [])
    if not types:
        return "unknown"
    combined = " ".join(types).lower()
    if "freelance" in combined or "contract" in combined:
        return "freelance"
    if "full" in combined or "permanent" in combined:
        return "permanent"
    return "unknown"


class ArbeitnowScraper(BaseScraper):
    BASE_URL = "https://www.arbeitnow.com/api/job-board-api"

    def scrape(self) -> list[JobPosting]:
        results: list[JobPosting] = []
        seen_urls: set[str] = set()

        MAX_PAGES = 25  # ~2500 jobs; API rate-limits around page 11+ without delays

        with httpx.Client(timeout=30) as client:
            page = 1
            while page <= MAX_PAGES:
                if page > 1:
                    time.sleep(0.4)  # stay under rate limit
                try:
                    resp = client.get(self.BASE_URL, params={"page": page})
                    resp.raise_for_status()
                    data = resp.json()
                except Exception:
                    break

                jobs = data.get("data", [])
                if not jobs:
                    break

                page_all_old = True
                for job in jobs:
                    title = job.get("title", "")
                    location = job.get("location", "")
                    url = job.get("url", "")

                    if not url or url in seen_urls:
                        continue

                    posted_at = None
                    created_at = job.get("created_at")
                    if created_at:
                        try:
                            posted_at = datetime.fromtimestamp(created_at)
                        except Exception:
                            pass

                    if is_too_old(posted_at):
                        continue

                    page_all_old = False

                    if not _is_relevant(title):
                        continue

                    seen_urls.add(url)
                    is_remote = job.get("remote", False)

                    results.append(
                        JobPosting(
                            source="arbeitnow",
                            url=url,
                            title=title,
                            company=job.get("company_name"),
                            location=location,
                            employment_type=_parse_employment_type(job),
                            remote_type="remote" if is_remote else "onsite",
                            description=job.get("description", ""),
                            posted_at=posted_at,
                            external_id=job.get("slug"),
                        )
                    )

                # Stop if every job on this page was older than 14 days
                if page_all_old:
                    break

                # Check pagination
                meta = data.get("meta", {})
                if meta.get("current_page", page) >= meta.get("last_page", page):
                    break
                page += 1

        return results
