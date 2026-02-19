"""
GLWA Meeting Scraper
Scrapes Great Lakes Water Authority board meetings from Legistar

Legistar uses a Telerik RadGrid table (tr.rgRow / tr.rgAltRow) with 13 cells:
  0: Name (plain text)       4: Location          8: Not available
  1: Date (MM/DD/YYYY)       5: Meeting details   9-12: docs
  2: Calendar icon link      6: ePacket
  3: Time (HH:MM AM/PM)     7: Agenda
"""

import asyncio
import hashlib
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
GLWA_LEGISTAR_URL = "https://glwater.legistar.com/Calendar.aspx"
MICHIGAN_TZ = ZoneInfo("America/Detroit")

# Meeting type mapping
GLWA_MEETING_TYPES = {
    "board of directors": "board_meeting",
    "audit committee": "committee_meeting",
    "legal committee": "committee_meeting",
    "operations": "committee_meeting",
    "capital planning": "committee_meeting",
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


async def scrape_meeting_detail(page, detail_url):
    """
    Follow a GLWA Legistar meeting detail page to extract virtual meeting info.
    Returns dict with virtual_url, virtual_phone, virtual_meeting_id, or empty dict.
    """
    try:
        await page.goto(detail_url, wait_until="networkidle", timeout=20000)
        await page.wait_for_timeout(2000)

        content = await page.content()
        body_text = await page.locator("body").inner_text()

        result = {}

        # Extract Zoom URL (GLWA uses glwater.zoom.us)
        zoom_match = re.search(r'(https?://[^\s"<>]*zoom\.us/[^\s"<>]+)', content)
        if zoom_match:
            result["virtual_url"] = zoom_match.group(1)

        # Extract Teams URL
        if "virtual_url" not in result:
            teams_match = re.search(r'(https?://teams\.microsoft\.com/[^\s"<>]+)', content)
            if teams_match:
                result["virtual_url"] = teams_match.group(1)

        # Extract toll-free dial-in number
        tollfree_match = re.search(r'(?:Toll-Free|US Toll-Free)[:\s]*(\d{3}\s*\d{3}\s*\d{4})', body_text, re.IGNORECASE)
        if tollfree_match:
            result["virtual_phone"] = tollfree_match.group(1).strip()
        else:
            phone_match = re.search(r'\+1\s*(\d{3}\s*\d{3}\s*\d{4})', body_text)
            if phone_match:
                result["virtual_phone"] = phone_match.group(1).strip()

        # Extract meeting/conference ID
        id_match = re.search(r'(?:Meeting\s*ID|Conference\s*ID)[:\s]*(\d[\d\s]{6,})', body_text, re.IGNORECASE)
        if id_match:
            result["virtual_meeting_id"] = re.sub(r'\s+', '', id_match.group(1))

        return result

    except Exception as e:
        print(f"    Error scraping detail: {e}")
        return {}


async def scrape_glwa_meetings():
    """Scrape upcoming GLWA meetings from Legistar RadGrid table."""
    meetings = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        print(f"Fetching GLWA calendar from {GLWA_LEGISTAR_URL}")
        try:
            await page.goto(GLWA_LEGISTAR_URL, wait_until="networkidle", timeout=30000)
        except Exception as e:
            print(f"  Failed to load page: {e}")
            await browser.close()
            return meetings

        await page.wait_for_timeout(3000)

        # Legistar uses Telerik RadGrid rows
        rows = await page.query_selector_all("tr.rgRow, tr.rgAltRow")
        print(f"  Found {len(rows)} RadGrid rows")

        now = datetime.now(MICHIGAN_TZ)

        for row in rows:
            try:
                cells = await row.query_selector_all("td")
                if len(cells) < 6:
                    continue

                # Cell 0: Meeting name (plain text)
                title = (await cells[0].inner_text()).strip()
                if not title:
                    continue

                # Cell 1: Date (MM/DD/YYYY)
                date_text = (await cells[1].inner_text()).strip()
                date_match = re.search(r'(\d{1,2}/\d{1,2}/\d{4})', date_text)
                if not date_match:
                    continue

                # Cell 3: Time (HH:MM AM/PM)
                time_text = (await cells[3].inner_text()).strip()
                time_match = re.search(r'(\d{1,2}:\d{2}\s*[AP]M)', time_text, re.IGNORECASE)

                # Parse date + time
                meeting_date = datetime.strptime(date_match.group(1), "%m/%d/%Y")
                if time_match:
                    t = datetime.strptime(time_match.group(1).strip(), "%I:%M %p")
                    meeting_date = meeting_date.replace(hour=t.hour, minute=t.minute)
                else:
                    meeting_date = meeting_date.replace(hour=10, minute=0)

                meeting_date = meeting_date.replace(tzinfo=MICHIGAN_TZ)

                # Skip past meetings
                if meeting_date < now:
                    continue

                # Cell 4: Location
                location_text = (await cells[4].inner_text()).strip()

                # Cell 5: "Meeting details" link
                detail_link_el = await cells[5].query_selector("a")
                detail_url = None
                if detail_link_el:
                    href = await detail_link_el.get_attribute("href")
                    if href:
                        detail_url = f"https://glwater.legistar.com/{href}" if not href.startswith("http") else href

                # Cell 7: Agenda link (if available)
                agenda_url = None
                if len(cells) > 7:
                    agenda_link_el = await cells[7].query_selector("a")
                    if agenda_link_el:
                        agenda_text = (await agenda_link_el.inner_text()).strip()
                        if agenda_text and agenda_text != "Not available":
                            href = await agenda_link_el.get_attribute("href")
                            if href:
                                agenda_url = f"https://glwater.legistar.com/{href}" if not href.startswith("http") else href

                # Determine if virtual/hybrid based on location
                is_zoom = "zoom" in location_text.lower()
                is_in_person = "water board" in location_text.lower() or "building" in location_text.lower()
                is_virtual = is_zoom
                is_hybrid = is_zoom and is_in_person

                meeting = {
                    "title": title,
                    "description": f"GLWA {title}",
                    "agency": "GLWA",
                    "agency_full_name": "Great Lakes Water Authority",
                    "department": None,
                    "meeting_type": determine_meeting_type(title),
                    "start_datetime": meeting_date.isoformat(),
                    "timezone": "America/Detroit",
                    "meeting_date": meeting_date.strftime("%Y-%m-%d"),
                    "meeting_time": meeting_date.strftime("%H:%M"),
                    "location_name": "Water Board Building" if is_in_person else location_text,
                    "location_address": "735 Randolph Street" if is_in_person else None,
                    "location_city": "Detroit",
                    "location_state": "Michigan",
                    "location_zip": "48226",
                    "latitude": 42.3350,
                    "longitude": -83.0456,
                    "is_virtual": is_virtual,
                    "is_hybrid": is_hybrid,
                    "accepts_public_comment": True,
                    "public_comment_instructions": "Public comment is typically allowed at the beginning of board meetings",
                    "contact_phone": "313-267-6000",
                    "contact_email": "systemcontrol@glwater.org",
                    "issue_tags": ["drinking_water", "water_quality", "infrastructure"],
                    "region": "southeast_michigan",
                    "source": "glwa_scraper",
                    "source_url": detail_url or GLWA_LEGISTAR_URL,
                    "source_id": f"glwa-{meeting_date.strftime('%Y%m%d')}-{hashlib.md5(title.encode()).hexdigest()[:12]}",
                    "status": "upcoming",
                    "details_url": detail_url,
                    "agenda_url": agenda_url,
                }

                meetings.append(meeting)
                print(f"  Found: {title} on {meeting_date.strftime('%Y-%m-%d %H:%M')}")

            except Exception as e:
                print(f"  Error parsing row: {e}")
                continue

        # Collect clickable MeetingDetail links from the page.
        # Note: GLWA Legistar only publishes detail pages for recent/past meetings.
        # Far-future meetings have grayed-out "Not viewable" links with no href.
        # We still scrape available detail pages to capture Zoom info for any
        # upcoming meetings that have been published (usually same-week meetings).
        detail_links = await page.query_selector_all('a[href*="MeetingDetail"]')
        detail_urls = []
        for link in detail_links:
            href = await link.get_attribute("href")
            if href:
                full = f"https://glwater.legistar.com/{href}" if not href.startswith("http") else href
                detail_urls.append(full)

        # Build a lookup of our upcoming meetings by (name_lower, date_str)
        meeting_lookup = {}
        for meeting in meetings:
            # Convert YYYY-MM-DD to M/D/YYYY for matching Legistar page titles
            d = datetime.strptime(meeting["meeting_date"], "%Y-%m-%d")
            legistar_date = f"{d.month}/{d.day}/{d.year}"
            key = (meeting["title"].lower(), legistar_date)
            meeting_lookup[key] = meeting

        matched = 0
        if detail_urls:
            print(f"\n  Checking {len(detail_urls)} detail pages for Zoom links...")
            for detail_url in detail_urls:
                try:
                    resp = await page.goto(detail_url, wait_until="domcontentloaded", timeout=15000)
                    await page.wait_for_timeout(1500)

                    # Extract meeting name & date from page title
                    page_title = await page.title()
                    title_match = re.search(r'Meeting of (.+?) on (\d{1,2}/\d{1,2}/\d{4})', page_title)
                    if not title_match:
                        continue

                    detail_name = title_match.group(1).strip().lower()
                    detail_date = title_match.group(2)

                    # Check if this matches any of our upcoming meetings
                    key = (detail_name, detail_date)
                    meeting = meeting_lookup.get(key)
                    if not meeting:
                        continue

                    # Found a match — extract Zoom info
                    virtual_info = await scrape_meeting_detail(page, detail_url)
                    if virtual_info:
                        meeting["details_url"] = detail_url
                        if "virtual_url" in virtual_info:
                            meeting["virtual_url"] = virtual_info["virtual_url"]
                            meeting["is_virtual"] = True
                            meeting["is_hybrid"] = True
                        if "virtual_phone" in virtual_info:
                            meeting["virtual_phone"] = virtual_info["virtual_phone"]
                        if "virtual_meeting_id" in virtual_info:
                            meeting["virtual_meeting_id"] = virtual_info["virtual_meeting_id"]
                        matched += 1
                        print(f"    {meeting['title'][:45]} ({meeting['meeting_date']}) -> Zoom={bool(virtual_info.get('virtual_url'))}")

                except Exception as e:
                    continue

            print(f"  Matched Zoom info to {matched} upcoming meetings")

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
