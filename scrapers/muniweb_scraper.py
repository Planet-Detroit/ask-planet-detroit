"""
MuniWeb CMS Meeting Scraper (shared)
Scrapes meetings from MuniWeb/MuniCMS-powered city websites.

Used by: City of Novi, City of Farmington Hills (and future MuniWeb cities).

Strategy: Fetch the current year listing page for each board, parse dates and
agenda/minutes PDF links. Uses known default times and locations per board.

No API available. No Playwright needed — HTML is server-rendered.
"""

import os
import re
import sys
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

# Date patterns found in MuniWeb listing pages
DATE_PATTERNS = [
    re.compile(r"([A-Z][a-z]{2,8}\s+\d{1,2},?\s+\d{4})"),  # "Mar 9, 2026" or "March 9, 2026"
    re.compile(r"(\d{1,2}/\d{1,2}/\d{4})"),  # "3/19/2026" (Farmington Hills format)
]

# Bodies with environmental/infrastructure relevance (shared across all cities)
ENV_BODIES = {
    "planning": ["planning", "zoning"],
    "zoning": ["zoning", "planning"],
    "environmental": ["environment", "climate"],
    "beautification": ["environment", "beautification"],
    "parks": ["parks", "environment"],
    "public utilities": ["utilities", "infrastructure"],
    "mobility": ["infrastructure", "transportation"],
    "water": ["water", "environment"],
    "historic": ["historic", "planning"],
}

# ── Per-city configurations ─────────────────────────────────────────────

MUNIWEB_CONFIGS = {
    "novi": {
        "city_name": "City of Novi",
        "base_url": "https://www.cityofnovi.org",
        "url_path": "agendas-minutes",  # {base_url}/{url_path}/{slug}/{year}/
        "region": "Oakland County",
        "source": "novi_scraper",
        "default_tags": ["government", "novi"],
        "boards": {
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
        },
    },
    "farmington_hills": {
        "city_name": "City of Farmington Hills",
        "base_url": "https://www.fhgov.com",
        "url_path": "government-business/agendasminutesvideos",
        "region": "Oakland County",
        "source": "farmington_hills_scraper",
        "default_tags": ["government", "farmington-hills"],
        "boards": {
            "city_council": {
                "name": "City Council",
                "slug": "city-council",
                "time": "19:30",
                "location": "City Hall Council Chambers, 31555 W Eleven Mile Road",
            },
            "planning_commission": {
                "name": "Planning Commission",
                "slug": "planning-commission",
                "time": "19:30",
                "location": "City Hall Council Chambers, 31555 W Eleven Mile Road",
            },
            "zba": {
                "name": "Zoning Board of Appeals",
                "slug": "zoning-board-of-appeals",
                "time": "19:30",
                "location": "City Hall Council Chambers, 31555 W Eleven Mile Road",
            },
        },
    },
}


def determine_meeting_type(title):
    """Determine meeting type from title."""
    lower = title.lower()
    if "council" in lower:
        return "board_meeting"
    if "hearing" in lower:
        return "public_hearing"
    return "committee_meeting"


def get_issue_tags(title, default_tags):
    """Get issue tags based on meeting title."""
    lower = title.lower()
    for key, tags in ENV_BODIES.items():
        if key in lower:
            return tags
    return default_tags


def parse_listing_page(html, base_url):
    """Parse a MuniWeb agendas/minutes listing page.

    MuniWeb uses different HTML layouts per board:
      - Some boards: Bootstrap cards (div.card > div.card-header + div.card-body)
      - Other boards: div > strong (date) + p (links)
      - Other boards: p (date) + p (links)

    The generic fallback handles all non-card formats by scanning for
    date text in any element and collecting links from ancestors/siblings.

    Returns list of dicts: {date, agenda_url, minutes_url}
    """
    soup = BeautifulSoup(html, "html.parser")
    entries = []

    # Format 1: Bootstrap cards
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
                        agenda_url = urljoin(base_url, href)
                    elif "minutes" in link_text and not minutes_url:
                        minutes_url = urljoin(base_url, href)

            entries.append({
                "date": date,
                "agenda_url": agenda_url,
                "minutes_url": minutes_url,
            })
        return entries

    # Format 2: Generic — scan for date text, collect links from ancestors/siblings
    entries = _parse_generic_format(soup, base_url)
    return entries


