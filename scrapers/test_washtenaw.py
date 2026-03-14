"""
Tests for Washtenaw County CivicClerk scraper.

Tests the pure parsing logic WITHOUT hitting the live API.

Run with: cd scrapers && python -m pytest test_washtenaw.py -v
"""

import pytest
from civicclerk_scraper import (
    extract_virtual_url,
    extract_zoom_meeting_id,
    extract_dial_in,
    build_location_string,
    get_issue_tags,
    determine_meeting_type,
    determine_format,
    build_meeting,
    CIVICCLERK_CONFIGS,
)

# Use Washtenaw config for tests
TEST_CONFIG = CIVICCLERK_CONFIGS["washtenaw"]
DEFAULT_ISSUE_TAGS = TEST_CONFIG["default_tags"]


class TestVirtualUrlExtraction:
    """Test extracting Zoom/Teams URLs from free text."""

    def test_extracts_zoom_url(self):
        text = "Zoom link: https://us02web.zoom.us/j/88341991916?pwd=abc123"
        assert extract_virtual_url(text) == "https://us02web.zoom.us/j/88341991916?pwd=abc123"

    def test_extracts_teams_url(self):
        text = "Join at https://teams.microsoft.com/l/meetup-join/abc123"
        assert extract_virtual_url(text) == "https://teams.microsoft.com/l/meetup-join/abc123"

    def test_strips_trailing_punctuation(self):
        text = "Link: https://us02web.zoom.us/j/123456."
        result = extract_virtual_url(text)
        assert not result.endswith(".")

    def test_returns_none_for_no_url(self):
        assert extract_virtual_url("No virtual meeting info here") is None

    def test_returns_none_for_empty(self):
        assert extract_virtual_url("") is None
        assert extract_virtual_url(None) is None


class TestZoomMeetingId:
    """Test extracting Zoom meeting ID from URLs."""

    def test_extracts_from_url(self):
        text = "https://us02web.zoom.us/j/88341991916?pwd=abc"
        assert extract_zoom_meeting_id(text) == "88341991916"

    def test_returns_none_for_no_zoom(self):
        assert extract_zoom_meeting_id("no zoom here") is None

    def test_returns_none_for_empty(self):
        assert extract_zoom_meeting_id(None) is None


class TestDialIn:
    """Test extracting phone dial-in numbers."""

    def test_extracts_phone(self):
        text = "Dial in: +1 929-205-6099"
        result = extract_dial_in(text)
        assert "929" in result

    def test_returns_none_for_no_phone(self):
        assert extract_dial_in("no phone") is None


class TestLocationString:
    """Test building location strings from eventLocation objects."""

    def test_full_location(self):
        loc = {"address1": "555 Towner", "address2": "Room 2123", "city": "Ypsilanti", "state": "MI", "zipCode": "48198"}
        result = build_location_string(loc)
        assert "555 Towner" in result
        assert "Room 2123" in result
        assert "Ypsilanti" in result

    def test_no_address2(self):
        loc = {"address1": "555 Towner", "address2": None, "city": "Ann Arbor", "state": "MI", "zipCode": "48104"}
        result = build_location_string(loc)
        assert "555 Towner" in result
        assert "Ann Arbor" in result

    def test_empty_location(self):
        loc = {"address1": None, "address2": None, "city": None, "state": None, "zipCode": None}
        assert build_location_string(loc) is None

    def test_none_location(self):
        assert build_location_string(None) is None


class TestIssueTags:
    """Test issue tag assignment by category."""

    def test_environmental_council(self):
        tags = get_issue_tags(58, TEST_CONFIG)
        assert "environment" in tags

    def test_dioxane_coalition(self):
        tags = get_issue_tags(64, TEST_CONFIG)
        assert "water_quality" in tags
        assert "pfas" in tags

    def test_water_resources(self):
        tags = get_issue_tags(36, TEST_CONFIG)
        assert "water_quality" in tags

    def test_unknown_category_gets_defaults(self):
        tags = get_issue_tags(9999, TEST_CONFIG)
        assert tags == DEFAULT_ISSUE_TAGS


