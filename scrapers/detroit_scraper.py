"""
Detroit City Council Meeting Scraper
Scrapes upcoming meetings from Detroit's eSCRIBE system.
Source: https://pub-detroitmi.escribemeetings.com/

Strategy:
  1. Load the page and click "List" view
  2. Extract .calendar-item cards (title link, date-title text)
  3. Parse date from "Day, Month DD, YYYY @ H:MM AM/PM" format
  4. Falls back to generating meetings from known Council schedule if scraping fails
"""

import asyncio
import hashlib
import re
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from playwright.async_api import async_playwright
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

# Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
DETROIT_ESCRIBEMEETINGS_URL = "https://pub-detroitmi.escribemeetings.com/"
MICHIGAN_TZ = ZoneInfo("America/Detroit")

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
    "community development": ["community", "housing", "detroit"],
}


def get_supabase():
    """Initialize Supabase client."""
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def get_issues_for_meeting(title):
    """Determine issue tags based on meeting title."""
    title_lower = title.lower()
    issues = set(["local_government", "detroit"])

    for keyword, issue_list in MEETING_ISSUE_MAP.items():
        if keyword in title_lower:
            issues.update(issue_list)

    return list(issues)


def determine_meeting_type(title):
    """Determine meeting type from title."""
    title_lower = title.lower()
    if "formal session" in title_lower:
        return "city_council"
    if "special session" in title_lower:
        return "special_meeting"
    if "committee" in title_lower or "standing" in title_lower:
        return "committee_meeting"
    if "block grant" in title_lower:
        return "public_hearing"
    return "city_council"


def build_agenda_url(guid):
    """Build eSCRIBE agenda URL from meeting GUID."""
    return f"https://pub-detroitmi.escribemeetings.com/Meeting.aspx?Id={guid}&Agenda=Agenda&lang=English"


async def fetch_escribemeetings_calendar(page, months_ahead=3):
    """
    Call eSCRIBE's internal calendar API to get meeting GUIDs and metadata.
    Returns a dict mapping (title_lower, date_str) -> meeting info with GUID.
    """
    try:
        now = datetime.now(MICHIGAN_TZ)
        end = now + timedelta(days=months_ahead * 30)
        start_str = now.strftime("%Y-%m-%dT00:00:00-05:00")
        end_str = end.strftime("%Y-%m-%dT00:00:00-05:00")

        result = await page.evaluate(f'''async () => {{
            const resp = await fetch('/MeetingsCalendarView.aspx/GetCalendarMeetings', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest' }},
                body: JSON.stringify({{
                    calendarStartDate: '{start_str}',
                    calendarEndDate: '{end_str}'
                }})
            }});
            return await resp.text();
        }}''')

        import json
        data = json.loads(result)
        inner = json.loads(data['d']) if isinstance(data['d'], str) else data['d']

        lookup = {}
        for m in inner:
            name = m.get("MeetingName", "").strip()
            guid = m.get("ID", "")
            start = m.get("StartDate", "")
            has_agenda = m.get("HasAgenda", False)
            if not name or not guid:
                continue
            # Parse date from "2026/02/18 10:00:00"
            date_str = start[:10].replace("/", "-") if start else ""
            key = (name.lower(), date_str)
            lookup[key] = {
                "guid": guid,
                "has_agenda": has_agenda,
                "agenda_url": build_agenda_url(guid) if has_agenda else None,
                "details_url": f"https://pub-detroitmi.escribemeetings.com/Meeting.aspx?Id={guid}&lang=English",
            }

        print(f"  eSCRIBE calendar API: {len(lookup)} meetings with GUIDs")
        return lookup

    except Exception as e:
        print(f"  Warning: Could not fetch eSCRIBE calendar API: {e}")
        return {}


