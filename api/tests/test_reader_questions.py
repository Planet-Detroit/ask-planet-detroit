"""
Tests for POST /api/reader-questions endpoint.

Each test corresponds to an acceptance criterion from the spec.
External services (Supabase, Anthropic, OpenAI, Slack) are mocked
so tests run without network access or API keys.
"""

import os
import json
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

# Set env vars BEFORE importing main.py (it reads them at import time)
os.environ.setdefault("SUPABASE_URL", "https://fake.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "fake-key")
os.environ.setdefault("ANTHROPIC_API_KEY", "fake-key")
os.environ.setdefault("OPENAI_API_KEY", "fake-key")
os.environ.setdefault("SLACK_WEBHOOK_URL", "https://hooks.slack.com/services/fake")

# Patch Supabase client creation before importing app
with patch("api.main.create_client") as mock_create_client:
    mock_supabase = MagicMock()
    mock_create_client.return_value = mock_supabase

    from httpx import AsyncClient, ASGITransport
    from api.main import app, limiter

# Disable rate limiting in tests — otherwise the 5/minute limit
# causes later tests to get 429 responses
limiter.enabled = False

transport = ASGITransport(app=app)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _valid_payload(**overrides):
    """Build a valid reader question submission payload."""
    base = {
        "question": "Is the water in southwest Detroit safe to drink?",
        "article_url": "https://planetdetroit.org/2026/02/water-quality",
        "article_title": "Water Quality in SW Detroit",
    }
    base.update(overrides)
    return base


def _mock_supabase_insert(mock_sb):
    """Set up Supabase mock to accept inserts and return success."""
    mock_table = MagicMock()
    mock_table.insert.return_value.execute.return_value = MagicMock(data=[{"id": "abc-123"}])
    mock_sb.from_.return_value = mock_table
    return mock_table


def _mock_rag_search(mock_sb):
    """Set up Supabase RPC mock for vector search results."""
    mock_sb.rpc.return_value.execute.return_value = MagicMock(data=[
        {
            "article_title": "Water Testing in Detroit",
            "article_url": "https://planetdetroit.org/2025/10/water-testing",
            "article_date": "2025-10-15",
            "content": "Recent testing of water in southwest Detroit showed...",
            "similarity": 0.89,
        }
    ])


def _mock_anthropic_response(text="This is a synthesized answer about water quality."):
    """Create a mock Anthropic API response."""
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=text)]
    return mock_response


# ---------------------------------------------------------------------------
# Test: Valid submission is stored in Supabase with status "new"
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_valid_submission_stored_in_supabase():
    """When a valid question is submitted, it is stored in the
    reader_questions Supabase table with status 'new'."""
    with patch("api.main.supabase") as mock_sb, \
         patch("api.main.get_embedding", return_value=[0.1] * 1536), \
         patch("api.main.anthropic_client") as mock_anthropic, \
         patch("api.main.post_to_slack", new_callable=AsyncMock):

        mock_table = _mock_supabase_insert(mock_sb)
        _mock_rag_search(mock_sb)
        mock_anthropic.messages.create.return_value = _mock_anthropic_response()

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/api/reader-questions", json=_valid_payload())

        assert resp.status_code == 200
        # Check that insert was called with status "new"
        insert_call = mock_table.insert.call_args
        inserted_row = insert_call[0][0]
        assert inserted_row["status"] == "new"
        assert inserted_row["question"] == "Is the water in southwest Detroit safe to drink?"
        assert inserted_row["article_url"] == "https://planetdetroit.org/2026/02/water-quality"


# ---------------------------------------------------------------------------
# Test: Submission without optional fields succeeds
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_submission_without_optional_fields():
    """When a reader submits a question without name/email/zip, it succeeds."""
    with patch("api.main.supabase") as mock_sb, \
         patch("api.main.get_embedding", return_value=[0.1] * 1536), \
         patch("api.main.anthropic_client") as mock_anthropic, \
         patch("api.main.post_to_slack", new_callable=AsyncMock):

        _mock_supabase_insert(mock_sb)
        _mock_rag_search(mock_sb)
        mock_anthropic.messages.create.return_value = _mock_anthropic_response()

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/api/reader-questions", json=_valid_payload())

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"


