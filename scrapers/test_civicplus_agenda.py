"""Tests for CivicPlus AgendaCenter scraper."""

import pytest
from civicplus_agenda_scraper import (
    parse_agenda_html,
    determine_meeting_type,
    get_issue_tags,
    build_rss_cid,
    CIVICPLUS_CONFIGS,
)

# --- Config validation ---

class TestConfigs:
    def test_all_cities_have_required_fields(self):
        for key, city in CIVICPLUS_CONFIGS.items():
            assert "city_name" in city, f"{key} missing city_name"
            assert "domain" in city, f"{key} missing domain"
            assert "region" in city, f"{key} missing region"
            assert "source" in city, f"{key} missing source"
            assert "default_tags" in city, f"{key} missing default_tags"
            assert "boards" in city, f"{key} missing boards"

    def test_all_boards_have_required_fields(self):
        for city_key, city in CIVICPLUS_CONFIGS.items():
            for board_key, board in city["boards"].items():
                assert "name" in board, f"{city_key}/{board_key} missing name"
                assert "cat_id" in board, f"{city_key}/{board_key} missing cat_id"
                assert "slug" in board, f"{city_key}/{board_key} missing slug"

    def test_sterling_heights_has_city_council(self):
        boards = CIVICPLUS_CONFIGS["sterling_heights"]["boards"]
        assert "city_council" in boards
        assert boards["city_council"]["cat_id"] == 23

    def test_westland_has_city_council(self):
        boards = CIVICPLUS_CONFIGS["westland"]["boards"]
        assert "city_council" in boards
        assert boards["city_council"]["cat_id"] == 2

    def test_waterford_has_board_of_trustees(self):
        boards = CIVICPLUS_CONFIGS["waterford"]["boards"]
        assert "board_of_trustees" in boards
        assert boards["board_of_trustees"]["cat_id"] == 6


# --- RSS CID slug builder ---

class TestBuildRssCid:
    def test_simple(self):
        assert build_rss_cid("City Council", 23) == "City-Council-23"

    def test_multi_word(self):
        assert build_rss_cid("Planning Commission", 20) == "Planning-Commission-20"

    def test_special_chars(self):
        assert build_rss_cid("Zoning Board of Appeals", 22) == "Zoning-Board-of-Appeals-22"


# --- Meeting type ---

class TestMeetingType:
    def test_council(self):
        assert determine_meeting_type("City Council") == "board_meeting"

    def test_trustees(self):
        assert determine_meeting_type("Board of Trustees") == "board_meeting"

    def test_planning(self):
        assert determine_meeting_type("Planning Commission") == "committee_meeting"

    def test_zba(self):
        assert determine_meeting_type("Zoning Board of Appeals") == "committee_meeting"


# --- Issue tags ---

class TestIssueTags:
    def test_planning(self):
        tags = get_issue_tags("Planning Commission", ["government", "sterling-heights"])
        assert "planning" in tags

    def test_sustainability(self):
        tags = get_issue_tags("Sustainability Commission", ["government", "sterling-heights"])
        assert "environment" in tags

    def test_default(self):
        default = ["government", "sterling-heights"]
        assert get_issue_tags("City Council", default) == default


# --- HTML parsing ---

# Sample HTML mimicking real CivicPlus AgendaCenter AJAX response (table format)
SAMPLE_AGENDA_HTML = """
<table id="table23" summary="List of Agendas">
<tbody>
<tr id="row1603" class="catAgendaRow">
  <td>
    <h3 class="noMargin" id="h403092026-1603">
      <strong aria-label="Agenda for March 9, 2026"><abbr title="March">Mar</abbr> 9, 2026</strong>
    </h3>
    <p><a href="/AgendaCenter/ViewFile/Agenda/_03092026-1603?html=true" target="_blank">
      City Council Regular Meeting
    </a></p>
  </td>
  <td class="minutes">
    <a href="/AgendaCenter/ViewFile/Minutes/_03092026-1603" target="_blank">
      <img src="/Areas/AgendaCenter/Assets/Images/HomeIconMinutes.png" alt="Minutes">
    </a>
  </td>
  <td class="downloads"></td>
</tr>
<tr id="row1590" class="catAgendaRow">
  <td>
    <h3 class="noMargin" id="h402232026-1590">
      <strong aria-label="Agenda for February 23, 2026"><abbr title="February">Feb</abbr> 23, 2026</strong>
    </h3>
    <p><a href="/AgendaCenter/ViewFile/Agenda/_02232026-1590?html=true" target="_blank">
      City Council Regular Meeting
    </a></p>
  </td>
  <td class="minutes"></td>
  <td class="downloads"></td>
</tr>
<tr id="row1575" class="catAgendaRow">
  <td>
    <h3 class="noMargin" id="h402092026-1575">
      <strong aria-label="Agenda for February 9, 2026"><abbr title="February">Feb</abbr> 9, 2026</strong>
      — Amended Feb 10, 2026 11:07 AM
    </h3>
    <p><a href="/AgendaCenter/ViewFile/Agenda/_02092026-1575?html=true" target="_blank">
      City Council Regular Meeting
    </a></p>
  </td>
  <td class="minutes">
    <a href="/AgendaCenter/ViewFile/Minutes/_02092026-1575" target="_blank">
      <img alt="Minutes">
    </a>
  </td>
  <td class="downloads"></td>
</tr>
</tbody>
</table>
"""

