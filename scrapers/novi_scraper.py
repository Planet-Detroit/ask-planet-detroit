"""
Novi Meeting Scraper
Scrapes City of Novi public meetings from their MuniWeb CMS listing pages.

Strategy: Fetch the current year listing page for each board, parse dates and
agenda/minutes PDF links. Uses known default times and locations per board.

No API available. No Playwright needed — HTML is server-rendered.

Source: https://www.cityofnovi.org/agendas-minutes/
"""

import os
import re
from datetime import datetime, timedelta
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

import httpx
from bs4 import BeautifulSoup
from dotenv import load_dotenv

from scraper_utils import print_result

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
MICHIGAN_TZ = ZoneInfo("America/Detroit")

BASE_URL = "https://www.cityofnovi.org"

# Known default times and locations for each board
BOARD_CONFIGS = {
    "city_council": {
        "name": "City Council",
        "slug": "city-council",
        "time": "19:00",
        "location": "Council Chambers, Novi Civic Center, 45175 Ten Mile Road",
    },
    "planning_commission": {
        "name": "Planning Commission",
        "slug": "planning-commission",
        "time": "19:00",
        "location": "Council Chambers, Novi Civic Center, 45175 Ten Mile Road",
    },
    "zba": {
        "name": "Zoning Board of Appeals",
        "slug": "zoning-board-of-appeals",
        "time": "19:00",
        "location": "Council Chambers, Novi Civic Center, 45175 Ten Mile Road",
    },
    "environmental": {
        "name": "Environmental Sustainability Committee",
        "slug": "environmental-sustainability-committee",
        "time": "19:00",
        "location": "Novi Civic Center, 45175 Ten Mile Road",
    },
    "parks_rec": {
        "name": "Parks, Recreation and Cultural Services Commission",
        "slug": "parks-recreation-and-cultural-services-commission",
        "time": "19:00",
        "location": "Novi Civic Center, 45175 Ten Mile Road",
    },
    "beautification": {
        "name": "Beautification Commission",
        "slug": "beautification-commission",
        "time": "19:00",
        "location": "Novi Civic Center, 45175 Ten Mile Road",
    },
    "historical": {
        "name": "Historical Commission",
        "slug": "historical-commission",
        "time": "19:00",
        "location": "Novi Civic Center, 45175 Ten Mile Road",
    },
    "library_board": {
        "name": "Library Board",
        "slug": "library-board",
        "time": "19:00",
        "location": "Novi Public Library, 45255 W Ten Mile Road",
    },
    "public_utilities": {
        "name": "Public Utilities and Technology Committee",
        "slug": "public-utilities-and-technology-committee",
        "time": "19:00",
        "location": "Novi Civic Center, 45175 Ten Mile Road",
    },
}

# Bodies with environmental/infrastructure relevance
ENV_BODIES = {
    "planning": ["planning", "zoning"],
    "zoning": ["zoning", "planning"],
    "environmental": ["environment", "climate"],
    "beautification": ["environment", "beautification"],
    "parks": ["parks", "environment"],
    "public utilities": ["utilities", "infrastructure"],
    "mobility": ["infrastructure", "transportation"],
}

DEFAULT_TAGS = ["government", "novi"]

# Date patterns found in listing pages
DATE_PATTERNS = [
    re.compile(r"([A-Z][a-z]{2,8}\s+\d{1,2},?\s+\d{4})"),  # "Mar 9, 2026" or "March 9, 2026"
]


def determine_meeting_type(title):
    """Determine meeting type from title."""
    lower = title.lower()
    if "council" in lower:
        return "board_meeting"
    if "hearing" in lower:
        return "public_hearing"
    return "committee_meeting"


def get_issue_tags(title):
    """Get issue tags based on meeting title."""
    lower = title.lower()
    for key, tags in ENV_BODIES.items():
        if key in lower:
            return tags
    return DEFAULT_TAGS


