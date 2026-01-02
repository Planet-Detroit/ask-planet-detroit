"""
GLWA Meeting Scraper
Scrapes Great Lakes Water Authority board meetings from Legistar
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
GLWA_LEGISTAR_URL = "https://glwater.legistar.com/Calendar.aspx"
MICHIGAN_TZ = ZoneInfo("America/Detroit")

# Meeting type mapping
GLWA_MEETING_TYPES = {
    "board of directors": "board_meeting",
    "audit committee": "committee_meeting",
    "legal committee": "committee_meeting",
    "operations": "committee_meeting",
    "finance committee": "committee_meeting",
    "workshop": "workshop",
    "special": "special_meeting",
}


def get_supabase():
    """Initialize Supabase client."""
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def determine_meeting_type(title):
    """Determine meeting type from title."""
    title_lower = title.lower()
    
    for keyword, meeting_type in GLWA_MEETING_TYPES.items():
        if keyword in title_lower:
            return meeting_type
    
    return "public_meeting"


async def scrape_glwa_meetings():
    """Scrape upcoming GLWA meetings from Legistar."""
    meetings = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        print(f"Fetching GLWA calendar from {GLWA_LEGISTAR_URL}")
        await page.goto(GLWA_LEGISTAR_URL, wait_until="networkidle")
        
        # Wait for calendar to load
        await asyncio.sleep(2)
        
        # Legistar uses a table-based layout
        # Look for meeting rows in the calendar
        rows = await page.query_selector_all("tr.rgRow, tr.rgAltRow, .meeting-row")
        print(f"Found {len(rows)} potential meeting rows")
        
        # If no rows found, try the calendar grid
        if not rows:
            # Try getting events from calendar cells
            cells = await page.query_selector_all("td.fc-day, .calendar-day")
            print(f"Found {len(cells)} calendar cells")
        
        for row in rows:
            try:
                # Get all cells in the row
                cells = await row.query_selector_all("td")
                if len(cells) < 3:
                    continue
                
                # Typical Legistar layout: Name | Date | Time | Location | Agenda
                # Get meeting name/title
                name_cell = cells[0] if cells else None
                title_el = await name_cell.query_selector("a") if name_cell else None
                
                if not title_el:
                    continue
                
                title = await title_el.inner_text()
                link = await title_el.get_attribute("href")
                
                # Make absolute URL
                if link and not link.startswith("http"):
                    link = f"https://glwater.legistar.com/{link}"
                
                # Get date
                date_text = ""
                time_text = ""
                
                for i, cell in enumerate(cells):
                    cell_text = await cell.inner_text()
                    
                    # Look for date pattern (MM/DD/YYYY or similar)
                    if re.search(r'\d{1,2}/\d{1,2}/\d{4}', cell_text):
                        date_text = cell_text.strip()
                    # Look for time pattern (HH:MM AM/PM)
                    elif re.search(r'\d{1,2}:\d{2}\s*(AM|PM|am|pm)', cell_text):
                        time_text = cell_text.strip()
                
                if not date_text:
                    continue
                
                # Parse date and time
                try:
                    # Try to extract just the date
                    date_match = re.search(r'(\d{1,2}/\d{1,2}/\d{4})', date_text)
                    if date_match:
                        date_str = date_match.group(1)
                        meeting_date = datetime.strptime(date_str, "%m/%d/%Y")
                    else:
                        continue
                    
                    # Add time if available
                    time_match = re.search(r'(\d{1,2}):(\d{2})\s*(AM|PM|am|pm)', time_text)
                    if time_match:
                        hour = int(time_match.group(1))
                        minute = int(time_match.group(2))
                        ampm = time_match.group(3).upper()
                        
                        if ampm == "PM" and hour != 12:
                            hour += 12
                        elif ampm == "AM" and hour == 12:
                            hour = 0
                        
                        meeting_date = meeting_date.replace(hour=hour, minute=minute)
                    else:
                        # Default to 10 AM
                        meeting_date = meeting_date.replace(hour=10, minute=0)
                    
                    meeting_date = meeting_date.replace(tzinfo=MICHIGAN_TZ)
                    
                except ValueError as e:
                    print(f"  Error parsing date '{date_text}': {e}")
                    continue
                
                # Skip past meetings
                if meeting_date < datetime.now(MICHIGAN_TZ):
                    continue
                
                # Get location if available
                location = ""
                for cell in cells:
                    cell_text = await cell.inner_text()
                    if "water board" in cell_text.lower() or "randolph" in cell_text.lower():
                        location = cell_text.strip()
                        break
                
                # Try to get agenda link
                agenda_url = None
                agenda_el = await row.query_selector("a[href*='Agenda'], a[href*='agenda']")
                if agenda_el:
                    agenda_url = await agenda_el.get_attribute("href")
                    if agenda_url and not agenda_url.startswith("http"):
                        agenda_url = f"https://glwater.legistar.com/{agenda_url}"
                
                meeting = {
                    "title": title.strip(),
                    "description": f"GLWA {title.strip()}",
                    "agency": "GLWA",
                    "agency_full_name": "Great Lakes Water Authority",
                    "department": None,
                    "meeting_type": determine_meeting_type(title),
                    "start_datetime": meeting_date.isoformat(),
                    "timezone": "America/Detroit",
                    "location_name": "Water Board Building",
                    "location_address": "735 Randolph Street",
                    "location_city": "Detroit",
                    "location_state": "Michigan",
                    "location_zip": "48226",
                    "latitude": 42.3350,
                    "longitude": -83.0456,
                    "is_virtual": True,
                    "is_hybrid": True,
                    "accepts_public_comment": True,
                    "public_comment_instructions": "Public comment is typically allowed at the beginning of board meetings",
                    "contact_phone": "313-267-6000",
                    "contact_email": "systemcontrol@glwater.org",
                    "issue_tags": ["drinking_water", "water_quality", "infrastructure"],
                    "region": "southeast_michigan",
                    "source": "glwa_scraper",
                    "source_url": link,
                    "source_id": f"glwa-{meeting_date.strftime('%Y%m%d')}-{hash(title) % 10000}",
                    "status": "upcoming",
                    "details_url": link,
                    "agenda_url": agenda_url,
                }
                
                meetings.append(meeting)
                print(f"  Found: {title[:50]}... on {meeting_date.strftime('%Y-%m-%d %H:%M')}")
                
            except Exception as e:
                print(f"  Error parsing row: {e}")
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
    print("GLWA Meeting Scraper")
    print("=" * 60)
    
    meetings = await scrape_glwa_meetings()
    print(f"\nFound {len(meetings)} upcoming GLWA meetings")
    
    if meetings:
        print("\nUpserting to database...")
        upsert_meetings(meetings)
    
    print("\nDone!")
    return meetings


if __name__ == "__main__":
    asyncio.run(main())