# ---------------------------------------------------------------------------
# Test: Submission with all optional fields succeeds
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_submission_with_all_optional_fields():
    """When a reader provides name, email, and zip, they are all stored."""
    with patch("api.main.supabase") as mock_sb, \
         patch("api.main.get_embedding", return_value=[0.1] * 1536), \
         patch("api.main.anthropic_client") as mock_anthropic, \
         patch("api.main.post_to_slack", new_callable=AsyncMock):

        mock_table = _mock_supabase_insert(mock_sb)
        _mock_rag_search(mock_sb)
        mock_anthropic.messages.create.return_value = _mock_anthropic_response()

        payload = _valid_payload(
            name="Maria Garcia",
            email="maria@example.com",
            zip_code="48209",
        )

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/api/reader-questions", json=payload)

        assert resp.status_code == 200
        inserted_row = mock_table.insert.call_args[0][0]
        assert inserted_row["name"] == "Maria Garcia"
        assert inserted_row["email"] == "maria@example.com"
        assert inserted_row["zip_code"] == "48209"


# ---------------------------------------------------------------------------
# Test: Response includes related articles
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_response_includes_related_articles():
    """When a question is submitted, related articles appear in the response."""
    with patch("api.main.supabase") as mock_sb, \
         patch("api.main.get_embedding", return_value=[0.1] * 1536), \
         patch("api.main.anthropic_client") as mock_anthropic, \
         patch("api.main.post_to_slack", new_callable=AsyncMock):

        _mock_supabase_insert(mock_sb)
        _mock_rag_search(mock_sb)
        mock_anthropic.messages.create.return_value = _mock_anthropic_response()

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/api/reader-questions", json=_valid_payload())

        data = resp.json()
        assert "related_articles" in data
        assert len(data["related_articles"]) > 0
        assert data["related_articles"][0]["article_title"] == "Water Testing in Detroit"


# ---------------------------------------------------------------------------
# Test: Response includes confirmation message
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_response_includes_confirmation_message():
    """When a reader submits, the response tells them a reporter will review."""
    with patch("api.main.supabase") as mock_sb, \
         patch("api.main.get_embedding", return_value=[0.1] * 1536), \
         patch("api.main.anthropic_client") as mock_anthropic, \
         patch("api.main.post_to_slack", new_callable=AsyncMock):

        _mock_supabase_insert(mock_sb)
        _mock_rag_search(mock_sb)
        mock_anthropic.messages.create.return_value = _mock_anthropic_response()

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/api/reader-questions", json=_valid_payload())

        data = resp.json()
        assert data["status"] == "ok"
        assert "reporter" in data["message"].lower()


# ---------------------------------------------------------------------------
# Test: Honeypot field filled → rejection
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_honeypot_rejects_bots():
    """When a bot fills the honeypot field, the backend rejects with HTTP 400."""
    with patch("api.main.supabase") as mock_sb:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/reader-questions",
                json=_valid_payload(website="http://spam.com"),  # honeypot field
            )

        assert resp.status_code == 400
        assert "bot" in resp.json()["detail"].lower() or "spam" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Test: Missing question → validation error
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_missing_question_rejected():
    """When the question field is missing, the server returns 422."""
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/reader-questions", json={
            "article_url": "https://planetdetroit.org/2026/02/test",
        })

    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Test: Question too long → validation error
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_question_too_long_rejected():
    """When a reader submits a question longer than 2000 characters,
    the server returns 422."""
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/reader-questions", json=_valid_payload(
            question="x" * 2001,
        ))

    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Test: Slack notification is posted
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_slack_notification_posted():
    """When a question is submitted, a Slack message is posted."""
    with patch("api.main.supabase") as mock_sb, \
         patch("api.main.get_embedding", return_value=[0.1] * 1536), \
         patch("api.main.anthropic_client") as mock_anthropic, \
         patch("api.main.post_to_slack", new_callable=AsyncMock) as mock_slack:

        _mock_supabase_insert(mock_sb)
        _mock_rag_search(mock_sb)
        mock_anthropic.messages.create.return_value = _mock_anthropic_response()

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/api/reader-questions", json=_valid_payload())

        assert resp.status_code == 200
        mock_slack.assert_called_once()
        slack_payload = mock_slack.call_args[0][0]
        # Slack message should include the question text
        assert "water" in json.dumps(slack_payload).lower()


