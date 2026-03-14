"""
Dearborn Meeting Scraper
Scrapes City of Dearborn public meetings from their Drupal calendar.

Strategy: GET requests to the calendar page with pagination (?page=,,N)
and category filter (?field_event_category_target_id=483 for meetings).
Extracts structured date/time from <time datetime=""> elements.

No API available. No Playwright needed — plain HTTP requests.

Source: https://dearborn.gov/calendar
"""

import os
import re
import json
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

BASE_URL = "https://dearborn.gov"
CALENDAR_URL = "https://dearborn.gov/calendar"

# Category filter for "Meeting" events only
MEETING_CATEGORY_ID = "483"

# Max pages to paginate through
MAX_PAGES = 20

# Bodies with environmental/infrastructure relevance
ENV_BODIES = {
    "city beautiful": ["environment", "beautification"],
    "planning": ["planning", "zoning"],
    "demolition board": ["infrastructure", "housing"],
    "environmental": ["environment"],
    "parks": ["parks", "environment"],
}

DEFAULT_TAGS = ["government", "dearborn"]


def determine_meeting_type(title):
    """Determine meeting type from title."""
    lower = title.lower()
    if "special" in lower:
        return "special_meeting"
    if "hearing" in lower:
        return "public_hearing"
    if "city council" in lower or "committee of the whole" in lower:
        return "board_meeting"
    if "commission" in lower or "committee" in lower or "advisory" in lower:
        return "committee_meeting"
    if "board" in lower or "authority" in lower:
        return "committee_meeting"
    if "workshop" in lower or "work session" in lower:
        return "workshop"
    if "briefing" in lower:
        return "public_meeting"
    return "public_meeting"


def get_issue_tags(title):
    """Get issue tags based on meeting title."""
    lower = title.lower()
    for key, tags in ENV_BODIES.items():
        if key in lower:
            return tags
    return DEFAULT_TAGS


def parse_event_card(card_html):
    """Parse a single event card from the AJAX response.

    Returns a meeting dict or None if this isn't a meeting.
    """
    soup = BeautifulSoup(card_html, "html.parser") if isinstance(card_html, str) else card_html

    # Check category badge — only process "Meeting" events
    badge = soup.find("div", class_="badge")
    if badge:
        badge_text = badge.get_text(strip=True).lower()
        if badge_text != "meeting":
            return None

    # Title
    h2 = soup.find("h2", attrs={"data-history-node-id": True})
    if not h2:
        h2 = soup.find("h2")
    if not h2:
        return None

    title = h2.get_text(strip=True)
    node_id = h2.get("data-history-node-id", "")

    # Skip canceled meetings
    if title.upper().startswith("CANCELED"):
        return None

    # Date/time from <time datetime=""> elements
    time_elements = soup.find_all("time", attrs={"datetime": True})
    if not time_elements:
        return None

    start_dt_str = time_elements[0].get("datetime", "")
    start_dt = parse_iso_datetime(start_dt_str)
    if not start_dt:
        return None

    # Check if it's an all-day event
    time_text = time_elements[0].get_text(strip=True)
    is_all_day = "all day" in time_text.lower()

    # Location — find the span with location text
    # It's in a flex container with a location icon
    location = None
    location_divs = soup.find_all("div", class_="flex")
    for div in location_divs:
        span = div.find("span", class_="text-sm")
        if span:
            text = span.get_text(strip=True)
            # Location text contains addresses or place names, not dates
            if text and not re.search(r'\d{4}\s+\d{1,2}', text) and "datetime" not in str(span):
                # Check it's not the date/time span by looking for time-related content
                if not re.search(r'(am|pm|All day)', text, re.IGNORECASE):
                    location = text
                    break

    # Detail page link
    detail_link = soup.find("a", class_="button--link")
    details_url = None
    if detail_link:
        href = detail_link.get("href", "")
        details_url = f"{BASE_URL}{href}" if href.startswith("/") else href

    # Clean title — remove "CANCELED: " prefix if present
    clean_title = re.sub(r'^CANCELED\s*:?\s*', '', title, flags=re.IGNORECASE).strip()

    source_id = f"dearborn-{node_id}" if node_id else f"dearborn-{start_dt.strftime('%Y%m%d')}-{clean_title[:30]}"

    meeting = {
        "title": clean_title,
        "agency": f"City of Dearborn - {clean_title}" if "dearborn" not in clean_title.lower() else f"City of Dearborn",
        "meeting_date": start_dt.strftime("%Y-%m-%d"),
        "meeting_time": start_dt.strftime("%H:%M") if not is_all_day else None,
        "start_datetime": start_dt.isoformat(),
        "location": location,
        "meeting_type": determine_meeting_type(clean_title),
        "source": "dearborn_scraper",
        "source_id": source_id,
        "details_url": details_url,
        "agenda_url": None,
        "minutes_url": None,
        "region": "Wayne County",
        "issue_tags": get_issue_tags(clean_title),
    }

    return meeting


