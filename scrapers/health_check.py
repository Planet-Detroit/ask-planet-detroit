"""
Scraper Health Check
Queries Supabase for coverage stats and generates a health report.
Designed to run weekly via GitHub Actions and post to Slack.

Usage:
  python health_check.py              # Print report to stdout
  python health_check.py --json       # Output JSON for Slack webhook
  python health_check.py --slack      # Post directly to Slack (needs SLACK_WEBHOOK_URL)
"""

import os
import sys
import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from collections import Counter

from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
MICHIGAN_TZ = ZoneInfo("America/Detroit")


def get_supabase():
    from supabase import create_client
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def fetch_all_rows(supabase, table, select="*", filters=None):
    """Fetch all rows from a table, handling Supabase pagination."""
    all_rows = []
    offset = 0
    page_size = 1000
    while True:
        query = supabase.table(table).select(select).range(offset, offset + page_size - 1)
        if filters:
            for col, op, val in filters:
                query = query.filter(col, op, val)
        page = query.execute()
        batch = page.data or []
        all_rows.extend(batch)
        if len(batch) < page_size:
            break
        offset += page_size
    return all_rows


def generate_report():
    """Generate a health report from current Supabase data."""
    supabase = get_supabase()
    now = datetime.now(MICHIGAN_TZ)
    today = now.strftime("%Y-%m-%d")

    # Fetch all meetings
    meetings = fetch_all_rows(supabase, "meetings", "source,meeting_date,agenda_url,virtual_url,created_at")

    # Fetch comment periods
    comment_periods = fetch_all_rows(supabase, "comment_periods", "source,end_date,created_at")

    # Fetch agenda summaries
    summaries = fetch_all_rows(supabase, "agenda_summaries", "source,created_at")

    report = {
        "generated_at": now.isoformat(),
        "totals": {},
        "by_source": {},
        "warnings": [],
        "data_freshness": {},
    }

    # --- Total counts ---
    upcoming_meetings = [m for m in meetings if (m.get("meeting_date") or "") >= today]
    past_meetings = [m for m in meetings if (m.get("meeting_date") or "") < today]
    open_comment_periods = [c for c in comment_periods if (c.get("end_date") or "") >= today]

    report["totals"] = {
        "meetings_total": len(meetings),
        "meetings_upcoming": len(upcoming_meetings),
        "meetings_past": len(past_meetings),
        "comment_periods_total": len(comment_periods),
        "comment_periods_open": len(open_comment_periods),
        "agenda_summaries": len(summaries),
    }

    # --- Per-source breakdown ---
    source_counts = Counter(m["source"] for m in meetings)
    source_upcoming = Counter(m["source"] for m in upcoming_meetings)
    source_with_agenda = Counter(m["source"] for m in meetings if m.get("agenda_url"))
    source_with_virtual = Counter(m["source"] for m in meetings if m.get("virtual_url"))

    for source in sorted(source_counts.keys()):
        report["by_source"][source] = {
            "total": source_counts[source],
            "upcoming": source_upcoming.get(source, 0),
            "with_agenda": source_with_agenda.get(source, 0),
            "with_virtual": source_with_virtual.get(source, 0),
        }

    # --- Warnings ---

    # Sources with 0 upcoming meetings
    for source, total in source_counts.items():
        if source_upcoming.get(source, 0) == 0:
            report["warnings"].append(f"{source}: 0 upcoming meetings (has {total} total)")

    # Meetings with null dates
    null_date_count = sum(1 for m in meetings if not m.get("meeting_date"))
    if null_date_count > 0:
        report["warnings"].append(f"{null_date_count} meetings have null meeting_date")

    # Past meetings that should have been cleaned up (>30 days old)
    cutoff = (now - timedelta(days=30)).strftime("%Y-%m-%d")
    stale = [m for m in past_meetings if (m.get("meeting_date") or "") < cutoff]
    if stale:
        report["warnings"].append(f"{len(stale)} meetings older than 30 days still in DB")

    # Expired comment periods
    expired = [c for c in comment_periods if (c.get("end_date") or "") < today]
    if expired:
        report["warnings"].append(f"{len(expired)} expired comment periods still in DB")

    # --- Data freshness ---
    # When was the most recent meeting added per source?
    for source in sorted(source_counts.keys()):
        source_meetings = [m for m in meetings if m["source"] == source]
        if source_meetings:
            latest_created = max(m.get("created_at", "") for m in source_meetings)
            report["data_freshness"][source] = latest_created[:10] if latest_created else "unknown"

    return report


