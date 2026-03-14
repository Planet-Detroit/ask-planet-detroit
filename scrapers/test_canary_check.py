"""Tests for canary_check.py — DOM canary check system."""

import pytest
from canary_check import (
    run_css_check,
    run_text_check,
    run_element_check,
    format_text_report,
    format_slack_message,
    CANARY_CONFIGS,
)
from bs4 import BeautifulSoup


# --- run_css_check ---

class TestRunCssCheck:
    def test_finds_element(self):
        soup = BeautifulSoup('<div class="views-row">event</div>', "html.parser")
        passed, count = run_css_check(soup, "div.views-row")
        assert passed is True
        assert count == 1

    def test_finds_multiple(self):
        soup = BeautifulSoup('<tr class="rgRow">1</tr><tr class="rgAltRow">2</tr>', "html.parser")
        passed, count = run_css_check(soup, "tr.rgRow, tr.rgAltRow")
        assert passed is True
        assert count == 2

    def test_missing_element(self):
        soup = BeautifulSoup("<div>no match</div>", "html.parser")
        passed, count = run_css_check(soup, "table.table")
        assert passed is False
        assert count == 0

    def test_nested_selector(self):
        soup = BeautifulSoup('<main id="freeform-main"><ul><li>item</li></ul></main>', "html.parser")
        passed, count = run_css_check(soup, "main#freeform-main ul li")
        assert passed is True
        assert count == 1


# --- run_text_check ---

class TestRunTextCheck:
    def test_finds_pattern(self):
        html = '<a href="/Calendar.aspx?EID=2159">Meeting</a>'
        passed, count = run_text_check(html, r"EID=\d+")
        assert passed is True
        assert count == 1

    def test_multiple_matches(self):
        html = '<a href="?EID=1">A</a><a href="?EID=2">B</a>'
        passed, count = run_text_check(html, r"EID=\d+")
        assert passed is True
        assert count == 2

    def test_no_match(self):
        html = "<div>no event IDs here</div>"
        passed, count = run_text_check(html, r"EID=\d+")
        assert passed is False
        assert count == 0

    def test_sitemap_pattern(self):
        html = '<loc>https://www.cityofwarren.org/meetings/city-council-meeting-march-10-2026/</loc>'
        passed, count = run_text_check(html, r"<loc>https://www\.cityofwarren\.org/meetings/")
        assert passed is True


# --- run_element_check ---

class TestRunElementCheck:
    def test_finds_time_datetime(self):
        soup = BeautifulSoup('<time datetime="2026-03-18T12:00:00">Mar 18</time>', "html.parser")
        passed, count = run_element_check(soup, "time", "datetime")
        assert passed is True
        assert count == 1

    def test_missing_attr(self):
        soup = BeautifulSoup("<time>Mar 18</time>", "html.parser")
        passed, count = run_element_check(soup, "time", "datetime")
        assert passed is False


# --- CANARY_CONFIGS validation ---

class TestCanaryConfigs:
    def test_all_have_required_fields(self):
        for key, config in CANARY_CONFIGS.items():
            assert "name" in config, f"{key} missing name"
            assert "url" in config, f"{key} missing url"
            assert "checks" in config, f"{key} missing checks"
            assert len(config["checks"]) > 0, f"{key} has no checks"

    def test_all_checks_have_type(self):
        for key, config in CANARY_CONFIGS.items():
            for check in config["checks"]:
                assert "type" in check, f"{key} check missing type"
                assert "description" in check, f"{key} check missing description"
                assert check["type"] in ("css", "text", "element"), f"{key} has invalid check type"

    def test_css_checks_have_selector(self):
        for key, config in CANARY_CONFIGS.items():
            for check in config["checks"]:
                if check["type"] == "css":
                    assert "selector" in check, f"{key} CSS check missing selector"

    def test_text_checks_have_pattern(self):
        for key, config in CANARY_CONFIGS.items():
            for check in config["checks"]:
                if check["type"] == "text":
                    assert "pattern" in check, f"{key} text check missing pattern"


# --- format_text_report ---

class TestFormatTextReport:
    def test_all_ok(self):
        results = [
            {"name": "Test", "url": "http://test", "status": "ok", "checks": [
                {"type": "css", "description": "table", "passed": True, "count": 1}
            ]},
        ]
        report = format_text_report(results)
        assert "1 OK" in report
        assert "0 FAILED" in report

    def test_failure(self):
        results = [
            {"name": "Bad Scraper", "url": "http://test", "status": "failed", "checks": [
                {"type": "css", "description": "missing element", "passed": False, "count": 0}
            ]},
        ]
        report = format_text_report(results)
        assert "1 FAILED" in report
        assert "Missing: missing element" in report

    def test_error(self):
        results = [
            {"name": "Down Site", "url": "http://test", "status": "error",
             "reason": "Connection refused", "checks": []},
        ]
        report = format_text_report(results)
        assert "1 ERROR" in report
        assert "Connection refused" in report

    def test_skipped(self):
        results = [
            {"name": "Browser Scraper", "url": "http://test", "status": "skipped",
             "reason": "needs_browser", "checks": []},
        ]
        report = format_text_report(results)
        assert "1 skipped" in report


# --- format_slack_message ---

class TestFormatSlackMessage:
    def test_all_ok(self):
        results = [
            {"name": "Test", "url": "http://test", "status": "ok", "checks": []},
        ]
        msg = format_slack_message(results)
        assert "All 1 checks passed" in msg["text"]

    def test_failure(self):
        results = [
            {"name": "Bad Scraper", "url": "http://test", "status": "failed", "checks": [
                {"type": "css", "description": "table rows", "passed": False, "count": 0}
            ]},
        ]
        msg = format_slack_message(results)
        assert "1 issues detected" in msg["text"]
        assert "Bad Scraper" in msg["text"]
