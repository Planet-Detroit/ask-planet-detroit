"""
Wayne County Meeting Scraper
Scrapes Wayne County Commission meetings from waynecountymi.gov

Wayne County uses Granicus/OpenCities CMS with ASP.NET WebForms.
The listing page at /Government/County-Meetings uses postback-based pagination
with 10 meetings per page, sorted newest-first. We only need the first few
pages to capture all upcoming meetings.

Detail pages are server-rendered HTML, so we use httpx instead of Playwright.
"""

import asyncio
import hashlib
import os
import re

import httpx
from bs4 import BeautifulSoup
from datetime import datetime
from zoneinfo import ZoneInfo
from playwright.async_api import async_playwright
from supabase import create_client
from dotenv import load_dotenv

from scraper_utils import print_result

load_dotenv()

# Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
WAYNE_COUNTY_URL = "https://www.waynecountymi.gov/Government/County-Meetings"
BASE_URL = "https://www.waynecountymi.gov"
MICHIGAN_TZ = ZoneInfo("America/Detroit")

# How many listing pages to scrape (10 meetings per page).
# Since listings are newest-first, 3 pages = 30 most recent entries,
# which should cover all future meetings.
MAX_PAGES = 3

# Committee-specific issue tags
COMMITTEE_TAGS = {
    "health & human services": ["public_health", "government", "wayne_county"],
    "health and human services": ["public_health", "government", "wayne_county"],
    "public safety": ["public_safety", "government", "wayne_county"],
    "public safety judiciary": ["public_safety", "government", "wayne_county"],
    "public services": ["infrastructure", "government", "wayne_county"],
    "ways & means": ["government", "budget", "wayne_county"],
    "ways and means": ["government", "budget", "wayne_county"],
    "economic development": ["economic_development", "government", "wayne_county"],
    "environment": ["environment", "government", "wayne_county"],
    "ethics board": ["government", "ethics", "wayne_county"],
}

# Default tags for meetings that don't match a specific committee
DEFAULT_ISSUE_TAGS = ["government", "wayne_county"]


def generate_source_id(title, date_str):
    """Generate a deterministic source ID using hashlib.md5.

    Uses title + date to create a stable hash that won't change between runs.
    """
    key = f"{title}|{date_str}"
    hash_hex = hashlib.md5(key.encode()).hexdigest()[:12]
    return f"wayne-county-{hash_hex}"


def get_issue_tags(meeting_type_text):
    """Determine issue tags based on the meeting type / committee name."""
    if not meeting_type_text:
        return DEFAULT_ISSUE_TAGS
    text_lower = meeting_type_text.lower()
    for keyword, tags in COMMITTEE_TAGS.items():
        if keyword in text_lower:
            return tags
    return DEFAULT_ISSUE_TAGS


def determine_meeting_type(meeting_type_text):
    """Determine the meeting_type field from the committee/meeting type text."""
    if not meeting_type_text:
        return "public_meeting"
    text_lower = meeting_type_text.lower()
    if "full commission" in text_lower:
        return "board_meeting"
    if "committee" in text_lower or "commission" in text_lower:
        return "committee_meeting"
    if "hearing" in text_lower:
        return "public_hearing"
    if "workshop" in text_lower:
        return "workshop"
    if "special" in text_lower:
        return "special_meeting"
    if "board" in text_lower:
        return "board_meeting"
    return "public_meeting"


def parse_meeting_date(date_text):
    """Parse a date string like 'January 08, 2026' into a datetime.date.

    Returns None if parsing fails.
    """
    if not date_text:
        return None
    # Clean up extra whitespace
    date_text = re.sub(r'\s+', ' ', date_text.strip())
    try:
        return datetime.strptime(date_text, "%B %d, %Y").date()
    except ValueError:
        return None


def parse_meeting_time(time_text):
    """Parse a time string like '10:00 AM - 11:00 AM' into start time components.

    Returns a tuple of (hour, minute) in 24h format, or None if parsing fails.
    """
    if not time_text:
        return None
    # Extract the start time (before the dash)
    match = re.search(r'(\d{1,2}:\d{2}\s*[AP]M)', time_text, re.IGNORECASE)
    if not match:
        return None
    try:
        t = datetime.strptime(match.group(1).strip(), "%I:%M %p")
        return (t.hour, t.minute)
    except ValueError:
        return None


