"""Tests for the Legistar API scraper."""

import pytest
from legistar_scraper import (
    extract_virtual_url,
    extract_meeting_id,
    extract_dial_in,
    determine_meeting_type,
    determine_format,
    generate_source_id,
    get_issue_tags,
    build_meeting,
    LEGISTAR_CONFIGS,
)


# --- Virtual URL extraction ---

class TestExtractVirtualUrl:
    def test_zoom_url(self):
        text = "Join from PC: https://a2gov.zoom.us/j/91585416250?pwd=abc123"
        assert extract_virtual_url(text) == "https://a2gov.zoom.us/j/91585416250?pwd=abc123"

    def test_teams_url(self):
        text = "Join: https://teams.microsoft.com/l/meetup-join/abc"
        assert extract_virtual_url(text) == "https://teams.microsoft.com/l/meetup-join/abc"

    def test_webex_url(self):
        text = "Join: https://cityofdetroit.webex.com/meet/abc123"
        assert extract_virtual_url(text) == "https://cityofdetroit.webex.com/meet/abc123"

    def test_no_url(self):
        assert extract_virtual_url("No virtual info here") is None

    def test_none_input(self):
        assert extract_virtual_url(None) is None

    def test_strips_trailing_punctuation(self):
        text = "Link: https://zoom.us/j/123456789."
        assert extract_virtual_url(text) == "https://zoom.us/j/123456789"


# --- Meeting ID extraction ---

class TestExtractMeetingId:
    def test_zoom_url_meeting_id(self):
        text = "https://a2gov.zoom.us/j/91585416250?pwd=abc"
        assert extract_meeting_id(text) == "91585416250"

    def test_webinar_id_in_text(self):
        text = "Webinar ID: 943 5402 4789"
        assert extract_meeting_id(text) == "94354024789"

    def test_meeting_id_in_text(self):
        text = "Meeting ID: 123 456 7890"
        assert extract_meeting_id(text) == "1234567890"

    def test_zoom_webinar_url(self):
        text = "https://zoom.us/w/91585416250"
        assert extract_meeting_id(text) == "91585416250"

    def test_no_id(self):
        assert extract_meeting_id("No meeting ID") is None

    def test_none_input(self):
        assert extract_meeting_id(None) is None


# --- Dial-in extraction ---

class TestExtractDialIn:
    def test_phone_with_plus(self):
        text = "To speak at public comment call: +1 301 715 8592"
        result = extract_dial_in(text)
        assert result is not None
        assert "301" in result
        assert "715" in result
        assert "8592" in result

    def test_phone_with_dashes(self):
        text = "Call 877-853-5247 to join"
        result = extract_dial_in(text)
        assert result is not None
        assert "877" in result

    def test_no_phone(self):
        assert extract_dial_in("No phone here") is None

    def test_none_input(self):
        assert extract_dial_in(None) is None


# --- Meeting type ---

class TestDetermineMeetingType:
    def test_city_council(self):
        assert determine_meeting_type("City Council") == "board_meeting"

    def test_committee(self):
        assert determine_meeting_type("Finance Committee") == "committee_meeting"

    def test_commission(self):
        assert determine_meeting_type("Environmental Commission") == "committee_meeting"

    def test_advisory(self):
        assert determine_meeting_type("Greenbelt Advisory Commission (GAC)") == "committee_meeting"

    def test_work_session(self):
        assert determine_meeting_type("City Council", "Work Session - broadcast") == "workshop"

    def test_public_hearing(self):
        assert determine_meeting_type("Public Hearing on Zoning") == "public_hearing"

    def test_special_meeting(self):
        assert determine_meeting_type("Finance Committee", "Special Meeting No. 1") == "special_meeting"

    def test_generic(self):
        assert determine_meeting_type("Board of Review") == "public_meeting"


# --- Meeting format ---

