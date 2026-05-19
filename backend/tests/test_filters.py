"""Unit tests for the title and age filters in scrapers/filters.py."""

from datetime import datetime, timedelta

from app.scrapers.filters import apply_filters, _passes_title, _passes_age
from app.scrapers.base import JobPosting


def _make_job(title: str, posted_at=None) -> JobPosting:
    return JobPosting(
        source="test",
        url=f"https://example.com/{title.replace(' ', '-')}",
        title=title,
        company="Test Co",
        location="Berlin",
        posted_at=posted_at,
    )


class TestPassesTitle:
    def test_relevant_data_title_passes(self):
        assert _passes_title("Data Engineer") is True
        assert _passes_title("AI Engineer") is True
        assert _passes_title("Analytics Engineer") is True
        assert _passes_title("ML Engineer") is True

    def test_blacklisted_title_blocked(self):
        assert _passes_title("Junior Data Engineer") is False
        assert _passes_title("Data Engineering Intern") is False
        assert _passes_title("Werkstudent Data Analytics") is False
        assert _passes_title("Data Analytics Internship") is False

    def test_irrelevant_title_blocked(self):
        assert _passes_title("Marketing Manager") is False
        assert _passes_title("Sales Representative") is False
        assert _passes_title("HR Business Partner") is False

    def test_case_insensitive(self):
        assert _passes_title("DATA ENGINEER") is True
        assert _passes_title("JUNIOR data engineer") is False

    def test_allowlist_keyword_anywhere_in_title(self):
        assert _passes_title("Senior Engineer – Data Platforms") is True
        assert _passes_title("Machine Learning Researcher") is True


class TestPassesAge:
    def test_recent_job_passes(self):
        job = _make_job(
            "Data Engineer", posted_at=datetime.utcnow() - timedelta(days=3)
        )
        assert _passes_age(job) is True

    def test_old_job_blocked(self):
        job = _make_job(
            "Data Engineer", posted_at=datetime.utcnow() - timedelta(days=20)
        )
        assert _passes_age(job) is False

    def test_exactly_at_cutoff_passes(self):
        job = _make_job(
            "Data Engineer", posted_at=datetime.utcnow() - timedelta(days=13)
        )
        assert _passes_age(job) is True

    def test_none_date_passes(self):
        # Unknown date → always include
        job = _make_job("Data Engineer", posted_at=None)
        assert _passes_age(job) is True


class TestApplyFilters:
    def test_keeps_valid_jobs(self):
        jobs = [
            _make_job("Data Engineer", datetime.utcnow() - timedelta(days=1)),
            _make_job("AI Engineer", datetime.utcnow() - timedelta(days=5)),
        ]
        assert len(apply_filters(jobs)) == 2

    def test_removes_blacklisted_titles(self):
        jobs = [
            _make_job("Data Engineer", datetime.utcnow() - timedelta(days=1)),
            _make_job("Junior Data Engineer", datetime.utcnow() - timedelta(days=1)),
        ]
        result = apply_filters(jobs)
        assert len(result) == 1
        assert result[0].title == "Data Engineer"

    def test_removes_old_jobs(self):
        jobs = [
            _make_job("Data Engineer", datetime.utcnow() - timedelta(days=1)),
            _make_job("Analytics Engineer", datetime.utcnow() - timedelta(days=30)),
        ]
        result = apply_filters(jobs)
        assert len(result) == 1
        assert result[0].title == "Data Engineer"

    def test_empty_list(self):
        assert apply_filters([]) == []

    def test_all_blocked(self):
        jobs = [
            _make_job("Marketing Manager"),
            _make_job("HR Business Partner"),
        ]
        assert apply_filters(jobs) == []
