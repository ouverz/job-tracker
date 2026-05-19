"""Shared helpers for HTML scrapers."""

import re
import time
import random
from typing import Optional

import httpx
from bs4 import BeautifulSoup

# Cap per scraper — keeps total runtime reasonable
MAX_DESC = 15

# Patterns that reliably wrap the main job description content
_DESC_CLASS = re.compile(
    r"job-?desc|job-?detail|job-?body|job-?content|job-?ad|"
    r"vacancy-?detail|vacancy-?desc|offer-?content|offer-?desc|"
    r"stellenbeschreibung|position-?desc|ad-?content|"
    r"main-?content|page-?content",
    re.I,
)
_DESC_ID = re.compile(r"job|description|detail|content|vacancy", re.I)

_PROBE_ORDER = [
    lambda s: s.find("div", class_=_DESC_CLASS),
    lambda s: s.find("section", class_=_DESC_CLASS),
    lambda s: s.find("div", id=_DESC_ID),
    lambda s: s.find("article"),
    lambda s: s.find("main"),
]


def fetch_description(
    client: httpx.Client, url: str, delay: float = 1.0
) -> Optional[str]:
    """Fetch a job detail page and extract the description text. Returns None on failure."""
    try:
        time.sleep(random.uniform(delay * 0.6, delay * 1.4))
        resp = client.get(url, timeout=15)
        if resp.status_code != 200:
            return None
        soup = BeautifulSoup(resp.text, "lxml")
        for probe in _PROBE_ORDER:
            el = probe(soup)
            if el:
                text = el.get_text(separator="\n", strip=True)
                if len(text) > 120:
                    return text
        return None
    except Exception:
        return None