class TestDetermineFormat:
    def test_electronic_meeting(self):
        assert determine_format("Electronic Meeting", "") == "virtual"

    def test_physical_location(self):
        assert determine_format("Larcom City Hall, 301 E Huron St", "") == "in_person"

    def test_hybrid_physical_with_zoom(self):
        assert determine_format("Larcom City Hall, 301 E Huron St", "Join zoom meeting") == "hybrid"

    def test_virtual_in_comment(self):
        # No physical address indicators, so "virtually" makes it virtual
        assert determine_format("Some place", "Meeting will be held virtually") == "virtual"

    def test_hybrid_address_plus_virtual(self):
        assert determine_format("City Hall, 100 Main St", "Meeting will be held virtually") == "hybrid"

    def test_empty(self):
        assert determine_format("", "") == "in_person"

    def test_webinar(self):
        assert determine_format("Electronic Meeting", "Webinar ID: 123") == "virtual"


# --- Source ID ---

class TestGenerateSourceId:
    def test_basic(self):
        assert generate_source_id("a2gov", 13927) == "a2gov-13927"

    def test_dwsd(self):
        assert generate_source_id("dwsd", 2264) == "dwsd-2264"


# --- Issue tags ---

class TestGetIssueTags:
    def test_env_body(self):
        config = LEGISTAR_CONFIGS["ann_arbor"]
        tags = get_issue_tags(222, config)
        assert "environment" in tags

    def test_greenbelt(self):
        config = LEGISTAR_CONFIGS["ann_arbor"]
        tags = get_issue_tags(223, config)
        assert "greenbelt" in tags

    def test_default_tags(self):
        config = LEGISTAR_CONFIGS["ann_arbor"]
        tags = get_issue_tags(999, config)
        assert tags == ["government", "ann_arbor"]

    def test_dwsd_all_water(self):
        # DWSD default tags are all water-related since everything is relevant
        config = LEGISTAR_CONFIGS["dwsd"]
        tags = get_issue_tags(999, config)
        assert "water_quality" in tags


# --- Build meeting ---

