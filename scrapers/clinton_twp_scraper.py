"""
Clinton Township Meeting Scraper
Scrapes Clinton Township public meetings from their CivicPlus calendar.

Strategy: Fetch the list view calendar filtered by meeting categories
(Township Meetings CID=41, Committee Meetings CID=14), parse event entries,
then fetch detail pages for CivicClerk agenda links.

No Playwright needed — calendar list view is server-rendered HTML.

Source: https://www.clintontownship.com/calendar.aspx?view=list
"""

import os
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import httpx
from bs4 import BeautifulSoup
from dotenv import load_dotenv

from scraper_utils import print_result

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
MICHIGAN_TZ = ZoneInfo("America/Detroit")

BASE_URL = "https://www.clintontownship.com"
CALENDAR_URL = f"{BASE_URL}/calendar.aspx"

# Calendar category IDs
MEETING_CATEGORIES = [41, 14]  # Township Meetings, Committee Meetings

# How many months ahead to look
LOOKAHEAD_MONTHS = 3

# Bodies with environmental/infrastructure relevance
ENV_BODIES = {
    "conservation": ["environment", "conservation"],
    "parks": ["parks", "environment"],
    "planning": ["planning", "zoning"],
    "zoning board": ["planning", "zoning"],
    "brownfield": ["environment", "contamination"],
}

DEFAULT_TAGS = ["government", "clinton_township"]

TOWNSHIP_LOCATION = "40700 Romeo Plank Road, Clinton Township, MI 48038"


def parse_event_title(raw_title):
    """Parse the event title, which often includes the date appended.

    Examples:
        "Board of Trustees - Regular Board Meeting March 16, 2026"
        "Planning Commission Meeting March 12, 2026"
        "DDA Meeting"

    Returns (clean_title, date_from_title_or_None).
    """
    raw_title = raw_title.strip()

    # Try to extract a trailing date like "March 16, 2026"
    date_match = re.search(
        r'\s+(January|February|March|April|May|June|July|August|September|October|November|December)'
        r'\s+\d{1,2},\s+\d{4}\s*$',
        raw_title
    )
    if date_match:
        clean_title = raw_title[:date_match.start()].strip()
        try:
            dt = datetime.strptime(date_match.group(0).strip(), "%B %d, %Y")
            return clean_title, dt
        except ValueError:
            return clean_title, None

    return raw_title, None


def parse_date_time_text(text):
    """Parse a date/time string like 'March 16, 2026, 6:30 PM - 7:30 PM'.

    Returns (datetime, end_time_str) or (None, None).
    """
    text = text.strip()

    # Match: Month Day, Year, StartTime AM/PM - EndTime AM/PM
    match = re.match(
        r'(\w+ \d{1,2}, \d{4}),?\s+(\d{1,2}:\d{2}\s*[AP]M)',
        text,
        re.IGNORECASE
    )
    if match:
        try:
            dt = datetime.strptime(
                f"{match.group(1)} {match.group(2).strip()}",
                "%B %d, %Y %I:%M %p"
            )
            return dt.replace(tzinfo=MICHIGAN_TZ), None
        except ValueError:
            pass

    # Date only (no time)
    date_match = re.match(r'(\w+ \d{1,2}, \d{4})', text)
    if date_match:
        try:
            dt = datetime.strptime(date_match.group(1), "%B %d, %Y")
            return dt.replace(tzinfo=MICHIGAN_TZ), None
        except ValueError:
            pass

    return None, None


def extract_event_id(href):
    """Extract EID from a calendar link like '/Calendar.aspx?EID=2159&...'."""
    match = re.search(r'EID=(\d+)', href)
    return match.group(1) if match else None


def is_canceled(text):
    """Check if an event title/text indicates cancellation."""
    return bool(re.search(r'cancel', text, re.IGNORECASE))


def determine_meeting_type(title):
    """Determine meeting type from title."""
    lower = title.lower()
    if "board of trustees" in lower:
        return "board_meeting"
    if "commission" in lower or "committee" in lower or "advisory" in lower:
        return "committee_meeting"
    if "board" in lower or "authority" in lower:
        return "committee_meeting"
    if "special" in lower:
        return "special_meeting"
    if "hearing" in lower:
        return "public_hearing"
    return "public_meeting"


def get_issue_tags(title):
    """Get issue tags based on body name."""
    lower = title.lower()
    for key, tags in ENV_BODIES.items():
        if key in lower:
            return tags
    return DEFAULT_TAGS


def parse_calendar_list(html):
    """Parse the calendar list view HTML into a list of raw event dicts.

    Returns list of dicts with: title, date, time, event_id, detail_url.
    """
    soup = BeautifulSoup(html, "html.parser")
    events = []

    # Events are in <h3><a href="...">Title Date</a></h3> followed by <div>Date, Time</div>
    for h3 in soup.find_all("h3"):
        link = h3.find("a", href=True)
        if not link:
            continue

        href = link["href"]
        if "EID=" not in href:
            continue

        raw_title = link.get_text(strip=True)
        event_id = extract_event_id(href)

        # Skip canceled events
        if is_canceled(raw_title):
            continue

        clean_title, title_date = parse_event_title(raw_title)

        # Look for date/time in the next sibling <div>
        dt = None
        next_div = h3.find_next_sibling("div")
        if next_div:
            div_text = next_div.get_text(strip=True)
            dt, _ = parse_date_time_text(div_text)

        # Fall back to date from title
        if not dt and title_date:
            dt = title_date.replace(tzinfo=MICHIGAN_TZ)

        if not dt:
            continue

        detail_url = f"{BASE_URL}{href}" if href.startswith("/") else href

        events.append({
            "title": clean_title,
            "date": dt,
            "event_id": event_id,
            "detail_url": detail_url,
        })

    return events


