"""
Troy Meeting Scraper
Scrapes City of Troy public meetings from their Revize CMS apps.

Strategy:
1. Council schedule page (/CouncilSchedule) — <ul>/<li> list of dates/times
2. Meeting archive (/meetings/MeetingArchive?year=YYYY) — <table> with agenda/minutes PDFs
3. Board meeting schedules (/BoardsAndCommittees/MeetingSchedule?boardAndCommitteeName=X) — <ul>/<li>

No Playwright needed — all content is server-rendered HTML.

Source: https://apps.troymi.gov
"""

import os
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import httpx
from bs4 import BeautifulSoup
from dotenv import load_dotenv

from scraper_utils import print_result

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
MICHIGAN_TZ = ZoneInfo("America/Detroit")

APPS_BASE = "https://apps.troymi.gov"
CITY_HALL = "City Hall, 500 West Big Beaver Road, Troy, MI"

# Boards to scrape meeting schedules for
BOARD_CONFIGS = {
    "Planning Commission": {
        "tags": ["planning", "zoning"],
        "type": "committee_meeting",
    },
    "Zoning Board of Appeals": {
        "tags": ["planning", "zoning"],
        "type": "committee_meeting",
    },
    "Historic District Commission": {
        "tags": ["historic_preservation"],
        "type": "committee_meeting",
    },
    "Brownfield Redevelopment Authority": {
        "tags": ["environment", "contamination"],
        "type": "committee_meeting",
    },
    "Parks and Recreation Board": {
        "tags": ["parks", "environment"],
        "type": "committee_meeting",
    },
    "Downtown Development Authority": {
        "tags": ["planning", "economic_development"],
        "type": "committee_meeting",
    },
}

DEFAULT_TAGS = ["government", "troy"]


def parse_council_schedule_item(text):
    """Parse a council schedule <li> text into date, time, and optional label.

    Formats:
        "January 12, 2026 7:30 PM"
        "January 17, 2026 9:00 AM  :  - SPECIAL - 2026 ADVANCE"

    Returns (datetime, label) or (None, None) if unparseable.
    """
    text = text.strip()

    # Split on "  :  " to separate date/time from label
    parts = re.split(r'\s*:\s*-\s*', text, maxsplit=1)
    date_part = parts[0].strip()
    label = parts[1].strip() if len(parts) > 1 else None

    # Parse date + time
    match = re.match(
        r'(\w+ \d{1,2}, \d{4})\s+(\d{1,2}:\d{2}\s*[AP]M)',
        date_part,
        re.IGNORECASE
    )
    if not match:
        return None, None

    try:
        dt = datetime.strptime(f"{match.group(1)} {match.group(2).strip()}", "%B %d, %Y %I:%M %p")
        dt = dt.replace(tzinfo=MICHIGAN_TZ)
        return dt, label
    except ValueError:
        return None, None


def parse_board_schedule_item(text):
    """Parse a board schedule <li> text into date, time, and cancelled flag.

    Formats:
        "Tuesday, January 13, 2026 7:00 PM - 8:00 PM"
        "Tuesday, March 10, 2026 7:00 PM - 8:00 PM  : CANCELLED"

    Returns (datetime, is_cancelled) or (None, False) if unparseable.
    """
    text = text.strip()

    is_cancelled = ": CANCELLED" in text.upper() or ":CANCELLED" in text.upper()

    # Extract date and start time (ignore end time and day-of-week)
    match = re.search(
        r'(\w+ \d{1,2}, \d{4})\s+(\d{1,2}:\d{2}\s*[AP]M)',
        text,
        re.IGNORECASE
    )
    if not match:
        return None, False

    try:
        dt = datetime.strptime(f"{match.group(1)} {match.group(2).strip()}", "%B %d, %Y %I:%M %p")
        dt = dt.replace(tzinfo=MICHIGAN_TZ)
        return dt, is_cancelled
    except ValueError:
        return None, False


def generate_source_id(body_name, date_str):
    """Generate a stable source_id from body name and date."""
    slug = re.sub(r'[^a-z0-9]+', '-', body_name.lower()).strip('-')
    return f"troy-{slug}-{date_str}"


