"""Title and age filters applied to all scraped jobs before DB insertion."""

from datetime import datetime, timedelta
from typing import List

from .base import JobPosting

TITLE_BLACKLIST = [
    "intern",
    "internship",
    "working student",
    "work student",
    "werkstudent",
    "junior",
    "praktikum",
    "praktikant",
]

TITLE_ALLOWLIST = [
    "data",
    "ai",
    "ml",
    "analytics",
    "machine learning",
    "intelligence",
    "scientist",
    "mlops",
    "quantitative",
    "bi",
    "nlp",
    "llm",
    "deep learning",
]

MAX_AGE_DAYS = 14


def _passes_title(title: str) -> bool:
    t = title.lower()
    if any(b in t for b in TITLE_BLACKLIST):
        return False
    if not any(a in t for a in TITLE_ALLOWLIST):
        return False
    return True


def _passes_age(job: JobPosting) -> bool:
    if job.posted_at is None:
        return True  # unknown date → include
    cutoff = datetime.utcnow() - timedelta(days=MAX_AGE_DAYS)
    return job.posted_at >= cutoff


def apply_filters(jobs: List[JobPosting]) -> List[JobPosting]:
    return [j for j in jobs if _passes_title(j.title) and _passes_age(j)]