def parse_detail_page(html):
    """Parse an event detail page to extract agenda URL and location.

    Returns dict with optional keys: agenda_url, location.
    """
    soup = BeautifulSoup(html, "html.parser")
    result = {}

    # CivicClerk agenda link
    for link in soup.find_all("a", href=True):
        href = link["href"]
        if "civicclerk.com" in href:
            result["agenda_url"] = href
            break

    # Location — look for address-like text
    # CivicPlus puts location in a div with class containing "location"
    for el in soup.find_all(string=re.compile(r'\d+\s+\w+.*\d{5}')):
        text = el.strip()
        if len(text) < 200:
            result["location"] = text
            break

    return result


def upsert_meetings(meetings):
    """Upsert meetings to Supabase."""
    from supabase import create_client
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    for meeting in meetings:
        try:
            supabase.table("meetings").upsert(
                meeting,
                on_conflict="source,source_id"
            ).execute()
            print(f"  Upserted: {meeting['title'][:50]} ({meeting['meeting_date']})")
        except Exception as e:
            print(f"  Error upserting {meeting['title'][:30]}: {e}")


async def main():
    """Main entry point — scrape Clinton Township meetings from CivicPlus calendar."""
    print("=" * 60)
    print("Clinton Township Meeting Scraper")
    print("=" * 60)

    now = datetime.now(MICHIGAN_TZ)
    all_events = []

    async with httpx.AsyncClient(
        follow_redirects=True,
        headers={"User-Agent": "PlanetDetroit-CivicScraper/1.0"}
    ) as client:
        # Fetch calendar list for each category and each month
        for cid in MEETING_CATEGORIES:
            for month_offset in range(LOOKAHEAD_MONTHS + 1):
                target = now + timedelta(days=30 * month_offset)
                params = {
                    "view": "list",
                    "CID": str(cid),
                    "year": str(target.year),
                    "month": str(target.month),
                }

                try:
                    resp = await client.get(CALENDAR_URL, params=params, timeout=30)
                    resp.raise_for_status()
                    events = parse_calendar_list(resp.text)
                    # Filter to upcoming only
                    events = [e for e in events if e["date"] >= now - timedelta(days=1)]
                    all_events.extend(events)
                    print(f"  CID={cid} {target.strftime('%Y-%m')}: {len(events)} events")
                except Exception as e:
                    print(f"  Error fetching CID={cid} {target.strftime('%Y-%m')}: {e}")

        # Deduplicate by event_id
        seen = set()
        unique_events = []
        for event in all_events:
            eid = event["event_id"]
            if eid and eid not in seen:
                seen.add(eid)
                unique_events.append(event)
            elif not eid:
                unique_events.append(event)

        print(f"\n  {len(unique_events)} unique upcoming events")

        # Fetch detail pages for agenda URLs
        print("\n  Checking detail pages for agenda links...")
        detail_data = {}
        for event in unique_events:
            if event.get("detail_url"):
                try:
                    resp = await client.get(event["detail_url"], timeout=20)
                    resp.raise_for_status()
                    detail = parse_detail_page(resp.text)
                    if detail:
                        detail_data[event["event_id"]] = detail
                        if detail.get("agenda_url"):
                            print(f"    {event['title'][:40]} -> agenda found")
                except Exception as e:
                    pass  # Non-critical — we still have the basic meeting data

        print(f"  Found agendas for {sum(1 for d in detail_data.values() if d.get('agenda_url'))} meetings")

        # Build meeting dicts
        meetings = []
        for event in unique_events:
            dt = event["date"]
            eid = event["event_id"]
            detail = detail_data.get(eid, {})

            meeting = {
                "title": event["title"],
                "agency": f"Clinton Township - {event['title']}",
                "meeting_date": dt.strftime("%Y-%m-%d"),
                "meeting_time": dt.strftime("%H:%M") if dt.hour > 0 else None,
                "start_datetime": dt.isoformat(),
                "location": detail.get("location", TOWNSHIP_LOCATION),
                "meeting_type": determine_meeting_type(event["title"]),
                "source": "clinton_twp_scraper",
                "source_id": f"clinton-twp-{eid}" if eid else f"clinton-twp-{dt.strftime('%Y%m%d')}-{event['title'][:20]}",
                "details_url": event.get("detail_url"),
                "agenda_url": detail.get("agenda_url"),
                "minutes_url": None,
                "region": "Macomb County",
                "issue_tags": get_issue_tags(event["title"]),
            }
            meetings.append(meeting)

    print(f"\nBuilt {len(meetings)} meeting records")
    env_count = sum(1 for m in meetings if m["issue_tags"] != DEFAULT_TAGS)
    print(f"  {env_count} environmentally relevant, {len(meetings) - env_count} general")

    if meetings:
        print("\nUpserting to database...")
        upsert_meetings(meetings)

    print("\nDone!")
    print_result("clinton_twp", "ok", len(meetings), "meetings")
    return meetings


if __name__ == "__main__":
    import asyncio
    try:
        asyncio.run(main())
    except Exception as e:
        print_result("clinton_twp", "error", error=str(e))
        raise