def parse_listing_page(html, board_key):
    """Parse a Novi agendas/minutes listing page.

    Real Novi pages use Bootstrap cards:
      <div class="card">
        <div class="card-header">Mar 9, 2026</div>
        <div class="card-body">
          <a class="btn btn-green" href="...">Agenda</a>
          <a class="btn btn-green" href="...pdf">Minutes</a>
        </div>
      </div>

    Novi uses different HTML layouts per board:
      - City Council: Bootstrap cards (div.card > div.card-header + div.card-body)
      - Planning Commission: div > strong (date) + p (links)
      - ZBA and others: p (date) + p (links)

    The generic fallback handles all non-card formats by scanning for
    date text in any element and collecting links from siblings.

    Returns list of dicts: {date, agenda_url, minutes_url}
    """
    soup = BeautifulSoup(html, "html.parser")
    entries = []

    # Format 1: Bootstrap cards (City Council)
    cards = soup.find_all("div", class_="card")
    if cards:
        for card in cards:
            header = card.find("div", class_="card-header")
            if not header:
                continue

            text = header.get_text(strip=True)
            date = _parse_date_text(text)
            if not date:
                continue

            if "CANCELED" in text.upper() or "CANCELLED" in text.upper():
                continue

            agenda_url = None
            minutes_url = None
            body = card.find("div", class_="card-body")
            if body:
                for link in body.find_all("a"):
                    href = link.get("href", "")
                    link_text = link.get_text(strip=True).lower()
                    if "agenda" in link_text and not agenda_url:
                        agenda_url = urljoin(BASE_URL, href)
                    elif "minutes" in link_text and not minutes_url:
                        minutes_url = urljoin(BASE_URL, href)

            entries.append({
                "date": date,
                "agenda_url": agenda_url,
                "minutes_url": minutes_url,
            })
        return entries

    # Format 2: Generic — scan for date text in strong/p/div elements,
    # then collect links from siblings until the next date element.
    # Works for Planning Commission (strong), ZBA (p), and other boards.
    entries = _parse_generic_format(soup)
    return entries


def _parse_generic_format(soup):
    """Parse dates and links from any flat HTML layout.

    Scans all strong, p, and div elements for date text. When a date is found,
    collects agenda/minutes links from subsequent sibling elements until the
    next date element is encountered.

    Handles:
      - Planning Commission: <div><strong>Mar 11, 2026</strong><p><a>...</a></p></div>
      - ZBA: <p>Mar 10, 2026</p><p><a>...</a></p>
      - Any similar flat layout
    """
    entries = []
    content = soup.find("div", class_="content-area") or soup

    # Collect all candidate elements that might contain dates or links
    # Walk through direct children (and their children) looking for date text
    date_elements = []
    for el in content.find_all(["strong", "p", "div", "h3", "h4"]):
        # Skip if this element contains child elements that themselves have dates
        # (avoids double-counting parent divs)
        text = el.get_text(strip=True)
        if not text:
            continue

        date = _parse_date_text(text)
        if date:
            # Check it's a leaf-level date (not a wrapper containing date + links)
            child_dates = [
                c for c in el.find_all(["strong", "p", "div"], recursive=True)
                if c != el and _parse_date_text(c.get_text(strip=True))
            ]
            if not child_dates:
                date_elements.append((el, date, text))

    if not date_elements:
        return entries

    for i, (el, date, text) in enumerate(date_elements):
        if "CANCELED" in text.upper() or "CANCELLED" in text.upper():
            continue

        agenda_url = None
        minutes_url = None

        # Strategy 1: Walk up ancestors to find the nearest container with
        # agenda/minutes links. Real Novi structure nests the date div 2-3
        # levels deep inside the meeting container that holds the links.
        # Stop at containers with ≤5 links to avoid grabbing the whole page.
        ancestor = el.parent
        for _ in range(4):  # Check up to 4 ancestor levels
            if not ancestor or ancestor == content or ancestor == soup:
                break
            ancestor_links = ancestor.find_all("a", recursive=True)
            if 1 <= len(ancestor_links) <= 5:
                for link in ancestor_links:
                    href = link.get("href", "")
                    link_text = link.get_text(strip=True).lower()
                    if "agenda" in link_text and not agenda_url:
                        agenda_url = urljoin(BASE_URL, href)
                    elif "minutes" in link_text and not minutes_url:
                        minutes_url = urljoin(BASE_URL, href)
                if agenda_url:
                    break  # Found links, stop walking up
            ancestor = ancestor.parent

        # Strategy 2: Check sibling elements after this date element
        if not agenda_url:
            for sibling in el.next_siblings:
                if not hasattr(sibling, 'name') or not sibling.name:
                    continue
                # Stop at the next date element
                sib_text = sibling.get_text(strip=True)
                if _parse_date_text(sib_text):
                    break
                for link in sibling.find_all("a"):
                    href = link.get("href", "")
                    link_text = link.get_text(strip=True).lower()
                    if "agenda" in link_text and not agenda_url:
                        agenda_url = urljoin(BASE_URL, href)
                    elif "minutes" in link_text and not minutes_url:
                        minutes_url = urljoin(BASE_URL, href)

        entries.append({
            "date": date,
            "agenda_url": agenda_url,
            "minutes_url": minutes_url,
        })

    return entries


