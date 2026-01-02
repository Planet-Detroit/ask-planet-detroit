"""
MPSC Meeting Scraper
Scrapes Michigan Public Service Commission meetings from michigan.gov/mpsc

MPSC typically holds Commission Meetings on the 1st and 3rd Thursday of each month.
This scraper generates expected meeting dates and verifies they exist.
"""

import asyncio
import os
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from playwright.async_api import async_playwright
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

# Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
MPSC_BASE_URL = "https://www.michigan.gov/mpsc/commission/events"
MICHIGAN_TZ = ZoneInfo("America/Detroit")


def get_supabase():
    """Initialize Supabase client."""
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def get_upcoming_meeting_dates(months_ahead=3):
    """
    Generate expected MPSC meeting dates.
    MPSC typically meets on 1st and 3rd Thursday of each month.
    """
    dates = []
    today = datetime.now(MICHIGAN_TZ)
    
    for month_offset in range(months_ahead + 1):
        # Calculate target month
        year = today.year
        month = today.month + month_offset
        
        while month > 12:
            month -= 12
            year += 1
        
        # Find 1st and 3rd Thursday
        first_day = datetime(year, month, 1, tzinfo=MICHIGAN_TZ)
        
        # Find first Thursday (weekday 3)
        days_until_thursday = (3 - first_day.weekday()) % 7
        first_thursday = first_day + timedelta(days=days_until_thursday)
        
        # Third Thursday is 2 weeks later
        third_thursday = first_thursday + timedelta(weeks=2)
        
        # Add if in the future
        if first_thursday > today:
            dates.append(first_thursday)
        if third_thursday > today:
            dates.append(third_thursday)
    
    return sorted(dates)


def generate_event_url(meeting_date):
    """Generate the expected URL for a meeting date."""
    month_name = meeting_date.strftime("%B").lower()
    day = meeting_date.day
    year = meeting_date.year
    
    # Format: /mpsc/commission/events/2025/01/16/january-16-2025-commission-meeting
    url = f"{MPSC_BASE_URL}/{year}/{meeting_date.month:02d}/{day:02d}/{month_name}-{day}-{year}-commission-meeting"
    return url


