"""Tests for the Michigan Legislature committee meeting scraper."""

import pytest
from mi_legislature_scraper import (
    parse_rss,
    parse_title,
    parse_ics,
    extract_agenda_bills,
    get_issue_tags,
    build_meeting,
    DEFAULT_TAGS,
)


# --- RSS Parsing ---

SAMPLE_RSS = """<?xml version="1.0"?>
<rss version="2.0">
  <channel>
    <title>Michigan Legislature Bill Updates</title>
    <item>
      <title>House Meeting - Energy 3/17/2026 09:00 AM</title>
      <link>https://legislature.mi.gov/Committees/Meeting?meetingID=5848</link>
      <description>House Energy - 3/17/2026 09:00 AM - New</description>
      <guid>5848</guid>
    </item>
    <item>
      <title>Senate Meeting - Appropriations Subcommittee on DHHS 3/17/2026 03:00 PM</title>
      <link>https://legislature.mi.gov/Committees/Meeting?meetingID=5855</link>
      <description>Senate Appropriations Subcommittee on DHHS - 3/17/2026 03:00 PM - New</description>
      <guid>5855</guid>
    </item>
  </channel>
</rss>"""


class TestParseRss:
    def test_parses_entries(self):
        entries = parse_rss(SAMPLE_RSS)
        assert len(entries) == 2

    def test_first_entry_fields(self):
        entries = parse_rss(SAMPLE_RSS)
        e = entries[0]
        assert e["meeting_id"] == "5848"
        assert e["chamber"] == "House"
        assert e["committee"] == "Energy"
        assert e["date_str"] == "3/17/2026"
        assert e["time_str"] == "09:00 AM"

    def test_second_entry_committee(self):
        entries = parse_rss(SAMPLE_RSS)
        e = entries[1]
        assert e["committee"] == "Appropriations Subcommittee on DHHS"
        assert e["chamber"] == "Senate"


# --- Title Parsing ---

class TestParseTitle:
    def test_house_meeting(self):
        chamber, committee, date, time = parse_title("House Meeting - Energy 3/17/2026 09:00 AM")
        assert chamber == "House"
        assert committee == "Energy"
        assert date == "3/17/2026"
        assert time == "09:00 AM"

    def test_senate_meeting(self):
        chamber, committee, date, time = parse_title(
            "Senate Meeting - Natural Resources and Agriculture 3/18/2026 10:30 AM"
        )
        assert chamber == "Senate"
        assert committee == "Natural Resources and Agriculture"
        assert date == "3/18/2026"
        assert time == "10:30 AM"

    def test_subcommittee(self):
        chamber, committee, date, time = parse_title(
            "Senate Meeting - Appropriations Subcommittee on DHHS 3/17/2026 03:00 PM"
        )
        assert committee == "Appropriations Subcommittee on DHHS"
        assert time == "03:00 PM"

    def test_pm_time(self):
        _, _, _, time = parse_title("House Meeting - Rules 3/17/2026 3:30 PM")
        assert time == "3:30 PM"


# --- ICS Parsing ---

