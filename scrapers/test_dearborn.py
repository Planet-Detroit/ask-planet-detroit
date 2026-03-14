"""Tests for dearborn_scraper.py — City of Dearborn meeting scraper."""

import pytest
from dearborn_scraper import (
    determine_meeting_type,
    get_issue_tags,
    parse_event_card,
    parse_iso_datetime,
    extract_events_from_ajax,
    parse_events_html,
)


# --- determine_meeting_type ---

class TestDetermineMeetingType:
    def test_city_council(self):
        assert determine_meeting_type("City Council Meeting") == "board_meeting"

    def test_committee_of_whole(self):
        assert determine_meeting_type("Committee of the Whole") == "board_meeting"

    def test_commission(self):
        assert determine_meeting_type("Housing Commission Meeting") == "committee_meeting"

    def test_board(self):
        assert determine_meeting_type("Demolition Board of Appeals") == "committee_meeting"

    def test_authority(self):
        assert determine_meeting_type("Downtown Development Authority Board Meeting") == "committee_meeting"

    def test_special(self):
        assert determine_meeting_type("Special City Council Meeting") == "special_meeting"

    def test_hearing(self):
        assert determine_meeting_type("Public Hearing on Zoning") == "public_hearing"

    def test_briefing(self):
        assert determine_meeting_type("Mayor's Briefing Session") == "public_meeting"

    def test_default(self):
        assert determine_meeting_type("Federation of Neighborhood Associations") == "public_meeting"


# --- get_issue_tags ---

class TestGetIssueTags:
    def test_city_beautiful(self):
        tags = get_issue_tags("City Beautiful Commission")
        assert "environment" in tags

    def test_planning(self):
        tags = get_issue_tags("Planning Commission")
        assert "planning" in tags

    def test_demolition(self):
        tags = get_issue_tags("Demolition Board of Appeals")
        assert "infrastructure" in tags

    def test_default(self):
        assert get_issue_tags("City Council Meeting") == ["government", "dearborn"]


# --- parse_iso_datetime ---

class TestParseIsoDatetime:
    def test_with_timezone(self):
        dt = parse_iso_datetime("2026-03-18T12:00:00-04:00")
        assert dt.year == 2026
        assert dt.month == 3
        assert dt.day == 18
        assert dt.hour == 12

    def test_date_only(self):
        dt = parse_iso_datetime("2026-03-15")
        assert dt.year == 2026
        assert dt.month == 3
        assert dt.day == 15
        assert dt.tzinfo is not None

    def test_none(self):
        assert parse_iso_datetime(None) is None

    def test_empty(self):
        assert parse_iso_datetime("") is None

    def test_invalid(self):
        assert parse_iso_datetime("not a date") is None


# --- extract_events_from_ajax ---

class TestExtractEventsFromAjax:
    def test_insert_command(self):
        response = [
            {"command": "settings", "data": {}},
            {"command": "insert", "data": '<div class="views-row">event</div>'},
        ]
        html = extract_events_from_ajax(response)
        assert "views-row" in html

    def test_no_insert(self):
        response = [{"command": "settings", "data": {}}]
        html = extract_events_from_ajax(response)
        assert html == ""

    def test_dict_fallback(self):
        response = {"data": '<div class="views-row">event</div>'}
        html = extract_events_from_ajax(response)
        assert "views-row" in html

    def test_empty_list(self):
        assert extract_events_from_ajax([]) == ""


# --- parse_events_html ---

class TestParseEventsHtml:
    def test_finds_rows(self):
        html = '<div class="views-row">A</div><div class="views-row">B</div>'
        cards = parse_events_html(html)
        assert len(cards) == 2

    def test_empty_html(self):
        assert parse_events_html("") == []


# --- parse_event_card ---

SAMPLE_MEETING_CARD = """
<div class="views-row">
  <div class="event-result max-w-screen-content-container mx-auto h-full">
    <div class="event-card h-full bg-white w-full p-4 flex flex-col md:flex-row gap-8 items-center">
      <div class="w-full h-full flex flex-col space-y-2">
        <div class="h-full space-y-2">
          <div><div class="badge badge--blue">Meeting</div></div>
          <h2 data-history-node-id="7651" class="text-xl font-bold text-gray-900 text-left line-clamp-1">
            Housing Commission Meeting
          </h2>
          <div class="line-clamp-3">
            <span class="text-base font-normal text-gray-500">Regular monthly meeting</span>
          </div>
          <div class="flex items-center gap-1.5">
            <span class="text-sm font-normal text-gray-600 text-left">
              Townsend Towers, 7000 Freda, Dearborn, MI, 48126
            </span>
          </div>
          <div class="flex items-center gap-1.5">
            <span class="text-sm font-normal text-gray-600 text-left">
              <time datetime="2026-03-18T12:00:00-04:00">Wednesday, Mar 18 2026 12pm</time>
              to <time datetime="2026-03-18T13:00:00-04:00">1pm</time>
            </span>
          </div>
        </div>
        <a href="/events/2026/03/18/housing-commission-meeting"
           aria-label="Learn more about Housing Commission Meeting"
           class="button button--link font-medium !text-blue-900">
          <span>Learn More</span>
        </a>
      </div>
    </div>
  </div>
</div>
"""