def extract_virtual_url(text):
    """Extract Zoom or Teams URL from free text."""
    if not text:
        return None
    # Look for Zoom URLs
    match = re.search(r'(https?://[\w.-]*zoom\.us/\S+)', text)
    if match:
        return match.group(1).rstrip('.,;)')
    # Look for Teams URLs
    match = re.search(r'(https?://teams\.microsoft\.com/\S+)', text)
    if match:
        return match.group(1).rstrip('.,;)')
    return None


def extract_meeting_id(text):
    """Extract virtual meeting ID from text.

    Looks for patterns like:
    - 'meeting identification number is: 277 771 1868'
    - 'Meeting ID: 817 153 5870'
    - zoom.us/j/85846903626
    """
    if not text:
        return None
    # Check for 'meeting identification number' or 'Meeting ID' patterns
    match = re.search(
        r'(?:meeting\s+identification\s+number\s+is|meeting\s*id)[:\s]*(\d[\d\s]{6,})',
        text, re.IGNORECASE
    )
    if match:
        return re.sub(r'\s+', '', match.group(1)).strip()
    # Check for Zoom URL with meeting ID
    match = re.search(r'zoom\.us/j/(\d+)', text)
    if match:
        return match.group(1)
    # Check for Zoom personal room URL — no numeric ID available
    return None


def extract_phone_numbers(text):
    """Extract dial-in phone numbers from text.

    Returns the first phone number found, formatted as-is.
    """
    if not text:
        return None
    # Match patterns like (312) 626-6799 or 312-626-6799 or +1 312 626 6799
    match = re.search(r'(\(?\d{3}\)?\s*[\-\s]?\d{3}[\-\s]?\d{4})', text)
    if match:
        return match.group(1).strip()
    return None


def parse_location(address_div_text):
    """Parse physical location from the meeting-address div text.

    The text often contains both virtual info and physical address.
    We extract the physical address line (typically the last paragraph
    or the line containing street address patterns).
    """
    if not address_div_text:
        return None

    # Split by newlines and look for physical address lines
    lines = [line.strip() for line in address_div_text.split('\n') if line.strip()]

    # Filter out lines that are just "Location" header or virtual meeting info
    address_lines = []
    for line in lines:
        # Skip header
        if line.lower() == 'location':
            continue
        # Skip lines that are primarily about virtual meetings
        if line.startswith('You can join the meeting by'):
            continue
        if line.startswith('or by dialing'):
            continue
        # A physical address typically contains a street number
        if re.search(r'\d+\s+\w+', line) and not line.startswith('http'):
            address_lines.append(line)

    if address_lines:
        return address_lines[0]
    return None


