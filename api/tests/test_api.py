"""
Smoke tests for the Ask Planet Detroit API.

These tests verify that:
- All endpoints return correct status codes and response shapes
- Input validation rejects bad input (too short, too long, out of range)
- CORS headers are set correctly for allowed and blocked origins
- The root endpoint returns version info

Tests mock Supabase and Anthropic so they run without real credentials.
Run with: cd api && python -m pytest tests/ -v
"""

import os
import pytest
from unittest.mock import patch, MagicMock

# Set dummy env vars BEFORE importing the app, so it doesn't crash on startup
os.environ.setdefault("SUPABASE_URL", "https://fake.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "fake-key")
os.environ.setdefault("ANTHROPIC_API_KEY", "fake-key")
os.environ.setdefault("OPENAI_API_KEY", "fake-key")


def make_mock_supabase():
    """Create a mock Supabase client that returns empty results for any query."""
    mock = MagicMock()

    # Make chained query methods return the mock itself
    chain = MagicMock()
    chain.execute.return_value = MagicMock(data=[], count=0)
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.gte.return_value = chain
    chain.lt.return_value = chain
    chain.order.return_value = chain
    chain.limit.return_value = chain
    chain.range.return_value = chain
    chain.update.return_value = chain

    mock.from_.return_value = chain
    mock.table.return_value = chain
    mock.rpc.return_value = chain
    return mock


def make_mock_anthropic():
    """Create a mock Anthropic client that returns a simple text response."""
    mock = MagicMock()
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text='{"detected_issues": [], "entities": [], "summary": "Test summary"}')]
    mock.messages.create.return_value = mock_response
    return mock


# Ensure api/ is on the path so 'main' can be imported from any working directory
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Patch external clients before importing the app module
with patch("main.create_client", return_value=make_mock_supabase()):
    with patch("main.anthropic.Anthropic", return_value=make_mock_anthropic()):
        from main import app

from fastapi.testclient import TestClient

client = TestClient(app)


# =========================================================================
# Root and health endpoints
# =========================================================================

class TestRootEndpoints:
    """Test that basic endpoints are alive and return correct shapes."""

    def test_root_returns_200(self):
        response = client.get("/")
        assert response.status_code == 200

    def test_root_has_version(self):
        data = client.get("/").json()
        assert "version" in data
        assert "message" in data

    def test_stats_returns_200(self):
        response = client.get("/api/stats")
        assert response.status_code == 200

    def test_stats_has_expected_keys(self):
        data = client.get("/api/stats").json()
        expected_keys = ["total_chunks", "total_organizations", "upcoming_meetings", "open_comment_periods"]
        for key in expected_keys:
            assert key in data, f"Missing key: {key}"


# =========================================================================
# Meetings endpoints
# =========================================================================

class TestMeetingsEndpoints:
    """Test meetings list and detail endpoints."""

    def test_meetings_returns_200(self):
        response = client.get("/api/meetings")
        assert response.status_code == 200

    def test_meetings_response_shape(self):
        data = client.get("/api/meetings").json()
        assert "meetings" in data
        assert "count" in data
        assert isinstance(data["meetings"], list)

    def test_meetings_with_status_filter(self):
        response = client.get("/api/meetings?status=upcoming")
        assert response.status_code == 200

    def test_meetings_with_agency_filter(self):
        response = client.get("/api/meetings?agency=EGLE")
        assert response.status_code == 200

    def test_meetings_with_pagination(self):
        response = client.get("/api/meetings?limit=5&offset=0")
        assert response.status_code == 200

    def test_meetings_detail_not_found(self):
        # A non-existent ID should return 404 or empty
        response = client.get("/api/meetings/99999")
        # The endpoint may return 404 or 200 with null — both acceptable
        assert response.status_code in [200, 404]


# =========================================================================
# Comment periods endpoints
# =========================================================================

class TestCommentPeriodsEndpoints:
    """Test comment periods list and detail endpoints."""

    def test_comment_periods_returns_200(self):
        response = client.get("/api/comment-periods")
        assert response.status_code == 200

    def test_comment_periods_response_shape(self):
        data = client.get("/api/comment-periods").json()
        assert "comment_periods" in data
        assert isinstance(data["comment_periods"], list)

    def test_comment_periods_detail_not_found(self):
        response = client.get("/api/comment-periods/99999")
        assert response.status_code in [200, 404]


# =========================================================================
# Organizations endpoints
# =========================================================================

class TestOrganizationsEndpoints:
    """Test organizations list and detail endpoints."""

    def test_organizations_returns_200(self):
        response = client.get("/api/organizations")
        assert response.status_code == 200

    def test_organizations_response_shape(self):
        data = client.get("/api/organizations").json()
        assert "organizations" in data
        assert isinstance(data["organizations"], list)


# =========================================================================
# Officials endpoints
# =========================================================================

class TestOfficialsEndpoints:
    """Test officials list and detail endpoints."""

    def test_officials_returns_200(self):
        response = client.get("/api/officials")
        assert response.status_code == 200

    def test_officials_response_shape(self):
        data = client.get("/api/officials").json()
        assert "officials" in data
        assert isinstance(data["officials"], list)


# =========================================================================
# Input validation — SearchRequest
# =========================================================================

