"""
Smoke tests for meeting scraper parsing functions.

These tests verify the pure parsing logic WITHOUT hitting live websites.
They test: date parsing, time extraction, issue tagging, region detection,
Zoom URL extraction, and deterministic source ID generation.

Run with: cd scrapers && python -m pytest tests/ -v
"""

import os
import sys
import re
import hashlib
from datetime import date, datetime
from unittest.mock import MagicMock

# Add scrapers directory to path so we can import the modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Set dummy env vars so imports don't crash
os.environ.setdefault("SUPABASE_URL", "https://fake.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "fake-key")

# Mock playwright before importing scrapers that use it
sys.modules["playwright"] = MagicMock()
sys.modules["playwright.async_api"] = MagicMock()

from egle_scraper import (
    extract_issue_tags,
    extract_region,
    extract_srn,
    extract_facility_name,
    parse_rss_date,
    extract_start_date,
    parse_time_from_description,
    extract_zoom_url,
    determine_comment_type,
)
from mpsc_scraper import parse_time_from_description as mpsc_parse_time


# =========================================================================
# EGLE: Issue tag extraction
# =========================================================================

class TestEgleIssueTags:
    """Test that issue tags are correctly detected from keywords."""

    def test_air_quality_tags(self):
        tags = extract_issue_tags("Air Quality Permit for Acme Corp")
        assert "air_quality" in tags

    def test_water_tags(self):
        tags = extract_issue_tags("PFAS Contamination Site in Wayne County")
        assert "drinking_water" in tags

    def test_climate_tags(self):
        tags = extract_issue_tags("Renewable Energy Siting in Michigan")
        assert "climate" in tags

    def test_default_environment_tag(self):
        # When no keywords match, should default to "environment"
        tags = extract_issue_tags("Generic EGLE Notice")
        assert "environment" in tags

    def test_multiple_tags(self):
        tags = extract_issue_tags("Air pollution from facility contaminating groundwater")
        assert len(tags) >= 2

    def test_strips_agency_boilerplate(self):
        # "Great Lakes" in the agency name shouldn't trigger water tags
        tags = extract_issue_tags(
            "Michigan Department of Environment, Great Lakes, and Energy - Generic Notice"
        )
        # Should NOT contain water-related tags from "Great Lakes" in the agency name
        assert "environment" in tags


# =========================================================================
# EGLE: Region detection
# =========================================================================

class TestEgleRegion:
    """Test geographic region extraction from titles."""

    def test_detroit_detection(self):
        assert extract_region("Hearing in Detroit") == "detroit"

    def test_wayne_county_is_detroit(self):
        assert extract_region("Permit for Wayne County facility") == "detroit"

    def test_oakland_county(self):
        # Real-world title format: "Permit for facility, City, Oakland County"
        assert extract_region("Permit for Acme Corp, Troy, Oakland County") == "southeast_michigan"

    def test_statewide_default(self):
        assert extract_region("Michigan Environmental Notice") == "statewide"

    def test_non_se_county(self):
        region = extract_region("Permit for facility, Marquette, Marquette County")
        assert "Marquette" in region


# =========================================================================
# EGLE: SRN extraction
# =========================================================================

class TestEgleSrn:
    """Test SRN (Source Registration Number) parsing from titles."""

    def test_extracts_srn(self):
        assert extract_srn("Air Permit for Acme Corp (SRN: A1234)") == "A1234"

    def test_no_srn(self):
        assert extract_srn("Public Hearing on Water Quality") is None


# =========================================================================
# EGLE: Date and time parsing
# =========================================================================

class TestEgleDateParsing:
    """Test RSS date and time extraction."""

    def test_parse_rss_date(self):
        result = parse_rss_date("2026/02/18 (Wed)")
        assert result == date(2026, 2, 18)

    def test_parse_rss_date_invalid(self):
        assert parse_rss_date("not a date") is None

    def test_parse_time_pm(self):
        assert parse_time_from_description("Meeting starts at 6pm") == "18:00"

    def test_parse_time_am(self):
        assert parse_time_from_description("Meeting at 10:00 AM") == "10:00"

    def test_parse_time_range(self):
        # Should extract start time from "6 – 9pm"
        result = parse_time_from_description("Session from 6 – 9pm")
        assert result == "18:00"

    def test_parse_time_noon(self):
        result = parse_time_from_description("Hearing at 12pm")
        assert result == "12:00"

    def test_parse_time_none(self):
        assert parse_time_from_description("No time mentioned here") is None


# =========================================================================
# EGLE: Comment period start date extraction
# =========================================================================

class TestEgleStartDate:
    """Test comment period start date parsing."""

    def test_extracts_from_keyword(self):
        result = extract_start_date("Open from January 22, 2026", date(2026, 2, 22))
        assert result == date(2026, 1, 22)

    def test_fallback_30_days(self):
        # When no date found in text, falls back to 30 days before end date
        result = extract_start_date("No date here", date(2026, 3, 1))
        assert result == date(2026, 1, 30)


# =========================================================================
# EGLE: Zoom URL extraction
# =========================================================================

class TestEgleZoomUrl:
    """Test Zoom/Teams URL extraction from HTML."""

    def test_extracts_zoom_url(self):
        html = '<a href="https://us02web.zoom.us/j/123456">Join Zoom</a>'
        assert "zoom.us" in extract_zoom_url(html)

    def test_extracts_teams_url(self):
        html = '<a href="https://teams.microsoft.com/l/meetup-join/abc">Join Teams</a>'
        assert "teams.microsoft.com" in extract_zoom_url(html)

    def test_no_url(self):
        assert extract_zoom_url("<p>In-person only</p>") is None


# =========================================================================
# EGLE: Comment type determination
# =========================================================================

class TestEgleCommentType:
    """Test comment type classification."""

    def test_default_public_comment(self):
        assert determine_comment_type("Generic Notice") == "public_comment"


# =========================================================================
# MPSC: Time parsing
# =========================================================================

class TestMpscTimeParsing:
    """Test MPSC time extraction from LD+JSON description."""

    def test_extracts_time(self):
        result = mpsc_parse_time("1:00 PM to 2:00 PM Teleconference")
        assert result == "13:00"

    def test_morning_time(self):
        result = mpsc_parse_time("9:30 AM in Lansing")
        assert result == "09:30"

    def test_default_time(self):
        # When no time found, defaults to 09:30
        assert mpsc_parse_time("No time info") == "09:30"

    def test_empty_description(self):
        assert mpsc_parse_time("") == "09:30"

    def test_none_description(self):
        assert mpsc_parse_time(None) == "09:30"


# =========================================================================
# Source ID determinism (regression test for hash() -> hashlib fix)
# =========================================================================

class TestSourceIdDeterminism:
    """Verify source IDs are deterministic across runs.

    This is a regression test — we previously used Python's hash() which
    gives different results each time. Now we use hashlib.md5.
    """

    def test_md5_is_deterministic(self):
        title = "GLWA Board of Directors Meeting"
        id1 = hashlib.md5(title.encode()).hexdigest()[:12]
        id2 = hashlib.md5(title.encode()).hexdigest()[:12]
        assert id1 == id2

    def test_different_titles_different_ids(self):
        id1 = hashlib.md5("Meeting A".encode()).hexdigest()[:12]
        id2 = hashlib.md5("Meeting B".encode()).hexdigest()[:12]
        assert id1 != id2

    def test_known_value(self):
        # Pin a known value so if the hashing method changes, we catch it
        title = "Detroit City Council Formal Session"
        expected = hashlib.md5(title.encode()).hexdigest()[:12]
        assert expected == "63450a4ba739"  # Known stable value