SAMPLE_NON_MEETING_CARD = """
<div class="views-row">
  <div class="event-card">
    <div class="w-full h-full flex flex-col space-y-2">
      <div class="h-full space-y-2">
        <div><div class="badge badge--green">Important Date</div></div>
        <h2 data-history-node-id="7700" class="text-xl font-bold">Tax Payment Deadline</h2>
        <div class="flex items-center gap-1.5">
          <span class="text-sm font-normal text-gray-600 text-left">
            <time datetime="2026-04-15">Thursday, Apr 15 2026 All day</time>
          </span>
        </div>
      </div>
    </div>
  </div>
</div>
"""

SAMPLE_CANCELED_CARD = """
<div class="views-row">
  <div class="event-card">
    <div class="w-full h-full flex flex-col space-y-2">
      <div class="h-full space-y-2">
        <div><div class="badge badge--blue">Meeting</div></div>
        <h2 data-history-node-id="7800" class="text-xl font-bold">CANCELED: City Council Meeting</h2>
        <div class="flex items-center gap-1.5">
          <span class="text-sm font-normal text-gray-600 text-left">
            <time datetime="2026-03-25T19:00:00-04:00">Tuesday, Mar 25 2026 7pm</time>
          </span>
        </div>
      </div>
    </div>
  </div>
</div>
"""

SAMPLE_COUNCIL_CARD = """
<div class="views-row">
  <div class="event-card">
    <div class="w-full h-full flex flex-col space-y-2">
      <div class="h-full space-y-2">
        <div><div class="badge badge--blue">Meeting</div></div>
        <h2 data-history-node-id="7500" class="text-xl font-bold">City Council Meeting</h2>
        <div class="flex items-center gap-1.5">
          <span class="text-sm font-normal text-gray-600 text-left">
            Dearborn Administrative Center, 16901 Michigan Ave
          </span>
        </div>
        <div class="flex items-center gap-1.5">
          <span class="text-sm font-normal text-gray-600 text-left">
            <time datetime="2026-03-24T19:00:00-04:00">Tuesday, Mar 24 2026 7pm</time>
          </span>
        </div>
      </div>
      <a href="/events/2026/03/24/city-council-meeting"
         class="button button--link font-medium !text-blue-900">
        <span>Learn More</span>
      </a>
    </div>
  </div>
</div>
"""


class TestParseEventCard:
    def test_meeting_title(self):
        m = parse_event_card(SAMPLE_MEETING_CARD)
        assert m["title"] == "Housing Commission Meeting"

    def test_meeting_date(self):
        m = parse_event_card(SAMPLE_MEETING_CARD)
        assert m["meeting_date"] == "2026-03-18"

    def test_meeting_time(self):
        m = parse_event_card(SAMPLE_MEETING_CARD)
        assert m["meeting_time"] == "12:00"

    def test_meeting_location(self):
        m = parse_event_card(SAMPLE_MEETING_CARD)
        assert m["location"] is not None
        assert "Townsend Towers" in m["location"]

    def test_meeting_source_id(self):
        m = parse_event_card(SAMPLE_MEETING_CARD)
        assert m["source_id"] == "dearborn-7651"

    def test_meeting_details_url(self):
        m = parse_event_card(SAMPLE_MEETING_CARD)
        assert m["details_url"] == "https://dearborn.gov/events/2026/03/18/housing-commission-meeting"

    def test_meeting_type(self):
        m = parse_event_card(SAMPLE_MEETING_CARD)
        assert m["meeting_type"] == "committee_meeting"

    def test_meeting_source(self):
        m = parse_event_card(SAMPLE_MEETING_CARD)
        assert m["source"] == "dearborn_scraper"

    def test_meeting_region(self):
        m = parse_event_card(SAMPLE_MEETING_CARD)
        assert m["region"] == "Wayne County"

    def test_non_meeting_returns_none(self):
        """Non-meeting events (Important Date, etc.) should be skipped."""
        m = parse_event_card(SAMPLE_NON_MEETING_CARD)
        assert m is None

    def test_canceled_returns_none(self):
        """Canceled meetings should be skipped."""
        m = parse_event_card(SAMPLE_CANCELED_CARD)
        assert m is None

    def test_council_meeting(self):
        m = parse_event_card(SAMPLE_COUNCIL_CARD)
        assert m["title"] == "City Council Meeting"
        assert m["meeting_type"] == "board_meeting"
        assert m["meeting_date"] == "2026-03-24"
        assert m["meeting_time"] == "19:00"

    def test_council_location(self):
        m = parse_event_card(SAMPLE_COUNCIL_CARD)
        assert m["location"] is not None
        assert "16901 Michigan Ave" in m["location"]

    def test_agency_format(self):
        m = parse_event_card(SAMPLE_MEETING_CARD)
        assert m["agency"] == "City of Dearborn - Housing Commission Meeting"

    def test_no_title_returns_none(self):
        html = '<div class="views-row"><div class="badge">Meeting</div></div>'
        assert parse_event_card(html) is None

    def test_no_datetime_returns_none(self):
        html = """
        <div class="views-row">
          <div><div class="badge">Meeting</div></div>
          <h2 data-history-node-id="999">Test Meeting</h2>
        </div>"""
        assert parse_event_card(html) is None


# --- Integration ---

class TestIntegration:
    def test_ajax_to_meeting(self):
        """Test full flow: AJAX response → extract HTML → parse cards → meetings."""
        ajax_response = [
            {"command": "settings", "data": {}},
            {"command": "insert", "data": SAMPLE_MEETING_CARD},
        ]
        html = extract_events_from_ajax(ajax_response)
        cards = parse_events_html(html)
        assert len(cards) == 1

        meeting = parse_event_card(cards[0])
        assert meeting["title"] == "Housing Commission Meeting"
        assert meeting["meeting_date"] == "2026-03-18"
