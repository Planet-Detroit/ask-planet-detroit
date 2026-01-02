"""
EGLE Meeting Scraper
Scrapes Michigan EGLE (Environment, Great Lakes, and Energy) public meetings and hearings
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
EGLE_CALENDAR_URL = "https://www.michigan.gov/egle/outreach/calendar"
MICHIGAN_TZ = ZoneInfo("America/Detroit")

# Issue tag mapping based on EGLE divisions
EGLE_ISSUE_MAPPING = {
    "air quality": ["air_quality"],
    "air permit": ["air_quality"],
    "water": ["drinking_water", "water_quality"],
    "drinking water": ["drinking_water"],
    "groundwater": ["drinking_water", "water_quality"],
    "wetland": ["water_quality"],
    "npdes": ["water_quality"],
    "waste": ["waste", "pollution"],
    "hazardous": ["waste", "pollution"],
    "contamination": ["pollution", "pfas"],
    "pfas": ["pfas", "drinking_water"],
    "remediation": ["pollution"],
    "brownfield": ["pollution"],
    "climate": ["climate"],
    "energy": ["energy"],
    "renewable": ["energy", "climate"],
}


def get_supabase():
    """Initialize Supabase client."""
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def extract_issue_tags(title, description=""):
    """Extract issue tags based on keywords in title/description."""
    text = f"{title} {description}".lower()
    tags = set()
    
    for keyword, issue_tags in EGLE_ISSUE_MAPPING.items():
        if keyword in text:
            tags.update(issue_tags)
    
    # Default tag if none found
    if not tags:
        tags.add("environment")
    
    return list(tags)


def determine_meeting_type(title):
    """Determine meeting type from title."""
    title_lower = title.lower()
    
    if "public hearing" in title_lower or "hearing" in title_lower:
        return "public_hearing"
    elif "public comment" in title_lower or "comment period" in title_lower:
        return "comment_period"
    elif "board" in title_lower or "commission" in title_lower:
        return "board_meeting"
    elif "workshop" in title_lower or "training" in title_lower:
        return "workshop"
    elif "webinar" in title_lower:
        return "webinar"
    else:
        return "public_meeting"


async def scrape_egle_meetings():
    """Scrape upcoming EGLE meetings and events."""
    meetings = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        print(f"Fetching EGLE calendar from {EGLE_CALENDAR_URL}")
        await page.goto(EGLE_CALENDAR_URL, wait_until="networkidle")
        
        # Wait for calendar to load
        await asyncio.sleep(3)  # Give dynamic content time to load
        
        # Try multiple selectors for events
        selectors = [
            ".calendar-event",
            ".event-item",
            ".views-row",
            "[data-event]",
            ".fc-event",  # FullCalendar
        ]
        
        event_items = []
        for selector in selectors:
            items = await page.query_selector_all(selector)
            if items:
                event_items = items
                print(f"Found {len(items)} events using selector: {selector}")
                break
        
        if not event_items:
            # Try getting events from the page content directly
            print("No events found with standard selectors, trying content extraction...")
            content = await page.content()
            
            # Look for event patterns in the HTML
            # Michigan.gov often uses specific date formats
            date_pattern = r'(\d{1,2}/\d{1,2}/\d{4})'
            dates_found = re.findall(date_pattern, content)
            print(f"Found {len(dates_found)} date patterns in page content")
        
        for item in event_items:
            try:
                # Get event title
                title_el = await item.query_selector("a, .event-title, h3, h4")
                if not title_el:
                    continue
                
                title = await title_el.inner_text()
                link = await title_el.get_attribute("href")
                
                # Make absolute URL
                if link and not link.startswith("http"):
                    link = f"https://www.michigan.gov{link}"
                
                # Try to get date
                date_el = await item.query_selector(".date, .event-date, time")
                date_text = await date_el.inner_text() if date_el else ""
                
                # Parse date (try multiple formats)
                meeting_date = None
                date_formats = [
                    "%B %d, %Y",      # January 15, 2025
                    "%m/%d/%Y",       # 01/15/2025
                    "%Y-%m-%d",       # 2025-01-15
                    "%b %d, %Y",      # Jan 15, 2025
                ]
                
                for fmt in date_formats:
                    try:
                        meeting_date = datetime.strptime(date_text.strip(), fmt)
                        meeting_date = meeting_date.replace(hour=10, minute=0, tzinfo=MICHIGAN_TZ)
                        break
                    except ValueError:
                        continue
                
                # Also try extracting from URL
                if not meeting_date and link:
                    date_match = re.search(r'/(\d{4})/(\d{2})/(\d{2})/', link)
                    if date_match:
                        year, month, day = date_match.groups()
                        meeting_date = datetime(int(year), int(month), int(day), 10, 0, tzinfo=MICHIGAN_TZ)
                
                if not meeting_date:
                    continue
                
                # Skip past meetings
                if meeting_date < datetime.now(MICHIGAN_TZ):
                    continue
                
                # Get description if available
                desc_el = await item.query_selector(".description, .event-description, p")
                description = await desc_el.inner_text() if desc_el else ""
                
                meeting = {
                    "title": title.strip(),
                    "description": description.strip()[:500] if description else None,
                    "agency": "EGLE",
                    "agency_full_name": "Michigan Department of Environment, Great Lakes, and Energy",
                    "department": None,  # Could be Air Quality, Water Resources, etc.
                    "meeting_type": determine_meeting_type(title),
                    "start_datetime": meeting_date.isoformat(),
                    "timezone": "America/Detroit",
                    "location_name": "EGLE Headquarters",
                    "location_address": "525 W. Allegan St.",
                    "location_city": "Lansing",
                    "location_state": "Michigan",
                    "location_zip": "48933",
                    "latitude": 42.7335,
                    "longitude": -84.5555,
                    "is_virtual": True,  # Most EGLE meetings are hybrid now
                    "is_hybrid": True,
                    "accepts_public_comment": True,
                    "contact_email": "EGLE-Assist@Michigan.gov",
                    "contact_phone": "800-662-9278",
                    "issue_tags": extract_issue_tags(title, description),
                    "region": "statewide",  # Could be regional based on content
                    "source": "egle_scraper",
                    "source_url": link,
                    "source_id": f"egle-{meeting_date.strftime('%Y%m%d')}-{hash(title) % 10000}",
                    "status": "upcoming",
                    "details_url": link,
                }
                
                meetings.append(meeting)
                print(f"  Found: {title[:50]}... on {meeting_date.strftime('%Y-%m-%d')}")
                
            except Exception as e:
                print(f"  Error parsing event: {e}")
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
            print(f"  Upserted: {meeting['title'][:50]}...")
        except Exception as e:
            print(f"  Error upserting {meeting['title'][:30]}: {e}")


async def main():
    """Main entry point."""
    print("=" * 60)
    print("EGLE Meeting Scraper")
    print("=" * 60)
    
    meetings = await scrape_egle_meetings()
    print(f"\nFound {len(meetings)} upcoming EGLE meetings")
    
    if meetings:
        print("\nUpserting to database...")
        upsert_meetings(meetings)
    
    print("\nDone!")
    return meetings


if __name__ == "__main__":
    asyncio.run(main())
