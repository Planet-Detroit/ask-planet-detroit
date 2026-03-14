"""Tests for the generic agenda summarizer module."""

import pytest
from unittest.mock import patch, MagicMock
from agenda_summarizer import (
    _extract_html_text,
    _extract_pdf_text,
    fetch_agenda_text,
)


class TestHtmlExtraction:
    """Test HTML text extraction from agenda pages."""

    def test_extracts_text_from_simple_html(self):
        html = "<html><body><h1>Meeting Agenda</h1><p>Item 1: Budget review</p><p>Item 2: Water rates</p></body></html>"
        result = _extract_html_text(html)
        assert "Meeting Agenda" in result
        assert "Budget review" in result
        assert "Water rates" in result

    def test_strips_script_and_style_tags(self):
        html = "<html><body><script>alert('xss')</script><style>.foo{}</style><p>Real content here with enough text to pass the minimum length check for extraction</p></body></html>"
        result = _extract_html_text(html)
        assert "alert" not in result
        assert ".foo" not in result
        assert "Real content here" in result

    def test_strips_nav_and_footer(self):
        html = "<html><body><nav>Site Navigation Links</nav><main><p>Agenda item about water quality standards and public comment period for residents</p></main><footer>Copyright 2026</footer></body></html>"
        result = _extract_html_text(html)
        assert "water quality" in result
        assert "Site Navigation" not in result
        assert "Copyright" not in result

    def test_returns_none_for_tiny_content(self):
        html = "<html><body><p>Hi</p></body></html>"
        result = _extract_html_text(html)
        assert result is None

    def test_cleans_excessive_whitespace(self):
        html = "<html><body><p>Item 1 about budget review and fiscal year planning for the department</p>\n\n\n\n\n<p>Item 2 about water infrastructure improvements and capital spending</p></body></html>"
        result = _extract_html_text(html)
        assert result is not None
        # Should not have more than 2 consecutive newlines
        assert "\n\n\n" not in result


class TestPdfExtraction:
    """Test PDF text extraction."""

    def test_returns_none_for_invalid_pdf(self):
        result = _extract_pdf_text(b"not a pdf")
        assert result is None

    def test_returns_none_for_empty_bytes(self):
        result = _extract_pdf_text(b"")
        assert result is None


class TestFetchAgendaText:
    """Test the fetch_agenda_text dispatcher."""

    def test_returns_none_for_empty_url(self):
        assert fetch_agenda_text("") is None
        assert fetch_agenda_text(None) is None

    @patch("agenda_summarizer.httpx")
    def test_handles_404(self, mock_httpx):
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_httpx.get.return_value = mock_resp
        result = fetch_agenda_text("https://example.com/agenda.pdf")
        assert result is None

    @patch("agenda_summarizer.httpx")
    def test_detects_pdf_by_extension(self, mock_httpx):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.headers = {"content-type": "application/octet-stream"}
        mock_resp.content = b"not a real pdf"
        mock_httpx.get.return_value = mock_resp

        # Should attempt PDF extraction (which will fail on invalid content)
        result = fetch_agenda_text("https://example.com/agenda.pdf")
        assert result is None  # Invalid PDF returns None

    @patch("agenda_summarizer.httpx")
    def test_detects_pdf_by_content_type(self, mock_httpx):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.headers = {"content-type": "application/pdf"}
        mock_resp.content = b"not a real pdf"
        mock_httpx.get.return_value = mock_resp

        result = fetch_agenda_text("https://example.com/document")
        assert result is None  # Invalid PDF returns None

    @patch("agenda_summarizer.httpx")
    def test_falls_back_to_html(self, mock_httpx):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.headers = {"content-type": "text/html"}
        mock_resp.text = "<html><body><p>This is an agenda with enough content to be valid for extraction purposes</p></body></html>"
        mock_httpx.get.return_value = mock_resp

        result = fetch_agenda_text("https://example.com/meeting")
        assert result is not None
        assert "agenda" in result.lower()
