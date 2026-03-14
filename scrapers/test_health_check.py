"""Tests for the health check report generator."""

import pytest
from unittest.mock import patch, MagicMock
from health_check import generate_report, format_text_report, format_slack_message


@pytest.fixture
def sample_report():
    """A sample report for testing formatters."""
    return {
        "generated_at": "2026-03-14T10:00:00-04:00",
        "totals": {
            "meetings_total": 100,
            "meetings_upcoming": 60,
            "meetings_past": 40,
            "comment_periods_total": 10,
            "comment_periods_open": 5,
            "agenda_summaries": 20,
        },
        "by_source": {
            "detroit_scraper": {"total": 50, "upcoming": 30, "with_agenda": 20, "with_virtual": 50},
            "egle_scraper": {"total": 10, "upcoming": 5, "with_agenda": 10, "with_virtual": 2},
        },
        "warnings": ["detroit_scraper: 5 meetings older than 30 days still in DB"],
        "data_freshness": {
            "detroit_scraper": "2026-03-14",
            "egle_scraper": "2026-03-10",
        },
    }


class TestFormatTextReport:
    def test_contains_header(self, sample_report):
        text = format_text_report(sample_report)
        assert "SCRAPER HEALTH REPORT" in text

    def test_contains_totals(self, sample_report):
        text = format_text_report(sample_report)
        assert "60 upcoming" in text
        assert "5 open" in text

    def test_contains_sources(self, sample_report):
        text = format_text_report(sample_report)
        assert "detroit_scraper" in text
        assert "egle_scraper" in text

    def test_contains_warnings(self, sample_report):
        text = format_text_report(sample_report)
        assert "WARNINGS" in text
        assert "older than 30 days" in text

    def test_no_warnings(self, sample_report):
        sample_report["warnings"] = []
        text = format_text_report(sample_report)
        assert "No warnings" in text


class TestFormatSlackMessage:
    def test_returns_dict_with_text(self, sample_report):
        msg = format_slack_message(sample_report)
        assert "text" in msg
        assert isinstance(msg["text"], str)

    def test_healthy_emoji_when_no_warnings(self, sample_report):
        sample_report["warnings"] = []
        msg = format_slack_message(sample_report)
        assert "white_check_mark" in msg["text"]

    def test_warning_emoji_when_few_warnings(self, sample_report):
        msg = format_slack_message(sample_report)
        assert "warning" in msg["text"]

    def test_alert_emoji_when_many_warnings(self, sample_report):
        sample_report["warnings"] = ["w1", "w2", "w3", "w4"]
        msg = format_slack_message(sample_report)
        assert "rotating_light" in msg["text"]

    def test_contains_totals(self, sample_report):
        msg = format_slack_message(sample_report)
        assert "60 upcoming meetings" in msg["text"]
        assert "5 open comment periods" in msg["text"]