async def scrape_mpsc_meetings():
    """Scrape upcoming MPSC meetings."""
    meetings = []
    expected_dates = get_upcoming_meeting_dates(months_ahead=4)
    
    print(f"Checking {len(expected_dates)} expected meeting dates...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        for meeting_date in expected_dates:
            url = generate_event_url(meeting_date)
            print(f"  Checking: {meeting_date.strftime('%Y-%m-%d')} - {url}")
            
            try:
                response = await page.goto(url, wait_until="domcontentloaded", timeout=15000)
                
                # Check if page exists (not 404)
                if response and response.status == 200:
                    # Wait a moment for content to load
                    await asyncio.sleep(1)
                    
                    # Get page title to verify it's a meeting page
                    title = await page.title()
                    
                    # Check page content for meeting info
                    content = await page.content()
                    
                    # Skip if it's a 404 or error page
                    if "not found" in title.lower() or "error" in title.lower():
                        print(f"    → Page not found")
                        continue
                    
                    # Extract meeting title from page
                    meeting_title = f"{meeting_date.strftime('%B')} {meeting_date.day}, {meeting_date.year} Commission Meeting"
                    
                    # Check for virtual meeting info
                    has_teams = "teams.microsoft.com" in content.lower() or "microsoft teams" in content.lower()
                    
                    # Extract phone number if present
                    phone_match = re.search(r'\+1\s*(\d{3}[-.\s]?\d{3}[-.\s]?\d{4})', content)
                    virtual_phone = phone_match.group(0) if phone_match else "+1 248-509-0316"
                    
                    # Extract conference ID if present
                    conf_match = re.search(r'Conference ID[:\s]*(\d[\d\s#]+)', content)
                    conference_id = conf_match.group(1).strip() if conf_match else "420 519 407#"
                    
                    meeting = {
                        "title": meeting_title,
                        "description": f"Regular commission meeting of the Michigan Public Service Commission. Meetings are hybrid - attend in person or via Microsoft Teams.",
                        "agency": "MPSC",
                        "agency_full_name": "Michigan Public Service Commission",
                        "department": "LARA",
                        "meeting_type": "commission_meeting",
                        "start_datetime": meeting_date.replace(hour=9, minute=30).isoformat(),
                        "timezone": "America/Detroit",
                        "location_name": "MPSC Headquarters",
                        "location_address": "7109 W. Saginaw Highway",
                        "location_city": "Lansing",
                        "location_state": "Michigan",
                        "location_zip": "48917",
                        "latitude": 42.7325,
                        "longitude": -84.6358,
                        "is_virtual": True,
                        "is_hybrid": True,
                        "virtual_url": "https://teams.microsoft.com",
                        "virtual_phone": virtual_phone,
                        "virtual_meeting_id": conference_id,
                        "accepts_public_comment": True,
                        "public_comment_instructions": "Public comment may be provided during the meeting. Contact the Commission's Executive Secretary for accommodations.",
                        "contact_email": "lara-mpsc-commissioners@michigan.gov",
                        "contact_phone": "(517) 284-8090",
                        "issue_tags": ["energy", "utilities", "dte_energy", "consumers_energy", "rates"],
                        "region": "statewide",
                        "source": "mpsc_scraper",
                        "source_url": url,
                        "source_id": f"mpsc-{meeting_date.strftime('%Y-%m-%d')}",
                        "status": "upcoming",
                        "details_url": url,
                    }
                    
                    meetings.append(meeting)
                    print(f"    ✓ Found meeting: {meeting_title}")
                else:
                    print(f"    → No meeting page (status: {response.status if response else 'no response'})")
                    
            except Exception as e:
                print(f"    → Error: {str(e)[:50]}")
                continue
        
        await browser.close()
    
    return meetings


async def scrape_from_calendar_page():
    """
    Alternative: Try to scrape from the main calendar page.
    Falls back to this if date-based approach doesn't work.
    """
    meetings = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        print(f"Fetching MPSC calendar from {MPSC_BASE_URL}")
        await page.goto(MPSC_BASE_URL, wait_until="networkidle", timeout=30000)
        
        # Wait for dynamic content
        await asyncio.sleep(3)
        
        # Try to find event links
        event_links = await page.query_selector_all('a[href*="/commission/events/"]')
        print(f"Found {len(event_links)} event links")
        
        for link in event_links:
            try:
                href = await link.get_attribute("href")
                text = await link.inner_text()
                
                # Skip navigation links
                if not href or "commission-meeting" not in href.lower():
                    continue
                
                # Parse date from URL
                date_match = re.search(r'/(\d{4})/(\d{2})/(\d{2})/', href)
                if date_match:
                    year, month, day = map(int, date_match.groups())
                    meeting_date = datetime(year, month, day, 9, 30, tzinfo=MICHIGAN_TZ)
                    
                    if meeting_date > datetime.now(MICHIGAN_TZ):
                        full_url = f"https://www.michigan.gov{href}" if not href.startswith("http") else href
                        
                        meeting = {
                            "title": text.strip() or f"{meeting_date.strftime('%B %d, %Y')} Commission Meeting",
                            "agency": "MPSC",
                            "agency_full_name": "Michigan Public Service Commission",
                            "meeting_type": "commission_meeting",
                            "start_datetime": meeting_date.isoformat(),
                            "timezone": "America/Detroit",
                            "location_name": "MPSC Headquarters",
                            "location_address": "7109 W. Saginaw Highway",
                            "location_city": "Lansing",
                            "location_state": "Michigan",
                            "is_virtual": True,
                            "is_hybrid": True,
                            "accepts_public_comment": True,
                            "contact_email": "lara-mpsc-commissioners@michigan.gov",
                            "issue_tags": ["energy", "utilities"],
                            "region": "statewide",
                            "source": "mpsc_scraper",
                            "source_url": full_url,
                            "source_id": f"mpsc-{meeting_date.strftime('%Y-%m-%d')}",
                            "status": "upcoming",
                            "details_url": full_url,
                        }
                        meetings.append(meeting)
                        print(f"  Found: {meeting['title']}")
                        
            except Exception as e:
                continue
        
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
            result = supabase.table("meetings").upsert(
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
    
    # Try the date-based approach first
    meetings = await scrape_mpsc_meetings()
    
    # If that didn't work, try the calendar page
    if not meetings:
        print("\nNo meetings found via date check, trying calendar page...")
        meetings = await scrape_from_calendar_page()
    
    print(f"\nFound {len(meetings)} upcoming MPSC meetings")
    
    if meetings:
        print("\nUpserting to database...")
        upsert_meetings(meetings)
    
    print("\nDone!")
    return meetings


if __name__ == "__main__":
    asyncio.run(main())
