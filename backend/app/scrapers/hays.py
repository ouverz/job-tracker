"""hays.de scraper — DACH region specialist staffing.

Strategy (2026-03): Hays search pages are JS-rendered and not scrapeable via httpx.
Instead, we parse their XML job sitemap which lists current job URLs with lastmod dates.
Job title and location are extracted from the URL slug.
"""
import re
import time
import random
import httpx
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import Optional

from .base import BaseScraper, JobPosting, MAX_AGE_DAYS

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

SITEMAP_URL = "https://www.hays.de/o/sitemaps/de/job-sitemap.xml"

# Keywords matched against the URL slug (lowercase, hyphen-separated)
ROLE_KEYWORDS = [
    "data-engineer", "data-architect", "data-scientist", "data-analyst",
    "machine-learning", "ml-engineer", "ai-engineer", "ki-engineer",
    "analytics-engineer", "mlops", "nlp-engineer", "bi-engineer",
    "data-platform", "daten-engineer", "data-modell", "data-integration",
    "data-warehouse", "databricks", "spark-engineer",
]


def _parse_slug(slug: str) -> tuple[str, str]:
    """Extract (title, city) from a Hays job URL slug.

    URL format: stellenangebote-jobs-detail-{title-slug}-{city-slug}-{job_id}
    e.g. stellenangebote-jobs-detail-senior-data-engineer-koeln-851963
         stellenangebote-jobs-detail-ki-engineer-frankfurt-am-main-866190
    """
    # Strip standard prefix
    slug = re.sub(r"^stellenangebote-jobs-detail-", "", slug)
    # Strip trailing /1 etc. from path segment
    slug = slug.rstrip("/").split("/")[0] if "/" in slug else slug

    # Remove trailing numeric job ID
    match = re.match(r"^(.+?)-(\d{5,7})$", slug)
    if not match:
        return slug.replace("-", " ").title(), "Germany"

    title_city = match.group(1)

    # Handle compound city names (frankfurt-am-main, ludwigshafen-am-rhein, etc.)
    compound = re.search(r"-([a-z]+-(?:am|an-der|im|ob-der)-[a-z]+)$", title_city)
    if compound:
        city_slug = compound.group(1)
        title_slug = title_city[: -(len(city_slug) + 1)]
    else:
        parts = title_city.rsplit("-", 1)
        title_slug = parts[0] if len(parts) == 2 else title_city
        city_slug = parts[1] if len(parts) == 2 else "germany"

    return title_slug.replace("-", " ").title(), city_slug.replace("-", " ").title()


def _detect_employment_type(text: str) -> str:
    t = text.lower()
    if any(w in t for w in ["freelance", "freiberuflich", "selbständig", "contract", "interim"]):
        return "freelance"
    return "permanent"


def _detect_remote(text: str) -> str:
    t = text.lower()
    if "remote" in t:
        return "remote"
    if "hybrid" in t:
        return "hybrid"
    return "onsite"


class HaysScraper(BaseScraper):

    def scrape(self) -> list[JobPosting]:
        results: list[JobPosting] = []
        cutoff = (datetime.now() - timedelta(days=MAX_AGE_DAYS)).strftime("%Y-%m-%d")

        # Fetch sitemap
        try:
            with httpx.Client(timeout=30, headers=HEADERS, follow_redirects=True) as client:
                resp = client.get(SITEMAP_URL)
                if resp.status_code != 200:
                    print(f"[hays] Sitemap returned {resp.status_code}")
                    return results
                sitemap_xml = resp.text
        except Exception as e:
            print(f"[hays] Sitemap fetch error: {e}")
            return results

        # Parse sitemap XML
        soup = BeautifulSoup(sitemap_xml, "xml")
        for url_el in soup.find_all("url"):
            loc_el = url_el.find("loc")
            lastmod_el = url_el.find("lastmod")
            if not loc_el:
                continue

            url = loc_el.get_text(strip=True)
            lastmod = lastmod_el.get_text(strip=True) if lastmod_el else ""

            # Filter by recency
            if lastmod and lastmod < cutoff:
                continue

            # Filter by keyword match in URL slug
            url_lower = url.lower()
            if not any(k in url_lower for k in ROLE_KEYWORDS):
                continue

            # Extract slug from URL path
            # e.g. https://www.hays.de/jobsuche/stellenangebote-jobs-detail-...-{id}/1
            path_match = re.search(r"/jobsuche/(stellenangebote-jobs-detail-[^/]+)", url)
            if not path_match:
                continue

            slug = path_match.group(1)
            title, city = _parse_slug(slug)
            if not title:
                continue

            # Parse lastmod as posted_at
            posted_at: Optional[datetime] = None
            if lastmod:
                try:
                    posted_at = datetime.strptime(lastmod, "%Y-%m-%d")
                except Exception:
                    pass

            snippet = f"{title} {city}"
            results.append(JobPosting(
                source="hays",
                url=url,
                title=title,
                company=None,
                location=city,
                employment_type=_detect_employment_type(snippet),
                remote_type=_detect_remote(snippet),
                posted_at=posted_at,
            ))

        print(f"[hays] Sitemap: {len(results)} matching jobs found")
        return results
