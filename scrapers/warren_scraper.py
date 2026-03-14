"""
Warren Meeting Scraper
Scrapes City of Warren public meetings from their WordPress site.

Strategy: Parse the meetings sitemap XML for all meeting URLs, then fetch
individual detail pages to extract date, time, location, and agenda PDFs.

No API available — WordPress REST API returns 401.
No Playwright needed — all content is server-rendered HTML.

Source: https://www.cityofwarren.org/meetings/
Sitemap: https://www.cityofwarren.org/meetings-sitemap.xml
"""

import hashlib
import os
import re
from datetime import datetime, timedelta
from xml.etree import ElementTree
from zoneinfo import ZoneInfo

import httpx
from bs4 import BeautifulSoup
from dotenv import load_dotenv

from scraper_utils import print_result

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
MICHIGAN_TZ = ZoneInfo("America/Detroit")

SITEMAP_URL = "https://www.cityofwarren.org/meetings-sitemap.xml"
BASE_URL = "https://www.cityofwarren.org"

# How far ahead to look for meetings (days)
LOOKAHEAD_DAYS = 90

# Bodies with environmental/infrastructure relevance
ENV_BODIES = {
    "planning commission": ["planning", "zoning"],
    "master plan committee": ["planning", "environment"],
    "brownfield redevelopment authority": ["environment", "contamination"],
    "parks and recreation commission": ["parks", "environment"],
    "sidewalk and tree board of review": ["infrastructure", "environment"],
}

DEFAULT_TAGS = ["government", "warren"]


def parse_body_name(title):
    """Extract the body/commission name from a meeting title.

    Titles follow the pattern: "Body Name Meeting – Date" or "Body Name Meeting - Date"
    """
    # Remove date portion after "Meeting" + separator
    match = re.match(r'^(.+?)\s+Meeting\s*[–—\-]\s*', title, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    # Fallback: "Special Meeting" or other format
    match = re.match(r'^(.+?)\s+(?:Special\s+)?Meeting', title, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return title.strip()


def parse_date_from_text(text):
    """Parse a date string like 'March 10, 2026' into a datetime."""
    # Common formats seen on Warren's site
    formats = [
        "%B %d, %Y",      # March 10, 2026
        "%b %d, %Y",      # Mar 10, 2026
        "%m/%d/%Y",        # 03/10/2026
    ]
    text = text.strip()
    for fmt in formats:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def parse_time_from_text(text):
    """Parse a time string like '7:00 pm' into (hour, minute)."""
    text = text.strip().lower()
    match = re.search(r'(\d{1,2}):(\d{2})\s*(am|pm)', text)
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2))
        ampm = match.group(3)
        if ampm == "pm" and hour != 12:
            hour += 12
        if ampm == "am" and hour == 12:
            hour = 0
        return hour, minute
    return None, None


def determine_meeting_type(body_name):
    """Determine meeting type from body name."""
    lower = body_name.lower()
    if "special" in lower:
        return "special_meeting"
    if "city council" in lower or "committee of the whole" in lower:
        return "board_meeting"
    if "commission" in lower or "committee" in lower or "advisory" in lower:
        return "committee_meeting"
    if "board" in lower or "authority" in lower:
        return "committee_meeting"
    if "hearing" in lower:
        return "public_hearing"
    return "public_meeting"


def get_issue_tags(body_name):
    """Get issue tags based on body name."""
    lower = body_name.lower()
    for key, tags in ENV_BODIES.items():
        if key in lower:
            return tags
    return DEFAULT_TAGS


def generate_source_id(url):
    """Generate a stable source_id from the meeting URL."""
    # Use the URL slug as the ID — it's unique and stable
    slug = url.rstrip("/").split("/")[-1]
    return f"warren-{slug}"


