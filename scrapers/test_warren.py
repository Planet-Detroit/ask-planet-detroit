"""Tests for warren_scraper.py — City of Warren meeting scraper."""

import pytest
from warren_scraper import (
    parse_body_name,
    parse_date_from_text,
    parse_time_from_text,
    determine_meeting_type,
    get_issue_tags,
    generate_source_id,
    parse_meeting_page,
    parse_sitemap,
    filter_upcoming_urls,
)


# --- parse_body_name ---

class TestParseBodyName:
    def test_city_council(self):
        assert parse_body_name("City Council Meeting – March 10, 2026") == "City Council"

    def test_planning_commission(self):
        assert parse_body_name("Planning Commission Meeting – March 9, 2026") == "Planning Commission"

    def test_zba(self):
        assert parse_body_name("Zoning Board of Appeals Meeting – March 11, 2026") == "Zoning Board of Appeals"

    def test_em_dash(self):
        assert parse_body_name("Library Commission Meeting — March 19, 2026") == "Library Commission"

    def test_hyphen(self):
        assert parse_body_name("Crime Commission Meeting - March 5, 2026") == "Crime Commission"

    def test_special_meeting(self):
        assert parse_body_name("City Council Special Meeting – March 15, 2026") == "City Council Special"

    def test_no_date(self):
        # Fallback when there's no date separator
        assert parse_body_name("City Council Meeting") == "City Council"


# --- parse_date_from_text ---

class TestParseDateFromText:
    def test_full_month_name(self):
        dt = parse_date_from_text("March 10, 2026")
        assert dt.month == 3
        assert dt.day == 10
        assert dt.year == 2026

    def test_abbreviated_month(self):
        dt = parse_date_from_text("Mar 10, 2026")
        assert dt.month == 3
        assert dt.day == 10

    def test_numeric(self):
        dt = parse_date_from_text("03/10/2026")
        assert dt.month == 3
        assert dt.day == 10

    def test_invalid(self):
        assert parse_date_from_text("not a date") is None

    def test_whitespace(self):
        dt = parse_date_from_text("  January 1, 2026  ")
        assert dt.month == 1
        assert dt.day == 1


# --- parse_time_from_text ---

class TestParseTimeFromText:
    def test_pm(self):
        h, m = parse_time_from_text("7:00 pm")
        assert h == 19 and m == 0

    def test_am(self):
        h, m = parse_time_from_text("10:30 AM")
        assert h == 10 and m == 30

    def test_noon(self):
        h, m = parse_time_from_text("12:00 PM")
        assert h == 12 and m == 0

    def test_midnight(self):
        h, m = parse_time_from_text("12:00 AM")
        assert h == 0 and m == 0

    def test_no_space(self):
        h, m = parse_time_from_text("7:00pm")
        assert h == 19 and m == 0

    def test_invalid(self):
        h, m = parse_time_from_text("not a time")
        assert h is None and m is None


# --- determine_meeting_type ---

class TestDetermineMeetingType:
    def test_city_council(self):
        assert determine_meeting_type("City Council") == "board_meeting"

    def test_commission(self):
        assert determine_meeting_type("Planning Commission") == "committee_meeting"

    def test_committee(self):
        assert determine_meeting_type("Master Plan Committee") == "committee_meeting"

    def test_board(self):
        assert determine_meeting_type("Zoning Board of Appeals") == "committee_meeting"

    def test_authority(self):
        assert determine_meeting_type("Brownfield Redevelopment Authority") == "committee_meeting"

    def test_special(self):
        assert determine_meeting_type("City Council Special") == "special_meeting"

    def test_default(self):
        assert determine_meeting_type("Some Other Body") == "public_meeting"

    def test_committee_of_whole(self):
        assert determine_meeting_type("Committee of the Whole") == "board_meeting"


# --- get_issue_tags ---

class TestGetIssueTags:
    def test_planning(self):
        tags = get_issue_tags("Planning Commission")
        assert "planning" in tags

    def test_brownfield(self):
        tags = get_issue_tags("Brownfield Redevelopment Authority")
        assert "environment" in tags
        assert "contamination" in tags

    def test_parks(self):
        tags = get_issue_tags("Parks and Recreation Commission")
        assert "parks" in tags

    def test_default(self):
        tags = get_issue_tags("City Council")
        assert tags == ["government", "warren"]


# --- generate_source_id ---

class TestGenerateSourceId:
    def test_basic(self):
        url = "https://www.cityofwarren.org/meetings/city-council-meeting-march-10-2026/"
        sid = generate_source_id(url)
        assert sid == "warren-city-council-meeting-march-10-2026"

    def test_no_trailing_slash(self):
        url = "https://www.cityofwarren.org/meetings/planning-commission-meeting-march-9-2026"
        sid = generate_source_id(url)
        assert sid == "warren-planning-commission-meeting-march-9-2026"

    def test_stability(self):
        # Same URL always produces same ID
        url = "https://www.cityofwarren.org/meetings/city-council-meeting-march-10-2026/"
        assert generate_source_id(url) == generate_source_id(url)


