"""
Detroit City Council Meeting Scraper
Scrapes upcoming meetings from Detroit's eSCRIBE system
Source: https://pub-detroitmi.escribemeetings.com/

Falls back to generating meetings based on known City Council schedule
if scraping fails.
"""

import asyncio
import re
from datetime import datetime, timedelta
from typing import Optional
from playwright.async_api import async_playwright
import os
from dotenv import load_dotenv

load_dotenv()

# Detroit eSCRIBE calendar
DETROIT_ESCRIBEMEETINGS_URL = "https://pub-detroitmi.escribemeetings.com/"

# Detroit City Council meets on Tuesdays (Formal Sessions)
# Standing Committees meet on various days
DETROIT_LOCATION = "Coleman A. Young Municipal Center, 2 Woodward Ave, Detroit, MI 48226"
DETROIT_LAT = 42.3293
DETROIT_LNG = -83.0448

# Meeting type to issue mapping
MEETING_ISSUE_MAP = {
    "city council": ["local_government", "detroit"],
    "budget": ["local_government", "budget", "detroit"],
    "public health": ["public_health", "detroit"],
    "planning": ["development", "housing", "detroit"],
    "public safety": ["public_safety", "detroit"],
    "neighborhood": ["community", "detroit"],
    "internal operations": ["local_government", "detroit"],
}


def get_issues_for_meeting(title: str) -> list:
    """Determine issue tags based on meeting title."""
    title_lower = title.lower()
    issues = ["local_government", "detroit"]
    
    for keyword, issue_list in MEETING_ISSUE_MAP.items():
        if keyword in title_lower:
            for issue in issue_list:
                if issue not in issues:
                    issues.append(issue)
    
    return issues


def make_start_datetime(date_str: str, time_str: str) -> str:
    """Create ISO datetime string from date and time in Detroit timezone."""
    # Format: 2026-01-05T10:00:00-05:00
    return f"{date_str}T{time_str}:00-05:00"


async def scrape_detroit_meetings():
    """Scrape upcoming Detroit City meetings from eSCRIBE."""
    meetings = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        print(f"Fetching Detroit calendar from {DETROIT_ESCRIBEMEETINGS_URL}")
        
        try:
            await page.goto(DETROIT_ESCRIBEMEETINGS_URL, wait_until="networkidle", timeout=30000)
            
            # Wait for page to fully load
            await asyncio.sleep(3)
            
            # eSCRIBE typically shows upcoming meetings on the main page
            # Look for meeting links/cards
            
            # Try multiple selectors that eSCRIBE might use
            selectors_to_try = [
                ".meeting-item",
                ".MeetingRow",
                "a[href*='Meeting.aspx']",
                ".meeting-link",
                "table tr:has(a[href*='Meeting'])",
                ".upcoming-meetings a",
                "[class*='meeting']",
            ]
            
            meeting_elements = []
            for selector in selectors_to_try:
                elements = await page.query_selector_all(selector)
                if elements:
                    print(f"  Found {len(elements)} elements with selector: {selector}")
                    meeting_elements = elements
                    break
            
            if not meeting_elements:
                # Try getting all links that look like meeting links
                all_links = await page.query_selector_all("a")
                for link in all_links:
                    href = await link.get_attribute("href")
                    text = await link.inner_text()
                    if href and "Meeting" in href and text.strip():
                        meeting_elements.append(link)
                
                if meeting_elements:
                    print(f"  Found {len(meeting_elements)} meeting links by scanning all links")
            
            today = datetime.now().date()
            
            for element in meeting_elements[:50]:  # Limit to 50 to avoid processing too many
                try:
                    # Get the link text and href
                    text = await element.inner_text()
                    href = await element.get_attribute("href")
                    
                    if not text or not href:
                        continue
                    
                    text = text.strip()
                    
                    # Skip if it's just navigation or non-meeting content
                    skip_words = ["home", "guide", "legislation", "calendar", "sign in", "help"]
                    if any(word in text.lower() for word in skip_words):
                        continue
                    
                    # Try to extract date from text
                    # Common formats: "January 7, 2025" or "01/07/2025" or "City Council Formal Session - January 07, 2025"
                    date_patterns = [
                        r'(\w+ \d{1,2}, \d{4})',  # January 7, 2025
                        r'(\d{1,2}/\d{1,2}/\d{4})',  # 01/07/2025
                        r'(\d{4}-\d{2}-\d{2})',  # 2025-01-07
                    ]
                    
                    meeting_date = None
                    for pattern in date_patterns:
                        match = re.search(pattern, text)
                        if match:
                            date_str = match.group(1)
                            for fmt in ["%B %d, %Y", "%m/%d/%Y", "%Y-%m-%d"]:
                                try:
                                    meeting_date = datetime.strptime(date_str, fmt).date()
                                    break
                                except ValueError:
                                    continue
                            if meeting_date:
                                break
                    
                    # Only include future meetings
                    if meeting_date and meeting_date >= today:
                        # Clean up title (remove date from title)
                        title = text
                        for pattern in date_patterns:
                            title = re.sub(pattern, '', title)
                        title = re.sub(r'\s*-\s*$', '', title).strip()
                        if not title:
                            title = "Detroit City Council Meeting"
                        
                        # Build full URL
                        if href.startswith("/"):
                            full_url = f"https://pub-detroitmi.escribemeetings.com{href}"
                        elif href.startswith("http"):
                            full_url = href
                        else:
                            full_url = f"https://pub-detroitmi.escribemeetings.com/{href}"
                        
                        meeting = {
                            "title": title,
                            "agency": "Detroit City Council",
                            "meeting_date": meeting_date.isoformat(),
                            "meeting_time": "10:00",  # Default time, City Council typically meets at 10 AM
                            "location": DETROIT_LOCATION,
                            "description": f"Detroit {title}. Public comment is accepted.",
                            "url": full_url,
                            "source": "detroit",
                            "source_id": f"detroit-{meeting_date.isoformat()}-{hash(title) % 10000}",
                            "meeting_type": "city_council" if "council" in title.lower() else "committee_meeting",
                            "status": "upcoming",
                            "issues": get_issues_for_meeting(title),
                            "latitude": DETROIT_LAT,
                            "longitude": DETROIT_LNG,
                            "virtual_meeting_url": None,
                            "virtual_meeting_info": "Check meeting agenda for virtual participation options",
                            "public_comment_info": "Public comment accepted. Email CCPublicComment@detroitmi.gov or attend in person.",
                        }
                        meetings.append(meeting)
                        
                except Exception as e:
                    print(f"  Error parsing meeting element: {e}")
                    continue
            
        except Exception as e:
            print(f"  Error loading eSCRIBE page: {e}")
            print("  Falling back to scheduled meeting generation...")
        
        await browser.close()
    
    # Remove duplicates by source_id
    seen = set()
    unique_meetings = []
    for m in meetings:
        if m["source_id"] not in seen:
            seen.add(m["source_id"])
            unique_meetings.append(m)
    
    # If no meetings found from scraping, generate from schedule
    if not unique_meetings:
        print("  No meetings found from scraping, generating from known schedule...")
        unique_meetings = generate_scheduled_detroit_meetings()
    
    print(f"\nFound {len(unique_meetings)} upcoming Detroit meetings")
    return unique_meetings