async def scrape_meeting_detail(page, detail_url):
    """
    Follow a Detroit eSCRIBE meeting detail page to extract virtual meeting info.
    Returns dict with virtual_url, virtual_phone, virtual_meeting_id, or empty dict.
    """
    try:
        await page.goto(detail_url, wait_until="networkidle", timeout=20000)
        await page.wait_for_timeout(2000)

        content = await page.content()
        body_text = await page.locator("body").inner_text()

        result = {}

        # Extract Zoom URL
        zoom_match = re.search(r'(https?://[^\s"<>]*zoom\.us/[^\s"<>]+)', content)
        if zoom_match:
            result["virtual_url"] = zoom_match.group(1)

        # Extract Teams URL
        if "virtual_url" not in result:
            teams_match = re.search(r'(https?://teams\.microsoft\.com/[^\s"<>]+)', content)
            if teams_match:
                result["virtual_url"] = teams_match.group(1)

        # Extract Zoom meeting ID from text
        id_match = re.search(r'Meeting\s*ID[:\s]*(\d[\d\s]{6,})', body_text, re.IGNORECASE)
        if id_match:
            meeting_id = re.sub(r'\s+', '', id_match.group(1))
            result["virtual_meeting_id"] = meeting_id
            # Construct Zoom join URL from meeting ID if no URL was found
            if "virtual_url" not in result:
                result["virtual_url"] = f"https://zoom.us/j/{meeting_id}"

        # Extract phone numbers for dial-in
        # Pattern: +1 NNN NNN NNNN or similar
        phone_matches = re.findall(r'\+1\s*\d{3}\s*\d{3}\s*\d{4}', body_text)
        if phone_matches:
            result["virtual_phone"] = phone_matches[0].strip()

        if result:
            result["is_virtual"] = True
            result["is_hybrid"] = True

        return result

    except Exception as e:
        print(f"    Error scraping detail page: {e}")
        return {}


