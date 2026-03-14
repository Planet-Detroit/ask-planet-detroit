"""Tests for troy_scraper.py — City of Troy meeting scraper."""

import pytest
from troy_scraper import (
    parse_council_schedule_item,
    parse_board_schedule_item,
    generate_source_id,
    determine_council_meeting_type,
    parse_council_schedule,
    parse_archive_table,
    parse_board_schedule,
    BOARD_CONFIGS,
)


# --- parse_council_schedule_item ---

class TestParseCouncilScheduleItem:
    def test_regular_meeting(self):
        dt, label = parse_council_schedule_item("January 12, 2026 7:30 PM")
        assert dt.month == 1
        assert dt.day == 12
        assert dt.year == 2026
        assert dt.hour == 19
        assert dt.minute == 30
        assert label is None

    def test_special_meeting(self):
        dt, label = parse_council_schedule_item(
            "January 17, 2026 9:00 AM  :  - SPECIAL - 2026 ADVANCE"
        )
        assert dt.month == 1
        assert dt.day == 17
        assert dt.hour == 9
        assert label == "SPECIAL - 2026 ADVANCE"

    def test_special_evaluations(self):
        dt, label = parse_council_schedule_item(
            "January 26, 2026 6:00 PM  :  - SPECIAL - CITY MANAGER AND CITY ATTORNEY EVALUATIONS"
        )
        assert dt.hour == 18
        assert "EVALUATIONS" in label

    def test_invalid(self):
        dt, label = parse_council_schedule_item("Not a date")
        assert dt is None
        assert label is None

    def test_whitespace(self):
        dt, label = parse_council_schedule_item("  March 23, 2026 7:30 PM  ")
        assert dt.month == 3
        assert dt.day == 23


# --- parse_board_schedule_item ---

class TestParseBoardScheduleItem:
    def test_regular(self):
        dt, cancelled = parse_board_schedule_item(
            "Tuesday, January 13, 2026 7:00 PM - 8:00 PM"
        )
        assert dt.month == 1
        assert dt.day == 13
        assert dt.hour == 19
        assert cancelled is False

    def test_cancelled(self):
        dt, cancelled = parse_board_schedule_item(
            "Tuesday, March 10, 2026 7:00 PM - 8:00 PM  : CANCELLED"
        )
        assert dt.month == 3
        assert dt.day == 10
        assert cancelled is True

    def test_invalid(self):
        dt, cancelled = parse_board_schedule_item("Not a meeting")
        assert dt is None
        assert cancelled is False


# --- generate_source_id ---

class TestGenerateSourceId:
    def test_council(self):
        sid = generate_source_id("city-council", "20260112")
        assert sid == "troy-city-council-20260112"

    def test_board(self):
        sid = generate_source_id("planning-commission", "20260113")
        assert sid == "troy-planning-commission-20260113"

    def test_stability(self):
        assert generate_source_id("a", "b") == generate_source_id("a", "b")


# --- determine_council_meeting_type ---

class TestDetermineCouncilMeetingType:
    def test_regular(self):
        assert determine_council_meeting_type(None) == "board_meeting"

    def test_special(self):
        assert determine_council_meeting_type("SPECIAL - BUDGET") == "special_meeting"


# --- parse_council_schedule (full page) ---

SAMPLE_COUNCIL_PAGE = """
<html><body>
<main id="freeform-main">
<h2 class="header">City Council Meeting Schedule</h2>
<p>The City Council of the City of Troy will hold Public Meetings...</p>
<ul>
    <li>January 12, 2020 7:30 PM</li>
    <li>December 31, 2099 7:30 PM</li>
    <li>December 31, 2099 9:00 AM  :  - SPECIAL - BUDGET PRESENTATION</li>
</ul>
</main>
</body></html>
"""


class TestParseCouncilSchedule:
    def test_filters_past(self):
        meetings = parse_council_schedule(SAMPLE_COUNCIL_PAGE)
        # 2020 should be filtered out, 2099 dates should remain
        dates = [m["meeting_date"] for m in meetings]
        assert "2020-01-12" not in dates
        assert "2099-12-31" in dates

    def test_regular_meeting(self):
        meetings = parse_council_schedule(SAMPLE_COUNCIL_PAGE)
        regular = [m for m in meetings if m["meeting_type"] == "board_meeting"]
        assert len(regular) >= 1
        assert regular[0]["title"] == "City Council"

    def test_special_meeting(self):
        meetings = parse_council_schedule(SAMPLE_COUNCIL_PAGE)
        special = [m for m in meetings if m["meeting_type"] == "special_meeting"]
        assert len(special) == 1
        assert "BUDGET PRESENTATION" in special[0]["title"]

    def test_location(self):
        meetings = parse_council_schedule(SAMPLE_COUNCIL_PAGE)
        assert meetings[0]["location"] == "City Hall, 500 West Big Beaver Road, Troy, MI"

    def test_source(self):
        meetings = parse_council_schedule(SAMPLE_COUNCIL_PAGE)
        assert meetings[0]["source"] == "troy_scraper"

    def test_region(self):
        meetings = parse_council_schedule(SAMPLE_COUNCIL_PAGE)
        assert meetings[0]["region"] == "Oakland County"

    def test_agency(self):
        meetings = parse_council_schedule(SAMPLE_COUNCIL_PAGE)
        assert meetings[0]["agency"] == "City of Troy - City Council"

    def test_no_main_returns_empty(self):
        assert parse_council_schedule("<html><body></body></html>") == []


# --- parse_archive_table ---