def format_text_report(report):
    """Format the report for terminal/text output."""
    lines = []
    lines.append("=" * 60)
    lines.append("SCRAPER HEALTH REPORT")
    lines.append(f"Generated: {report['generated_at'][:19]}")
    lines.append("=" * 60)

    t = report["totals"]
    lines.append(f"\nTOTALS:")
    lines.append(f"  Meetings: {t['meetings_total']} total, {t['meetings_upcoming']} upcoming, {t['meetings_past']} past")
    lines.append(f"  Comment Periods: {t['comment_periods_total']} total, {t['comment_periods_open']} open")
    lines.append(f"  Agenda Summaries: {t['agenda_summaries']}")

    lines.append(f"\nBY SOURCE:")
    lines.append(f"  {'Source':<30} {'Total':>5} {'Upcoming':>8} {'Agenda':>6} {'Virtual':>7}")
    lines.append(f"  {'-'*30} {'-'*5} {'-'*8} {'-'*6} {'-'*7}")
    for source, data in report["by_source"].items():
        lines.append(f"  {source:<30} {data['total']:>5} {data['upcoming']:>8} {data['with_agenda']:>6} {data['with_virtual']:>7}")

    if report["warnings"]:
        lines.append(f"\nWARNINGS ({len(report['warnings'])}):")
        for w in report["warnings"]:
            lines.append(f"  ⚠ {w}")
    else:
        lines.append(f"\nNo warnings.")

    lines.append(f"\nDATA FRESHNESS (last record created):")
    for source, date in report["data_freshness"].items():
        lines.append(f"  {source:<30} {date}")

    return "\n".join(lines)


def format_slack_message(report):
    """Format the report as a Slack message."""
    t = report["totals"]
    warning_count = len(report["warnings"])

    if warning_count == 0:
        emoji = "white_check_mark"
        status = "All systems healthy"
    elif warning_count <= 2:
        emoji = "warning"
        status = f"{warning_count} warning(s)"
    else:
        emoji = "rotating_light"
        status = f"{warning_count} warnings — review needed"

    # Source table
    source_lines = []
    for source, data in report["by_source"].items():
        source_lines.append(f"  {source}: {data['upcoming']} upcoming, {data['with_agenda']} w/agenda")

    warnings_text = "\n".join(f"  - {w}" for w in report["warnings"]) if report["warnings"] else "  None"

    text = (
        f":{emoji}: *Scraper Health Report* — {status}\n\n"
        f"*Totals:* {t['meetings_upcoming']} upcoming meetings | "
        f"{t['comment_periods_open']} open comment periods | "
        f"{t['agenda_summaries']} agenda summaries\n\n"
        f"*By Source:*\n{''.join(chr(10) + s for s in source_lines)}\n\n"
        f"*Warnings:*\n{warnings_text}"
    )

    return {"text": text}


def post_to_slack(message):
    """Post a message to Slack via webhook."""
    import httpx
    webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    if not webhook_url:
        print("ERROR: SLACK_WEBHOOK_URL not set", file=sys.stderr)
        sys.exit(1)

    resp = httpx.post(webhook_url, json=message, timeout=10)
    if resp.status_code == 200:
        print("Posted to Slack successfully")
    else:
        print(f"Slack post failed: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    report = generate_report()

    if "--json" in sys.argv:
        print(json.dumps(report, indent=2))
    elif "--slack" in sys.argv:
        message = format_slack_message(report)
        post_to_slack(message)
    else:
        print(format_text_report(report))