def parse_meeting_page(html, url):
    """Parse a Warren meeting detail page into a meeting dict.

    Returns a meeting dict or None if the page can't be parsed.
    """
    soup = BeautifulSoup(html, "html.parser")

    # Title from <h1>
    h1 = soup.find("h1")
    if not h1:
        return None
    title = h1.get_text(strip=True)

    body_name = parse_body_name(title)

    # Extract date, time, location from the <p> tags after the title
    # The structure is: <h1>, then <p>Location</p>, <p>Date</p>, <p>Time</p>
    # But this isn't guaranteed — we search all <p> tags for date/time patterns
    content_div = soup.find("div", class_="entry-content") or soup.find("article") or soup
    paragraphs = content_div.find_all("p")

    meeting_date = None
    meeting_time_hour = None
    meeting_time_minute = None
    location = None

    for p in paragraphs:
        text = p.get_text(strip=True)
        if not text or len(text) > 200:
            continue

        # Try to find a date (e.g., "March 10, 2026")
        if not meeting_date:
            date_match = re.search(
                r'(January|February|March|April|May|June|July|August|September|October|November|December)'
                r'\s+\d{1,2},\s+\d{4}',
                text
            )
            if date_match:
                meeting_date = parse_date_from_text(date_match.group(0))
                continue

        # Try to find a time (e.g., "7:00 pm")
        if meeting_time_hour is None:
            time_match = re.search(r'\d{1,2}:\d{2}\s*[aApP][mM]', text)
            if time_match and len(text) < 30:
                meeting_time_hour, meeting_time_minute = parse_time_from_text(time_match.group(0))
                continue

        # Location: a short text that's not a date, time, or boilerplate
        if not location and len(text) < 100:
            if not re.search(r'(disability|accommodation|contact|phone|email)', text, re.IGNORECASE):
                if not re.search(r'\d{1,2}:\d{2}\s*[aApP][mM]', text):
                    if not re.search(r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d', text):
                        location = text

    # If we couldn't find a date from the page, try from the URL slug
    if not meeting_date:
        slug = url.rstrip("/").split("/")[-1]
        slug_match = re.search(r'(\w+)-(\d{1,2})-(\d{4})$', slug)
        if slug_match:
            month_str, day, year = slug_match.groups()
            try:
                meeting_date = datetime.strptime(f"{month_str} {day} {year}", "%B %d %Y")
            except ValueError:
                pass

    if not meeting_date:
        return None

    # Build datetime
    if meeting_time_hour is not None:
        meeting_date = meeting_date.replace(hour=meeting_time_hour, minute=meeting_time_minute)
    meeting_date = meeting_date.replace(tzinfo=MICHIGAN_TZ)

    # Extract agenda/minutes PDFs from resource links
    agenda_url = None
    minutes_url = None
    for link in soup.find_all("a", href=True):
        href = link["href"]
        link_text = link.get_text(strip=True).lower()
        if not href.endswith(".pdf"):
            continue
        if "agenda" in link_text and not agenda_url:
            agenda_url = href if href.startswith("http") else f"{BASE_URL}{href}"
        elif "minutes" in link_text and not minutes_url:
            minutes_url = href if href.startswith("http") else f"{BASE_URL}{href}"

    # Contact info
    contact_email = None
    contact_phone = None
    for link in soup.find_all("a", href=True):
        href = link["href"]
        if href.startswith("mailto:") and not contact_email:
            contact_email = href.replace("mailto:", "")
        elif href.startswith("tel:") and not contact_phone:
            contact_phone = href.replace("tel:", "")

    meeting = {
        "title": body_name,
        "agency": f"City of Warren - {body_name}",
        "meeting_date": meeting_date.strftime("%Y-%m-%d"),
        "meeting_time": meeting_date.strftime("%H:%M") if meeting_time_hour is not None else None,
        "start_datetime": meeting_date.isoformat(),
        "location": location,
        "meeting_type": determine_meeting_type(body_name),
        "source": "warren_scraper",
        "source_id": generate_source_id(url),
        "details_url": url,
        "agenda_url": agenda_url,
        "minutes_url": minutes_url,
        "region": "Macomb County",
        "issue_tags": get_issue_tags(body_name),
    }

    return meeting


def parse_sitemap(xml_text):
    """Parse a WordPress sitemap XML and return list of (url, lastmod) tuples."""
    # Remove XML namespace for easier parsing
    xml_text = re.sub(r'\sxmlns="[^"]*"', '', xml_text, count=1)
    root = ElementTree.fromstring(xml_text)

    urls = []
    for url_el in root.findall(".//url"):
        loc = url_el.findtext("loc", "")
        lastmod = url_el.findtext("lastmod", "")
        if loc:
            urls.append((loc, lastmod))
    return urls


def filter_upcoming_urls(sitemap_urls):
    """Filter sitemap URLs to only those that could be upcoming meetings.

    We use the URL slug date to pre-filter, avoiding fetching hundreds of past meetings.
    """
    now = datetime.now(MICHIGAN_TZ)
    cutoff = now - timedelta(days=7)  # Include meetings from the past week too
    max_date = now + timedelta(days=LOOKAHEAD_DAYS)

    upcoming = []
    for url, lastmod in sitemap_urls:
        slug = url.rstrip("/").split("/")[-1]
        # Try to extract date from slug: body-name-meeting-month-day-year
        date_match = re.search(r'-(\w+)-(\d{1,2})-(\d{4})$', slug)
        if date_match:
            month_str, day, year = date_match.groups()
            try:
                meeting_date = datetime.strptime(f"{month_str} {day} {year}", "%B %d %Y")
                meeting_date = meeting_date.replace(tzinfo=MICHIGAN_TZ)
                if cutoff <= meeting_date <= max_date:
                    upcoming.append(url)
                continue
            except ValueError:
                pass
        # If we can't parse the date from the slug, include it (conservative)
        upcoming.append(url)
    return upcoming


async def fetch_sitemap(client):
    """Fetch and parse the meetings sitemap."""
    print(f"Fetching sitemap from {SITEMAP_URL}")
    resp = await client.get(SITEMAP_URL, timeout=30)
    resp.raise_for_status()
    return parse_sitemap(resp.text)


async def fetch_meeting_page(client, url):
    """Fetch a single meeting detail page."""
    resp = await client.get(url, timeout=20)
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
    """Main entry point — scrape Warren meetings from sitemap + detail pages."""
    print("=" * 60)
    print("City of Warren Meeting Scraper")
    print("=" * 60)

    async with httpx.AsyncClient(
        follow_redirects=True,
        headers={"User-Agent": "PlanetDetroit-CivicScraper/1.0"}
    ) as client:
        # Step 1: Get all meeting URLs from sitemap
        sitemap_urls = await fetch_sitemap(client)
        print(f"  Found {len(sitemap_urls)} total meetings in sitemap")

        # Step 2: Filter to upcoming meetings only
        upcoming_urls = filter_upcoming_urls(sitemap_urls)
        print(f"  {len(upcoming_urls)} potentially upcoming meetings to check")

        # Step 3: Fetch and parse each meeting page
        meetings = []
        for url in upcoming_urls:
            try:
                html = await fetch_meeting_page(client, url)
                meeting = parse_meeting_page(html, url)
                if meeting:
                    meetings.append(meeting)
                    print(f"  Found: {meeting['title'][:45]} ({meeting['meeting_date']})")
            except Exception as e:
                print(f"  Error fetching {url}: {e}")

    print(f"\nBuilt {len(meetings)} meeting records")
    env_count = sum(1 for m in meetings if m["issue_tags"] != DEFAULT_TAGS)
    print(f"  {env_count} environmentally relevant, {len(meetings) - env_count} general")

    if meetings:
        print("\nUpserting to database...")
        upsert_meetings(meetings)

    print("\nDone!")
    print_result("warren", "ok", len(meetings), "meetings")
    return meetings


if __name__ == "__main__":
    import asyncio
    try:
        asyncio.run(main())
    except Exception as e:
        print_result("warren", "error", error=str(e))
        raise