def parse_detail_page(html, detail_url):
    """Parse a Wayne County meeting detail page and extract all fields.

    Returns a dict with parsed meeting data, or None if parsing fails.
    """
    soup = BeautifulSoup(html, 'html.parser')

    result = {}

    # Title from h1
    title_el = soup.select_one('h1.oc-page-title')
    if title_el:
        result['title'] = title_el.get_text(strip=True)

    # Meeting date and type from the details list
    details_list = soup.select_one('ul.minutes-details-list, ul.content-details-list')
    if details_list:
        for li in details_list.find_all('li'):
            label_el = li.select_one('span.field-label')
            value_el = li.select_one('span.field-value')
            if not label_el or not value_el:
                continue
            label = label_el.get_text(strip=True)
            value = value_el.get_text(strip=True)

            if label == 'Meeting Date':
                result['date_text'] = value
            elif label == 'Meeting Type':
                result['type_text'] = value

    # Time from meeting-time div
    time_div = soup.select_one('div.meeting-time')
    if time_div:
        time_text = time_div.get_text(strip=True)
        # Remove the "Time" header
        time_text = re.sub(r'^Time\s*', '', time_text, flags=re.IGNORECASE)
        result['time_text'] = time_text.strip()

    # Location and virtual info from meeting-address div
    address_div = soup.select_one('div.meeting-address')
    if address_div:
        full_text = address_div.get_text(separator='\n')
        result['address_text'] = full_text
        result['location'] = parse_location(full_text)
        result['virtual_url'] = extract_virtual_url(full_text)
        result['virtual_meeting_id'] = extract_meeting_id(full_text)
        result['virtual_phone'] = extract_phone_numbers(full_text)

    # Agenda and minutes from related-information-list
    attachments = soup.select_one('div.meeting-attachments')
    if attachments:
        links = attachments.select('a')
        for link in links:
            href = link.get('href', '')
            link_text = link.get_text(strip=True).lower()

            # Make relative URLs absolute
            if href and not href.startswith('http'):
                href = BASE_URL + href

            # Identify agenda PDFs
            if 'agenda' in link_text and href:
                result['agenda_url'] = href
            # Identify minutes/journal PDFs
            elif 'journal' in link_text and href:
                result['minutes_url'] = href
            # Also check for document class indicators
            elif 'ext-pdf' in link.get('class', []):
                if 'agenda' in href.lower() and 'agenda_url' not in result:
                    result['agenda_url'] = href
                elif 'journal' in href.lower() and 'minutes_url' not in result:
                    result['minutes_url'] = href

    result['details_url'] = detail_url
    return result


async def scrape_listing_page(page):
    """Scrape meeting cards from the current listing page.

    Returns a list of dicts with: date_text, type_text, detail_url
    """
    cards = []
    articles = await page.query_selector_all('div.accordion-list-item-container article')

    for article in articles:
        try:
            card = {}

            # Date from span.minutes-date
            date_el = await article.query_selector('span.minutes-date')
            if date_el:
                card['date_text'] = (await date_el.inner_text()).strip()

            # Meeting type from span.meeting-type
            type_el = await article.query_selector('span.meeting-type')
            if type_el:
                card['type_text'] = (await type_el.inner_text()).strip()

            # Detail URL from a.accordion-trigger
            link_el = await article.query_selector('a.accordion-trigger')
            if link_el:
                href = await link_el.get_attribute('href')
                if href:
                    if not href.startswith('http'):
                        href = BASE_URL + href
                    card['detail_url'] = href

            if card.get('date_text'):
                cards.append(card)

        except Exception as e:
            print(f"  Error parsing listing card: {e}")
            continue

    return cards


async def click_next_page(page):
    """Click the next page button in the ASP.NET pagination.

    Returns True if navigation succeeded, False if no next page.
    """
    try:
        # Look for a "Next" or ">" link in the pager
        next_link = await page.query_selector('a.next-page, a[title="Next"], li.next a')
        if not next_link:
            # Try finding a ">" text link
            links = await page.query_selector_all('.pagination a, .pager a')
            for link in links:
                text = (await link.inner_text()).strip()
                if text in ('>', 'Next', '>>'):
                    next_link = link
                    break

        if not next_link:
            return False

        await next_link.click()
        await page.wait_for_timeout(3000)
        return True

    except Exception as e:
        print(f"  Error navigating to next page: {e}")
        return False


async def fetch_detail_page(client, url):
    """Fetch a detail page using httpx (no browser needed — server-rendered HTML)."""
    try:
        resp = await client.get(url, timeout=15.0, follow_redirects=True)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        print(f"  Error fetching detail page {url}: {e}")
        return None


