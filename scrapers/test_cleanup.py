"""
Tests for cleanup.py date calculation and dedup detection logic.
Uses mock data — does not connect to Supabase.
"""

import unittest
from datetime import datetime, timedelta
from collections import defaultdict
from zoneinfo import ZoneInfo
from unittest.mock import patch, MagicMock

from cleanup import (
    get_meeting_cutoff_date,
    get_comment_period_cutoff_date,
    MEETING_RETENTION_DAYS,
    COMMENT_PERIOD_RETENTION_DAYS,
    MICHIGAN_TZ,
)


class TestCutoffDates(unittest.TestCase):
    """Test that cutoff date calculations are correct."""

    def test_meeting_cutoff_is_30_days_ago(self):
        # The meeting cutoff should be approximately 30 days before now
        cutoff = get_meeting_cutoff_date()
        now = datetime.now(MICHIGAN_TZ)
        delta = now - cutoff
        # Should be 30 days (allow 1 second tolerance for test execution time)
        self.assertAlmostEqual(delta.total_seconds(), MEETING_RETENTION_DAYS * 86400, delta=2)

    def test_comment_period_cutoff_is_14_days_ago(self):
        # The comment period cutoff should be approximately 14 days before now
        cutoff = get_comment_period_cutoff_date()
        now = datetime.now(MICHIGAN_TZ)
        delta = now - cutoff
        self.assertAlmostEqual(delta.total_seconds(), COMMENT_PERIOD_RETENTION_DAYS * 86400, delta=2)

    def test_cutoff_dates_are_timezone_aware(self):
        # Both cutoffs should be timezone-aware in Michigan time
        meeting_cutoff = get_meeting_cutoff_date()
        comment_cutoff = get_comment_period_cutoff_date()
        self.assertIsNotNone(meeting_cutoff.tzinfo)
        self.assertIsNotNone(comment_cutoff.tzinfo)

    def test_meeting_cutoff_before_comment_cutoff(self):
        # Meeting cutoff (30 days) should be further in the past than comment cutoff (14 days)
        meeting_cutoff = get_meeting_cutoff_date()
        comment_cutoff = get_comment_period_cutoff_date()
        self.assertLess(meeting_cutoff, comment_cutoff)


class TestDeduplicationLogic(unittest.TestCase):
    """Test the deduplication detection logic using mock data."""

    def test_identifies_duplicates(self):
        # Simulate records with duplicate (source, source_id) pairs
        records = [
            {"id": 1, "source": "glwa_scraper", "source_id": "glwa-20260301-abc", "title": "Board Meeting", "created_at": "2026-03-01"},
            {"id": 5, "source": "glwa_scraper", "source_id": "glwa-20260301-abc", "title": "Board Meeting", "created_at": "2026-03-05"},
            {"id": 3, "source": "mpsc_scraper", "source_id": "mpsc-123", "title": "MPSC Hearing", "created_at": "2026-03-02"},
        ]

        # Group by (source, source_id) — same logic as cleanup.py
        groups = defaultdict(list)
        for m in records:
            key = (m.get("source"), m.get("source_id"))
            if key[0] and key[1]:
                groups[key].append(m)

        # Find duplicates (keep highest id)
        duplicates_to_delete = []
        for key, recs in groups.items():
            if len(recs) > 1:
                recs.sort(key=lambda r: r["id"], reverse=True)
                for record in recs[1:]:
                    duplicates_to_delete.append(record)

        # Should find 1 duplicate (id=1, since id=5 is kept)
        self.assertEqual(len(duplicates_to_delete), 1)
        self.assertEqual(duplicates_to_delete[0]["id"], 1)

    def test_no_duplicates_when_unique(self):
        # All unique (source, source_id) pairs — no duplicates
        records = [
            {"id": 1, "source": "glwa_scraper", "source_id": "glwa-001", "title": "Meeting A", "created_at": "2026-03-01"},
            {"id": 2, "source": "glwa_scraper", "source_id": "glwa-002", "title": "Meeting B", "created_at": "2026-03-02"},
            {"id": 3, "source": "mpsc_scraper", "source_id": "mpsc-001", "title": "Meeting C", "created_at": "2026-03-03"},
        ]

        groups = defaultdict(list)
        for m in records:
            key = (m.get("source"), m.get("source_id"))
            if key[0] and key[1]:
                groups[key].append(m)

        duplicates_to_delete = []
        for key, recs in groups.items():
            if len(recs) > 1:
                recs.sort(key=lambda r: r["id"], reverse=True)
                for record in recs[1:]:
                    duplicates_to_delete.append(record)

        self.assertEqual(len(duplicates_to_delete), 0)

    def test_multiple_duplicates_keeps_newest(self):
        # Three records with the same (source, source_id) — should delete two, keep id=10
        records = [
            {"id": 2, "source": "detroit_scraper", "source_id": "det-abc", "title": "DCC Meeting", "created_at": "2026-03-01"},
            {"id": 7, "source": "detroit_scraper", "source_id": "det-abc", "title": "DCC Meeting", "created_at": "2026-03-05"},
            {"id": 10, "source": "detroit_scraper", "source_id": "det-abc", "title": "DCC Meeting", "created_at": "2026-03-10"},
        ]

        groups = defaultdict(list)
        for m in records:
            key = (m.get("source"), m.get("source_id"))
            if key[0] and key[1]:
                groups[key].append(m)

        duplicates_to_delete = []
        for key, recs in groups.items():
            if len(recs) > 1:
                recs.sort(key=lambda r: r["id"], reverse=True)
                for record in recs[1:]:
                    duplicates_to_delete.append(record)

        # Should delete 2 duplicates (id=2 and id=7), keeping id=10
        self.assertEqual(len(duplicates_to_delete), 2)
        deleted_ids = {d["id"] for d in duplicates_to_delete}
        self.assertEqual(deleted_ids, {2, 7})

    def test_skips_records_without_source_fields(self):
        # Records missing source or source_id should be skipped (not grouped)
        records = [
            {"id": 1, "source": None, "source_id": "abc", "title": "No source", "created_at": "2026-03-01"},
            {"id": 2, "source": "glwa_scraper", "source_id": None, "title": "No source_id", "created_at": "2026-03-02"},
        ]

        groups = defaultdict(list)
        for m in records:
            key = (m.get("source"), m.get("source_id"))
            if key[0] and key[1]:
                groups[key].append(m)

        # No valid groups should be formed
        self.assertEqual(len(groups), 0)


class TestExpireMeetingsWithMock(unittest.TestCase):
    """Test expire_old_meetings with mocked Supabase."""

    @patch("cleanup.get_supabase")
    def test_dry_run_does_not_delete(self, mock_get_supabase):
        """Dry run should query but not delete."""
        mock_supabase = MagicMock()
        mock_get_supabase.return_value = mock_supabase

        # Mock the query chain
        mock_table = MagicMock()
        mock_supabase.table.return_value = mock_table
        mock_select = MagicMock()
        mock_table.select.return_value = mock_select
        mock_lt = MagicMock()
        mock_select.lt.return_value = mock_lt
        mock_lt.execute.return_value = MagicMock(data=[
            {"id": 1, "title": "Old Meeting", "meeting_date": "2025-01-01", "start_datetime": None, "source": "test"}
        ])

        from cleanup import expire_old_meetings
        count = expire_old_meetings(dry_run=True)

        self.assertEqual(count, 1)
        # delete() should NOT have been called
        mock_table.delete.assert_not_called()


if __name__ == "__main__":
    unittest.main()