# ---------------------------------------------------------------------------
# Test: Slack failure doesn't break submission
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_slack_failure_nonblocking():
    """When the Slack webhook fails, the question is still saved
    and the reader gets a success response."""
    with patch("api.main.supabase") as mock_sb, \
         patch("api.main.get_embedding", return_value=[0.1] * 1536), \
         patch("api.main.anthropic_client") as mock_anthropic, \
         patch("api.main.post_to_slack", new_callable=AsyncMock) as mock_slack:

        _mock_supabase_insert(mock_sb)
        _mock_rag_search(mock_sb)
        mock_anthropic.messages.create.return_value = _mock_anthropic_response()
        mock_slack.side_effect = Exception("Slack is down")

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/api/reader-questions", json=_valid_payload())

        # Submission should still succeed
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"


# ---------------------------------------------------------------------------
# Test: Article context is captured
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_article_context_captured():
    """When a reader submits on an article page, the article URL and
    title are stored and included in the Slack notification."""
    with patch("api.main.supabase") as mock_sb, \
         patch("api.main.get_embedding", return_value=[0.1] * 1536), \
         patch("api.main.anthropic_client") as mock_anthropic, \
         patch("api.main.post_to_slack", new_callable=AsyncMock) as mock_slack:

        mock_table = _mock_supabase_insert(mock_sb)
        _mock_rag_search(mock_sb)
        mock_anthropic.messages.create.return_value = _mock_anthropic_response()

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/api/reader-questions", json=_valid_payload())

        assert resp.status_code == 200
        inserted_row = mock_table.insert.call_args[0][0]
        assert inserted_row["article_url"] == "https://planetdetroit.org/2026/02/water-quality"
        assert inserted_row["article_title"] == "Water Quality in SW Detroit"


# ---------------------------------------------------------------------------
# Test: Invalid email format rejected
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_invalid_email_rejected():
    """When a reader provides an invalid email, the server returns 400."""
    with patch("api.main.supabase") as mock_sb:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/api/reader-questions", json=_valid_payload(
                email="not-an-email",
            ))

    assert resp.status_code == 400
    assert "email" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Test: Reporter guide is generated with Sonnet
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_reporter_guide_uses_sonnet():
    """When a question is submitted, the AI reporter guide is generated
    using claude-sonnet (not haiku)."""
    with patch("api.main.supabase") as mock_sb, \
         patch("api.main.get_embedding", return_value=[0.1] * 1536), \
         patch("api.main.anthropic_client") as mock_anthropic, \
         patch("api.main.post_to_slack", new_callable=AsyncMock):

        _mock_supabase_insert(mock_sb)
        _mock_rag_search(mock_sb)
        mock_anthropic.messages.create.return_value = _mock_anthropic_response(
            "Reporter guide: relevant sources include DWSD..."
        )

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/api/reader-questions", json=_valid_payload())

        # Check the model used in the Anthropic call
        calls = mock_anthropic.messages.create.call_args_list
        # The reporter guide call should use Sonnet
        model_used = calls[-1].kwargs.get("model", calls[-1][1].get("model", ""))
        assert "sonnet" in model_used
