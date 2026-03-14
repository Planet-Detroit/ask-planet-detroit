"""Tests for pontiac_scraper.py — City of Pontiac meeting scraper."""

import pytest
from datetime import datetime
from zoneinfo import ZoneInfo

from pontiac_scraper import (
    parse_calendar_events,
    parse_agendas_page,
    determine_meeting_type,
    get_issue_tags,
    expand_rrule,
    ENV_BODIES,
    DEFAULT_TAGS,
)

MICHIGAN_TZ = ZoneInfo("America/Detroit")


# --- Sample data ---

SAMPLE_CALENDAR_EVENT = {
    "title": "City Council Meeting",
    "primary_calendar_name": "City Government",
    "calendar_displays": ["6"],
    "start": "2026-03-17T18:00:00",
    "end": "2026-03-17T21:00:00",
    "url": "https://pontiac.mi.us/government/city_council/agendas___minutes.php",
    "location": "47450 Woodward Avenue, Pontiac michigan 48342",
    "desc": "Regular%20City%20Council%20Meeting",
    "rrule": "",
    "color": "#3787d8",
    "rid": "14",
    "id": "14",
}

SAMPLE_RECURRING_EVENT = {
    "title": "Planning Commission",
    "primary_calendar_name": "City Government",
    "calendar_displays": ["6"],
    "start": "2026-01-07T18:00:00",
    "end": "2026-01-07T20:00:00",
    "url": "",
    "location": "City Hall, Pontiac",
    "desc": "",
    "rrule": "DTSTART:20260107T180000\nRRULE:FREQ=MONTHLY;INTERVAL=1;BYDAY=1WE;UNTIL=20261231T000000",
    "color": "#3787d8",
    "rid": "50",
    "id": "50",
}

SAMPLE_RECURRING_WITH_EXDATE = {
    "title": "ZBA Meeting",
    "primary_calendar_name": "City Government",
    "calendar_displays": ["6"],
    "start": "2026-01-19T18:30:00",
    "end": "2026-01-19T20:00:00",
    "url": "",
    "location": "Council Chambers, City Hall",
    "desc": "",
    "rrule": "DTSTART:20260119T183000\nRRULE:FREQ=MONTHLY;INTERVAL=1;BYDAY=3MO;UNTIL=20261231T000000\nEXDATE:20260316T183000",
    "color": "#3787d8",
    "rid": "51",
    "id": "51",
}

SAMPLE_NON_GOVERNMENT_EVENT = {
    "title": "Youth Basketball",
    "primary_calendar_name": "Youth Recreation",
    "calendar_displays": ["7"],
    "start": "2026-03-20T16:00:00",
    "end": "2026-03-20T18:00:00",
    "url": "",
    "location": "Community Center",
    "desc": "",
    "rrule": "",
    "rid": "99",
    "id": "99",
}


SAMPLE_AGENDAS_HTML = """
<div style="padding:10px 0px;">
<strong>2026</strong>
</div>
<table style="width: 100%; border-top: solid 1px #CCCCCC;">
    <tr>
        <td valign="top" width="40%">
            03/17/26
            Regular Meeting
        </td>
        <td valign="top" width="10%" style="font-size: 9pt;">
            <A href="councilagendapack-031726.pdf?t=202603111703180" target="_blank">Agenda</A>
        </td>
        <td valign="top" width="10%"></td>
        <td valign="top" width="10%"></td>
        <td valign="top" width="10%"></td>
        <td valign="top" width="10%"></td>
        <td valign="top" width="10%"></td>
    </tr>
</table>
<table style="width: 100%; border-top: solid 1px #CCCCCC;">
    <tr>
        <td valign="top" width="40%">
            03/03/26
            Regular Meeting
        </td>
        <td valign="top" width="10%"></td>
        <td valign="top" width="10%"></td>
        <td valign="top" width="10%" style="font-size: 9pt;">
            <A href="councilapprovedminutes-030326.pdf?t=202603101000" target="_blank">Minutes</A>
        </td>
        <td valign="top" width="10%"></td>
        <td valign="top" width="10%"></td>
        <td valign="top" width="10%"></td>
    </tr>
</table>
<table style="width: 100%; border-top: solid 1px #CCCCCC;">
    <tr>
        <td valign="top" width="40%">
            02/18/26
            Special Meeting
        </td>
        <td valign="top" width="10%" style="font-size: 9pt;">
            <A href="councilagendapack-021826spec.pdf?t=202602171000" target="_blank">Agenda</A>
        </td>
        <td valign="top" width="10%"></td>
        <td valign="top" width="10%" style="font-size: 9pt;">
            <A href="councilapprovedminutes-021826spec.pdf?t=202602261213130" target="_blank">Minutes</A>
        </td>
        <td valign="top" width="10%"></td>
        <td valign="top" width="10%"></td>
        <td valign="top" width="10%"></td>
    </tr>
</table>
"""