async def scrape_wayne_county_meetings():
    """Scrape upcoming Wayne County meetings.

    1. Use Playwright to load the listing page and scrape meeting cards
    2. Filter to future dates only
    3. Use httpx to fetch detail pages for each future meeting
    4. Parse detail pages for full meeting info
    """
    meetings = []
    now = datetime.now(MICHIGAN_TZ).date()

    # Step 1: Scrape listing pages with Playwright
    all_cards = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        print(f"Fetching Wayne County meetings from {WAYNE_COUNTY_URL}")
        try:
            await page.goto(WAYNE_COUNTY_URL, wait_until="networkidle", timeout=30000)
        except Exception as e:
            print(f"  Failed to load page: {e}")
            await browser.close()
            return meetings

        await page.wait_for_timeout(3000)

        for page_num in range(1, MAX_PAGES + 1):
            print(f"  Scraping listing page {page_num}...")
            cards = await scrape_listing_page(page)
            print(f"    Found {len(cards)} meeting cards")
            all_cards.extend(cards)

            # If we got fewer than 10 cards, probably the last page
            if len(cards) < 10:
                break

            # Check if any cards on this page are already past — since sorted
            # newest-first, once we see past meetings we can stop
            has_past = False
            for card in cards:
                card_date = parse_meeting_date(card.get('date_text'))
                if card_date and card_date < now:
                    has_past = True
                    break

            if has_past and page_num > 1:
                print("    Found past meetings, stopping pagination")
                break

            if page_num < MAX_PAGES:
                if not await click_next_page(page):
                    print("    No next page available")
                    break

        await browser.close()

    # Step 2: Filter to future meetings only
    future_cards = []
    for card in all_cards:
        card_date = parse_meeting_date(card.get('date_text'))
        if card_date and card_date >= now:
            card['parsed_date'] = card_date
            future_cards.append(card)

    print(f"\n  {len(future_cards)} future meetings out of {len(all_cards)} total")

    if not future_cards:
        return meetings

    # Step 3: Fetch detail pages with httpx
    async with httpx.AsyncClient() as client:
        for card in future_cards:
            detail_url = card.get('detail_url')
            if not detail_url:
                print(f"  No detail URL for {card.get('date_text')} {card.get('type_text')}")
                continue

            print(f"  Fetching detail: {card.get('type_text', 'Unknown')} - {card.get('date_text')}")
            html = await fetch_detail_page(client, detail_url)
            if not html:
                continue

            # Step 4: Parse detail page
            detail = parse_detail_page(html, detail_url)
            if not detail:
                continue

            # Build meeting record
            meeting_date = card['parsed_date']
            time_parts = parse_meeting_time(detail.get('time_text', ''))

            if time_parts:
                hour, minute = time_parts
                start_dt = datetime(
                    meeting_date.year, meeting_date.month, meeting_date.day,
                    hour, minute, tzinfo=MICHIGAN_TZ
                )
                meeting_time = f"{hour:02d}:{minute:02d}"
            else:
                start_dt = datetime(
                    meeting_date.year, meeting_date.month, meeting_date.day,
                    10, 0, tzinfo=MICHIGAN_TZ
                )
                meeting_time = "10:00"

            title = detail.get('title', card.get('type_text', 'Wayne County Meeting'))
            type_text = detail.get('type_text', card.get('type_text', ''))
            date_str = meeting_date.isoformat()

            meeting = {
                "title": title,
                "agency": "Wayne County Commission",
                "meeting_date": date_str,
                "meeting_time": meeting_time,
                "start_datetime": start_dt.isoformat(),
                "location": detail.get('location'),
                "meeting_type": determine_meeting_type(type_text),
                "source": "wayne_county_scraper",
                "source_id": generate_source_id(title, date_str),
                "details_url": detail_url,
                "agenda_url": detail.get('agenda_url'),
                "minutes_url": detail.get('minutes_url'),
                "virtual_url": detail.get('virtual_url'),
                "virtual_meeting_id": detail.get('virtual_meeting_id'),
                "virtual_phone": detail.get('virtual_phone'),
                "region": "Wayne County",
                "issue_tags": get_issue_tags(type_text),
            }

            meetings.append(meeting)
            print(f"    -> {title} on {date_str} at {meeting_time}")

    return meetings


def upsert_meetings(meetings):
    """Insert or update meetings in Supabase."""
    if not meetings:
        print("No meetings to upsert")
        return

    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

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
    print("Wayne County Meeting Scraper")
    print("=" * 60)

    meetings = await scrape_wayne_county_meetings()
    print(f"\nFound {len(meetings)} upcoming Wayne County meetings")

    if meetings:
        print("\nUpserting to database...")
        upsert_meetings(meetings)

    print("\nDone!")
    print_result("wayne_county", "ok", len(meetings), "meetings")
    return meetings


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print_result("wayne_county", "error", error=str(e))
        raise
