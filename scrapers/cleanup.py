"""
Data Cleanup & Expiration
Removes stale records from the database:
- Meetings older than 30 days
- Comment periods with end_date older than 14 days
- Does NOT touch agenda_summaries (kept as journalism archive)

Also deduplicates meetings on first run.

Usage:
    python cleanup.py              # Run all cleanup
    python cleanup.py --dry-run    # Show what would be deleted without deleting
    python cleanup.py --dedup-only # Only fix duplicates
"""

import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
MICHIGAN_TZ = ZoneInfo("America/Detroit")

# How far back to keep records
MEETING_RETENTION_DAYS = 30
COMMENT_PERIOD_RETENTION_DAYS = 14


def get_supabase():
    """Initialize Supabase client."""
    from supabase import create_client
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def get_meeting_cutoff_date():
    """Return the cutoff datetime for meeting expiration (30 days ago)."""
    return datetime.now(MICHIGAN_TZ) - timedelta(days=MEETING_RETENTION_DAYS)


def get_comment_period_cutoff_date():
    """Return the cutoff date for comment period expiration (14 days ago)."""
    return datetime.now(MICHIGAN_TZ) - timedelta(days=COMMENT_PERIOD_RETENTION_DAYS)


def expire_old_meetings(dry_run=False):
    """Delete meetings older than MEETING_RETENTION_DAYS.

    Uses start_datetime if available, falls back to meeting_date.
    Returns the count of deleted records.
    """
    supabase = get_supabase()
    cutoff = get_meeting_cutoff_date()
    cutoff_date_str = cutoff.strftime("%Y-%m-%d")
    cutoff_iso = cutoff.isoformat()

    # Find expired meetings: start_datetime < cutoff OR meeting_date < cutoff_date
    # Supabase doesn't support OR filters easily, so we query by meeting_date
    # (which all records have) as the primary filter
    result = supabase.table("meetings") \
        .select("id, title, meeting_date, start_datetime, source") \
        .lt("meeting_date", cutoff_date_str) \
        .execute()

    expired = result.data or []

    if dry_run:
        if expired:
            print(f"  [DRY RUN] Would expire {len(expired)} meetings older than {cutoff_date_str}:")
            for m in expired[:10]:
                print(f"    - {m.get('title', 'Unknown')[:50]} ({m.get('meeting_date')}) [{m.get('source')}]")
            if len(expired) > 10:
                print(f"    ... and {len(expired) - 10} more")
        return len(expired)

    # Delete expired meetings
    deleted_count = 0
    for m in expired:
        try:
            supabase.table("meetings").delete().eq("id", m["id"]).execute()
            deleted_count += 1
        except Exception as e:
            print(f"  Error deleting meeting {m['id']}: {e}")

    if deleted_count:
        print(f"  Expired {deleted_count} meetings older than {cutoff_date_str}")

    return deleted_count


def expire_old_comment_periods(dry_run=False):
    """Delete comment periods with end_date older than COMMENT_PERIOD_RETENTION_DAYS.

    Returns the count of deleted records.
    """
    supabase = get_supabase()
    cutoff = get_comment_period_cutoff_date()
    cutoff_date_str = cutoff.strftime("%Y-%m-%d")

    result = supabase.table("comment_periods") \
        .select("id, title, end_date, source") \
        .lt("end_date", cutoff_date_str) \
        .execute()

    expired = result.data or []

    if dry_run:
        if expired:
            print(f"  [DRY RUN] Would expire {len(expired)} comment periods with end_date before {cutoff_date_str}:")
            for cp in expired[:10]:
                print(f"    - {cp.get('title', 'Unknown')[:50]} (ends {cp.get('end_date')}) [{cp.get('source')}]")
            if len(expired) > 10:
                print(f"    ... and {len(expired) - 10} more")
        return len(expired)

    # Delete expired comment periods
    deleted_count = 0
    for cp in expired:
        try:
            supabase.table("comment_periods").delete().eq("id", cp["id"]).execute()
            deleted_count += 1
        except Exception as e:
            print(f"  Error deleting comment period {cp['id']}: {e}")

    if deleted_count:
        print(f"  Expired {deleted_count} comment periods with end_date before {cutoff_date_str}")

    return deleted_count


def find_duplicates(dry_run=False):
    """Find and remove duplicate meetings (same source + source_id).

    Keeps the most recent record (highest id) and deletes older duplicates.
    Returns the count of removed duplicates.
    """
    supabase = get_supabase()

    # Fetch all meetings with pagination (Supabase default limit is 1000)
    all_meetings = []
    page_size = 1000
    offset = 0
    while True:
        result = supabase.table("meetings") \
            .select("id, source, source_id, title, created_at") \
            .order("id", desc=False) \
            .range(offset, offset + page_size - 1) \
            .execute()
        batch = result.data or []
        all_meetings.extend(batch)
        if len(batch) < page_size:
            break
        offset += page_size

    print(f"  Fetched {len(all_meetings)} total meetings for dedup check")

    # Group by (source, source_id) to find duplicates
    groups = defaultdict(list)
    for m in all_meetings:
        key = (m.get("source"), m.get("source_id"))
        if key[0] and key[1]:  # Only group records that have both fields
            groups[key].append(m)

    # Find groups with more than one record
    duplicates_to_delete = []
    for key, records in groups.items():
        if len(records) > 1:
            # Sort by id descending — keep the highest id (most recent)
            records.sort(key=lambda r: r["id"], reverse=True)
            # Mark all but the first (newest) for deletion
            for record in records[1:]:
                duplicates_to_delete.append(record)

    if dry_run:
        if duplicates_to_delete:
            print(f"  [DRY RUN] Would remove {len(duplicates_to_delete)} duplicate meetings:")
            for d in duplicates_to_delete[:10]:
                print(f"    - ID {d['id']}: {d.get('title', 'Unknown')[:50]} [{d.get('source')}:{d.get('source_id')}]")
            if len(duplicates_to_delete) > 10:
                print(f"    ... and {len(duplicates_to_delete) - 10} more")
        return len(duplicates_to_delete)

    # Delete duplicates
    deleted_count = 0
    for d in duplicates_to_delete:
        try:
            supabase.table("meetings").delete().eq("id", d["id"]).execute()
            deleted_count += 1
        except Exception as e:
            print(f"  Error deleting duplicate {d['id']}: {e}")

    if deleted_count:
        print(f"  Removed {deleted_count} duplicate meetings")

    return deleted_count


def main():
    """Run cleanup tasks based on command-line flags."""
    dry_run = "--dry-run" in sys.argv
    dedup_only = "--dedup-only" in sys.argv

    if dry_run:
        print("DRY RUN MODE — no records will be deleted\n")

    if dedup_only:
        print("Deduplication only\n")
        dupes = find_duplicates(dry_run=dry_run)
        print(f"\nRemoved {dupes} duplicates.")
        return

    # Run all cleanup tasks
    print("Running data cleanup...\n")

    expired_meetings = expire_old_meetings(dry_run=dry_run)
    expired_comments = expire_old_comment_periods(dry_run=dry_run)
    dupes = find_duplicates(dry_run=dry_run)

    action = "Would expire" if dry_run else "Expired"
    print(f"\n{action} {expired_meetings} meetings, {expired_comments} comment periods. "
          f"Removed {dupes} duplicates.")


if __name__ == "__main__":
    main()