# --- parse_sitemap ---

class TestParseSitemap:
    def test_basic_sitemap(self):
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <url>
                <loc>https://www.cityofwarren.org/meetings/city-council-meeting-march-10-2026/</loc>
                <lastmod>2026-03-06</lastmod>
            </url>
            <url>
                <loc>https://www.cityofwarren.org/meetings/planning-commission-meeting-march-9-2026/</loc>
                <lastmod>2026-03-05</lastmod>
            </url>
        </urlset>"""
        urls = parse_sitemap(xml)
        assert len(urls) == 2
        assert urls[0][0] == "https://www.cityofwarren.org/meetings/city-council-meeting-march-10-2026/"
        assert urls[0][1] == "2026-03-06"

    def test_empty_sitemap(self):
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
        </urlset>"""
        assert parse_sitemap(xml) == []


# --- filter_upcoming_urls ---

class TestFilterUpcomingUrls:
    def test_filters_past_meetings(self):
        from datetime import datetime, timedelta
        from zoneinfo import ZoneInfo
        # Use a date 30 days from now (within LOOKAHEAD_DAYS)
        future = datetime.now(ZoneInfo("America/Detroit")) + timedelta(days=30)
        future_slug = future.strftime("%B-%d-%Y").lower().replace(" ", "")
        # Split to get "month-day-year" format matching slug pattern
        future_month = future.strftime("%B").lower()
        future_day = str(future.day)
        future_year = str(future.year)
        urls = [
            ("https://www.cityofwarren.org/meetings/city-council-meeting-january-5-2020/", "2020-01-05"),
            (f"https://www.cityofwarren.org/meetings/city-council-meeting-{future_month}-{future_day}-{future_year}/", ""),
        ]
        result = filter_upcoming_urls(urls)
        # 2020 should be filtered out, future date should pass
        assert len(result) == 1
        assert str(future_year) in result[0]

    def test_unparseable_slug_included(self):
        """URLs with unparseable date slugs are included (conservative)."""
        urls = [
            ("https://www.cityofwarren.org/meetings/some-weird-page/", ""),
        ]
        result = filter_upcoming_urls(urls)
        assert len(result) == 1


# --- parse_meeting_page ---

SAMPLE_COUNCIL_HTML = """
<html>
<body>
<article>
<div class="entry-content">
<h1>City Council Meeting – March 10, 2026</h1>

<p>Warren Community Center</p>
<p>March 10, 2026</p>
<p>7:00 pm</p>

<p>Any person with a disability who needs accommodation may contact
<a href="mailto:citycouncil@cityofwarren.org">citycouncil@cityofwarren.org</a>
or <a href="tel:5862582060">(586) 258-2060</a>.</p>

<table>
<thead><tr><th>Name</th><th>Date Published</th><th>Resources</th></tr></thead>
<tbody>
<tr>
<td>City Council Meeting – March 10, 2026</td>
<td>03-06-2026</td>
<td>
<a href="/wp-content/uploads/2026/03/City-Council-Notice-3.10.2026.pdf">Notice (277 Kilobytes)</a>
<a href="/wp-content/uploads/2026/03/City-Council-Agenda-3.10.2026.pdf">Agenda (312 Kilobytes)</a>
<a href="/wp-content/uploads/2026/03/City-Council-ePacket-3.10.2026-compressed.pdf">ePacket (16 Megabytes)</a>
</td>
</tr>
</tbody>
</table>
</div>
</article>
</body>
</html>
"""

SAMPLE_COMMISSION_HTML = """
<html>
<body>
<article>
<div class="entry-content">
<h1>Planning Commission Meeting – March 9, 2026</h1>

<p>Warren City Hall</p>
<p>March 9, 2026</p>
<p>6:30 pm</p>

<p>For more info contact <a href="mailto:planning@cityofwarren.org">planning@cityofwarren.org</a></p>
</div>
</article>
</body>
</html>
"""


