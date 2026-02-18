"""
MPSC Meeting Scraper
Scrapes Michigan Public Service Commission meetings from michigan.gov/mpsc

Uses Playwright to load the events listing page, then scrapes each individual
meeting page for structured data (schema.org LD+JSON), Teams links, and
conference details.
"""

import asyncio
import json
import os
import re
from datetime import datetime
from zoneinfo import ZoneInfo
from playwright.async_api import async_playwright
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

# Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
MPSC_EVENTS_URL = "https://www.michigan.gov/mpsc/commission/events"
MICHIGAN_TZ = ZoneInfo("America/Detroit")


def get_supabase():
    """Initialize Supabase client."""
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def parse_time_from_description(description):
    """
    Extract start time from the LD+JSON description field.
    Example: '1:00 PM to 2:00 PM Teleconference and In-Person'
    """
    if not description:
        return "09:30"

    match = re.search(r'(\d{1,2}:\d{2}\s*[AP]M)', description, re.IGNORECASE)
    if match:
        time_str = match.group(1).strip()
        try:
            t = datetime.strptime(time_str, "%I:%M %p")
            return t.strftime("%H:%M")
        except ValueError:
            pass

    return "09:30"


async def scrape_meeting_detail(page, url):
    """
    Scrape a single meeting detail page for structured data.
    Returns enriched meeting dict or None on failure.
    """
    try:
        resp = await page.goto(url, wait_until="domcontentloaded", timeout=15000)
        if not resp or resp.status != 200:
            print(f"    → Status {resp.status if resp else 'no response'}")
            return None

        await page.wait_for_timeout(1000)
        content = await page.content()

        # Extract LD+JSON structured data
        ld_json = None
        scripts = await page.query_selector_all('script[type="application/ld+json"]')
        for script in scripts:
            text = await script.inner_text()
            try:
                data = json.loads(text)
                if data.get("@type") == "Event":
                    ld_json = data
                    break
            except (json.JSONDecodeError, AttributeError):
                continue

        if not ld_json:
            print(f"    → No structured event data found")
            return None

        # Parse date
        start_date_str = ld_json.get("startDate", "")
        if not start_date_str:
            return None

        # Parse time from description (e.g. "1:00 PM to 2:00 PM Teleconference")
        description = ld_json.get("description", "")
        meeting_time = parse_time_from_description(description)
        hour, minute = map(int, meeting_time.split(":"))

        meeting_date = datetime.strptime(start_date_str[:10], "%Y-%m-%d").replace(
            hour=hour, minute=minute, tzinfo=MICHIGAN_TZ
        )

        # Extract title
        title = ld_json.get("name", f"{meeting_date.strftime('%B %d, %Y')} Commission Meeting")

        # Extract location
        location = ld_json.get("location", {})
        address = location.get("address", {})
        lat = float(location.get("latitude", 0)) or 42.7325
        lng = float(location.get("longitude", 0)) or -84.6358

        # Extract Teams URL
        teams_match = re.search(
            r'(https://teams\.microsoft\.com/(?:meet|l/meetup-join)/[^\s"<>]+)',
            content
        )
        teams_url = teams_match.group(1) if teams_match else None

        # Extract phone number (look for the +1 pattern)
        phone_match = re.search(r'(\+1\s*\d{3}[-.\s]?\d{3}[-.\s]?\d{4})', content)
        virtual_phone = phone_match.group(1) if phone_match else None

        # Extract conference ID
        conf_match = re.search(r'Conference\s*ID[:\s]*(\d[\d\s]*\d#?)', content, re.IGNORECASE)
        conference_id = conf_match.group(1).strip() if conf_match else None

        # Determine if virtual/hybrid
        is_virtual = bool(teams_url) or "teleconference" in description.lower()
        is_hybrid = is_virtual and ("in-person" in description.lower() or "in person" in description.lower())

        meeting = {
            "title": title,
            "description": (
                "Regular commission meeting of the Michigan Public Service Commission. "
                f"{description}" if description else
                "Regular commission meeting of the Michigan Public Service Commission."
            ),
            "agency": "MPSC",
            "agency_full_name": "Michigan Public Service Commission",
            "department": "LARA",
            "meeting_type": "commission_meeting",
            "start_datetime": meeting_date.isoformat(),
            "timezone": "America/Detroit",
            "location_name": location.get("name", "Michigan Public Service Commission"),
            "location_address": "7109 W. Saginaw Highway",
            "location_city": address.get("addressLocality", "Lansing"),
            "location_state": "Michigan",
            "location_zip": address.get("postalCode", "48917"),
            "latitude": lat,
            "longitude": lng,
            "is_virtual": is_virtual,
            "is_hybrid": is_hybrid,
            "virtual_url": teams_url,
            "virtual_phone": virtual_phone,
            "virtual_meeting_id": conference_id,
            "accepts_public_comment": True,
            "public_comment_instructions": (
                "Public comment may be provided during the meeting. "
                "Contact the Commission's Executive Secretary for accommodations."
            ),
            "contact_email": "lara-mpsc-commissioners@michigan.gov",
            "contact_phone": "(517) 284-8090",
            "issue_tags": ["energy", "utilities", "dte_energy", "consumers_energy", "rates"],
            "region": "statewide",
            "meeting_date": meeting_date.strftime("%Y-%m-%d"),
            "meeting_time": meeting_time,
            "source": "mpsc_scraper",
            "source_url": url,
            "source_id": f"mpsc-{meeting_date.strftime('%Y-%m-%d')}",
            "status": "upcoming",
            "details_url": url,
        }

        return meeting

    except Exception as e:
        print(f"    → Error: {str(e)[:60]}")
        return None