def _parse_generic_format(soup, base_url):
    """Parse dates and links from any flat HTML layout.

    Scans all strong, p, and div elements for date text. When a date is found,
    walks up ancestors to find the nearest container with agenda/minutes links.
    Falls back to checking sibling elements.
    """
    entries = []
    content = soup.find("div", class_="content-area") or soup

    # Find leaf-level date elements (deepest elements containing date text)
    date_elements = []
    for el in content.find_all(["strong", "p", "div", "h3", "h4"]):
        text = el.get_text(strip=True)
        if not text:
            continue

        date = _parse_date_text(text)
        if date:
            # Only keep leaf-level dates (no child elements also containing dates)
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
        # agenda/minutes links. MuniWeb nests the date div 2-3 levels deep
        # inside the meeting container that holds the links.
        ancestor = el.parent
        for _ in range(4):
            if not ancestor or ancestor == content or ancestor == soup:
                break
            ancestor_links = ancestor.find_all("a", recursive=True)
            if 1 <= len(ancestor_links) <= 5:
                for link in ancestor_links:
                    href = link.get("href", "")
                    link_text = link.get_text(strip=True).lower()
                    if "agenda" in link_text and not agenda_url:
                        agenda_url = urljoin(base_url, href)
                    elif "minutes" in link_text and not minutes_url:
                        minutes_url = urljoin(base_url, href)
                if agenda_url:
                    break
            ancestor = ancestor.parent

        # Strategy 2: Check sibling elements after this date element
        if not agenda_url:
            for sibling in el.next_siblings:
                if not hasattr(sibling, 'name') or not sibling.name:
                    continue
                sib_text = sibling.get_text(strip=True)
                if _parse_date_text(sib_text):
                    break
                for link in sibling.find_all("a"):
                    href = link.get("href", "")
                    link_text = link.get_text(strip=True).lower()
                    if "agenda" in link_text and not agenda_url:
                        agenda_url = urljoin(base_url, href)
                    elif "minutes" in link_text and not minutes_url:
                        minutes_url = urljoin(base_url, href)

        entries.append({
            "date": date,
            "agenda_url": agenda_url,
            "minutes_url": minutes_url,
        })

    return entries


def _parse_date_text(text):
    """Parse a date string like 'Mar 9, 2026', 'March 11, 2026', or '3/19/2026'.

    Returns YYYY-MM-DD string or None.
    """
    for pattern in DATE_PATTERNS:
        match = pattern.search(text)
        if match:
            date_str = match.group(1)
            for fmt in ["%b %d, %Y", "%B %d, %Y", "%b %d %Y", "%B %d %Y", "%m/%d/%Y"]:
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


async def scrape_city(config_key):
    """Scrape meetings for a single MuniWeb city."""
    config = MUNIWEB_CONFIGS[config_key]
    city_name = config["city_name"]
    base_url = config["base_url"]
    url_path = config["url_path"]
    default_tags = config["default_tags"]

    print("=" * 60)
    print(f"{city_name} Meeting Scraper (MuniWeb)")
    print("=" * 60)

    now = datetime.now(MICHIGAN_TZ)
    current_year = now.year
    meetings = []

    async with httpx.AsyncClient(
        follow_redirects=True,
        headers={"User-Agent": "PlanetDetroit-CivicScraper/1.0"}
    ) as client:
        for board_key, board in config["boards"].items():
            slug = board["slug"]
            name = board["name"]
            url = f"{base_url}/{url_path}/{slug}/{current_year}/"

            print(f"\n  Fetching {name}...")
            try:
                resp = await client.get(url, timeout=30)
                if resp.status_code != 200:
                    print(f"    HTTP {resp.status_code}, skipping")
                    continue

                entries = parse_listing_page(resp.text, base_url)
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

                    source_id = f"{config_key}-{board_key}-{meeting_date}"

                    time_str = board.get("time", "19:00")
                    hour, minute = map(int, time_str.split(":"))
                    start_dt = dt.replace(hour=hour, minute=minute)

                    meeting = {
                        "title": name,
                        "agency": f"{city_name} - {name}",
                        "meeting_date": meeting_date,
                        "meeting_time": time_str,
                        "start_datetime": start_dt.isoformat(),
                        "location": board.get("location"),
                        "meeting_type": determine_meeting_type(name),
                        "source": config["source"],
                        "source_id": source_id,
                        "details_url": entry.get("agenda_url"),
                        "agenda_url": entry.get("agenda_url"),
                        "minutes_url": entry.get("minutes_url"),
                        "region": config["region"],
                        "issue_tags": get_issue_tags(name, default_tags),
                    }
                    meetings.append(meeting)
                    print(f"    {name} ({meeting_date})")

            except Exception as e:
                print(f"    Error: {e}")

    print(f"\nBuilt {len(meetings)} meeting records")
    env_count = sum(1 for m in meetings if m["issue_tags"] != default_tags)
    print(f"  {env_count} environmentally relevant, {len(meetings) - env_count} general")

    if meetings:
        print("\nUpserting to database...")
        upsert_meetings(meetings)

    print("\nDone!")
    print_result(config_key, "ok", len(meetings), "meetings")
    return meetings


async def main(config_key=None):
    """Main entry point. Pass config_key to scrape a single city."""
    if config_key:
        return await scrape_city(config_key)

    # Scrape all configured cities
    all_meetings = []
    for key in MUNIWEB_CONFIGS:
        meetings = await scrape_city(key)
        all_meetings.extend(meetings)
    return all_meetings


if __name__ == "__main__":
    import asyncio
    # Accept config_key as CLI argument
    config_key = sys.argv[1] if len(sys.argv) > 1 else None
    try:
        asyncio.run(main(config_key))
    except Exception as e:
        label = config_key or "muniweb"
        print_result(label, "error", error=str(e))
        raise
