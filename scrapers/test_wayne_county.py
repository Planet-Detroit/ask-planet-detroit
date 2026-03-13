"""
Tests for Wayne County meeting scraper.

Tests the pure parsing logic WITHOUT hitting the live website.

Run with: cd scrapers && python -m pytest test_wayne_county.py -v
"""

import hashlib
import pytest
from wayne_county_scraper import (
    parse_meeting_date,
    parse_meeting_time,
    extract_virtual_url,
    extract_meeting_id,
    extract_phone_numbers,
    parse_location,
    parse_detail_page,
    determine_meeting_type,
    get_issue_tags,
    generate_source_id,
    DEFAULT_ISSUE_TAGS,
)


# --- Sample HTML for detail page tests ---

SAMPLE_DETAIL_HTML = """
<div class="grid obj-meeting">
  <h1 class='oc-page-title'>Wayne County Commission - January 8, 2026</h1>
  <ul class="content-details-list minutes-details-list">
    <li><span class="field-label">Meeting Date</span>
        <span class="field-value"><span class="minutes-date">January 08, 2026</span></span></li>
    <li><span class="field-label">Meeting Type</span>
        <span class="field-value">Full Commission</span></li>
  </ul>
  <div class="meeting-container">
    <div class='meeting-time'><h2>Time</h2>10:00 AM - 11:00 AM</div>
    <div class='meeting-address'>
      <h2>Location</h2>
      <p>You can join the meeting by visiting https://waynecounty.zoom.us/my/waynecountycommission
         or by dialing (312) 626-6799. The meeting identification number is: 277 771 1868.</p>
      <p>Commission Chambers, Mezzanine, Guardian Building, 500 Griswold, Detroit, MI</p>
    </div>
    <div class="meeting-attachments">
      <h2 class="folder-title">Related Information</h2>
      <ul class="related-information-list">
        <li><a href="https://youtu.be/xyz">Video</a></li>
        <li><a href="/files/documents/agenda2026-0108.pdf" class="document ext-pdf">Agenda2026-0108.pdf</a></li>
        <li><a href="/files/documents/journal-010826.pdf" class="document ext-pdf">Journal-010826.pdf</a></li>
      </ul>
    </div>
  </div>
</div>
"""

SAMPLE_DETAIL_NO_VIRTUAL = """
<div class="grid obj-meeting">
  <h1 class='oc-page-title'>Ethics Board Meeting - March 15, 2026</h1>
  <ul class="content-details-list minutes-details-list">
    <li><span class="field-label">Meeting Date</span>
        <span class="field-value"><span class="minutes-date">March 15, 2026</span></span></li>
    <li><span class="field-label">Meeting Type</span>
        <span class="field-value">Ethics Board</span></li>
  </ul>
  <div class="meeting-container">
    <div class='meeting-time'><h2>Time</h2>2:00 PM - 3:30 PM</div>
    <div class='meeting-address'>
      <h2>Location</h2>
      <p>Guardian Building, 500 Griswold, Detroit, MI 48226</p>
    </div>
  </div>
</div>
"""


class TestDateParsing:
    """Test parsing dates from the Wayne County format like 'January 08, 2026'."""

    def test_standard_date(self):
        # Standard date with zero-padded day
        result = parse_meeting_date("January 08, 2026")
        assert result is not None
        assert result.year == 2026
        assert result.month == 1
        assert result.day == 8

    def test_single_digit_day(self):
        # Day without leading zero
        result = parse_meeting_date("March 5, 2026")
        assert result is not None
        assert result.month == 3
        assert result.day == 5

    def test_december_date(self):
        result = parse_meeting_date("December 31, 2026")
        assert result is not None
        assert result.month == 12
        assert result.day == 31

    def test_empty_string(self):
        assert parse_meeting_date("") is None

    def test_none(self):
        assert parse_meeting_date(None) is None

    def test_invalid_format(self):
        assert parse_meeting_date("01/08/2026") is None

    def test_extra_whitespace(self):
        # Handle extra whitespace gracefully
        result = parse_meeting_date("  January  08,  2026  ")
        assert result is not None
        assert result.day == 8


class TestTimeParsing:
    """Test parsing time from strings like '10:00 AM - 11:00 AM'."""

    def test_morning_time_range(self):
        result = parse_meeting_time("10:00 AM - 11:00 AM")
        assert result == (10, 0)

    def test_afternoon_time_range(self):
        result = parse_meeting_time("2:00 PM - 3:30 PM")
        assert result == (14, 0)

    def test_noon(self):
        result = parse_meeting_time("12:00 PM - 1:00 PM")
        assert result == (12, 0)

    def test_single_time(self):
        # Just a start time, no range
        result = parse_meeting_time("10:00 AM")
        assert result == (10, 0)

    def test_empty(self):
        assert parse_meeting_time("") is None
        assert parse_meeting_time(None) is None

    def test_no_time_in_text(self):
        assert parse_meeting_time("No time specified") is None


