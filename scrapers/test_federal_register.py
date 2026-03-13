"""Tests for Federal Register scraper."""

import pytest
from federal_register_scraper import (
    is_michigan_relevant,
    extract_issue_tags,
    build_comment_period,
)


class TestMichiganRelevance:
    def test_detects_michigan_keyword(self):
        doc = {"title": "EPA Notice for Michigan Water Standards", "abstract": ""}
        assert is_michigan_relevant(doc)

    def test_detects_great_lakes(self):
        doc = {"title": "Ballast Water Standards", "abstract": "Impacts Great Lakes shipping"}
        assert is_michigan_relevant(doc)

    def test_detects_pfas(self):
        doc = {"title": "National PFAS Drinking Water Standard", "abstract": "New limits on PFAS"}
        assert is_michigan_relevant(doc)

    def test_detects_line_5(self):
        doc = {"title": "Pipeline Safety Regulations", "abstract": "Including Line 5 in Straits of Mackinac"}
        assert is_michigan_relevant(doc)

    def test_rejects_irrelevant(self):
        doc = {"title": "California Air Quality Standards", "abstract": "Los Angeles basin emissions"}
        assert not is_michigan_relevant(doc)

    def test_case_insensitive(self):
        doc = {"title": "great lakes water quality", "abstract": ""}
        assert is_michigan_relevant(doc)


class TestIssueTagExtraction:
    def test_epa_agency_tags(self):
        tags = extract_issue_tags("Test", "", [{"slug": "environmental-protection-agency"}])
        assert "environment" in tags
        assert "epa" in tags

    def test_keyword_tags(self):
        tags = extract_issue_tags("PFAS Drinking Water Limits", "New standards for PFAS contamination", [])
        assert "pfas" in tags
        assert "drinking_water" in tags

    def test_default_tag(self):
        tags = extract_issue_tags("Generic Notice", "", [])
        assert "environment" in tags

    def test_combined_agency_and_keyword(self):
        tags = extract_issue_tags(
            "Great Lakes Pipeline Review",
            "Pipeline safety in the Great Lakes region",
            [{"slug": "federal-energy-regulatory-commission"}]
        )
        assert "energy" in tags
        assert "great_lakes" in tags


class TestBuildCommentPeriod:
    def test_builds_complete_record(self):
        doc = {
            "title": "EPA PFAS Drinking Water Standard",
            "abstract": "Proposed limits on PFAS in drinking water",
            "document_number": "2026-12345",
            "type": "PROPOSED_RULE",
            "publication_date": "2026-03-01",
            "comments_close_on": "2026-04-15",
            "html_url": "https://federalregister.gov/d/2026-12345",
            "agencies": [{"name": "Environmental Protection Agency", "slug": "environmental-protection-agency"}],
        }
        result = build_comment_period(doc)
        assert result["source"] == "federal_register"
        assert result["source_id"] == "fed-reg-2026-12345"
        assert result["agency"] == "Environmental Protection Agency"
        assert result["end_date"] == "2026-04-15"
        assert result["start_date"] == "2026-03-01"
        assert result["status"] == "open"
        assert "pfas" in result["issue_tags"]

    def test_handles_missing_fields(self):
        doc = {
            "title": "Some Notice",
            "abstract": "",
            "document_number": "2026-99999",
        }
        result = build_comment_period(doc)
        assert result["source_id"] == "fed-reg-2026-99999"
        assert result["agency"] == "Federal Government"
        assert result["status"] == "open"

    def test_stable_source_id(self):
        doc = {"title": "Test", "document_number": "2026-11111"}
        r1 = build_comment_period(doc)
        r2 = build_comment_period(doc)
        assert r1["source_id"] == r2["source_id"]