class TestSearchValidation:
    """Test that the /api/search endpoint rejects invalid input."""

    def test_search_rejects_empty_question(self):
        # question must be >= 3 chars
        response = client.post("/api/search", json={"question": ""})
        assert response.status_code == 422

    def test_search_rejects_too_short_question(self):
        response = client.post("/api/search", json={"question": "ab"})
        assert response.status_code == 422

    def test_search_rejects_too_long_question(self):
        # question must be <= 1000 chars
        response = client.post("/api/search", json={"question": "x" * 1001})
        assert response.status_code == 422

    def test_search_rejects_num_results_too_high(self):
        response = client.post("/api/search", json={"question": "test query", "num_results": 100})
        assert response.status_code == 422

    def test_search_rejects_num_results_zero(self):
        response = client.post("/api/search", json={"question": "test query", "num_results": 0})
        assert response.status_code == 422

    def test_search_rejects_missing_question(self):
        response = client.post("/api/search", json={})
        assert response.status_code == 422

    def test_search_accepts_valid_input(self):
        # Mock OpenAI embedding call so search can proceed with mocked Supabase
        with patch("main.get_embedding", return_value=[0.0] * 1536):
            response = client.post("/api/search", json={"question": "What is PFAS contamination?"})
            assert response.status_code == 200


# =========================================================================
# Input validation — AnalyzeArticleRequest
# =========================================================================

class TestAnalyzeArticleValidation:
    """Test that /api/analyze-article rejects invalid input."""

    def test_analyze_rejects_missing_article_text(self):
        response = client.post("/api/analyze-article", json={})
        assert response.status_code == 422

    def test_analyze_rejects_too_short_article(self):
        # article_text must be >= 50 chars
        response = client.post("/api/analyze-article", json={"article_text": "too short"})
        assert response.status_code == 422

    def test_analyze_rejects_too_long_article(self):
        # article_text must be <= 50000 chars
        response = client.post("/api/analyze-article", json={"article_text": "x" * 50001})
        assert response.status_code == 422

    def test_analyze_accepts_valid_input(self):
        article = "Michigan's environmental regulators are investigating PFAS contamination " * 5
        response = client.post("/api/analyze-article", json={"article_text": article})
        assert response.status_code == 200


# =========================================================================
# CORS headers
# =========================================================================

class TestCORS:
    """Test that CORS headers allow expected origins and block others."""

    def test_cors_allows_civic_action_builder(self):
        response = client.options(
            "/api/meetings",
            headers={
                "Origin": "https://civic-action-builder.vercel.app",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.headers.get("access-control-allow-origin") == "https://civic-action-builder.vercel.app"

    def test_cors_allows_newsletter_builder(self):
        response = client.options(
            "/api/search",
            headers={
                "Origin": "https://newsletter-builder-azure.vercel.app",
                "Access-Control-Request-Method": "POST",
            },
        )
        assert response.headers.get("access-control-allow-origin") == "https://newsletter-builder-azure.vercel.app"

    def test_cors_allows_localhost_dev(self):
        response = client.options(
            "/api/meetings",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"

    def test_cors_blocks_unknown_origin(self):
        response = client.options(
            "/api/meetings",
            headers={
                "Origin": "https://evil-site.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        # Should NOT return the evil origin in the allow header
        allow_origin = response.headers.get("access-control-allow-origin")
        assert allow_origin != "https://evil-site.com"


# =========================================================================
# Response shape for search
# =========================================================================

class TestSearchResponseShape:
    """Test that search returns the expected response structure."""

    def test_search_response_has_expected_keys(self):
        with patch("main.get_embedding", return_value=[0.0] * 1536):
            response = client.post("/api/search", json={"question": "water quality in Detroit"})
            assert response.status_code == 200
            data = response.json()
            # Should have these top-level keys
            assert "results" in data or "chunks" in data or "answer" in data


# =========================================================================
# API key authentication
# =========================================================================

class TestApiKeyAuth:
    """Test API key authentication on AI endpoints."""

    def test_search_works_without_key_when_no_keys_configured(self):
        # No API_KEYS env var set → auth is skipped (dev mode)
        with patch("main.get_embedding", return_value=[0.0] * 1536):
            response = client.post("/api/search", json={"question": "test query here"})
            assert response.status_code == 200

    def test_search_rejects_missing_key_when_keys_configured(self):
        with patch.dict(os.environ, {"API_KEYS": "test-key-123,test-key-456"}):
            response = client.post("/api/search", json={"question": "test query here"})
            assert response.status_code == 401

    def test_search_rejects_wrong_key_when_keys_configured(self):
        with patch.dict(os.environ, {"API_KEYS": "test-key-123"}):
            response = client.post(
                "/api/search",
                json={"question": "test query here"},
                headers={"Authorization": "Bearer wrong-key"},
            )
            assert response.status_code == 401

    def test_search_accepts_valid_key(self):
        with patch.dict(os.environ, {"API_KEYS": "test-key-123,test-key-456"}):
            with patch("main.get_embedding", return_value=[0.0] * 1536):
                response = client.post(
                    "/api/search",
                    json={"question": "test query here"},
                    headers={"Authorization": "Bearer test-key-123"},
                )
                assert response.status_code == 200

    def test_analyze_rejects_missing_key_when_keys_configured(self):
        with patch.dict(os.environ, {"API_KEYS": "test-key-123"}):
            article = "Michigan regulators investigating PFAS contamination " * 5
            response = client.post(
                "/api/analyze-article",
                json={"article_text": article},
            )
            assert response.status_code == 401

    def test_meetings_does_not_require_key(self):
        # Public data endpoints should remain open even with API_KEYS set
        with patch.dict(os.environ, {"API_KEYS": "test-key-123"}):
            response = client.get("/api/meetings")
            assert response.status_code == 200

    def test_organizations_does_not_require_key(self):
        with patch.dict(os.environ, {"API_KEYS": "test-key-123"}):
            response = client.get("/api/organizations")
            assert response.status_code == 200
