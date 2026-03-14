"""
DOM Canary Checks for HTML Scrapers
Verifies that key CSS selectors/elements still exist on scraped pages.
Detects site redesigns before they cause silent scraper failures.

Run: python canary_check.py [--json] [--slack]
"""

import argparse
import asyncio
import json
import os
import re
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

import httpx
import yaml
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

MICHIGAN_TZ = ZoneInfo("America/Detroit")
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")

# Canary definitions: each scraper that parses HTML has a URL to check
# and selectors/patterns that MUST be present for the scraper to work.
#
# Types of checks:
#   "css": BeautifulSoup CSS selector (find/select)
#   "text": Text pattern (regex) that must appear in page source
#   "element": Element + attribute combo (e.g., {"tag": "time", "attr": "datetime"})

CANARY_CONFIGS = {
    "glwa": {
        "name": "GLWA (Legistar RadGrid)",
        "url": "https://glwater.legistar.com/Calendar.aspx",
        "needs_browser": True,
        "checks": [
            {"type": "css", "selector": "tr.rgRow, tr.rgAltRow", "description": "RadGrid table rows"},
        ],
    },
    "detroit": {
        "name": "Detroit (eSCRIBE)",
        "url": "https://pub-detroitmi.escribemeetings.com/Meeting.aspx?Id=97b78cd5-6e0b-4243-8a77-578740c3e75a&Agenda=Agenda&lang=English",
        "needs_browser": True,
        "checks": [
            {"type": "text", "pattern": "MeetingsCalendarView", "description": "eSCRIBE calendar API endpoint"},
        ],
    },
    "wayne_county": {
        "name": "Wayne County (Granicus)",
        "url": "https://www.waynecounty.com/elected/commission/meeting-minutes.aspx",
        "needs_browser": True,
        "checks": [
            {"type": "css", "selector": "div.accordion-list-item-container", "description": "Meeting card container"},
        ],
    },
    "mpsc": {
        "name": "MPSC (michigan.gov LD+JSON)",
        "url": "https://www.michigan.gov/mpsc/commission/events",
        "needs_browser": True,
        "checks": [
            {"type": "css", "selector": "script[type='application/ld+json']", "description": "LD+JSON structured data"},
        ],
    },
    "warren": {
        "name": "Warren (WordPress sitemap)",
        "url": "https://www.cityofwarren.org/meetings-sitemap.xml",
        "needs_browser": False,
        "checks": [
            {"type": "text", "pattern": r"<loc>https://www\.cityofwarren\.org/meetings/", "description": "Meeting URLs in sitemap XML"},
        ],
    },
    "dearborn": {
        "name": "Dearborn (Drupal Views AJAX)",
        "url": "https://dearborn.gov/calendar",
        "needs_browser": False,
        "checks": [
            {"type": "text", "pattern": "event_schedule_tabs", "description": "Drupal Views AJAX view name"},
        ],
    },
    "troy_schedule": {
        "name": "Troy Council Schedule",
        "url": "https://apps.troymi.gov/CouncilSchedule",
        "needs_browser": False,
        "checks": [
            {"type": "css", "selector": "main#freeform-main", "description": "Main content container"},
            {"type": "css", "selector": "main#freeform-main ul li", "description": "Schedule list items"},
        ],
    },
    "troy_archive": {
        "name": "Troy Meeting Archive",
        "url": "https://apps.troymi.gov/meetings/MeetingArchive",
        "needs_browser": False,
        "checks": [
            {"type": "css", "selector": "table.table", "description": "Meeting archive table"},
            {"type": "text", "pattern": "DownloadPDF", "description": "PDF download links"},
        ],
    },
    "clinton_twp": {
        "name": "Clinton Twp (CivicPlus calendar)",
        "url": "https://www.clintontownship.com/calendar.aspx?view=list&CID=41",
        "needs_browser": False,
        "checks": [
            {"type": "text", "pattern": r"EID=\d+", "description": "Event ID links"},
        ],
    },
}


def run_css_check(soup, selector):
    """Check if a CSS selector matches any elements."""
    results = soup.select(selector)
    return len(results) > 0, len(results)


def run_text_check(html, pattern):
    """Check if a regex pattern matches in the HTML source."""
    matches = re.findall(pattern, html)
    return len(matches) > 0, len(matches)


def run_element_check(soup, tag, attr):
    """Check if elements with a specific tag and attribute exist."""
    results = soup.find_all(tag, attrs={attr: True})
    return len(results) > 0, len(results)


