from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional

MAX_AGE_DAYS = 14


def is_too_old(dt: Optional[datetime]) -> bool:
    """Return True if dt is older than MAX_AGE_DAYS. If dt is None, return False (unknown → keep)."""
    if dt is None:
        return False
    cutoff = datetime.now(timezone.utc) - timedelta(days=MAX_AGE_DAYS)
    # Make dt timezone-aware if naive (assume UTC)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt < cutoff


@dataclass
class JobPosting:
    source: str
    url: str
    title: str
    company: Optional[str] = None
    location: Optional[str] = None
    employment_type: Optional[str] = None  # 'permanent' | 'freelance' | 'unknown'
    remote_type: Optional[str] = None  # 'remote' | 'hybrid' | 'onsite' | 'unknown'
    salary_raw: Optional[str] = None
    description: Optional[str] = None
    posted_at: Optional[datetime] = None
    external_id: Optional[str] = None


SEARCH_ROLES = [
    "AI Engineer",
    "Data Engineer",
    "Analytics Engineer",
    "MLOps Engineer",
    "Machine Learning Engineer",
    "Data Architect",
]
SEARCH_LOCATION = "Germany"


class BaseScraper(ABC):
    roles: list[str] = SEARCH_ROLES
    location: str = SEARCH_LOCATION

    @abstractmethod
    def scrape(self) -> list[JobPosting]: ...

    def run_safe(self) -> tuple[list[JobPosting], Optional[str]]:
        try:
            results = self.scrape()
            return results, None
        except Exception as e:
            return [], str(e)