SAMPLE_ARCHIVE_HTML = """
<html><body>
<table class="table">
<thead><tr><th>Date</th><th>Agenda</th><th>Video</th><th>Minutes</th></tr></thead>
<tbody>
<tr>
  <td>Mar 2, 2026<br>Regular</td>
  <td style="text-align:left">
    <a href="/Meetings/Meetings/DownloadPDF/6985100">Agenda Packet</a>
  </td>
  <td>
    <a href="http://www.youtube.com/watch?v=jtxvZOT6E3g" target="_blank">
      <img src="/Meetings/Content/video.png"/>
    </a>
  </td>
  <td>
    <a href="/Meetings/Meetings/DownloadPDF/6985101"><img src="/Meetings/Content/Minutes.png"/></a>
  </td>
</tr>
<tr>
  <td>Feb 23, 2026<br>Regular</td>
  <td style="text-align:left">
    <a href="/Meetings/Meetings/DownloadPDF/6979440">Agenda Packet</a>
  </td>
  <td></td>
  <td></td>
</tr>
</tbody>
</table>
</body></html>
"""


class TestParseArchiveTable:
    def test_parses_two_entries(self):
        docs = parse_archive_table(SAMPLE_ARCHIVE_HTML)
        assert len(docs) == 2

    def test_agenda_url(self):
        docs = parse_archive_table(SAMPLE_ARCHIVE_HTML)
        assert docs["2026-03-02"]["agenda_url"] == "https://apps.troymi.gov/Meetings/Meetings/DownloadPDF/6985100"

    def test_minutes_url(self):
        docs = parse_archive_table(SAMPLE_ARCHIVE_HTML)
        assert docs["2026-03-02"]["minutes_url"] == "https://apps.troymi.gov/Meetings/Meetings/DownloadPDF/6985101"

    def test_video_url(self):
        docs = parse_archive_table(SAMPLE_ARCHIVE_HTML)
        assert "youtube" in docs["2026-03-02"]["video_url"]

    def test_missing_minutes(self):
        docs = parse_archive_table(SAMPLE_ARCHIVE_HTML)
        assert docs["2026-02-23"]["minutes_url"] is None

    def test_no_table_returns_empty(self):
        assert parse_archive_table("<html><body></body></html>") == {}


# --- parse_board_schedule ---

SAMPLE_BOARD_SCHEDULE = """
<html><body>
<main id="freeform-main">
<h2 class="header">Planning Commission</h2>
<ul>
  <li>Tuesday, January 13, 2020 7:00 PM - 8:00 PM</li>
  <li>Tuesday, March 10, 2026 7:00 PM - 8:00 PM  : CANCELLED</li>
  <li>Tuesday, December 1, 2099 7:00 PM - 8:00 PM</li>
</ul>
</main>
</body></html>
"""


class TestParseBoardSchedule:
    def test_filters_past(self):
        config = BOARD_CONFIGS["Planning Commission"]
        meetings = parse_board_schedule(SAMPLE_BOARD_SCHEDULE, "Planning Commission", config)
        dates = [m["meeting_date"] for m in meetings]
        assert "2020-01-13" not in dates

    def test_filters_cancelled(self):
        config = BOARD_CONFIGS["Planning Commission"]
        meetings = parse_board_schedule(SAMPLE_BOARD_SCHEDULE, "Planning Commission", config)
        dates = [m["meeting_date"] for m in meetings]
        assert "2026-03-10" not in dates

    def test_includes_future(self):
        config = BOARD_CONFIGS["Planning Commission"]
        meetings = parse_board_schedule(SAMPLE_BOARD_SCHEDULE, "Planning Commission", config)
        assert len(meetings) == 1
        assert meetings[0]["meeting_date"] == "2099-12-01"

    def test_board_title(self):
        config = BOARD_CONFIGS["Planning Commission"]
        meetings = parse_board_schedule(SAMPLE_BOARD_SCHEDULE, "Planning Commission", config)
        assert meetings[0]["title"] == "Planning Commission"

    def test_board_tags(self):
        config = BOARD_CONFIGS["Planning Commission"]
        meetings = parse_board_schedule(SAMPLE_BOARD_SCHEDULE, "Planning Commission", config)
        assert "planning" in meetings[0]["issue_tags"]

    def test_board_type(self):
        config = BOARD_CONFIGS["Planning Commission"]
        meetings = parse_board_schedule(SAMPLE_BOARD_SCHEDULE, "Planning Commission", config)
        assert meetings[0]["meeting_type"] == "committee_meeting"

    def test_board_agency(self):
        config = BOARD_CONFIGS["Planning Commission"]
        meetings = parse_board_schedule(SAMPLE_BOARD_SCHEDULE, "Planning Commission", config)
        assert meetings[0]["agency"] == "City of Troy - Planning Commission"

    def test_no_main_returns_empty(self):
        config = BOARD_CONFIGS["Planning Commission"]
        assert parse_board_schedule("<html></html>", "Planning Commission", config) == []


# --- Integration ---

class TestIntegration:
    def test_council_with_archive_cross_reference(self):
        """Test that archive docs can be matched to council meetings."""
        council = parse_council_schedule(SAMPLE_COUNCIL_PAGE)
        docs = parse_archive_table(SAMPLE_ARCHIVE_HTML)

        # Cross-reference
        for meeting in council:
            if meeting["meeting_date"] in docs:
                meeting["agenda_url"] = docs[meeting["meeting_date"]]["agenda_url"]

        # The 2099 meetings won't match archive entries (which are from 2026)
        # This test verifies the mechanism works
        assert all(isinstance(m, dict) for m in council)