async def scrape_mpsc_meetings():
    """Scrape upcoming MPSC meetings from the events listing page."""
    meetings = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # Step 1: Get event listing
        print(f"Fetching event listing from {MPSC_EVENTS_URL}...")
        try:
            resp = await page.goto(MPSC_EVENTS_URL, wait_until="networkidle", timeout=30000)
        except Exception as e:
            print(f"  Failed to load listing page: {e}")
            await browser.close()
            return meetings

        if not resp or resp.status != 200:
            print(f"  Listing page returned {resp.status if resp else 'no response'}")
            await browser.close()
            return meetings

        await page.wait_for_timeout(2000)

        # Step 2: Find event links
        links = await page.query_selector_all('a')
        event_urls = []
        for link in links:
            href = await link.get_attribute('href') or ''
            text = (await link.inner_text()).strip()
            if '/commission/events/' in href and text and len(text) > 5:
                full_url = f"https://www.michigan.gov{href}" if not href.startswith("http") else href
                event_urls.append((text, full_url))

        print(f"  Found {len(event_urls)} event links")

        # Step 3: Scrape each meeting detail page
        for title, url in event_urls:
            print(f"  Scraping: {title}")
            meeting = await scrape_meeting_detail(page, url)
            if meeting:
                meetings.append(meeting)
                print(f"    ✓ {meeting['meeting_date']} {meeting['meeting_time']} — {meeting['title']}")
            else:
                print(f"    ✗ Could not parse meeting data")

        await browser.close()

    return meetings


def upsert_meetings(meetings):
    """Insert or update meetings in Supabase."""
    if not meetings:
        print("No meetings to upsert")
        return

    supabase = get_supabase()

    for meeting in meetings:
        try:
            supabase.table("meetings").upsert(
                meeting,
                on_conflict="source,source_id"
            ).execute()
            print(f"  Upserted: {meeting['title']}")
        except Exception as e:
            print(f"  Error upserting {meeting['title']}: {e}")


async def main():
    """Main entry point."""
    print("=" * 60)
    print("MPSC Meeting Scraper")
    print("=" * 60)

    meetings = await scrape_mpsc_meetings()

    print(f"\nScraped {len(meetings)} upcoming MPSC meetings")

    if meetings:
        print("\nUpserting to database...")
        upsert_meetings(meetings)

    print("\nDone!")
    return meetings


if __name__ == "__main__":
    asyncio.run(main())