async def check_url(client, config):
    """Run all canary checks for a single URL.

    Returns dict with results for each check.
    """
    name = config["name"]
    url = config["url"]

    if config.get("needs_browser"):
        # Browser-based scrapers can't be checked with httpx
        # Return a skip result — these need Playwright in CI
        return {
            "name": name,
            "url": url,
            "status": "skipped",
            "reason": "needs_browser",
            "checks": [],
        }

    try:
        resp = await client.get(url, timeout=30)
        resp.raise_for_status()
        html = resp.text
        soup = BeautifulSoup(html, "html.parser")
    except Exception as e:
        return {
            "name": name,
            "url": url,
            "status": "error",
            "reason": str(e),
            "checks": [],
        }

    check_results = []
    all_passed = True

    for check in config["checks"]:
        check_type = check["type"]
        description = check["description"]

        if check_type == "css":
            passed, count = run_css_check(soup, check["selector"])
        elif check_type == "text":
            passed, count = run_text_check(html, check["pattern"])
        elif check_type == "element":
            passed, count = run_element_check(soup, check["tag"], check["attr"])
        else:
            passed, count = False, 0

        check_results.append({
            "type": check_type,
            "description": description,
            "passed": passed,
            "count": count,
        })

        if not passed:
            all_passed = False

    return {
        "name": name,
        "url": url,
        "status": "ok" if all_passed else "failed",
        "checks": check_results,
    }


async def run_all_checks():
    """Run canary checks for all configured scrapers."""
    results = []

    async with httpx.AsyncClient(
        follow_redirects=True,
        headers={"User-Agent": "PlanetDetroit-CanaryCheck/1.0"}
    ) as client:
        for key, config in CANARY_CONFIGS.items():
            print(f"  Checking {config['name']}...")
            result = await check_url(client, config)
            result["key"] = key
            results.append(result)

            if result["status"] == "ok":
                print(f"    OK — all checks passed")
            elif result["status"] == "skipped":
                print(f"    SKIPPED — needs browser")
            elif result["status"] == "error":
                print(f"    ERROR — {result['reason']}")
            else:
                for check in result["checks"]:
                    if not check["passed"]:
                        print(f"    FAILED: {check['description']}")

    return results


def format_text_report(results):
    """Format results as a text report."""
    now = datetime.now(MICHIGAN_TZ)
    lines = [
        f"DOM Canary Check — {now.strftime('%Y-%m-%d %H:%M %Z')}",
        "=" * 50,
        "",
    ]

    ok_count = sum(1 for r in results if r["status"] == "ok")
    failed_count = sum(1 for r in results if r["status"] == "failed")
    error_count = sum(1 for r in results if r["status"] == "error")
    skipped_count = sum(1 for r in results if r["status"] == "skipped")

    lines.append(f"Results: {ok_count} OK, {failed_count} FAILED, {error_count} ERROR, {skipped_count} skipped")
    lines.append("")

    # Show failures first
    if failed_count > 0 or error_count > 0:
        lines.append("ISSUES:")
        for r in results:
            if r["status"] == "failed":
                lines.append(f"  {r['name']}: FAILED")
                for check in r["checks"]:
                    if not check["passed"]:
                        lines.append(f"    Missing: {check['description']}")
            elif r["status"] == "error":
                lines.append(f"  {r['name']}: ERROR — {r['reason']}")
        lines.append("")

    # Show all results
    lines.append("All checks:")
    for r in results:
        status = r["status"].upper()
        lines.append(f"  [{status:7s}] {r['name']}")
        if r["status"] == "ok":
            for check in r["checks"]:
                lines.append(f"             {check['description']}: {check['count']} found")

    return "\n".join(lines)


def format_slack_message(results):
    """Format results as a Slack message."""
    now = datetime.now(MICHIGAN_TZ)

    ok_count = sum(1 for r in results if r["status"] == "ok")
    failed_count = sum(1 for r in results if r["status"] == "failed")
    error_count = sum(1 for r in results if r["status"] == "error")

    if failed_count > 0 or error_count > 0:
        emoji = ":warning:"
        title = f"DOM Canary Check: {failed_count + error_count} issues detected"
    else:
        emoji = ":white_check_mark:"
        title = f"DOM Canary Check: All {ok_count} checks passed"

    blocks = [f"*{emoji} {title}*\n_{now.strftime('%Y-%m-%d %H:%M %Z')}_\n"]

    if failed_count > 0 or error_count > 0:
        issues = []
        for r in results:
            if r["status"] == "failed":
                failed_checks = [c["description"] for c in r["checks"] if not c["passed"]]
                issues.append(f"*{r['name']}*: Missing {', '.join(failed_checks)}")
            elif r["status"] == "error":
                issues.append(f"*{r['name']}*: {r['reason']}")
        blocks.append("\n".join(issues))

    return {"text": "\n\n".join(blocks)}


def post_to_slack(message):
    """Post message to Slack webhook."""
    if not SLACK_WEBHOOK_URL:
        print("  No SLACK_WEBHOOK_URL set, skipping")
        return
    import httpx as httpx_sync
    resp = httpx_sync.post(SLACK_WEBHOOK_URL, json=message, timeout=10)
    print(f"  Slack response: {resp.status_code}")


async def main():
    parser = argparse.ArgumentParser(description="DOM canary checks for HTML scrapers")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--slack", action="store_true", help="Post to Slack")
    args = parser.parse_args()

    print("=" * 50)
    print("DOM Canary Check")
    print("=" * 50)

    results = await run_all_checks()

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print()
        print(format_text_report(results))

    if args.slack:
        print("\nPosting to Slack...")
        slack_msg = format_slack_message(results)
        post_to_slack(slack_msg)

    # Exit with error code if any checks failed
    failed = any(r["status"] == "failed" for r in results)
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
