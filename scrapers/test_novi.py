"""Tests for novi_scraper.py — City of Novi meeting scraper."""

import pytest
from novi_scraper import (
    parse_listing_page,
    determine_meeting_type,
    get_issue_tags,
    BOARD_CONFIGS,
    DEFAULT_TAGS,
)


# --- Sample HTML ---

SAMPLE_COUNCIL_HTML = """
<div class="content-area">
  <div class="card">
    <div class="card-header bg-dark text-white">Mar 9, 2026</div>
    <div class="card-body">
      <a class="btn btn-green" href="/agendas-minutes/city-council/2026/mar-9-2026/">Agenda</a>
    </div>
  </div>
  <div class="card">
    <div class="card-header bg-dark text-white">Feb 23, 2026</div>
    <div class="card-body">
      <a class="btn btn-green" href="/agendas-minutes/city-council/2026/feb-23-2026/">Agenda</a>
      <a class="btn btn-green" href="/media/q5tgfjoc/260223m.pdf">Minutes</a>
    </div>
  </div>
  <div class="card">
    <div class="card-header bg-dark text-white">Jan 13, 2026</div>
    <div class="card-body">
      <a class="btn btn-green" href="/agendas-minutes/city-council/2026/jan-13-2026/">Agenda</a>
      <a class="btn btn-green" href="/media/abc123/260113m.pdf">Minutes</a>
    </div>
  </div>
</div>
"""

# Planning Commission uses div > strong (date) + p (links) format
SAMPLE_PLANNING_HTML = """
<div class="content-area">
  <div>
    <strong>Mar 11, 2026</strong>
    <p>
      <a href="/agendas-minutes/planning-commission/2026/mar-11-2026/">Agenda</a>
      <a href="/media/eq1o4poj/260311as.pdf">Action Summary</a>
    </p>
  </div>
  <div>
    <strong>Feb 25, 2026</strong>
    <p>
      <a href="/agendas-minutes/planning-commission/2026/feb-25-2026/">Agenda</a>
      <a href="/media/y34iz3ft/260225m.pdf">Minutes</a>
    </p>
  </div>
  <div>
    <strong>Jan 28, 2026 - CANCELED</strong>
  </div>
</div>
"""

# ZBA uses flat p (date) + p (links) format
SAMPLE_ZBA_HTML = """
<div class="content-area">
  <p>Mar 10, 2026</p>
  <p><a href="/agendas-minutes/zoning-board-of-appeals/2026/mar-10-2026/">Agenda</a></p>
  <p>Feb 10, 2026</p>
  <p>
    <a href="/agendas-minutes/zoning-board-of-appeals/2026/feb-10-2026/">Agenda</a>
    <a href="/media/wi3dbmm5/260113as.pdf">Action Summary</a>
    <a href="/media/qqdfcb4z/260210m.pdf">Minutes</a>
  </p>
</div>
"""

SAMPLE_EMPTY_HTML = """
<div class="content-area">
  <p>No meetings scheduled.</p>
</div>
"""


# --- determine_meeting_type ---

class TestDetermineMeetingType:
    def test_city_council(self):
        assert determine_meeting_type("City Council") == "board_meeting"

    def test_planning(self):
        assert determine_meeting_type("Planning Commission") == "committee_meeting"

    def test_zba(self):
        assert determine_meeting_type("Zoning Board of Appeals") == "committee_meeting"

    def test_default(self):
        assert determine_meeting_type("Some Committee") == "committee_meeting"


# --- get_issue_tags ---

class TestGetIssueTags:
    def test_planning(self):
        tags = get_issue_tags("Planning Commission")
        assert "planning" in tags

    def test_environmental(self):
        tags = get_issue_tags("Environmental Sustainability Committee")
        assert "environment" in tags

    def test_parks(self):
        tags = get_issue_tags("Parks, Recreation and Cultural Services Commission")
        assert "parks" in tags

    def test_default(self):
        assert get_issue_tags("City Council") == DEFAULT_TAGS


# --- BOARD_CONFIGS validation ---