async def scrape_detroit_meetings():
    """Scrape upcoming Detroit City meetings from eSCRIBE."""
    meetings = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        print(f"Fetching Detroit calendar from {DETROIT_ESCRIBEMEETINGS_URL}")

        try:
            await page.goto(DETROIT_ESCRIBEMEETINGS_URL, wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(3000)

            # Switch to List view for cleaner structure
            list_btn = page.locator("text=List").first
            if await list_btn.is_visible():
                await list_btn.click()
                await page.wait_for_timeout(3000)
                print("  Switched to List view")

            # Extract .calendar-item containers
            cards = await page.locator(".calendar-item").all()
            print(f"  Found {len(cards)} meeting cards")

            now = datetime.now(MICHIGAN_TZ)

            for card in cards:
                try:
                    # Get title and link from .meeting-title-heading a
                    title_el = card.locator(".meeting-title-heading a").first
                    if await title_el.count() == 0:
                        continue

                    title = (await title_el.inner_text()).strip()
                    href = await title_el.get_attribute("href") or ""

                    # Build full URL and agenda URL
                    if href and not href.startswith("http"):
                        full_url = f"https://pub-detroitmi.escribemeetings.com/{href}"
                    else:
                        full_url = href

                    # Extract meeting ID for stable source_id and agenda URL
                    id_match = re.search(r'Id=([a-f0-9-]+)', href)
                    meeting_id = id_match.group(1) if id_match else ""

                    # eSCRIBE agenda URL (adds &Agenda=Agenda to show actual agenda items)
                    agenda_url = f"https://pub-detroitmi.escribemeetings.com/Meeting.aspx?Id={meeting_id}&Agenda=Agenda&lang=English" if meeting_id else None

                    # Get date/time and location from .date-title
                    date_el = card.locator(".date-title").first
                    date_text = (await date_el.inner_text()).strip() if await date_el.count() > 0 else ""

                    if not date_text:
                        continue

                    # Parse date: "Wednesday, February 18, 2026 @ 10:00 AM"
                    # Split into date line and location line
                    lines = [l.strip() for l in date_text.split("\n") if l.strip()]
                    date_line = lines[0] if lines else ""
                    location_line = lines[1] if len(lines) > 1 else ""

                    # Extract date and time from date line
                    date_match = re.search(
                        r'(\w+,\s+\w+ \d{1,2},\s+\d{4})\s*@\s*(\d{1,2}:\d{2}\s*[AP]M)',
                        date_line, re.IGNORECASE
                    )
                    if not date_match:
                        print(f"  Could not parse date from: {date_line}")
                        continue

                    date_str = date_match.group(1)
                    time_str = date_match.group(2).strip()

                    # Parse into datetime
                    # Remove the day name prefix ("Wednesday, ")
                    date_str_clean = re.sub(r'^\w+,\s*', '', date_str)
                    meeting_date = datetime.strptime(
                        f"{date_str_clean} {time_str}", "%B %d, %Y %I:%M %p"
                    ).replace(tzinfo=MICHIGAN_TZ)

                    # Skip past meetings
                    if meeting_date < now:
                        continue

                    meeting = {
                        "title": title,
                        "description": f"Detroit {title}. Public comment is accepted.",
                        "agency": "Detroit City Council",
                        "agency_full_name": "Detroit City Council",
                        "department": None,
                        "meeting_type": determine_meeting_type(title),
                        "start_datetime": meeting_date.isoformat(),
                        "timezone": "America/Detroit",
                        "meeting_date": meeting_date.strftime("%Y-%m-%d"),
                        "meeting_time": meeting_date.strftime("%H:%M"),
                        "location_name": "Coleman A. Young Municipal Center",
                        "location_address": "2 Woodward Ave",
                        "location_city": "Detroit",
                        "location_state": "Michigan",
                        "location_zip": "48226",
                        "latitude": DETROIT_LAT,
                        "longitude": DETROIT_LNG,
                        "is_virtual": False,
                        "is_hybrid": True,
                        "accepts_public_comment": True,
                        "public_comment_instructions": "Public comment accepted. Email CCPublicComment@detroitmi.gov or attend in person.",
                        "contact_email": "CCPublicComment@detroitmi.gov",
                        "contact_phone": "(313) 224-3443",
                        "issue_tags": get_issues_for_meeting(title),
                        "region": "detroit",
                        "source": "detroit_scraper",
                        "source_url": full_url,
                        "source_id": f"detroit-{meeting_id}" if meeting_id else f"detroit-{meeting_date.strftime('%Y%m%d')}-{hash(title) % 10000}",
                        "status": "upcoming",
                        "details_url": full_url,
                        "agenda_url": agenda_url,
                    }

                    meetings.append(meeting)
                    print(f"  Found: {title} on {meeting_date.strftime('%Y-%m-%d %H:%M')}")

                except Exception as e:
                    print(f"  Error parsing meeting card: {e}")
                    continue

            # Follow detail pages to extract virtual meeting info
            print(f"\n  Scraping {len(meetings)} detail pages for virtual meeting info...")
            for meeting in meetings:
                detail_url = meeting.get("details_url")
                if not detail_url:
                    continue
                print(f"    {meeting['title'][:50]}...", end="")
                virtual_info = await scrape_meeting_detail(page, detail_url)
                if virtual_info:
                    meeting.update(virtual_info)
                    zoom_id = virtual_info.get("virtual_meeting_id", "")
                    phone = virtual_info.get("virtual_phone", "")
                    print(f" Zoom ID={zoom_id}, Phone={phone}")
                else:
                    print(" (no virtual info)")

        except Exception as e:
            print(f"  Error loading eSCRIBE page: {e}")

        # Fetch eSCRIBE calendar API for meeting GUIDs (needed for agenda URLs)
        print("\n  Fetching eSCRIBE calendar API for agenda links...")
        await page.goto(DETROIT_ESCRIBEMEETINGS_URL, wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(2000)
        calendar_lookup = await fetch_escribemeetings_calendar(page)

        await browser.close()

    # Deduplicate by source_id
    seen = set()
    unique = []
    for m in meetings:
        if m["source_id"] not in seen:
            seen.add(m["source_id"])
            unique.append(m)
    scraped_count = len(unique)

    # If scraping found meetings, also generate schedule-based meetings for the
    # next 60 days to fill gaps (Council meets on a fixed schedule but eSCRIBE
    # only shows the next handful).
    if not unique:
        print("  No meetings scraped, generating from known schedule...")
        meetings = generate_scheduled_detroit_meetings()
    else:
        # Supplement with generated schedule for dates beyond what eSCRIBE shows
        meetings = list(unique)
        scraped_dates = {(m["title"].lower(), m["meeting_date"]) for m in meetings}
        generated = generate_scheduled_detroit_meetings()
        for g in generated:
            if (g["title"].lower(), g["meeting_date"]) not in scraped_dates:
                meetings.append(g)

    # Enrich all meetings with agenda URLs from eSCRIBE calendar API
    enriched = 0
    for meeting in meetings:
        key = (meeting["title"].lower(), meeting["meeting_date"])
        cal_info = calendar_lookup.get(key)
        if cal_info:
            if cal_info.get("agenda_url"):
                meeting["agenda_url"] = cal_info["agenda_url"]
            if not meeting.get("details_url") or meeting["details_url"] == DETROIT_ESCRIBEMEETINGS_URL:
                meeting["details_url"] = cal_info["details_url"]
            enriched += 1

    print(f"\nFound {len(meetings)} upcoming Detroit meetings ({scraped_count} scraped, {len(meetings) - scraped_count} generated, {enriched} with agenda links)")
    return meetings


def generate_scheduled_detroit_meetings():
    """
    Generate Detroit City Council meetings based on known schedule.
    Detroit City Council meets (verified against Documenters 2026-02-18):
      - Monday: Public Health & Safety 10 AM
      - Tuesday: Formal Session at 10:00 AM
      - Wednesday: Internal Ops 10 AM, Budget/Finance 1 PM
      - Thursday: Planning 10 AM, Neighborhood 1 PM
    """
    meetings = []
    today = datetime.now(MICHIGAN_TZ).date()

    # Shared Zoom for all Detroit City Council meetings
    DCC_ZOOM_ID = "85846903626"
    DCC_ZOOM_URL = f"https://cityofdetroit.zoom.us/j/{DCC_ZOOM_ID}"

    schedule = [
        (0, "Public Health and Safety Standing Committee", "10:00", "committee_meeting"),  # Monday
        (1, "City Council Formal Session", "10:00", "city_council"),  # Tuesday
        (2, "Internal Operations Standing Committee", "10:00", "committee_meeting"),  # Wednesday
        (2, "Budget, Finance and Audit Standing Committee", "13:00", "committee_meeting"),  # Wednesday
        (3, "Planning and Economic Development Standing Committee", "10:00", "committee_meeting"),  # Thursday
        (3, "Neighborhood and Community Services Standing Committee", "13:00", "committee_meeting"),  # Thursday
    ]

    for i in range(60):
        check_date = today + timedelta(days=i)
        for weekday, title, time_str, meeting_type in schedule:
            if check_date.weekday() != weekday:
                continue

            hour, minute = map(int, time_str.split(":"))
            meeting_dt = datetime(
                check_date.year, check_date.month, check_date.day,
                hour, minute, tzinfo=MICHIGAN_TZ
            )

            meetings.append({
                "title": title,
                "description": f"Detroit {title}. Public comment is accepted.",
                "agency": "Detroit City Council",
                "agency_full_name": "Detroit City Council",
                "department": None,
                "meeting_type": meeting_type,
                "start_datetime": meeting_dt.isoformat(),
                "timezone": "America/Detroit",
                "meeting_date": check_date.isoformat(),
                "meeting_time": time_str,
                "location_name": "Coleman A. Young Municipal Center",
                "location_address": "2 Woodward Ave",
                "location_city": "Detroit",
                "location_state": "Michigan",
                "location_zip": "48226",
                "latitude": DETROIT_LAT,
                "longitude": DETROIT_LNG,
                "is_virtual": True,
                "is_hybrid": True,
                "virtual_url": DCC_ZOOM_URL,
                "virtual_meeting_id": DCC_ZOOM_ID,
                "accepts_public_comment": True,
                "public_comment_instructions": "Public comment accepted. Email CCPublicComment@detroitmi.gov or attend in person.",
                "contact_email": "CCPublicComment@detroitmi.gov",
                "contact_phone": "(313) 224-3443",
                "issue_tags": get_issues_for_meeting(title),
                "region": "detroit",
                "source": "detroit_scraper",
                "source_url": DETROIT_ESCRIBEMEETINGS_URL,
                "source_id": f"detroit-sched-{check_date.isoformat()}-{hashlib.md5(title.encode()).hexdigest()[:8]}",
                "status": "upcoming",
                "details_url": None,
            })

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
            print(f"  Upserted: {meeting['title']} ({meeting['meeting_date']})")
        except Exception as e:
            print(f"  Error upserting {meeting['title'][:30]}: {e}")


async def main():
    """Main function to run the Detroit scraper."""
    print("=" * 60)
    print("Detroit City Council Meeting Scraper")
    print("=" * 60)

    meetings = await scrape_detroit_meetings()

    if meetings:
        print("\nUpcoming Detroit meetings (next 10):")
        for m in sorted(meetings, key=lambda x: x["start_datetime"])[:10]:
            print(f"  - {m['meeting_date']} {m['meeting_time']}: {m['title']}")

        if len(meetings) > 10:
            print(f"  ... and {len(meetings) - 10} more")

        print("\nUpserting to database...")
        upsert_meetings(meetings)
    else:
        print("No meetings found.")

    print("\nDone!")
    return meetings


if __name__ == "__main__":
    asyncio.run(main())