def parse_iso_datetime(dt_str):
    """Parse an ISO 8601 datetime string into a timezone-aware datetime."""
    if not dt_str:
        return None
    try:
        # Handle formats like "2026-03-18T12:00:00-04:00" or "2026-03-15" (date only)
        if "T" in dt_str:
            dt = datetime.fromisoformat(dt_str)
        else:
            dt = datetime.strptime(dt_str[:10], "%Y-%m-%d")
            dt = dt.replace(tzinfo=MICHIGAN_TZ)

        # Ensure timezone is set
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=MICHIGAN_TZ)
        return dt
    except (ValueError, TypeError):
        return None


def parse_events_html(html):
    """Parse the calendar HTML page and return list of event card soups."""
    soup = BeautifulSoup(html, "html.parser")
    return soup.find_all("div", class_="views-row")


def has_next_page(html):
    """Check if the calendar page has a 'Show more' pagination link."""
    soup = BeautifulSoup(html, "html.parser")
    pager = soup.find("nav", class_="pager")
    if pager:
        show_more = pager.find("a", title="Go to next page")
        return show_more is not None
    return False


async def fetch_events_page(client, page=0):
    """Fetch a single page of meeting events from the calendar.

    Uses ?page=,,N format (pager_element=2) and filters to meetings only.
    """
    params = {"field_event_category_target_id": MEETING_CATEGORY_ID}
    if page > 0:
        params["page"] = f",,{page}"
    resp = await client.get(CALENDAR_URL, params=params, timeout=30)
    resp.raise_for_status()
    return resp.text


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
    """Main entry point — scrape Dearborn meetings from Drupal AJAX endpoint."""
    print("=" * 60)
    print("City of Dearborn Meeting Scraper")
    print("=" * 60)

    meetings = []
    seen_ids = set()
    now = datetime.now(MICHIGAN_TZ)

    async with httpx.AsyncClient(
        follow_redirects=True,
        headers={"User-Agent": "PlanetDetroit-CivicScraper/1.0"}
    ) as client:
        for page in range(MAX_PAGES):
            try:
                print(f"  Fetching page {page}...")
                html = await fetch_events_page(client, page)

                cards = parse_events_html(html)
                if not cards:
                    print(f"  No event cards on page {page}, stopping")
                    break

                page_count = 0
                for card in cards:
                    meeting = parse_event_card(card)
                    if meeting:
                        # Deduplicate by source_id
                        if meeting["source_id"] in seen_ids:
                            continue
                        seen_ids.add(meeting["source_id"])

                        # Only include future meetings
                        meeting_dt = parse_iso_datetime(meeting["start_datetime"])
                        if meeting_dt and meeting_dt >= now - timedelta(days=1):
                            meetings.append(meeting)
                            page_count += 1
                            print(f"    {meeting['title'][:45]} ({meeting['meeting_date']})")

                print(f"  Page {page}: {page_count} meetings found")

                # Stop if no "Show more" link
                if not has_next_page(html):
                    print(f"  No more pages after page {page}")
                    break

            except Exception as e:
                print(f"  Error fetching page {page}: {e}")
                break

    print(f"\nBuilt {len(meetings)} meeting records")
    env_count = sum(1 for m in meetings if m["issue_tags"] != DEFAULT_TAGS)
    print(f"  {env_count} environmentally relevant, {len(meetings) - env_count} general")

    if meetings:
        print("\nUpserting to database...")
        upsert_meetings(meetings)

    print("\nDone!")
    print_result("dearborn", "ok", len(meetings), "meetings")
    return meetings


if __name__ == "__main__":
    import asyncio
    try:
        asyncio.run(main())
    except Exception as e:
        print_result("dearborn", "error", error=str(e))
        raise