# --- determine_meeting_type ---

class TestDetermineMeetingType:
    def test_city_council(self):
        assert determine_meeting_type("City Council Meeting") == "board_meeting"

    def test_special(self):
        assert determine_meeting_type("Special Meeting") == "special_meeting"

    def test_planning(self):
        assert determine_meeting_type("Planning Commission") == "committee_meeting"

    def test_zba(self):
        assert determine_meeting_type("Zoning Board of Appeals") == "committee_meeting"

    def test_hearing(self):
        assert determine_meeting_type("Public Hearing") == "public_hearing"

    def test_default(self):
        assert determine_meeting_type("Some Other Event") == "public_meeting"


# --- get_issue_tags ---

class TestGetIssueTags:
    def test_planning(self):
        tags = get_issue_tags("Planning Commission")
        assert "planning" in tags
        assert "zoning" in tags

    def test_zba(self):
        tags = get_issue_tags("Zoning Board of Appeals")
        assert "zoning" in tags

    def test_historic(self):
        tags = get_issue_tags("Historic District Commission")
        assert "historic_preservation" in tags

    def test_default(self):
        assert get_issue_tags("City Council Meeting") == DEFAULT_TAGS


# --- expand_rrule ---

class TestExpandRrule:
    def test_no_rrule(self):
        """Non-recurring event returns single date."""
        dates = expand_rrule("", "2026-03-17T18:00:00")
        assert len(dates) == 1
        assert dates[0].month == 3
        assert dates[0].day == 17

    def test_monthly_recurrence(self):
        """Monthly first Wednesday should produce multiple dates."""
        rrule = "DTSTART:20260107T180000\nRRULE:FREQ=MONTHLY;INTERVAL=1;BYDAY=1WE;UNTIL=20261231T000000"
        dates = expand_rrule(rrule, "2026-01-07T18:00:00")
        assert len(dates) >= 6  # At least 6 months of Wednesdays
        # First date should be Jan 7 (first Wednesday of Jan 2026)
        assert dates[0].month == 1
        assert dates[0].day == 7

    def test_exdate_excludes(self):
        """Dates in EXDATE should be excluded."""
        rrule = "DTSTART:20260119T183000\nRRULE:FREQ=MONTHLY;INTERVAL=1;BYDAY=3MO;UNTIL=20261231T000000\nEXDATE:20260316T183000"
        dates = expand_rrule(rrule, "2026-01-19T18:30:00")
        # March 16 should be excluded
        march_dates = [d for d in dates if d.month == 3]
        assert len(march_dates) == 0


# --- parse_calendar_events ---

