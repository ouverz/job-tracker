"""StepStone.de scraper using requests + BeautifulSoup."""
import re
import time
import random
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin, quote_plus
from datetime import datetime, timedelta
from typing import Optional

from .base import BaseScraper, JobPosting, is_too_old

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

BASE_URL = "https://www.stepstone.de"


def _slug(role: str) -> str:
    return role.lower().replace(" ", "-")


def _parse_date(article) -> Optional[datetime]:
    """Best-effort extraction of posting date from a StepStone listing card."""
    # Try <time> element first
    time_el = article.find("time")
    if time_el:
        dt_str = time_el.get("datetime") or time_el.get_text(strip=True)
        try:
            return datetime.fromisoformat(dt_str)
        except Exception:
            pass

    # Try date-labelled spans/divs
    date_el = article.find(attrs={"data-at": re.compile(r"date|posted|time", re.I)}) or \
              article.find(class_=re.compile(r"date|posted|pubdate|time", re.I))
    if date_el:
        text = date_el.get_text(strip=True).lower()
        now = datetime.now()
        if "heute" in text or "today" in text:
            return now
        if "gestern" in text or "yesterday" in text:
            return now.replace(hour=0, minute=0, second=0) - timedelta(days=1)
        m = re.search(r"vor\s+(\d+)\s+tag", text)
        if m:
            return now - timedelta(days=int(m.group(1)))
        # DD.MM.YYYY
        m = re.search(r"(\d{1,2})\.(\d{1,2})\.(\d{4})", text)
        if m:
            try:
                return datetime(int(m.group(3)), int(m.group(2)), int(m.group(1)))
            except Exception:
                pass
    return None


def _detect_employment_type(text: str) -> str:
    t = text.lower()
    if any(w in t for w in ["freelance", "freiberuflich", "selbständig", "freie mitarbeit"]):
        return "freelance"
    return "permanent"


def _detect_remote(text: str) -> str:
    t = text.lower()
    if "remote" in t:
        return "remote"
    if "hybrid" in t:
        return "hybrid"
    return "onsite"


def _get_description(client: httpx.Client, url: str) -> Optional[str]:
    try:
        time.sleep(random.uniform(1.5, 3.0))
        resp = client.get(url, headers=HEADERS, follow_redirects=True, timeout=15)
        if resp.status_code != 200:
            return None
        soup = BeautifulSoup(resp.text, "lxml")
        # StepStone job description container
        desc_el = soup.find("div", {"data-at": "job-ad-details"}) or \
                  soup.find("div", class_=re.compile(r"job-ad-display|JobAd|jobDescription", re.I))
        if desc_el:
            return desc_el.get_text(separator="\n", strip=True)
        return None
    except Exception:
        return None


class StepStoneScraper(BaseScraper):

    def scrape(self) -> list[JobPosting]:
        results: list[JobPosting] = []
        seen_urls: set[str] = set()

        with httpx.Client(timeout=20, headers=HEADERS, follow_redirects=True) as client:
            for role in self.roles:
                for page in range(1, 4):  # 3 pages per role
                    try:
                        # StepStone URL format
                        role_slug = quote_plus(role)
                        url = f"{BASE_URL}/jobs/?q={role_slug}&l=Deutschland&page={page}"
                        time.sleep(random.uniform(1.0, 2.5))
                        resp = client.get(url, timeout=15)
                        if resp.status_code in (403, 429):
                            print(f"[stepstone] Rate limited on {role} page {page}")
                            break
                        if resp.status_code != 200:
                            break
                    except Exception as e:
                        print(f"[stepstone] Request error: {e}")
                        break

                    soup = BeautifulSoup(resp.text, "lxml")

                    # Job article cards
                    articles = soup.find_all("article", {"data-at": "job-item"})
                    if not articles:
                        # Try alternative selectors
                        articles = soup.find_all("article", class_=re.compile(r"job-element|ResultItem", re.I))

                    if not articles:
                        break

                    for article in articles:
                        try:
                            # Title
                            title_el = article.find("a", {"data-at": "job-item-title"}) or \
                                       article.find("h2") or article.find("a")
                            if not title_el:
                                continue
                            title = title_el.get_text(strip=True)
                            href = title_el.get("href", "")
                            if not href:
                                continue
                            job_url = urljoin(BASE_URL, href)
                            if job_url in seen_urls:
                                continue

                            posted_at = _parse_date(article)
                            if is_too_old(posted_at):
                                continue

                            seen_urls.add(job_url)

                            # Company
                            company_el = article.find(attrs={"data-at": "job-item-company-name"}) or \
                                         article.find(class_=re.compile(r"company|employer", re.I))
                            company = company_el.get_text(strip=True) if company_el else None

                            # Location
                            location_el = article.find(attrs={"data-at": "job-item-location"}) or \
                                          article.find(class_=re.compile(r"location|city", re.I))
                            location = location_el.get_text(strip=True) if location_el else "Germany"

                            # Salary teaser
                            salary_el = article.find(class_=re.compile(r"salary|gehalt", re.I))
                            salary_raw = salary_el.get_text(strip=True) if salary_el else None

                            # Snippet text for remote/type detection
                            snippet = article.get_text(" ", strip=True)

                            results.append(JobPosting(
                                source="stepstone",
                                url=job_url,
                                title=title,
                                company=company,
                                location=location,
                                employment_type=_detect_employment_type(snippet),
                                remote_type=_detect_remote(f"{title} {location} {snippet}"),
                                salary_raw=salary_raw,
                                posted_at=posted_at,
                                description=None,  # fetched separately if needed
                            ))
                        except Exception:
                            continue

        # Fetch descriptions for up to 20 jobs to avoid too many requests
        with httpx.Client(timeout=20, headers=HEADERS, follow_redirects=True) as client:
            for job in results[:20]:
                if job.description is None:
                    job.description = _get_description(client, job.url)

        return results
