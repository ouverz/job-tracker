"""yer.de scraper — specialist IT/tech recruitment agency.

URL changed (2026-03): /jobs/ → /de/jobangebote/?search={role}
Card class changed to: job-items__item
Detail page has location in: div.jd-header__feature-location
"""

import re
import time
import random
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlencode

from .base import BaseScraper, JobPosting
from .utils import MAX_DESC

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

BASE_URL = "https://www.yer.de"


def _detect_employment_type(text: str) -> str:
    t = text.lower()
    if any(w in t for w in ["freelance", "freiberuflich", "contract", "selbständig"]):
        return "freelance"
    return "permanent"


def _detect_remote(text: str) -> str:
    t = text.lower()
    if "remote" in t:
        return "remote"
    if "hybrid" in t:
        return "hybrid"
    return "onsite"


def _get_detail(client: httpx.Client, url: str) -> tuple:
    """Fetch a yer.de job detail page. Returns (description, location)."""
    try:
        time.sleep(random.uniform(1.0, 2.0))
        resp = client.get(url, timeout=15)
        if resp.status_code != 200:
            return None, None
        soup = BeautifulSoup(resp.text, "lxml")

        loc_el = soup.find(
            "div", class_=re.compile(r"jd-header__feature-location", re.I)
        )
        location = loc_el.get_text(strip=True) if loc_el else None

        desc_el = soup.find(
            "div", class_=re.compile(r"job-detail__content-wrapper", re.I)
        )
        description = desc_el.get_text(separator="\n", strip=True) if desc_el else None

        return description, location
    except Exception:
        return None, None


class YerScraper(BaseScraper):

    def scrape(self) -> list[JobPosting]:
        results: list[JobPosting] = []
        seen_urls: set[str] = set()

        with httpx.Client(
            timeout=20, headers=HEADERS, follow_redirects=True, max_redirects=5
        ) as client:
            for role in self.roles:
                try:
                    params = {"search": role}
                    url = f"{BASE_URL}/de/jobangebote/?{urlencode(params)}"
                    time.sleep(random.uniform(1.0, 2.5))
                    resp = client.get(url, timeout=15)
                    if resp.status_code != 200:
                        continue
                except Exception as e:
                    print(f"[yer] Request error: {e}")
                    continue

                soup = BeautifulSoup(resp.text, "lxml")

                # Card selector confirmed from live inspection 2026-03
                cards = soup.find_all("div", class_="job-items__item")
                if not cards:
                    # Fallback: try broader class match
                    cards = soup.find_all(
                        "div", class_=re.compile(r"job-items__item", re.I)
                    )

                for card in cards:
                    try:
                        link = card.find(
                            "a", href=re.compile(r"/de/jobangebote/[^?]+$")
                        )
                        if not link:
                            link = card.find("a")
                        if not link:
                            continue

                        href = link.get("href", "")
                        if not href:
                            continue
                        job_url = urljoin(BASE_URL, href)
                        if job_url in seen_urls:
                            continue
                        seen_urls.add(job_url)

                        title_el = (
                            card.find(
                                "div", class_=re.compile(r"job-items__item-title", re.I)
                            )
                            or link
                        )
                        title = title_el.get_text(strip=True)
                        if not title:
                            continue

                        snippet = card.get_text(" ", strip=True)

                        results.append(
                            JobPosting(
                                source="yer",
                                url=job_url,
                                title=title,
                                company="yer.de",
                                location="Germany",  # enriched below from detail page
                                employment_type=_detect_employment_type(snippet),
                                remote_type=_detect_remote(f"{title} {snippet}"),
                            )
                        )
                    except Exception:
                        continue

                if len(results) >= 60:
                    break

            # Fetch detail pages: enrich location + description
            for job in results[:MAX_DESC]:
                description, location = _get_detail(client, job.url)
                if description:
                    job.description = description
                if location:
                    job.location = location

        return results