def determine_council_meeting_type(label):
    """Determine if a council meeting is regular or special."""
    if label and "special" in label.lower():
        return "special_meeting"
    return "board_meeting"


def parse_council_schedule(html):
    """Parse the council schedule page into a list of meeting dicts."""
    soup = BeautifulSoup(html, "html.parser")
    main = soup.find("main", id="freeform-main")
    if not main:
        return []

    # The schedule is the first <ul> in main
    ul = main.find("ul")
    if not ul:
        return []

    now = datetime.now(MICHIGAN_TZ)
    meetings = []

    for li in ul.find_all("li"):
        text = li.get_text(strip=True)
        dt, label = parse_council_schedule_item(text)
        if not dt:
            continue

        # Only include upcoming meetings
        if dt < now - timedelta(days=1):
            continue

        title = "City Council"
        if label and "special" in label.lower():
            title = f"City Council Special - {label.replace('SPECIAL -', '').replace('SPECIAL-', '').strip()}"

        meeting = {
            "title": title,
            "agency": "City of Troy - City Council",
            "meeting_date": dt.strftime("%Y-%m-%d"),
            "meeting_time": dt.strftime("%H:%M"),
            "start_datetime": dt.isoformat(),
            "location": CITY_HALL,
            "meeting_type": determine_council_meeting_type(label),
            "source": "troy_scraper",
            "source_id": generate_source_id("city-council", dt.strftime("%Y%m%d")),
            "details_url": f"{APPS_BASE}/CouncilSchedule",
            "agenda_url": None,
            "minutes_url": None,
            "region": "Oakland County",
            "issue_tags": DEFAULT_TAGS,
        }
        meetings.append(meeting)

    return meetings


def parse_archive_table(html):
    """Parse the meeting archive table to extract agenda/minutes PDF URLs.

    Returns a dict keyed by date string (YYYY-MM-DD) with agenda_url and minutes_url.
    """
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", class_="table")
    if not table:
        return {}

    docs = {}
    for row in table.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) < 4:
            continue

        # Cell 0: date + type
        date_text = cells[0].get_text(separator=" ", strip=True)
        date_match = re.search(r'(\w{3}\s+\d{1,2},\s+\d{4})', date_text)
        if not date_match:
            continue

        try:
            dt = datetime.strptime(date_match.group(1), "%b %d, %Y")
            date_key = dt.strftime("%Y-%m-%d")
        except ValueError:
            continue

        entry = {"agenda_url": None, "minutes_url": None, "video_url": None}

        # Cell 1: Agenda link (first <a> that's not javascript)
        for link in cells[1].find_all("a", href=True):
            href = link["href"]
            if "DownloadPDF" in href and "javascript" not in href:
                entry["agenda_url"] = f"{APPS_BASE}{href}"
                break

        # Cell 2: Video (YouTube link)
        for link in cells[2].find_all("a", href=True):
            href = link["href"]
            if "youtube" in href:
                entry["video_url"] = href
                break

        # Cell 3: Minutes link
        for link in cells[3].find_all("a", href=True):
            href = link["href"]
            if "DownloadPDF" in href:
                entry["minutes_url"] = f"{APPS_BASE}{href}"
                break

        docs[date_key] = entry

    return docs