class TestBuildMeeting:
    """Test building a meeting dict from a Legistar API event."""

    SAMPLE_EVENT = {
        "EventId": 13966,
        "EventGuid": "21377CEA-1214-4B40-9ADB-118D69CEFA16",
        "EventBodyId": 257,
        "EventBodyName": "Airport Advisory Committee",
        "EventDate": "2026-03-18T00:00:00",
        "EventTime": "5:15 PM",
        "EventLocation": "Electronic Meeting",
        "EventComment": "Join from PC, Mac, iPad, or Android: https://a2gov.zoom.us/j/91585416250?pwd=gmguSiEAtP0b7HOkn6RPVZS4dSASJN.1",
        "EventAgendaFile": None,
        "EventMinutesFile": None,
        "EventInSiteURL": "https://a2gov.legistar.com/MeetingDetail.aspx?LEGID=13966&GID=55",
        "EventAgendaStatusId": 10,
        "EventMinutesStatusId": 9,
        "EventVideoStatus": "Public",
        "EventVideoPath": None,
        "EventMedia": None,
        "EventItems": [],
    }

    SAMPLE_CITY_COUNCIL = {
        "EventId": 14146,
        "EventGuid": "ABC123",
        "EventBodyId": 138,
        "EventBodyName": "City Council",
        "EventDate": "2026-03-02T00:00:00",
        "EventTime": "7:00 PM",
        "EventLocation": "Larcom City Hall, 301 E Huron St, Second floor",
        "EventComment": "This meeting will be broadcast live on CTN Cable Channel 16",
        "EventAgendaFile": "https://a2gov.legistar1.com/a2gov/meetings/2026/3/14146_A_City_Council_26-03-02_Meeting_Agenda.pdf",
        "EventMinutesFile": "https://a2gov.legistar1.com/a2gov/meetings/2026/3/14146_M_City_Council_26-03-02_Action_Minutes.pdf",
        "EventInSiteURL": "https://a2gov.legistar.com/MeetingDetail.aspx?LEGID=14146&GID=55",
        "EventItems": [],
    }

    SAMPLE_DWSD = {
        "EventId": 2264,
        "EventGuid": "DEF456",
        "EventBodyId": 100,
        "EventBodyName": "Finance Committee",
        "EventDate": "2026-03-12T00:00:00",
        "EventTime": "1:00 PM",
        "EventLocation": "To attend by phone call one of these numbers:\n+1 301 715 8592",
        "EventComment": "BOWC Finance Committee Special Meeting No. 1",
        "EventAgendaFile": None,
        "EventMinutesFile": None,
        "EventInSiteURL": "https://dwsd.legistar.com/MeetingDetail.aspx?LEGID=2264&GID=267",
        "EventItems": [],
    }

    def test_virtual_meeting(self):
        config = LEGISTAR_CONFIGS["ann_arbor"]
        meeting = build_meeting(self.SAMPLE_EVENT, config)

        assert meeting["title"] == "Airport Advisory Committee"
        assert meeting["meeting_date"] == "2026-03-18"
        assert meeting["meeting_time"] == "17:15"
        assert meeting["virtual_url"] == "https://a2gov.zoom.us/j/91585416250?pwd=gmguSiEAtP0b7HOkn6RPVZS4dSASJN.1"
        assert meeting["virtual_meeting_id"] == "91585416250"
        assert meeting["source"] == "ann_arbor_scraper"
        assert meeting["source_id"] == "a2gov-13966"
        assert meeting["location"] is None  # Virtual meeting, no physical location

    def test_city_council_with_agenda(self):
        config = LEGISTAR_CONFIGS["ann_arbor"]
        meeting = build_meeting(self.SAMPLE_CITY_COUNCIL, config)

        assert meeting["title"] == "City Council"
        assert meeting["meeting_type"] == "board_meeting"
        assert meeting["agenda_url"] == "https://a2gov.legistar1.com/a2gov/meetings/2026/3/14146_A_City_Council_26-03-02_Meeting_Agenda.pdf"
        assert "301 E Huron" in meeting["location"]
        assert meeting["region"] == "Washtenaw County"

    def test_dwsd_phone_in_location(self):
        config = LEGISTAR_CONFIGS["dwsd"]
        meeting = build_meeting(self.SAMPLE_DWSD, config)

        assert meeting["title"] == "Finance Committee"
        assert meeting["source"] == "dwsd_scraper"
        assert meeting["source_id"] == "dwsd-2264"
        assert meeting["virtual_phone"] is not None
        assert "301" in meeting["virtual_phone"]
        # DWSD default tags are all water-related
        assert "water_quality" in meeting["issue_tags"]

    def test_agency_includes_body_name(self):
        config = LEGISTAR_CONFIGS["ann_arbor"]
        meeting = build_meeting(self.SAMPLE_EVENT, config)
        assert "City of Ann Arbor" in meeting["agency"]
        assert "Airport Advisory Committee" in meeting["agency"]

    def test_details_url(self):
        config = LEGISTAR_CONFIGS["ann_arbor"]
        meeting = build_meeting(self.SAMPLE_EVENT, config)
        assert meeting["details_url"] == "https://a2gov.legistar.com/MeetingDetail.aspx?LEGID=13966&GID=55"


# --- Config validation ---

class TestConfigs:
    def test_all_configs_have_required_fields(self):
        required = ["name", "client", "region", "source", "env_bodies", "default_tags"]
        for key, config in LEGISTAR_CONFIGS.items():
            for field in required:
                assert field in config, f"{key} missing {field}"

    def test_ann_arbor_has_env_bodies(self):
        config = LEGISTAR_CONFIGS["ann_arbor"]
        assert len(config["env_bodies"]) > 0

    def test_dwsd_config(self):
        config = LEGISTAR_CONFIGS["dwsd"]
        assert config["client"] == "dwsd"
        assert "water_quality" in config["default_tags"]