class TestBoardConfigs:
    def test_all_configs_have_required_fields(self):
        for key, config in BOARD_CONFIGS.items():
            assert "name" in config, f"{key} missing name"
            assert "slug" in config, f"{key} missing slug"

    def test_city_council_has_time(self):
        assert BOARD_CONFIGS["city_council"]["time"] == "19:00"


# --- parse_listing_page ---

class TestParseListingPage:
    def test_council_div_format(self):
        """City Council uses <div>/<strong> format."""
        entries = parse_listing_page(SAMPLE_COUNCIL_HTML, "city_council")
        assert len(entries) == 3

    def test_council_dates(self):
        entries = parse_listing_page(SAMPLE_COUNCIL_HTML, "city_council")
        assert entries[0]["date"] == "2026-03-09"
        assert entries[1]["date"] == "2026-02-23"

    def test_council_agenda_url(self):
        entries = parse_listing_page(SAMPLE_COUNCIL_HTML, "city_council")
        assert entries[0]["agenda_url"] is not None
        assert "/agendas-minutes/city-council/2026/mar-9-2026/" in entries[0]["agenda_url"]

    def test_council_minutes_url(self):
        entries = parse_listing_page(SAMPLE_COUNCIL_HTML, "city_council")
        # First entry has no minutes
        assert entries[0]["minutes_url"] is None
        # Second entry has minutes
        assert entries[1]["minutes_url"] is not None
        assert "260223m.pdf" in entries[1]["minutes_url"]

    def test_planning_strong_format(self):
        """Planning Commission uses div/strong date + p links format."""
        entries = parse_listing_page(SAMPLE_PLANNING_HTML, "planning_commission")
        # Canceled meeting should be excluded
        assert len(entries) == 2

    def test_planning_dates(self):
        entries = parse_listing_page(SAMPLE_PLANNING_HTML, "planning_commission")
        assert entries[0]["date"] == "2026-03-11"
        assert entries[1]["date"] == "2026-02-25"

    def test_planning_agenda_url(self):
        entries = parse_listing_page(SAMPLE_PLANNING_HTML, "planning_commission")
        assert entries[0]["agenda_url"] is not None
        assert "/planning-commission/2026/mar-11-2026/" in entries[0]["agenda_url"]

    def test_planning_minutes_url(self):
        entries = parse_listing_page(SAMPLE_PLANNING_HTML, "planning_commission")
        # First entry has no minutes (only Action Summary)
        assert entries[0]["minutes_url"] is None
        # Second entry has minutes
        assert entries[1]["minutes_url"] is not None
        assert "260225m.pdf" in entries[1]["minutes_url"]

    def test_canceled_excluded(self):
        """Meetings marked CANCELED should be skipped."""
        entries = parse_listing_page(SAMPLE_PLANNING_HTML, "planning_commission")
        dates = [e["date"] for e in entries]
        assert "2026-01-28" not in dates

    def test_zba_paragraph_format(self):
        """ZBA uses flat p date + p links format."""
        entries = parse_listing_page(SAMPLE_ZBA_HTML, "zba")
        assert len(entries) == 2

    def test_zba_dates(self):
        entries = parse_listing_page(SAMPLE_ZBA_HTML, "zba")
        assert entries[0]["date"] == "2026-03-10"
        assert entries[1]["date"] == "2026-02-10"

    def test_zba_agenda_url(self):
        entries = parse_listing_page(SAMPLE_ZBA_HTML, "zba")
        assert entries[0]["agenda_url"] is not None
        assert "/zoning-board-of-appeals/2026/mar-10-2026/" in entries[0]["agenda_url"]

    def test_zba_minutes_url(self):
        entries = parse_listing_page(SAMPLE_ZBA_HTML, "zba")
        assert entries[0]["minutes_url"] is None  # First entry has no minutes
        assert entries[1]["minutes_url"] is not None
        assert "260210m.pdf" in entries[1]["minutes_url"]

    def test_empty_page(self):
        entries = parse_listing_page(SAMPLE_EMPTY_HTML, "city_council")
        assert len(entries) == 0

    def test_full_url_construction(self):
        entries = parse_listing_page(SAMPLE_COUNCIL_HTML, "city_council")
        assert entries[0]["agenda_url"].startswith("https://www.cityofnovi.org/")
