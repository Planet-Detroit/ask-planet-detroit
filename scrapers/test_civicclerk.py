"""Tests for civicclerk_scraper.py — CivicClerk OData API scraper."""

import pytest
from civicclerk_scraper import (
    build_meeting,
    determine_meeting_type,
    get_issue_tags,
    extract_virtual_url,
    extract_zoom_meeting_id,
    extract_dial_in,
    build_location_string,
    CIVICCLERK_CONFIGS,
)


# --- Config validation ---

class TestConfigs:
    def test_all_configs_have_required_fields(self):
        for key, config in CIVICCLERK_CONFIGS.items():
            assert "name" in config, f"{key} missing name"
            assert "api_base" in config, f"{key} missing api_base"
            assert "portal_base" in config, f"{key} missing portal_base"
            assert "source" in config, f"{key} missing source"
            assert "region" in config, f"{key} missing region"

    def test_api_base_urls_are_https(self):
        for key, config in CIVICCLERK_CONFIGS.items():
            assert config["api_base"].startswith("https://"), f"{key} api_base not HTTPS"


# --- Agenda URL construction ---

class TestBuildMeetingAgendaUrl:
    """Verify agenda_url uses API file stream, not portal SPA."""

    SAMPLE_CONFIG = {
        "name": "Test County",
        "api_base": "https://testcomi.api.civicclerk.com/v1",
        "portal_base": "https://testcomi.portal.civicclerk.com",
        "site_key": "TESTCOMI",
        "region": "Test County",
        "source": "test_scraper",
        "env_categories": {},
        "default_tags": ["government"],
    }

    def _make_event(self, published_files=None):
        return {
            "id": 12345,
            "eventName": "Board Meeting",
            "eventCategoryName": "Board of Commissioners",
            "categoryId": 1,
            "eventDate": "2026-03-18T14:00:00Z",
            "eventDescription": "",
            "eventNotice": "",
            "eventLocation": None,
            "isPublished": "Published",
            "publishedFiles": published_files or [],
        }

    def test_agenda_url_uses_api_file_stream(self):
        """Agenda URL should use API endpoint, not portal URL."""
        event = self._make_event(published_files=[
            {"fileType": 1, "type": "Agenda", "fileId": 9999, "url": "stream/TESTCOMI/abc.pdf"}
        ])
        meeting = build_meeting(event, self.SAMPLE_CONFIG)
        assert meeting["agenda_url"] == "https://testcomi.api.civicclerk.com/v1/Meetings/GetMeetingFileStream(fileId=9999,plainText=false)"
        assert "portal" not in meeting["agenda_url"]

    def test_minutes_url_uses_api_file_stream(self):
        """Minutes URL should also use API endpoint."""
        event = self._make_event(published_files=[
            {"fileType": 4, "type": "Minutes", "fileId": 8888, "url": "stream/TESTCOMI/def.pdf"}
        ])
        meeting = build_meeting(event, self.SAMPLE_CONFIG)
        assert meeting["minutes_url"] == "https://testcomi.api.civicclerk.com/v1/Meetings/GetMeetingFileStream(fileId=8888,plainText=false)"

    def test_no_files_gives_none(self):
        event = self._make_event(published_files=[])
        meeting = build_meeting(event, self.SAMPLE_CONFIG)
        assert meeting["agenda_url"] is None
        assert meeting["minutes_url"] is None

    def test_file_without_id_gives_none(self):
        """If fileId is missing, agenda_url should be None."""
        event = self._make_event(published_files=[
            {"fileType": 1, "type": "Agenda", "url": "stream/TESTCOMI/abc.pdf"}
        ])
        meeting = build_meeting(event, self.SAMPLE_CONFIG)
        assert meeting["agenda_url"] is None


# --- Meeting type ---

class TestDetermineMeetingType:
    def test_board_of_commissioners(self):
        assert determine_meeting_type("Full Board Meeting", "Board of Commissioners") == "board_meeting"

    def test_committee(self):
        assert determine_meeting_type("Committee Meeting", "Environmental Council") == "committee_meeting"

    def test_hearing(self):
        assert determine_meeting_type("Public Hearing on Zoning", "") == "public_hearing"


# --- Virtual meeting extraction ---

class TestExtractVirtualUrl:
    def test_zoom_url(self):
        text = "Join us at https://us02web.zoom.us/j/12345 for the meeting"
        assert "zoom.us" in extract_virtual_url(text)

    def test_teams_url(self):
        text = "Join at https://teams.microsoft.com/l/meetup-join/abc"
        assert "teams.microsoft.com" in extract_virtual_url(text)

    def test_no_url(self):
        assert extract_virtual_url("No virtual meeting info") is None


class TestExtractZoomId:
    def test_from_url(self):
        text = "https://us02web.zoom.us/j/85846903626"
        assert extract_zoom_meeting_id(text) == "85846903626"

    def test_no_id(self):
        assert extract_zoom_meeting_id("No zoom here") is None


class TestBuildLocationString:
    def test_none(self):
        assert build_location_string(None) is None

    def test_dict_location(self):
        loc = {"address1": "123 Main St", "city": "Detroit", "state": "MI"}
        result = build_location_string(loc)
        assert "123 Main St" in result