SAMPLE_ICS = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//hacksw/handcal//NONSGML v1.0//EN
BEGIN:VEVENT
UID:00000000-0000-0000-0000-000000000000
DTSTAMP:20260317T090000
DTSTART:20260317T090000
DTEND:20260317T100000
SUMMARY:Energy
LOCATION:Room 519, House Office Building
DESCRIPTION:COMMITTEE:Energy\\nLOCATION:Room 519, House Office Building\\nDATTE:03/17/2026\\nTIME:09:00 AM\\nCLERK:517-373-0350\\n\\nAGENDA:HB 5710 (Wendzel) Energy: electricity; HB 5711 (Outman) Energy: alternative sources.
END:VEVENT
END:VCALENDAR"""


class TestParseIcs:
    def test_location(self):
        result = parse_ics(SAMPLE_ICS)
        assert result["location"] == "Room 519, House Office Building"

    def test_clerk_phone(self):
        result = parse_ics(SAMPLE_ICS)
        assert result["clerk_phone"] == "517-373-0350"

    def test_agenda_text(self):
        result = parse_ics(SAMPLE_ICS)
        assert "HB 5710" in result["agenda_text"]
        assert "HB 5711" in result["agenda_text"]

    def test_empty_ics(self):
        result = parse_ics("")
        assert result["location"] is None
        assert result["clerk_phone"] is None


# --- Bill Extraction ---

class TestExtractAgendaBills:
    def test_house_bills(self):
        text = "HB 5710 (Wendzel) Energy: electricity; HB 5711 (Outman) Energy: alt."
        bills = extract_agenda_bills(text)
        assert "HB 5710" in bills
        assert "HB 5711" in bills

    def test_senate_bills(self):
        text = "SB 123 (Smith) Environment; SB 456 (Jones) Water."
        bills = extract_agenda_bills(text)
        assert "SB 123" in bills
        assert "SB 456" in bills

    def test_no_bills(self):
        assert extract_agenda_bills("No bills here") == []

    def test_none(self):
        assert extract_agenda_bills(None) == []


# --- Issue Tags ---

class TestGetIssueTags:
    def test_energy_committee(self):
        tags = get_issue_tags("Energy")
        assert "energy" in tags
        assert "climate" in tags

    def test_natural_resources(self):
        tags = get_issue_tags("Natural Resources and Agriculture")
        assert "environment" in tags
        assert "natural_resources" in tags

    def test_energy_and_environment_senate(self):
        tags = get_issue_tags("Energy and Environment")
        assert "environment" in tags

    def test_generic_committee(self):
        tags = get_issue_tags("Finance")
        assert tags == DEFAULT_TAGS

    def test_transportation(self):
        tags = get_issue_tags("Transportation and Infrastructure")
        assert "infrastructure" in tags


# --- Build Meeting ---

class TestBuildMeeting:
    def test_basic_meeting(self):
        entry = {
            "meeting_id": "5848",
            "title": "House Meeting - Energy 3/17/2026 09:00 AM",
            "chamber": "House",
            "committee": "Energy",
            "date_str": "3/17/2026",
            "time_str": "09:00 AM",
            "link": "https://legislature.mi.gov/Committees/Meeting?meetingID=5848",
            "description": "House Energy - 3/17/2026 09:00 AM - New",
        }
        ics_data = {
            "location": "Room 519, House Office Building",
            "agenda_text": "HB 5710 (Wendzel) Energy",
            "clerk_phone": "517-373-0350",
        }

        meeting = build_meeting(entry, ics_data)

        assert meeting["title"] == "House Energy"
        assert meeting["agency"] == "Michigan House"
        assert meeting["meeting_date"] == "2026-03-17"
        assert meeting["meeting_time"] == "09:00"
        assert meeting["location"] == "Room 519, House Office Building"
        assert meeting["source"] == "mi_legislature_scraper"
        assert meeting["source_id"] == "mileg-5848"
        assert meeting["region"] == "Michigan"
        assert "energy" in meeting["issue_tags"]

    def test_details_url(self):
        entry = {
            "meeting_id": "5855",
            "title": "Senate Meeting - DHHS 3/17/2026 03:00 PM",
            "chamber": "Senate",
            "committee": "DHHS",
            "date_str": "3/17/2026",
            "time_str": "03:00 PM",
            "link": "",
            "description": "",
        }
        meeting = build_meeting(entry, {})
        assert "5855" in meeting["details_url"]

    def test_no_virtual(self):
        entry = {
            "meeting_id": "1",
            "title": "House Meeting - Rules 3/17/2026 09:00 AM",
            "chamber": "House",
            "committee": "Rules",
            "date_str": "3/17/2026",
            "time_str": "09:00 AM",
            "link": "",
            "description": "",
        }
        meeting = build_meeting(entry, {})
        assert meeting["virtual_url"] is None
        assert meeting["meeting_type"] == "committee_meeting"
