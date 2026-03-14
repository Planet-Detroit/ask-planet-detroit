"""
CivicPlus AgendaCenter Meeting Scraper (shared)
Scrapes meeting agendas from CivicPlus AgendaCenter-powered city websites.

Used by: Sterling Heights, Westland, Waterford Township (and future CivicPlus cities).

Strategy: POST to /AgendaCenter/UpdateCategoryList with year + catID to get
agenda listing HTML. Parse dates and agenda/minutes PDF links.

Limitation: AgendaCenter is a document repository, not a meeting calendar.
No meeting times or locations are available — we use known defaults per board.

No Playwright needed — uses HTTP POST for AJAX endpoint.
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

# Date pattern: "Mar 9, 2026" or "March 9, 2026" (may be followed by " — Amended ...")
DATE_PATTERN = re.compile(r"([A-Z][a-z]{2,8}\s+\d{1,2},?\s+\d{4})")

# Bodies with environmental/infrastructure relevance
ENV_BODIES = {
    "planning": ["planning", "zoning"],
    "zoning": ["zoning", "planning"],
    "sustainability": ["environment", "climate"],
    "environmental": ["environment", "climate"],
    "beautification": ["environment", "beautification"],
    "parks": ["parks", "environment"],
    "solid waste": ["environment", "infrastructure"],
    "water": ["water", "environment"],
    "brownfield": ["environment", "infrastructure"],
}

# ── Per-city configurations ─────────────────────────────────────────────

CIVICPLUS_CONFIGS = {
    "sterling_heights": {
        "city_name": "City of Sterling Heights",
        "domain": "www.sterlingheights.gov",
        "region": "Macomb County",
        "source": "sterling_heights_scraper",
        "default_tags": ["government", "sterling-heights"],
        "boards": {
            "city_council": {
                "name": "City Council",
                "cat_id": 23,
                "slug": "City-Council",
                "time": "19:00",
                "location": "Council Chambers, 40555 Utica Road",
            },
            "planning_commission": {
                "name": "Planning Commission",
                "cat_id": 20,
                "slug": "Planning-Commission",
                "time": "19:00",
                "location": "Council Chambers, 40555 Utica Road",
            },
            "zba": {
                "name": "Zoning Board of Appeals",
                "cat_id": 22,
                "slug": "Zoning-Board-of-Appeals",
                "time": "19:00",
                "location": "Council Chambers, 40555 Utica Road",
            },
            "sustainability": {
                "name": "Sustainability Commission",
                "cat_id": 36,
                "slug": "Sustainability-Commission",
                "time": "19:00",
                "location": "City Hall, 40555 Utica Road",
            },
            "brownfield": {
                "name": "Brownfield Redevelopment Authority",
                "cat_id": 4,
                "slug": "Brownfield-Redevelopment-Authority",
                "time": "17:00",
                "location": "City Hall, 40555 Utica Road",
            },
            "historical": {
                "name": "Historical Commission",
                "cat_id": 12,
                "slug": "Historical-Commission",
                "time": "19:00",
                "location": "City Hall, 40555 Utica Road",
            },
            "library_board": {
                "name": "Library Board of Trustees",
                "cat_id": 14,
                "slug": "Library-Board-of-Trustees",
                "time": "18:30",
                "location": "Sterling Heights Public Library, 40255 Dodge Park Road",
            },
        },
    },
    "westland": {
        "city_name": "City of Westland",
        "domain": "www.cityofwestland.com",
        "region": "Wayne County",
        "source": "westland_scraper",
        "default_tags": ["government", "westland"],
        "boards": {
            "city_council": {
                "name": "City Council",
                "cat_id": 2,
                "slug": "City-Council",
                "time": "19:00",
                "location": "Council Chambers, 36300 Warren Road",
            },
            "planning_commission": {
                "name": "Planning Commission",
                "cat_id": 10,
                "slug": "Planning-Commission",
                "time": "19:30",
                "location": "Council Chambers, 36300 Warren Road",
            },
            "zba": {
                "name": "Zoning Board of Appeals",
                "cat_id": 4,
                "slug": "Zoning-Board-of-Appeals",
                "time": "19:00",
                "location": "Council Chambers, 36300 Warren Road",
            },
            "beautification": {
                "name": "Beautification Committee",
                "cat_id": 21,
                "slug": "Beautification-Committee",
                "time": "17:00",
                "location": "City Hall, 36300 Warren Road",
            },
            "parks_rec": {
                "name": "Parks and Recreation Advisory Council",
                "cat_id": 19,
                "slug": "Parks-and-Recreation-Advisory-Council",
                "time": "18:00",
                "location": "Bailey Recreation Center, 36651 Ford Road",
            },
        },
    },
    "waterford": {
        "city_name": "Waterford Township",
        "domain": "waterfordmi.gov",
        "region": "Oakland County",
        "source": "waterford_scraper",
        "default_tags": ["government", "waterford"],
        "boards": {
            "board_of_trustees": {
                "name": "Board of Trustees",
                "cat_id": 6,
                "slug": "Board-of-Trustees",
                "time": "18:00",
                "location": "Township Hall, 5200 Civic Center Drive",
            },
            "board_of_trustees_work": {
                "name": "Board of Trustees Work Session",
                "cat_id": 11,
                "slug": "Board-of-Trustees-Work-Session",
                "time": "17:00",
                "location": "Township Hall, 5200 Civic Center Drive",
            },
            "planning_commission": {
                "name": "Planning Commission",
                "cat_id": 7,
                "slug": "Planning-Commission",
                "time": "18:00",
                "location": "Township Hall, 5200 Civic Center Drive",
            },
            "zba": {
                "name": "Zoning Board of Appeals",
                "cat_id": 8,
                "slug": "Zoning-Board-of-Appeals",
                "time": "18:00",
                "location": "Township Hall, 5200 Civic Center Drive",
            },
            "parks_rec": {
                "name": "Parks & Recreation Board",
                "cat_id": 5,
                "slug": "Parks-Recreation-Board",
                "time": "18:00",
                "location": "Township Hall, 5200 Civic Center Drive",
            },
            "water_advisory": {
                "name": "Community Water Advisory Council",
                "cat_id": 17,
                "slug": "Community-Water-Advisory-Council",
                "time": "18:00",
                "location": "Township Hall, 5200 Civic Center Drive",
            },
            "greenways": {
                "name": "Community Greenways Advisory Committee",
                "cat_id": 21,
                "slug": "Community-Greenways-Advisory-Committee",
                "time": "18:00",
                "location": "Township Hall, 5200 Civic Center Drive",
            },
        },
    },
}


def build_rss_cid(board_name, cat_id):
    """Build the CID slug used in RSS feed URLs.

    Example: build_rss_cid("City Council", 23) -> "City-Council-23"
    """
    slug = board_name.replace(" ", "-")
    return f"{slug}-{cat_id}"


def determine_meeting_type(title):
    """Determine meeting type from title."""
    lower = title.lower()
    if "council" in lower or "trustees" in lower:
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


def parse_agenda_html(html, base_url):
    """Parse CivicPlus AgendaCenter listing HTML.

    Real CivicPlus format uses table rows:
      <tr class="catAgendaRow">
        <td>
          <h3><strong><abbr title="April">Apr</abbr> 28, 2026</strong></h3>
          <p><a href="/AgendaCenter/ViewFile/Agenda/...">Meeting Name</a></p>
        </td>
        <td class="minutes"><a href="/AgendaCenter/ViewFile/Minutes/...">...</a></td>
        <td class="downloads">...</td>
      </tr>

    Returns list of dicts: {date, agenda_url, minutes_url}
    """
    soup = BeautifulSoup(html, "html.parser")
    entries = []

    # Primary format: table rows with class catAgendaRow
    rows = soup.find_all("tr", class_="catAgendaRow")
    if rows:
        for row in rows:
            h3 = row.find("h3")
            if not h3:
                continue

            # Use separator=" " to preserve spaces lost by <abbr> tags
            # e.g. <abbr>Mar</abbr> 9, 2026 → "Mar 9, 2026" not "Mar9, 2026"
            text = h3.get_text(separator=" ", strip=True)
            match = DATE_PATTERN.search(text)
            if not match:
                continue

            if "CANCELED" in text.upper() or "CANCELLED" in text.upper():
                continue

            date = _parse_date(match.group(1))
            if not date:
                continue

            agenda_url = None
            minutes_url = None

            # Agenda: first <td> contains agenda link
            for link in row.find_all("a"):
                href = link.get("href", "")
                if not href:
                    continue
                if "/ViewFile/Agenda/" in href and not agenda_url:
                    clean_href = href.split("?")[0]
                    agenda_url = urljoin(base_url + "/", clean_href)
                elif "/ViewFile/Minutes/" in href and not minutes_url:
                    clean_href = href.split("?")[0]
                    minutes_url = urljoin(base_url + "/", clean_href)

            entries.append({
                "date": date,
                "agenda_url": agenda_url,
                "minutes_url": minutes_url,
            })
        return entries

    # Fallback: h3 elements with sibling links (simpler pages or test HTML)
    for h3 in soup.find_all("h3"):
        text = h3.get_text(strip=True)
        match = DATE_PATTERN.search(text)
        if not match:
            continue

        if "CANCELED" in text.upper() or "CANCELLED" in text.upper():
            continue

        date = _parse_date(match.group(1))
        if not date:
            continue

        agenda_url = None
        minutes_url = None

        # Walk parent container or siblings for links
        container = h3.find_parent("div", class_="catAgendaRow") or h3.parent
        if container and container != soup:
            links = container.find_all("a")
        else:
            links = []
            for sibling in h3.next_siblings:
                if hasattr(sibling, 'name'):
                    if sibling.name == "h3":
                        break
                    if sibling.name == "a":
                        links.append(sibling)
                    elif sibling.name:
                        links.extend(sibling.find_all("a"))

        for link in links:
            href = link.get("href", "")
            if not href:
                continue
            if "/ViewFile/Agenda/" in href and not agenda_url:
                clean_href = href.split("?")[0]
                agenda_url = urljoin(base_url + "/", clean_href)
            elif "/ViewFile/Minutes/" in href and not minutes_url:
                clean_href = href.split("?")[0]
                minutes_url = urljoin(base_url + "/", clean_href)

        entries.append({
            "date": date,
            "agenda_url": agenda_url,
            "minutes_url": minutes_url,
        })

    return entries


def _parse_date(date_str):
    """Parse a date string like 'Mar 9, 2026' or 'March 9, 2026'.

    Returns YYYY-MM-DD string or None.
    """
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


async def scrape_city(config_key):
    """Scrape meetings for a single CivicPlus AgendaCenter city."""
    config = CIVICPLUS_CONFIGS[config_key]
    city_name = config["city_name"]
    domain = config["domain"]
    base_url = f"https://{domain}"
    default_tags = config["default_tags"]
    ajax_url = f"{base_url}/AgendaCenter/UpdateCategoryList"

    print("=" * 60)
    print(f"{city_name} Meeting Scraper (CivicPlus AgendaCenter)")
    print("=" * 60)

    now = datetime.now(MICHIGAN_TZ)
    current_year = now.year
    meetings = []

    async with httpx.AsyncClient(
        follow_redirects=True,
        headers={"User-Agent": "PlanetDetroit-CivicScraper/1.0"},
    ) as client:
        for board_key, board in config["boards"].items():
            name = board["name"]
            cat_id = board["cat_id"]

            print(f"\n  Fetching {name} (catID={cat_id})...")
            try:
                resp = await client.post(
                    ajax_url,
                    data={"year": current_year, "catID": cat_id},
                    headers={"X-Requested-With": "XMLHttpRequest"},
                    timeout=30,
                )
                if resp.status_code != 200:
                    print(f"    HTTP {resp.status_code}, skipping")
                    continue

                entries = parse_agenda_html(resp.text, base_url)
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

                    agenda_url = entry.get("agenda_url")

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
                        "details_url": agenda_url,
                        "agenda_url": agenda_url,
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
    for key in CIVICPLUS_CONFIGS:
        meetings = await scrape_city(key)
        all_meetings.extend(meetings)
    return all_meetings


if __name__ == "__main__":
    import asyncio
    config_key = sys.argv[1] if len(sys.argv) > 1 else None
    try:
        asyncio.run(main(config_key))
    except Exception as e:
        label = config_key or "civicplus_agenda"
        print_result(label, "error", error=str(e))
        raise