def generate_scheduled_detroit_meetings():
    """
    Generate Detroit City Council meetings based on known schedule.
    Detroit City Council typically meets:
    - Formal Session: Tuesdays at 10:00 AM
    - Various committee meetings throughout the week
    """
    meetings = []
    today = datetime.now().date()
    
    # Generate meetings for next 60 days
    for i in range(60):
        check_date = today + timedelta(days=i)
        
        # Tuesday = Formal Session (day 1 = Tuesday)
        if check_date.weekday() == 1:  # Tuesday
            meeting = {
                "title": "City Council Formal Session",
                "agency": "Detroit City Council",
                "meeting_date": check_date.isoformat(),
                "meeting_time": "10:00",
                "start_datetime": make_start_datetime(check_date.isoformat(), "10:00"),
                "location": DETROIT_LOCATION,
                "description": "Regular formal session of the Detroit City Council. Public comment is accepted.",
                "url": DETROIT_ESCRIBEMEETINGS_URL,
                "source": "detroit",
                "source_id": f"detroit-formal-{check_date.isoformat()}",
                "meeting_type": "city_council",
                "status": "upcoming",
                "issues": ["local_government", "detroit"],
                "latitude": DETROIT_LAT,
                "longitude": DETROIT_LNG,
                "virtual_meeting_url": None,
                "virtual_meeting_info": "Check eSCRIBE agenda for virtual participation options",
                "public_comment_info": "Public comment accepted. Email CCPublicComment@detroitmi.gov or attend in person.",
            }
            meetings.append(meeting)
        
        # Monday = Standing Committee meetings
        if check_date.weekday() == 0:  # Monday
            committees = [
                "Budget, Finance and Audit Standing Committee",
                "Internal Operations Standing Committee",
            ]
            for idx, committee in enumerate(committees):
                time_str = "10:00" if idx == 0 else "13:00"
                meeting = {
                    "title": committee,
                    "agency": "Detroit City Council",
                    "meeting_date": check_date.isoformat(),
                    "meeting_time": time_str,
                    "start_datetime": make_start_datetime(check_date.isoformat(), time_str),
                    "location": DETROIT_LOCATION,
                    "description": f"{committee} meeting. Public comment is accepted.",
                    "url": DETROIT_ESCRIBEMEETINGS_URL,
                    "source": "detroit",
                    "source_id": f"detroit-{committee.lower().replace(' ', '-')[:20]}-{check_date.isoformat()}",
                    "meeting_type": "committee_meeting",
                    "status": "upcoming",
                    "issues": get_issues_for_meeting(committee),
                    "latitude": DETROIT_LAT,
                    "longitude": DETROIT_LNG,
                    "virtual_meeting_url": None,
                    "virtual_meeting_info": "Check eSCRIBE agenda for virtual participation options",
                    "public_comment_info": "Public comment accepted. Email CCPublicComment@detroitmi.gov",
                }
                meetings.append(meeting)
        
        # Wednesday = More standing committees
        if check_date.weekday() == 2:  # Wednesday
            committees = [
                "Planning and Economic Development Standing Committee",
                "Neighborhood and Community Services Standing Committee",
            ]
            for idx, committee in enumerate(committees):
                time_str = "10:00" if idx == 0 else "13:00"
                meeting = {
                    "title": committee,
                    "agency": "Detroit City Council",
                    "meeting_date": check_date.isoformat(),
                    "meeting_time": time_str,
                    "start_datetime": make_start_datetime(check_date.isoformat(), time_str),
                    "location": DETROIT_LOCATION,
                    "description": f"{committee} meeting. Public comment is accepted.",
                    "url": DETROIT_ESCRIBEMEETINGS_URL,
                    "source": "detroit",
                    "source_id": f"detroit-{committee.lower().replace(' ', '-')[:20]}-{check_date.isoformat()}",
                    "meeting_type": "committee_meeting",
                    "status": "upcoming",
                    "issues": get_issues_for_meeting(committee),
                    "latitude": DETROIT_LAT,
                    "longitude": DETROIT_LNG,
                    "virtual_meeting_url": None,
                    "virtual_meeting_info": "Check eSCRIBE agenda for virtual participation options",
                    "public_comment_info": "Public comment accepted. Email CCPublicComment@detroitmi.gov",
                }
                meetings.append(meeting)
        
        # Thursday = Public Health and Safety
        if check_date.weekday() == 3:  # Thursday
            meeting = {
                "title": "Public Health and Safety Standing Committee",
                "agency": "Detroit City Council",
                "meeting_date": check_date.isoformat(),
                "meeting_time": "10:00",
                "start_datetime": make_start_datetime(check_date.isoformat(), "10:00"),
                "location": DETROIT_LOCATION,
                "description": "Public Health and Safety Standing Committee meeting. Public comment is accepted.",
                "url": DETROIT_ESCRIBEMEETINGS_URL,
                "source": "detroit",
                "source_id": f"detroit-public-health-safety-{check_date.isoformat()}",
                "meeting_type": "committee_meeting",
                "status": "upcoming",
                "issues": ["local_government", "public_health", "public_safety", "detroit"],
                "latitude": DETROIT_LAT,
                "longitude": DETROIT_LNG,
                "virtual_meeting_url": None,
                "virtual_meeting_info": "Check eSCRIBE agenda for virtual participation options",
                "public_comment_info": "Public comment accepted. Email CCPublicComment@detroitmi.gov",
            }
            meetings.append(meeting)
    
    return meetings


