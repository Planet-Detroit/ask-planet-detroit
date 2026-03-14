"""Tests for clinton_twp_scraper.py — Clinton Township meeting scraper."""

import pytest
from clinton_twp_scraper import (
    parse_event_title,
    parse_date_time_text,
    extract_event_id,
    is_canceled,
    determine_meeting_type,
    get_issue_tags,
    parse_calendar_list,
    parse_detail_page,
)


# --- parse_event_title ---

class TestParseEventTitle:
    def test_with_date(self):
        title, dt = parse_event_title("Board of Trustees - Regular Board Meeting March 16, 2026")
        assert title == "Board of Trustees - Regular Board Meeting"
        assert dt.month == 3
        assert dt.day == 16

    def test_simple_with_date(self):
        title, dt = parse_event_title("Planning Commission Meeting March 12, 2026")
        assert title == "Planning Commission Meeting"
        assert dt.month == 3

    def test_no_date(self):
        title, dt = parse_event_title("DDA Meeting")
        assert title == "DDA Meeting"
        assert dt is None

    def test_whitespace(self):
        title, dt = parse_event_title("  Budget Ways & Means Committee Meeting March 3, 2026  ")
        assert title == "Budget Ways & Means Committee Meeting"
        assert dt.month == 3


# --- parse_date_time_text ---

class TestParseDateTimeText:
    def test_with_time_range(self):
        dt, _ = parse_date_time_text("March 16, 2026, 6:30 PM - 7:30 PM")
        assert dt.month == 3
        assert dt.day == 16
        assert dt.hour == 18
        assert dt.minute == 30

    def test_morning(self):
        dt, _ = parse_date_time_text("March 3, 2026, 9:30 AM - 10:30 AM")
        assert dt.hour == 9
        assert dt.minute == 30

    def test_date_only(self):
        dt, _ = parse_date_time_text("March 16, 2026")
        assert dt.month == 3
        assert dt.day == 16
        assert dt.hour == 0

    def test_invalid(self):
        dt, _ = parse_date_time_text("not a date")
        assert dt is None


# --- extract_event_id ---

class TestExtractEventId:
    def test_basic(self):
        assert extract_event_id("/Calendar.aspx?EID=2159&month=3&year=2026") == "2159"

    def test_no_eid(self):
        assert extract_event_id("/Calendar.aspx?view=list") is None


# --- is_canceled ---

class TestIsCanceled:
    def test_canceled(self):
        assert is_canceled("Cancelled: ZBA Meeting") is True

    def test_canceled_variant(self):
        assert is_canceled("Zoning Board of Appeals - CANCELED") is True

    def test_not_canceled(self):
        assert is_canceled("Regular Board Meeting") is False


# --- determine_meeting_type ---

class TestDetermineMeetingType:
    def test_board_of_trustees(self):
        assert determine_meeting_type("Board of Trustees - Regular Board Meeting") == "board_meeting"

    def test_commission(self):
        assert determine_meeting_type("Planning Commission Meeting") == "committee_meeting"

    def test_committee(self):
        assert determine_meeting_type("Conservation Committee") == "committee_meeting"

    def test_board(self):
        assert determine_meeting_type("Zoning Board of Appeals") == "committee_meeting"

    def test_authority(self):
        assert determine_meeting_type("DDA Authority") == "committee_meeting"

    def test_default(self):
        assert determine_meeting_type("DDA Meeting") == "public_meeting"


# --- get_issue_tags ---

class TestGetIssueTags:
    def test_conservation(self):
        tags = get_issue_tags("Conservation Committee")
        assert "conservation" in tags

    def test_planning(self):
        tags = get_issue_tags("Planning Commission Meeting")
        assert "planning" in tags

    def test_parks(self):
        tags = get_issue_tags("Parks & Recreation Advisory")
        assert "parks" in tags

    def test_default(self):
        assert get_issue_tags("Board of Trustees") == ["government", "clinton_township"]


# --- parse_calendar_list ---