def _parse_date_text(text):
    """Parse a date string like 'Mar 9, 2026' or 'March 11, 2026'.

    Returns YYYY-MM-DD string or None.
    """
    for pattern in DATE_PATTERNS:
        match = pattern.search(text)
        if match:
            date_str = match.group(1)
            # Try multiple date formats
            for fmt in ["%b %d, %Y", "%B %d, %Y", "%b %d %Y", "%B %d %Y"]:
                try:
                    dt = datetime.strptime(date_str, fmt)
                    return dt.strftime("%Y-%m-%d")
                except ValueError:
                    continue
    return None


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
    """Main entry point — scrape Novi meetings from listing pages."""
    print("=" * 60)
    print("City of Novi Meeting Scraper")
    print("=" * 60)

    now = datetime.now(MICHIGAN_TZ)
    current_year = now.year
    meetings = []

    async with httpx.AsyncClient(
        follow_redirects=True,
        headers={"User-Agent": "PlanetDetroit-CivicScraper/1.0"}
    ) as client:
        for board_key, config in BOARD_CONFIGS.items():
            slug = config["slug"]
            name = config["name"]
            url = f"{BASE_URL}/agendas-minutes/{slug}/{current_year}/"

            print(f"\n  Fetching {name}...")
            try:
                resp = await client.get(url, timeout=30)
                if resp.status_code != 200:
                    print(f"    HTTP {resp.status_code}, skipping")
                    continue

                entries = parse_listing_page(resp.text, board_key)
                print(f"    Found {len(entries)} entries")

                for entry in entries:
                    meeting_date = entry["date"]

                    # Only include future meetings
                    try:
                        dt = datetime.strptime(meeting_date, "%Y-%m-%d")
                        dt = dt.replace(tzinfo=MICHIGAN_TZ)
                        if dt < now - timedelta(days=1):
                            continue
                    except ValueError:
                        continue

                    source_id = f"novi-{board_key}-{meeting_date}"

                    # Build start_datetime with known time
                    time_str = config.get("time", "19:00")
                    hour, minute = map(int, time_str.split(":"))
                    start_dt = dt.replace(hour=hour, minute=minute)

                    meeting = {
                        "title": name,
                        "agency": f"City of Novi - {name}",
                        "meeting_date": meeting_date,
                        "meeting_time": time_str,
                        "start_datetime": start_dt.isoformat(),
                        "location": config.get("location"),
                        "meeting_type": determine_meeting_type(name),
                        "source": "novi_scraper",
                        "source_id": source_id,
                        "details_url": entry.get("agenda_url"),
                        "agenda_url": entry.get("agenda_url"),
                        "minutes_url": entry.get("minutes_url"),
                        "region": "Oakland County",
                        "issue_tags": get_issue_tags(name),
                    }
                    meetings.append(meeting)
                    print(f"    {name} ({meeting_date})")

            except Exception as e:
                print(f"    Error: {e}")

    print(f"\nBuilt {len(meetings)} meeting records")
    env_count = sum(1 for m in meetings if m["issue_tags"] != DEFAULT_TAGS)
    print(f"  {env_count} environmentally relevant, {len(meetings) - env_count} general")

    if meetings:
        print("\nUpserting to database...")
        upsert_meetings(meetings)

    print("\nDone!")
    print_result("novi", "ok", len(meetings), "meetings")
    return meetings


if __name__ == "__main__":
    import asyncio
    try:
        asyncio.run(main())
    except Exception as e:
        print_result("novi", "error", error=str(e))
        raise