def parse_board_schedule(html, board_name, board_config):
    """Parse a board meeting schedule page into a list of meeting dicts."""
    soup = BeautifulSoup(html, "html.parser")
    main = soup.find("main", id="freeform-main")
    if not main:
        return []

    ul = main.find("ul")
    if not ul:
        return []

    now = datetime.now(MICHIGAN_TZ)
    meetings = []

    for li in ul.find_all("li"):
        text = li.get_text(strip=True)
        dt, is_cancelled = parse_board_schedule_item(text)
        if not dt or is_cancelled:
            continue

        # Only include upcoming meetings
        if dt < now - timedelta(days=1):
            continue

        slug = re.sub(r'[^a-z0-9]+', '-', board_name.lower()).strip('-')
        schedule_url = f"{APPS_BASE}/BoardsAndCommittees/MeetingSchedule?boardAndCommitteeName={board_name.replace(' ', '%20')}"

        meeting = {
            "title": board_name,
            "agency": f"City of Troy - {board_name}",
            "meeting_date": dt.strftime("%Y-%m-%d"),
            "meeting_time": dt.strftime("%H:%M"),
            "start_datetime": dt.isoformat(),
            "location": CITY_HALL,
            "meeting_type": board_config["type"],
            "source": "troy_scraper",
            "source_id": generate_source_id(slug, dt.strftime("%Y%m%d")),
            "details_url": schedule_url,
            "agenda_url": None,
            "minutes_url": None,
            "region": "Oakland County",
            "issue_tags": board_config["tags"],
        }
        meetings.append(meeting)

    return meetings


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
    """Main entry point — scrape Troy meetings from schedule pages + archive."""
    print("=" * 60)
    print("City of Troy Meeting Scraper")
    print("=" * 60)

    all_meetings = []

    async with httpx.AsyncClient(
        follow_redirects=True,
        headers={"User-Agent": "PlanetDetroit-CivicScraper/1.0"}
    ) as client:
        # Step 1: Council schedule
        print("\nFetching City Council schedule...")
        try:
            resp = await client.get(f"{APPS_BASE}/CouncilSchedule", timeout=30)
            resp.raise_for_status()
            council_meetings = parse_council_schedule(resp.text)
            print(f"  Found {len(council_meetings)} upcoming council meetings")
        except Exception as e:
            print(f"  Error fetching council schedule: {e}")
            council_meetings = []

        # Step 2: Meeting archive for agenda/minutes PDFs
        year = datetime.now(MICHIGAN_TZ).year
        print(f"\nFetching {year} meeting archive for agenda/minutes PDFs...")
        try:
            resp = await client.get(
                f"{APPS_BASE}/meetings/MeetingArchive",
                params={"year": str(year)},
                timeout=30
            )
            resp.raise_for_status()
            archive_docs = parse_archive_table(resp.text)
            print(f"  Found documents for {len(archive_docs)} meetings")

            # Cross-reference council meetings with archive PDFs
            matched = 0
            for meeting in council_meetings:
                date_key = meeting["meeting_date"]
                if date_key in archive_docs:
                    docs = archive_docs[date_key]
                    meeting["agenda_url"] = docs.get("agenda_url")
                    meeting["minutes_url"] = docs.get("minutes_url")
                    matched += 1
            print(f"  Matched {matched} council meetings with archive documents")
        except Exception as e:
            print(f"  Error fetching archive: {e}")

        all_meetings.extend(council_meetings)

        # Step 3: Board meeting schedules
        print(f"\nFetching {len(BOARD_CONFIGS)} board meeting schedules...")
        for board_name, config in BOARD_CONFIGS.items():
            try:
                url = f"{APPS_BASE}/BoardsAndCommittees/MeetingSchedule"
                resp = await client.get(
                    url,
                    params={"boardAndCommitteeName": board_name},
                    timeout=20
                )
                resp.raise_for_status()
                board_meetings = parse_board_schedule(resp.text, board_name, config)
                print(f"  {board_name}: {len(board_meetings)} upcoming meetings")
                all_meetings.extend(board_meetings)
            except Exception as e:
                print(f"  Error fetching {board_name}: {e}")

    print(f"\nBuilt {len(all_meetings)} meeting records")
    env_count = sum(1 for m in all_meetings if m["issue_tags"] != DEFAULT_TAGS)
    print(f"  {env_count} environmentally relevant, {len(all_meetings) - env_count} general")

    if all_meetings:
        print("\nUpserting to database...")
        upsert_meetings(all_meetings)

    print("\nDone!")
    print_result("troy", "ok", len(all_meetings), "meetings")
    return all_meetings


if __name__ == "__main__":
    import asyncio
    try:
        asyncio.run(main())
    except Exception as e:
        print_result("troy", "error", error=str(e))
        raise