SAMPLE_CALENDAR_HTML = """
<html><body>
<h3>
  <a href="/Calendar.aspx?EID=2159&month=3&year=2026&day=16&calType=0">
    Board of Trustees - Regular Board Meeting March 16, 2026
  </a>
</h3>
<div>March 16, 2026, 6:30 PM - 7:30 PM</div>
<a href="/Calendar.aspx?EID=2159&month=3&year=2026&day=16&calType=0">More Details</a>

<h3>
  <a href="/Calendar.aspx?EID=2278&month=3&year=2026&day=12&calType=0">
    Planning Commission Meeting March 12, 2026
  </a>
</h3>
<div>March 12, 2026, 6:30 PM - 7:30 PM</div>

<h3>
  <a href="/Calendar.aspx?EID=2273&month=3&year=2026&day=18&calType=0">
    Cancelled: Zoning Board of Appeals March 18, 2026
  </a>
</h3>
<div>March 18, 2026, 6:30 PM - 7:30 PM</div>

<h3>
  <a href="/Calendar.aspx?EID=2082&month=3&year=2026&day=11&calType=0">
    Conservation Committee Meeting March 11, 2026 - Cancelled
  </a>
</h3>
<div>March 11, 2026, 6:00 PM - 7:00 PM</div>
</body></html>
"""


class TestParseCalendarList:
    def test_finds_events(self):
        events = parse_calendar_list(SAMPLE_CALENDAR_HTML)
        # 2 events should be found (2 canceled are skipped)
        assert len(events) == 2

    def test_first_event_title(self):
        events = parse_calendar_list(SAMPLE_CALENDAR_HTML)
        assert events[0]["title"] == "Board of Trustees - Regular Board Meeting"

    def test_first_event_date(self):
        events = parse_calendar_list(SAMPLE_CALENDAR_HTML)
        assert events[0]["date"].month == 3
        assert events[0]["date"].day == 16
        assert events[0]["date"].hour == 18

    def test_event_id(self):
        events = parse_calendar_list(SAMPLE_CALENDAR_HTML)
        assert events[0]["event_id"] == "2159"

    def test_detail_url(self):
        events = parse_calendar_list(SAMPLE_CALENDAR_HTML)
        assert "EID=2159" in events[0]["detail_url"]
        assert events[0]["detail_url"].startswith("https://")

    def test_skips_canceled(self):
        events = parse_calendar_list(SAMPLE_CALENDAR_HTML)
        titles = [e["title"] for e in events]
        assert not any("Zoning Board" in t for t in titles)
        assert not any("Conservation" in t for t in titles)

    def test_planning_commission(self):
        events = parse_calendar_list(SAMPLE_CALENDAR_HTML)
        planning = [e for e in events if "Planning" in e["title"]]
        assert len(planning) == 1
        assert planning[0]["date"].day == 12


# --- parse_detail_page ---

SAMPLE_DETAIL_HTML = """
<html><body>
<h1>Board of Trustees - Regular Board Meeting</h1>
<div>March 16, 2026</div>
<div>6:30 PM - 7:30 PM</div>
<div>Event Location40700 Romeo Plank RoadClinton TownshipMI48038</div>
<a href="https://clintontwpmi.portal.civicclerk.com/event/429/overview">Download Agenda</a>
</body></html>
"""

SAMPLE_DETAIL_NO_AGENDA = """
<html><body>
<h1>DDA Meeting</h1>
<div>March 4, 2026</div>
<div>7:30 AM</div>
</body></html>
"""


class TestParseDetailPage:
    def test_agenda_url(self):
        result = parse_detail_page(SAMPLE_DETAIL_HTML)
        assert result["agenda_url"] == "https://clintontwpmi.portal.civicclerk.com/event/429/overview"

    def test_no_agenda(self):
        result = parse_detail_page(SAMPLE_DETAIL_NO_AGENDA)
        assert "agenda_url" not in result

    def test_empty_html(self):
        result = parse_detail_page("<html></html>")
        assert result == {}


# --- Integration ---

class TestIntegration:
    def test_calendar_to_meetings(self):
        """Test the flow: parse calendar → get events → build meeting dicts."""
        events = parse_calendar_list(SAMPLE_CALENDAR_HTML)
        assert len(events) == 2

        # Simulate building a meeting dict
        event = events[0]
        dt = event["date"]
        meeting = {
            "title": event["title"],
            "meeting_date": dt.strftime("%Y-%m-%d"),
            "meeting_time": dt.strftime("%H:%M"),
            "source_id": f"clinton-twp-{event['event_id']}",
        }
        assert meeting["meeting_date"] == "2026-03-16"
        assert meeting["meeting_time"] == "18:30"
        assert meeting["source_id"] == "clinton-twp-2159"
