"""Tests for the eSCRIBE Meetings API scraper."""

import pytest
from escribemeetings_scraper import (
    extract_virtual_url,
    extract_meeting_id,
    extract_dial_in,
    get_issue_tags,
    determine_meeting_type,
    parse_location,
    build_meeting,
    ESCRIBEMEETINGS_CONFIGS,
)


# --- Location parsing ---

class TestParseLocation:
    def test_html_breaks(self):
        desc = "City Hall Commission Chambers Room 121   <br/>203 South Troy Street<br/>Royal Oak, MI  48067"
        result = parse_location(desc)
        assert "203 South Troy Street" in result
        assert "Royal Oak" in result

    def test_empty(self):
        assert parse_location("") is None
        assert parse_location(None) is None

    def test_single_line(self):
        assert parse_location("Room 100") == "Room 100"


# --- Meeting type ---

class TestDetermineMeetingType:
    def test_city_commission(self):
        assert determine_meeting_type("City Commission") == "board_meeting"

    def test_planning_commission(self):
        assert determine_meeting_type("Planning Commission") == "committee_meeting"

    def test_dda(self):
        assert determine_meeting_type("DDA") == "public_meeting"

    def test_special_meeting(self):
        assert determine_meeting_type("Special City Commission Meeting") == "special_meeting"


# --- Issue tags ---

class TestGetIssueTags:
    def test_parks(self):
        config = ESCRIBEMEETINGS_CONFIGS["royal_oak"]
        tags = get_issue_tags("Parks and Recreation Advisory Board", config)
        assert "parks" in tags

    def test_planning(self):
        config = ESCRIBEMEETINGS_CONFIGS["royal_oak"]
        tags = get_issue_tags("Planning Commission", config)
        assert "planning" in tags

    def test_default(self):
        config = ESCRIBEMEETINGS_CONFIGS["royal_oak"]
        tags = get_issue_tags("City Commission", config)
        assert tags == ["government", "royal_oak"]


# --- Build meeting ---

class TestBuildMeeting:
    SAMPLE_EVENT = {
        "ID": "11fa0427-9b75-4afb-a1af-0ee96c31e81c",
        "MeetingName": "DDA",
        "StartDate": "2026/03/18 16:00:00",
        "FormattedStart": "Wednesday, March 18, 2026 @ 4:00 PM",
        "Description": "City Hall Commission Chambers Room 121   <br/>203 South Troy Street<br/>Royal Oak, MI  48067",
        "Location": "City Hall Commission Chambers Room 121",
        "Url": "https://pub-royaloak.escribemeetings.com/MeetingsCalendarView.aspx/Meeting?Id=11fa0427-9b75-4afb-a1af-0ee96c31e81c",
        "MeetingType": "DDA",
        "HasAgenda": True,
        "MeetingDocumentLink": [
            {
                "Format": ".pdf",
                "Title": "Agenda (PDF)",
                "Type": "Agenda",
                "Url": "FileStream.ashx?DocumentId=11748",
            },
            {
                "Format": "HTML",
                "Title": "Agenda (HTML)",
                "Type": "Agenda",
                "Url": "Meeting.aspx?Id=11fa0427&Agenda=Agenda&lang=English",
            },
        ],
        "MeetingPassed": False,
        "AllowPublicComments": False,
    }

    def test_basic_fields(self):
        config = ESCRIBEMEETINGS_CONFIGS["royal_oak"]
        meeting = build_meeting(self.SAMPLE_EVENT, config)

        assert meeting["title"] == "DDA"
        assert meeting["agency"] == "City of Royal Oak"
        assert meeting["meeting_date"] == "2026-03-18"
        assert meeting["meeting_time"] == "16:00"
        assert meeting["source"] == "royal_oak_scraper"
        assert meeting["region"] == "Oakland County"

    def test_source_id(self):
        config = ESCRIBEMEETINGS_CONFIGS["royal_oak"]
        meeting = build_meeting(self.SAMPLE_EVENT, config)
        assert meeting["source_id"].startswith("escribemeetings-")
        assert "11fa0427" in meeting["source_id"]

    def test_agenda_url_pdf(self):
        config = ESCRIBEMEETINGS_CONFIGS["royal_oak"]
        meeting = build_meeting(self.SAMPLE_EVENT, config)
        assert meeting["agenda_url"] is not None
        assert "FileStream.ashx" in meeting["agenda_url"]
        assert meeting["agenda_url"].startswith("https://pub-royaloak")

    def test_location_from_description(self):
        config = ESCRIBEMEETINGS_CONFIGS["royal_oak"]
        meeting = build_meeting(self.SAMPLE_EVENT, config)
        assert "203 South Troy Street" in meeting["location"]
        assert "Royal Oak" in meeting["location"]

    def test_details_url(self):
        config = ESCRIBEMEETINGS_CONFIGS["royal_oak"]
        meeting = build_meeting(self.SAMPLE_EVENT, config)
        assert "11fa0427" in meeting["details_url"]

    def test_no_agenda(self):
        event = dict(self.SAMPLE_EVENT)
        event["MeetingDocumentLink"] = []
        event["HasAgenda"] = False
        config = ESCRIBEMEETINGS_CONFIGS["royal_oak"]
        meeting = build_meeting(event, config)
        assert meeting["agenda_url"] is None


# --- Config validation ---

class TestConfigs:
    def test_all_configs_have_required_fields(self):
        required = ["name", "base_url", "region", "source", "env_committees", "default_tags"]
        for key, config in ESCRIBEMEETINGS_CONFIGS.items():
            for field in required:
                assert field in config, f"{key} missing {field}"

    def test_royal_oak(self):
        config = ESCRIBEMEETINGS_CONFIGS["royal_oak"]
        assert "royaloak" in config["base_url"]
        assert config["region"] == "Oakland County"
