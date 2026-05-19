"""Unit tests for the 3-layer deduplication logic in scrapers/runner.py."""
from app.scrapers.runner import (
    _normalize_title,
    _normalize_company,
    _content_hash,
    _title_hash,
    _companies_overlap,
)


class TestNormalizeTitle:
    def test_lowercases(self):
        assert _normalize_title("Data Engineer") == "data engineer"

    def test_strips_gender_markers(self):
        assert _normalize_title("Data Engineer (m/w/d)") == "data engineer"
        assert _normalize_title("Data Engineer (w/m/d)") == "data engineer"
        assert _normalize_title("Data Engineer (m/f/d)") == "data engineer"
        assert _normalize_title("Data Engineer (all genders)") == "data engineer"
        assert _normalize_title("Data Engineer (gn)") == "data engineer"
        assert _normalize_title("Data Engineer (f/m/d)") == "data engineer"

    def test_strips_punctuation(self):
        assert _normalize_title("Senior Data-Engineer") == "senior data engineer"

    def test_collapses_whitespace(self):
        assert _normalize_title("  AI   Engineer  ") == "ai engineer"

    def test_unicode_letters_preserved(self):
        result = _normalize_title("Dateningenieur")
        assert "dateningenieur" in result


class TestNormalizeCompany:
    def test_lowercases(self):
        assert _normalize_company("Acme Corp") == "acme corp"

    def test_strips_gmbh(self):
        assert _normalize_company("WashTec GmbH") == "washtec"

    def test_strips_ag(self):
        assert _normalize_company("SAP AG") == "sap"

    def test_strips_ltd(self):
        assert _normalize_company("Solutions Ltd.") == "solutions"

    def test_strips_inc(self):
        assert _normalize_company("DataCo Inc.") == "dataco"

    def test_strips_se(self):
        assert _normalize_company("Delivery Hero SE") == "delivery hero"

    def test_strips_punctuation(self):
        assert _normalize_company("Acme & Co.") == "acme co"

    def test_collapses_whitespace(self):
        result = _normalize_company("  Acme  GmbH  ")
        assert result == "acme"


class TestContentHash:
    def test_same_title_company_same_hash(self):
        h1 = _content_hash("Data Engineer", "Acme GmbH")
        h2 = _content_hash("Data Engineer", "Acme GmbH")
        assert h1 == h2

    def test_cross_source_dedup_ignores_gender_marker(self):
        # Same role posted on two sources with/without gender marker
        h1 = _content_hash("Data Engineer (m/w/d)", "WashTec GmbH")
        h2 = _content_hash("Data Engineer", "WashTec")
        assert h1 == h2

    def test_different_company_different_hash(self):
        h1 = _content_hash("Data Engineer", "Acme GmbH")
        h2 = _content_hash("Data Engineer", "Other Corp")
        assert h1 != h2

    def test_different_title_different_hash(self):
        h1 = _content_hash("Data Engineer", "Acme")
        h2 = _content_hash("ML Engineer", "Acme")
        assert h1 != h2

    def test_none_company_handled(self):
        h = _content_hash("Data Engineer", None)
        assert isinstance(h, str) and len(h) == 32


class TestTitleHash:
    def test_same_title_same_hash(self):
        assert _title_hash("Data Engineer") == _title_hash("Data Engineer")

    def test_gender_marker_normalised(self):
        assert _title_hash("Data Engineer (m/w/d)") == _title_hash("Data Engineer")

    def test_different_titles_different_hash(self):
        assert _title_hash("Data Engineer") != _title_hash("ML Engineer")


class TestCompaniesOverlap:
    def test_prefix_match(self):
        # "washtec" is prefix of "washtec cleaning technology"
        assert _companies_overlap("washtec", "washtec cleaning technology") is True

    def test_identical_names(self):
        assert _companies_overlap("acme", "acme") is True

    def test_no_overlap(self):
        assert _companies_overlap("acme", "other corp") is False

    def test_empty_string_no_overlap(self):
        assert _companies_overlap("", "acme") is False
        assert _companies_overlap("acme", "") is False

    def test_order_independent(self):
        a = _companies_overlap("washtec", "washtec cleaning")
        b = _companies_overlap("washtec cleaning", "washtec")
        assert a == b
