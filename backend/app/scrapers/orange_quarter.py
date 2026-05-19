"""orange-quarter.com scraper — data & analytics niche recruiter."""

import re
import time
import random
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from .base import BaseScraper, JobPosting
from .utils import fetch_description, MAX_DESC

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

BASE_URL = "https://www.orange-quarter.com"


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


class OrangeQuarterScraper(BaseScraper):

    def scrape(self) -> list[JobPosting]:
        results: list[JobPosting] = []
        seen_urls: set[str] = set()

        with httpx.Client(
            timeout=20, headers=HEADERS, follow_redirects=True, max_redirects=5
        ) as client:
            try_urls = [
                f"{BASE_URL}/jobs/",
                f"{BASE_URL}/stellenangebote/",
                f"{BASE_URL}/karriere/",
                f"{BASE_URL}/vacancies/",
            ]

            for url in try_urls:
                try:
                    time.sleep(random.uniform(1.0, 2.0))
                    resp = client.get(url, timeout=15)
                    if resp.status_code != 200:
                        continue
                except Exception as e:
                    print(f"[orange_quarter] Request error on {url}: {e}")
                    continue

                soup = BeautifulSoup(resp.text, "lxml")

                cards = soup.find_all(
                    class_=re.compile(
                        r"job-?card|job-?item|job-?listing|vacancy|position", re.I
                    )
                )
                if not cards:
                    cards = soup.find_all("article")
                if not cards:
                    cards = soup.find_all(
                        "li", class_=re.compile(r"job|result|position|vacancy", re.I)
                    )

                for card in cards:
                    try:
                        link = card.find("a")
                        if not link:
                            continue

                        title_el = card.find(["h2", "h3", "h4"]) or link
                        title = title_el.get_text(strip=True)
                        if not title:
                            continue

                        href = link.get("href", "")
                        if not href:
                            continue
                        job_url = urljoin(BASE_URL, href)
                        if job_url in seen_urls:
                            continue
                        seen_urls.add(job_url)

                        company_el = card.find(
                            class_=re.compile(r"company|employer|arbeitgeber", re.I)
                        )
                        company = (
                            company_el.get_text(strip=True)
                            if company_el
                            else "orange-quarter.com"
                        )

                        location_el = card.find(
                            class_=re.compile(r"location|city|ort|place", re.I)
                        )
                        location = (
                            location_el.get_text(strip=True)
                            if location_el
                            else "Germany"
                        )

                        snippet = card.get_text(" ", strip=True)

                        results.append(
                            JobPosting(
                                source="orange_quarter",
                                url=job_url,
                                title=title,
                                company=company,
                                location=location,
                                employment_type=_detect_employment_type(snippet),
                                remote_type=_detect_remote(
                                    f"{title} {location} {snippet}"
                                ),
                            )
                        )
                    except Exception:
                        continue

                if results:
                    break

            for job in results[:MAX_DESC]:
                if not job.description:
                    job.description = fetch_description(client, job.url)

        return results