SAMPLE_CANCELED_HTML = """
<table>
<tbody>
<tr id="row999" class="catAgendaRow">
  <td>
    <h3 class="noMargin">
      <strong><abbr title="March">Mar</abbr> 9, 2026 - CANCELED</strong>
    </h3>
  </td>
  <td class="minutes"></td>
  <td class="downloads"></td>
</tr>
<tr id="row998" class="catAgendaRow">
  <td>
    <h3 class="noMargin">
      <strong><abbr title="February">Feb</abbr> 23, 2026</strong>
    </h3>
    <p><a href="/AgendaCenter/ViewFile/Agenda/_02232026-1590?html=true" target="_blank">
      Planning Commission Agenda
    </a></p>
  </td>
  <td class="minutes"></td>
  <td class="downloads"></td>
</tr>
</tbody>
</table>
"""

SAMPLE_EMPTY_HTML = """
<div>
  <p>No agendas have been posted for this category.</p>
</div>
"""

# Minimal HTML with just h3 dates and links (fallback format)
SAMPLE_MINIMAL_HTML = """
<div>
  <h3>Mar 15, 2026</h3>
  <p><a href="/AgendaCenter/ViewFile/Agenda/_03152026-500?html=true">Board Agenda</a></p>
  <p><a href="/AgendaCenter/ViewFile/Minutes/_03152026-500"><img alt="Minutes"></a></p>
  <h3>Mar 1, 2026</h3>
  <p><a href="/AgendaCenter/ViewFile/Agenda/_03012026-490?html=true">Board Agenda</a></p>
</div>
"""

BASE_URL = "https://www.sterlingheights.gov"


class TestParseAgendaHtml:
    def test_count(self):
        entries = parse_agenda_html(SAMPLE_AGENDA_HTML, BASE_URL)
        assert len(entries) == 3

    def test_dates(self):
        entries = parse_agenda_html(SAMPLE_AGENDA_HTML, BASE_URL)
        assert entries[0]["date"] == "2026-03-09"
        assert entries[1]["date"] == "2026-02-23"
        assert entries[2]["date"] == "2026-02-09"

    def test_agenda_url(self):
        entries = parse_agenda_html(SAMPLE_AGENDA_HTML, BASE_URL)
        assert "/AgendaCenter/ViewFile/Agenda/_03092026-1603" in entries[0]["agenda_url"]
        assert entries[0]["agenda_url"].startswith("https://www.sterlingheights.gov/")

    def test_minutes_url(self):
        entries = parse_agenda_html(SAMPLE_AGENDA_HTML, BASE_URL)
        # First entry has minutes
        assert entries[0]["minutes_url"] is not None
        assert "/AgendaCenter/ViewFile/Minutes/_03092026-1603" in entries[0]["minutes_url"]
        # Second entry has no minutes
        assert entries[1]["minutes_url"] is None

    def test_amended_date_uses_original(self):
        """Amended dates should parse the original meeting date, not the amendment date."""
        entries = parse_agenda_html(SAMPLE_AGENDA_HTML, BASE_URL)
        assert entries[2]["date"] == "2026-02-09"

    def test_canceled_excluded(self):
        entries = parse_agenda_html(SAMPLE_CANCELED_HTML, BASE_URL)
        assert len(entries) == 1
        assert entries[0]["date"] == "2026-02-23"

    def test_empty_page(self):
        entries = parse_agenda_html(SAMPLE_EMPTY_HTML, BASE_URL)
        assert len(entries) == 0

    def test_minimal_format(self):
        """Parser handles HTML without catAgendaRow wrappers."""
        entries = parse_agenda_html(SAMPLE_MINIMAL_HTML, BASE_URL)
        assert len(entries) == 2
        assert entries[0]["date"] == "2026-03-15"
        assert entries[0]["agenda_url"] is not None

    def test_agenda_url_strips_html_param(self):
        """Agenda URLs should point to PDF, not HTML view."""
        entries = parse_agenda_html(SAMPLE_AGENDA_HTML, BASE_URL)
        assert "?html=true" not in entries[0]["agenda_url"]

    def test_full_url_construction(self):
        entries = parse_agenda_html(SAMPLE_AGENDA_HTML, BASE_URL)
        assert entries[0]["agenda_url"].startswith("https://www.sterlingheights.gov/")
        assert entries[0]["minutes_url"].startswith("https://www.sterlingheights.gov/")


class TestParseAgendaHtmlWestland:
    """Verify URL construction works with different domains."""
    def test_westland_urls(self):
        entries = parse_agenda_html(SAMPLE_AGENDA_HTML, "https://www.cityofwestland.com")
        assert entries[0]["agenda_url"].startswith("https://www.cityofwestland.com/")