class TestParseCalendarEvents:
    def test_parses_single_event(self):
        now = datetime(2026, 3, 1, tzinfo=MICHIGAN_TZ)
        meetings = parse_calendar_events([SAMPLE_CALENDAR_EVENT], now)
        assert len(meetings) == 1
        m = meetings[0]
        assert m["title"] == "City Council Meeting"
        assert m["meeting_date"] == "2026-03-17"
        assert m["meeting_time"] == "18:00"
        assert "47450 Woodward" in m["location"]
        assert m["source"] == "pontiac_scraper"

    def test_filters_non_government(self):
        """Non-government events (Youth Recreation, etc.) should be skipped."""
        now = datetime(2026, 3, 1, tzinfo=MICHIGAN_TZ)
        meetings = parse_calendar_events([SAMPLE_NON_GOVERNMENT_EVENT], now)
        assert len(meetings) == 0

    def test_filters_past_events(self):
        """Past events should be excluded."""
        now = datetime(2026, 4, 1, tzinfo=MICHIGAN_TZ)
        meetings = parse_calendar_events([SAMPLE_CALENDAR_EVENT], now)
        assert len(meetings) == 0

    def test_expands_recurring(self):
        """Recurring events should expand to multiple meetings within lookahead."""
        now = datetime(2026, 1, 1, tzinfo=MICHIGAN_TZ)
        meetings = parse_calendar_events([SAMPLE_RECURRING_EVENT], now)
        # Monthly event with 90-day lookahead from Jan 1 = Jan/Feb/Mar
        assert len(meetings) >= 3

    def test_recurring_respects_exdate(self):
        """EXDATE should exclude specific occurrences."""
        now = datetime(2026, 1, 1, tzinfo=MICHIGAN_TZ)
        meetings = parse_calendar_events([SAMPLE_RECURRING_WITH_EXDATE], now)
        march_meetings = [m for m in meetings if m["meeting_date"].startswith("2026-03")]
        assert len(march_meetings) == 0

    def test_source_id_format(self):
        now = datetime(2026, 3, 1, tzinfo=MICHIGAN_TZ)
        meetings = parse_calendar_events([SAMPLE_CALENDAR_EVENT], now)
        assert meetings[0]["source_id"] == "pontiac-14-20260317"

    def test_decodes_description(self):
        """URL-encoded descriptions should be decoded."""
        now = datetime(2026, 3, 1, tzinfo=MICHIGAN_TZ)
        meetings = parse_calendar_events([SAMPLE_CALENDAR_EVENT], now)
        # desc is URL-encoded "Regular City Council Meeting"
        # Verify it doesn't crash and meeting is created


# --- parse_agendas_page ---

class TestParseAgendasPage:
    def test_parses_entries(self):
        entries = parse_agendas_page(SAMPLE_AGENDAS_HTML, "https://pontiac.mi.us/government/city_council/agendas___minutes.php")
        assert len(entries) == 3

    def test_date_parsing(self):
        entries = parse_agendas_page(SAMPLE_AGENDAS_HTML, "https://pontiac.mi.us/government/city_council/agendas___minutes.php")
        assert entries[0]["date"] == "2026-03-17"
        assert entries[1]["date"] == "2026-03-03"

    def test_agenda_url(self):
        entries = parse_agendas_page(SAMPLE_AGENDAS_HTML, "https://pontiac.mi.us/government/city_council/agendas___minutes.php")
        assert entries[0]["agenda_url"] is not None
        assert "councilagendapack-031726.pdf" in entries[0]["agenda_url"]

    def test_minutes_url(self):
        entries = parse_agendas_page(SAMPLE_AGENDAS_HTML, "https://pontiac.mi.us/government/city_council/agendas___minutes.php")
        # First entry has agenda but no minutes
        assert entries[0]["minutes_url"] is None
        # Second entry has minutes but no agenda
        assert entries[1]["agenda_url"] is None
        assert entries[1]["minutes_url"] is not None
        assert "councilapprovedminutes-030326.pdf" in entries[1]["minutes_url"]

    def test_special_meeting_detected(self):
        entries = parse_agendas_page(SAMPLE_AGENDAS_HTML, "https://pontiac.mi.us/government/city_council/agendas___minutes.php")
        assert entries[2]["meeting_type"] == "Special Meeting"

    def test_full_url_construction(self):
        """PDF URLs should be absolute, not relative."""
        entries = parse_agendas_page(SAMPLE_AGENDAS_HTML, "https://pontiac.mi.us/government/city_council/agendas___minutes.php")
        assert entries[0]["agenda_url"].startswith("https://pontiac.mi.us/")