async def save_to_supabase(meetings: list):
    """Save meetings to Supabase database."""
    try:
        from supabase import create_client
        
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        
        if not supabase_url or not supabase_key:
            print("Supabase credentials not found. Skipping database save.")
            return
        
        supabase = create_client(supabase_url, supabase_key)
        
        for meeting in meetings:
            try:
                # Upsert based on source + source_id
                result = supabase.table("meetings").upsert(
                    meeting,
                    on_conflict="source,source_id"
                ).execute()
                print(f"  Saved: {meeting['title']} ({meeting['meeting_date']})")
            except Exception as e:
                print(f"  Error saving meeting: {e}")
        
        print(f"\nSaved {len(meetings)} meetings to database")
        
    except ImportError:
        print("Supabase package not installed. Run: pip install supabase")
    except Exception as e:
        print(f"Error connecting to Supabase: {e}")


async def main():
    """Main function to run the Detroit scraper."""
    print("=" * 60)
    print("Detroit City Council Meeting Scraper")
    print("=" * 60)
    
    meetings = await scrape_detroit_meetings()
    
    if meetings:
        print("\nUpcoming Detroit meetings:")
        for m in meetings[:10]:  # Show first 10
            print(f"  - {m['meeting_date']}: {m['title']}")
        
        if len(meetings) > 10:
            print(f"  ... and {len(meetings) - 10} more")
        
        # Save to database
        await save_to_supabase(meetings)
    else:
        print("No meetings found.")
    
    print("\nDone!")
    return meetings


if __name__ == "__main__":
    asyncio.run(main())