class TestVirtualUrlExtraction:
    """Test extracting Zoom/Teams URLs from meeting address text."""

    def test_zoom_personal_room(self):
        text = "You can join the meeting by visiting https://waynecounty.zoom.us/my/waynecountycommission"
        result = extract_virtual_url(text)
        assert result == "https://waynecounty.zoom.us/my/waynecountycommission"

    def test_zoom_meeting_url(self):
        text = "Join at https://zoom.us/j/2112321934 for the meeting"
        result = extract_virtual_url(text)
        assert result == "https://zoom.us/j/2112321934"

    def test_teams_url(self):
        text = "Join via https://teams.microsoft.com/l/meetup-join/abc123"
        result = extract_virtual_url(text)
        assert result == "https://teams.microsoft.com/l/meetup-join/abc123"

    def test_strips_trailing_punctuation(self):
        text = "Join at https://zoom.us/j/123456."
        result = extract_virtual_url(text)
        assert not result.endswith(".")

    def test_no_url(self):
        assert extract_virtual_url("No virtual meeting info here") is None

    def test_empty(self):
        assert extract_virtual_url("") is None
        assert extract_virtual_url(None) is None


class TestMeetingIdExtraction:
    """Test extracting meeting IDs from text."""

    def test_meeting_identification_number(self):
        # Wayne County uses "meeting identification number is:" pattern
        text = "The meeting identification number is: 277 771 1868."
        result = extract_meeting_id(text)
        assert result == "2777711868"

    def test_meeting_id_label(self):
        text = "Meeting ID: 817 153 5870"
        result = extract_meeting_id(text)
        assert result == "8171535870"

    def test_zoom_url_fallback(self):
        # Extract from Zoom URL if no explicit ID
        text = "Join at https://zoom.us/j/2112321934"
        result = extract_meeting_id(text)
        assert result == "2112321934"

    def test_personal_room_no_id(self):
        # Personal room URLs don't have numeric IDs
        text = "Visit https://waynecounty.zoom.us/my/waynecountycommission"
        result = extract_meeting_id(text)
        # Should find the meeting ID if mentioned elsewhere, or None
        assert result is None

    def test_empty(self):
        assert extract_meeting_id("") is None
        assert extract_meeting_id(None) is None


class TestPhoneExtraction:
    """Test extracting dial-in phone numbers."""

    def test_parenthesized_area_code(self):
        text = "or by dialing (312) 626-6799"
        result = extract_phone_numbers(text)
        assert "312" in result
        assert "626" in result
        assert "6799" in result

    def test_dashed_format(self):
        text = "Call 346-248-7799"
        result = extract_phone_numbers(text)
        assert "346" in result

    def test_no_phone(self):
        assert extract_phone_numbers("No phone here") is None

    def test_empty(self):
        assert extract_phone_numbers("") is None
        assert extract_phone_numbers(None) is None


class TestLocationParsing:
    """Test extracting physical location from meeting-address text."""

    def test_location_with_virtual_info(self):
        text = """Location
You can join the meeting by visiting https://waynecounty.zoom.us/my/waynecountycommission
or by dialing (312) 626-6799. The meeting identification number is: 277 771 1868.
Commission Chambers, Mezzanine, Guardian Building, 500 Griswold, Detroit, MI"""
        result = parse_location(text)
        assert result is not None
        assert "500 Griswold" in result

    def test_location_only(self):
        text = """Location
Guardian Building, 500 Griswold, Detroit, MI 48226"""
        result = parse_location(text)
        assert "500 Griswold" in result

    def test_empty(self):
        assert parse_location("") is None
        assert parse_location(None) is None


class TestMeetingType:
    """Test meeting type determination from committee names."""

    def test_full_commission(self):
        assert determine_meeting_type("Full Commission") == "board_meeting"

    def test_committee(self):
        assert determine_meeting_type("Ways & Means Committee") == "committee_meeting"

    def test_public_hearing(self):
        assert determine_meeting_type("Public Hearing") == "public_hearing"

    def test_ethics_board(self):
        assert determine_meeting_type("Ethics Board") == "board_meeting"

    def test_unknown(self):
        assert determine_meeting_type("Something Else") == "public_meeting"

    def test_empty(self):
        assert determine_meeting_type("") == "public_meeting"
        assert determine_meeting_type(None) == "public_meeting"


class TestIssueTags:
    """Test issue tag assignment based on committee name."""

    def test_health_committee(self):
        tags = get_issue_tags("Health & Human Services Committee")
        assert "public_health" in tags
        assert "wayne_county" in tags

    def test_public_safety(self):
        tags = get_issue_tags("Public Safety Judiciary & Homeland Security Committee")
        assert "public_safety" in tags

    def test_economic_development(self):
        tags = get_issue_tags("Economic Development Committee")
        assert "economic_development" in tags

    def test_ways_and_means(self):
        tags = get_issue_tags("Ways & Means Committee")
        assert "budget" in tags

    def test_default_tags(self):
        tags = get_issue_tags("Full Commission")
        assert tags == DEFAULT_ISSUE_TAGS

    def test_empty(self):
        tags = get_issue_tags("")
        assert tags == DEFAULT_ISSUE_TAGS