class TestMeetingType:
    """Test meeting type determination."""

    def test_board_meeting(self):
        assert determine_meeting_type("Board of Commissioners", "") == "board_meeting"

    def test_committee(self):
        assert determine_meeting_type("Environmental Council", "Environmental Council") == "committee_meeting"

    def test_working_session(self):
        assert determine_meeting_type("Board of Commissioners Working Session", "") == "workshop"

    def test_public_hearing(self):
        assert determine_meeting_type("Public Hearing on Water Rates", "") == "public_hearing"


class TestMeetingFormat:
    """Test virtual/hybrid/in-person detection."""

    def test_hybrid_explicit(self):
        assert determine_format("Meeting (In person & virtual)", "https://zoom.us/j/123") == "hybrid"

    def test_virtual_from_name(self):
        assert determine_format("Virtual Meeting", None) == "virtual"

    def test_hybrid_from_url(self):
        # Has URL but no "virtual" in name → hybrid
        assert determine_format("Regular Meeting", "https://zoom.us/j/123") == "hybrid"

    def test_in_person(self):
        assert determine_format("Regular Meeting", None) == "in_person"


class TestBuildMeeting:
    """Test building a full meeting record from an API event."""

    def test_builds_complete_record(self):
        event = {
            "id": 4051,
            "eventName": "Coalition for Action on Remediation of Dioxane Meeting",
            "eventDescription": "Zoom link: https://us02web.zoom.us/j/88341991916?pwd=abc",
            "eventDate": "2026-03-03T10:00:00Z",
            "startDateTime": "2026-03-03T10:00:00Z",
            "categoryId": 64,
            "eventCategoryName": "Coalition for Action on Remediation of Dioxane",
            "isPublished": "Published",
            "eventNotice": "",
            "eventLocation": {
                "address1": "555 Towner",
                "address2": None,
                "city": "Ypsilanti",
                "state": "MI",
                "zipCode": "48198",
            },
            "publishedFiles": [
                {
                    "fileId": 9059,
                    "type": "Agenda",
                    "fileType": 1,
                    "url": "stream/WASHTENAWCOMI/abc123.pdf",
                    "name": "CARD Agenda",
                }
            ],
        }

        meeting = build_meeting(event, TEST_CONFIG)

        assert meeting["source_id"] == "washtenaw-4051"
        assert meeting["source"] == "washtenaw_scraper"
        assert meeting["title"] == "Coalition for Action on Remediation of Dioxane Meeting"
        assert meeting["meeting_date"] == "2026-03-03"
        assert meeting["virtual_url"] == "https://us02web.zoom.us/j/88341991916?pwd=abc"
        assert meeting["virtual_meeting_id"] == "88341991916"
        assert "Ypsilanti" in meeting["location"]
        assert "GetMeetingFileStream(fileId=9059" in meeting["agenda_url"]
        assert "pfas" in meeting["issue_tags"]
        assert meeting["region"] == "Washtenaw County"

    def test_handles_no_virtual_info(self):
        event = {
            "id": 100,
            "eventName": "Board of Commissioners",
            "eventDescription": "",
            "eventDate": "2026-04-01T14:00:00Z",
            "startDateTime": "2026-04-01T14:00:00Z",
            "categoryId": 26,
            "eventCategoryName": "Board of Commissioners",
            "isPublished": "Published",
            "eventNotice": "",
            "eventLocation": {"address1": None, "address2": None, "city": None, "state": None, "zipCode": None},
            "publishedFiles": [],
        }

        meeting = build_meeting(event, TEST_CONFIG)

        assert meeting["virtual_url"] is None
        assert meeting["virtual_meeting_id"] is None
        assert meeting["agenda_url"] is None
        assert meeting["details_url"] == "https://washtenawcomi.portal.civicclerk.com/event/100"

    def test_source_id_is_stable(self):
        """Same event ID always produces the same source_id."""
        event = {
            "id": 4051,
            "eventName": "Test",
            "eventDescription": "",
            "eventDate": "2026-03-03T10:00:00Z",
            "startDateTime": "2026-03-03T10:00:00Z",
            "categoryId": 26,
            "eventCategoryName": "Test",
            "isPublished": "Published",
            "eventNotice": "",
            "eventLocation": {"address1": None, "address2": None, "city": None, "state": None, "zipCode": None},
            "publishedFiles": [],
        }
        m1 = build_meeting(event, TEST_CONFIG)
        m2 = build_meeting(event, TEST_CONFIG)
        assert m1["source_id"] == m2["source_id"] == "washtenaw-4051"
