"""Description backfill for jobs missing descriptions."""
import re
import time
import random
import threading
from datetime import datetime
from typing import Optional

import httpx
from bs4 import BeautifulSoup

from ..database import db
from ..constants import ENRICH_SLEEP_MIN_SEC, ENRICH_SLEEP_MAX_SEC

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def _fetch_stepstone(client: httpx.Client, url: str) -> Optional[str]:
    try:
        time.sleep(random.uniform(ENRICH_SLEEP_MIN_SEC, ENRICH_SLEEP_MAX_SEC))
        resp = client.get(url, headers=HEADERS, follow_redirects=True, timeout=15)
        if resp.status_code != 200:
            return None
        soup = BeautifulSoup(resp.text, "lxml")
        el = soup.find("div", {"data-at": "job-ad-details"}) or soup.find(
            "div", class_=re.compile(r"job-ad-display|JobAd|jobDescription", re.I)
        )
        return el.get_text(separator="\n", strip=True) if el else None
    except Exception:
        return None


def _fetch_linkedin(client: httpx.Client, url: str) -> Optional[str]:
    """Attempt to fetch LinkedIn job description from public job view page."""
    try:
        time.sleep(random.uniform(ENRICH_SLEEP_MIN_SEC, ENRICH_SLEEP_MAX_SEC))
        resp = client.get(url, headers=HEADERS, follow_redirects=True, timeout=15)
        if resp.status_code != 200:
            return None
        soup = BeautifulSoup(resp.text, "lxml")
        el = (
            soup.find("div", class_=re.compile(r"description__text|show-more-less-html", re.I))
            or soup.find("section", class_=re.compile(r"description", re.I))
            or soup.find("div", {"id": re.compile(r"job-description", re.I)})
        )
        if el:
            text = el.get_text(separator="\n", strip=True)
            return text if len(text) > 100 else None
        return None
    except Exception:
        return None


_FETCHERS = {
    "stepstone": _fetch_stepstone,
    "linkedin": _fetch_linkedin,
}

_state: dict = {"running": False, "done": 0, "total": 0, "errors": 0, "source_counts": {}}


def get_backfill_status() -> dict:
    return dict(_state)


def _worker(rows: list) -> None:
    _state.update(running=True, done=0, total=len(rows), errors=0, source_counts={})
    with httpx.Client(timeout=20, follow_redirects=True) as client:
        for row in rows:
            fetcher = _FETCHERS.get(row["source"])
            if not fetcher:
                _state["done"] += 1
                continue
            desc = fetcher(client, row["url"])
            if desc:
                now = datetime.utcnow().isoformat()
                with db() as conn:
                    conn.execute(
                        "UPDATE jobs SET description = ?, updated_at = ? WHERE id = ?",
                        (desc, now, row["id"]),
                    )
                src = row["source"]
                _state["source_counts"][src] = _state["source_counts"].get(src, 0) + 1
            else:
                _state["errors"] += 1
            _state["done"] += 1
    _state["running"] = False


def start_backfill(sources: Optional[list[str]] = None, limit: int = 300) -> int:
    """Start background description backfill. Returns number of jobs queued, 0 if already running."""
    if _state["running"]:
        return 0

    source_list = sources or ["stepstone", "linkedin"]
    placeholders = ",".join("?" * len(source_list))

    with db() as conn:
        rows = conn.execute(
            f"SELECT id, url, source FROM jobs "
            f"WHERE (description IS NULL OR description = '') "
            f"AND source IN ({placeholders}) "
            f"AND status != 'archived' "
            f"ORDER BY source, id "  # stepstone first (more reliable)
            f"LIMIT ?",
            source_list + [limit],
        ).fetchall()

    if not rows:
        return 0

    threading.Thread(target=_worker, args=(list(rows),), daemon=True).start()
    return len(rows)