class TestSourceId:
    """Test deterministic source ID generation with hashlib.md5."""

    def test_generates_stable_id(self):
        # Same inputs always produce the same ID
        id1 = generate_source_id("Wayne County Commission", "2026-01-08")
        id2 = generate_source_id("Wayne County Commission", "2026-01-08")
        assert id1 == id2

    def test_starts_with_prefix(self):
        result = generate_source_id("Test Meeting", "2026-01-01")
        assert result.startswith("wayne-county-")

    def test_different_inputs_different_ids(self):
        id1 = generate_source_id("Meeting A", "2026-01-08")
        id2 = generate_source_id("Meeting B", "2026-01-08")
        assert id1 != id2

    def test_different_dates_different_ids(self):
        id1 = generate_source_id("Same Meeting", "2026-01-08")
        id2 = generate_source_id("Same Meeting", "2026-01-09")
        assert id1 != id2

    def test_uses_md5_not_python_hash(self):
        # Verify it uses hashlib.md5 by checking the expected hash
        key = "Test|2026-01-01"
        expected_hash = hashlib.md5(key.encode()).hexdigest()[:12]
        result = generate_source_id("Test", "2026-01-01")
        assert result == f"wayne-county-{expected_hash}"


class TestDetailPageParsing:
    """Test parsing full detail pages with BeautifulSoup."""

    def test_parses_title(self):
        result = parse_detail_page(SAMPLE_DETAIL_HTML, "https://example.com/meeting")
        assert result['title'] == "Wayne County Commission - January 8, 2026"

    def test_parses_date(self):
        result = parse_detail_page(SAMPLE_DETAIL_HTML, "https://example.com/meeting")
        assert result['date_text'] == "January 08, 2026"

    def test_parses_meeting_type(self):
        result = parse_detail_page(SAMPLE_DETAIL_HTML, "https://example.com/meeting")
        assert result['type_text'] == "Full Commission"

    def test_parses_time(self):
        result = parse_detail_page(SAMPLE_DETAIL_HTML, "https://example.com/meeting")
        assert "10:00 AM" in result['time_text']

    def test_extracts_zoom_url(self):
        result = parse_detail_page(SAMPLE_DETAIL_HTML, "https://example.com/meeting")
        assert result['virtual_url'] == "https://waynecounty.zoom.us/my/waynecountycommission"

    def test_extracts_meeting_id(self):
        result = parse_detail_page(SAMPLE_DETAIL_HTML, "https://example.com/meeting")
        assert result['virtual_meeting_id'] == "2777711868"

    def test_extracts_phone(self):
        result = parse_detail_page(SAMPLE_DETAIL_HTML, "https://example.com/meeting")
        assert result['virtual_phone'] is not None
        assert "312" in result['virtual_phone']

    def test_extracts_agenda_url(self):
        result = parse_detail_page(SAMPLE_DETAIL_HTML, "https://example.com/meeting")
        assert result['agenda_url'] is not None
        assert "agenda2026-0108.pdf" in result['agenda_url']

    def test_extracts_minutes_url(self):
        result = parse_detail_page(SAMPLE_DETAIL_HTML, "https://example.com/meeting")
        assert result['minutes_url'] is not None
        assert "journal-010826.pdf" in result['minutes_url']

    def test_extracts_location(self):
        result = parse_detail_page(SAMPLE_DETAIL_HTML, "https://example.com/meeting")
        assert result['location'] is not None
        assert "500 Griswold" in result['location']

    def test_sets_details_url(self):
        url = "https://example.com/meeting"
        result = parse_detail_page(SAMPLE_DETAIL_HTML, url)
        assert result['details_url'] == url

    def test_no_virtual_info(self):
        # Detail page without Zoom/virtual info
        result = parse_detail_page(SAMPLE_DETAIL_NO_VIRTUAL, "https://example.com/meeting")
        assert result.get('virtual_url') is None
        assert result.get('virtual_meeting_id') is None
        assert result.get('virtual_phone') is None

    def test_no_attachments(self):
        result = parse_detail_page(SAMPLE_DETAIL_NO_VIRTUAL, "https://example.com/meeting")
        assert result.get('agenda_url') is None
        assert result.get('minutes_url') is None

    def test_agenda_url_made_absolute(self):
        # Relative URLs should be made absolute with BASE_URL
        result = parse_detail_page(SAMPLE_DETAIL_HTML, "https://example.com/meeting")
        assert result['agenda_url'].startswith("https://www.waynecountymi.gov")