class TestParseMeetingPage:
    def test_council_meeting_title(self):
        m = parse_meeting_page(SAMPLE_COUNCIL_HTML, "https://www.cityofwarren.org/meetings/city-council-meeting-march-10-2026/")
        assert m["title"] == "City Council"

    def test_council_meeting_date(self):
        m = parse_meeting_page(SAMPLE_COUNCIL_HTML, "https://www.cityofwarren.org/meetings/city-council-meeting-march-10-2026/")
        assert m["meeting_date"] == "2026-03-10"

    def test_council_meeting_time(self):
        m = parse_meeting_page(SAMPLE_COUNCIL_HTML, "https://www.cityofwarren.org/meetings/city-council-meeting-march-10-2026/")
        assert m["meeting_time"] == "19:00"

    def test_council_meeting_location(self):
        m = parse_meeting_page(SAMPLE_COUNCIL_HTML, "https://www.cityofwarren.org/meetings/city-council-meeting-march-10-2026/")
        assert m["location"] == "Warren Community Center"

    def test_council_meeting_agenda_url(self):
        m = parse_meeting_page(SAMPLE_COUNCIL_HTML, "https://www.cityofwarren.org/meetings/city-council-meeting-march-10-2026/")
        assert m["agenda_url"] == "https://www.cityofwarren.org/wp-content/uploads/2026/03/City-Council-Agenda-3.10.2026.pdf"

    def test_council_meeting_source_id(self):
        m = parse_meeting_page(SAMPLE_COUNCIL_HTML, "https://www.cityofwarren.org/meetings/city-council-meeting-march-10-2026/")
        assert m["source_id"] == "warren-city-council-meeting-march-10-2026"

    def test_council_meeting_type(self):
        m = parse_meeting_page(SAMPLE_COUNCIL_HTML, "https://www.cityofwarren.org/meetings/city-council-meeting-march-10-2026/")
        assert m["meeting_type"] == "board_meeting"

    def test_council_contact_email(self):
        m = parse_meeting_page(SAMPLE_COUNCIL_HTML, "https://www.cityofwarren.org/meetings/city-council-meeting-march-10-2026/")
        # Contact email is not in the meeting dict (not in our schema), but we parse it for potential future use
        # Just verify the meeting was parsed successfully
        assert m is not None

    def test_commission_meeting(self):
        m = parse_meeting_page(SAMPLE_COMMISSION_HTML, "https://www.cityofwarren.org/meetings/planning-commission-meeting-march-9-2026/")
        assert m["title"] == "Planning Commission"
        assert m["meeting_date"] == "2026-03-09"
        assert m["meeting_time"] == "18:30"
        assert m["meeting_type"] == "committee_meeting"
        assert "planning" in m["issue_tags"]

    def test_commission_no_agenda(self):
        m = parse_meeting_page(SAMPLE_COMMISSION_HTML, "https://www.cityofwarren.org/meetings/planning-commission-meeting-march-9-2026/")
        assert m["agenda_url"] is None

    def test_agency_format(self):
        m = parse_meeting_page(SAMPLE_COUNCIL_HTML, "https://www.cityofwarren.org/meetings/city-council-meeting-march-10-2026/")
        assert m["agency"] == "City of Warren - City Council"

    def test_region(self):
        m = parse_meeting_page(SAMPLE_COUNCIL_HTML, "https://www.cityofwarren.org/meetings/city-council-meeting-march-10-2026/")
        assert m["region"] == "Macomb County"

    def test_source(self):
        m = parse_meeting_page(SAMPLE_COUNCIL_HTML, "https://www.cityofwarren.org/meetings/city-council-meeting-march-10-2026/")
        assert m["source"] == "warren_scraper"

    def test_no_h1_returns_none(self):
        html = "<html><body><p>No heading here</p></body></html>"
        assert parse_meeting_page(html, "https://example.com/meetings/test/") is None

    def test_no_date_returns_none(self):
        html = "<html><body><h1>Mystery Meeting</h1><p>No date info</p></body></html>"
        # Should try URL slug fallback; if that fails too, returns None
        result = parse_meeting_page(html, "https://example.com/meetings/mystery/")
        assert result is None

    def test_date_from_url_fallback(self):
        """If page has no parseable date text, fall back to URL slug."""
        html = """<html><body>
        <div class="entry-content">
        <h1>City Council Meeting – TBD</h1>
        <p>Warren Community Center</p>
        </div></body></html>"""
        m = parse_meeting_page(html, "https://www.cityofwarren.org/meetings/city-council-meeting-april-15-2026/")
        assert m is not None
        assert m["meeting_date"] == "2026-04-15"


# --- Integration-style test ---

class TestEndToEnd:
    def test_sitemap_to_meeting(self):
        """Test the full flow: parse sitemap, then parse a meeting page."""
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <url>
                <loc>https://www.cityofwarren.org/meetings/city-council-meeting-march-10-2026/</loc>
                <lastmod>2026-03-06</lastmod>
            </url>
        </urlset>"""
        urls = parse_sitemap(xml)
        assert len(urls) == 1

        meeting = parse_meeting_page(SAMPLE_COUNCIL_HTML, urls[0][0])
        assert meeting["title"] == "City Council"
        assert meeting["meeting_date"] == "2026-03-10"
        assert meeting["source_id"] == "warren-city-council-meeting-march-10-2026"
