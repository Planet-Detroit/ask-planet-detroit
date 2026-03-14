"""
Pontiac Meeting Scraper
Scrapes City of Pontiac public meetings from their Revize CMS calendar JSON
endpoint and agendas/minutes pages.

Strategy:
1. Fetch calendar JSON endpoint for structured event data (titles, dates, times,
   locations, recurrence rules)
2. Expand recurring events using iCal RRULE patterns
3. Fetch agendas/minutes pages to get PDF links
4. Cross-reference calendar events with agenda PDFs by date

No API key needed. No Playwright needed — all data is server-rendered or JSON.

Source: https://pontiac.mi.us/calendar.php
Calendar JSON: https://pontiac.mi.us/_assets_/plugins/revizeCalendar/calendar_data_handler.php
"""

import os
import re
from datetime import datetime, timedelta
from urllib.parse import unquote, urljoin
from zoneinfo import ZoneInfo

import httpx
from bs4 import BeautifulSoup
from dotenv import load_dotenv

from scraper_utils import print_result

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
MICHIGAN_TZ = ZoneInfo("America/Detroit")

BASE_URL = "https://pontiac.mi.us"
CALENDAR_JSON_URL = "https://pontiac.mi.us/_assets_/plugins/revizeCalendar/calendar_data_handler.php"
CALENDAR_PARAMS = {
    "webspace": "pontiacminew",
    "relative_revize_url": "//cms3.revize.com/revize/",
    "protocol": "https:",
}

# Government calendar display ID (filters out recreation, events, etc.)
GOVERNMENT_CALENDAR_ID = "6"

# How far ahead to look for meetings (days)
LOOKAHEAD_DAYS = 90

# Agendas/minutes pages to scrape for PDF links
AGENDA_PAGES = {
    "city_council": {
        "url": "https://pontiac.mi.us/government/city_council/agendas___minutes.php",
        "body": "City Council",
    },
    "planning": {
        "url": "https://pontiac.mi.us/government/boards___commissions/planning_commission/agendas___minutes.php",
        "body": "Planning Commission",
    },
    "zba": {
        "url": "https://pontiac.mi.us/government/boards___commissions/zoning_board_of_appeals/agendas___minutes.php",
        "body": "Zoning Board of Appeals",
    },
}

# Bodies with environmental/infrastructure relevance
ENV_BODIES = {
    "planning": ["planning", "zoning"],
    "zoning": ["zoning", "planning"],
    "historic district": ["historic_preservation"],
    "charter revision": ["government_reform"],
    "tifa": ["economic_development", "infrastructure"],
    "brownfield": ["environment", "infrastructure"],
    "parks": ["parks", "environment"],
}

DEFAULT_TAGS = ["government", "pontiac"]


def determine_meeting_type(title):
    """Determine meeting type from title."""
    lower = title.lower()
    if "special" in lower:
        return "special_meeting"
    if "hearing" in lower:
        return "public_hearing"
    if "city council" in lower:
        return "board_meeting"
    if "commission" in lower or "committee" in lower or "board" in lower:
        return "committee_meeting"
    if "workshop" in lower or "work session" in lower:
        return "workshop"
    return "public_meeting"


def get_issue_tags(title):
    """Get issue tags based on meeting title."""
    lower = title.lower()
    for key, tags in ENV_BODIES.items():
        if key in lower:
            return tags
    return DEFAULT_TAGS


def expand_rrule(rrule_str, start_str):
    """Expand an iCal RRULE into a list of datetime occurrences.

    Handles FREQ=MONTHLY with BYDAY, UNTIL, and EXDATE.
    Returns list of datetime objects in Michigan time.
    """
    if not rrule_str:
        # Single event — just return the start datetime
        dt = datetime.fromisoformat(start_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=MICHIGAN_TZ)
        return [dt]

    lines = rrule_str.strip().split("\n")
    dtstart = None
    rule_line = None
    exdates = set()

    for line in lines:
        if line.startswith("DTSTART:"):
            dtstart = datetime.strptime(line.split(":")[1], "%Y%m%dT%H%M%S")
            dtstart = dtstart.replace(tzinfo=MICHIGAN_TZ)
        elif line.startswith("RRULE:"):
            rule_line = line.split(":", 1)[1]
        elif line.startswith("EXDATE:"):
            for ex in line.split(":")[1].split(","):
                ex_dt = datetime.strptime(ex.strip(), "%Y%m%dT%H%M%S")
                exdates.add(ex_dt.strftime("%Y%m%d"))

    if not dtstart or not rule_line:
        dt = datetime.fromisoformat(start_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=MICHIGAN_TZ)
        return [dt]

    # Parse RRULE parameters
    params = {}
    for part in rule_line.split(";"):
        k, v = part.split("=", 1)
        params[k] = v

    freq = params.get("FREQ", "")
    until_str = params.get("UNTIL", "")
    byday = params.get("BYDAY", "")
    interval = int(params.get("INTERVAL", "1"))

    if until_str:
        until = datetime.strptime(until_str, "%Y%m%dT%H%M%S")
        until = until.replace(tzinfo=MICHIGAN_TZ)
    else:
        until = dtstart + timedelta(days=365)

    # Day-of-week mapping
    DOW_MAP = {"MO": 0, "TU": 1, "WE": 2, "TH": 3, "FR": 4, "SA": 5, "SU": 6}

    dates = []

    if freq == "MONTHLY" and byday:
        # Parse BYDAY like "1WE" (1st Wednesday) or "3MO" (3rd Monday)
        match = re.match(r"(-?\d)?(\w{2})", byday)
        if not match:
            return [dtstart]

        nth = int(match.group(1)) if match.group(1) else 1
        dow = DOW_MAP.get(match.group(2), 0)
        time_part = dtstart.time()

        current = dtstart.replace(day=1)
        while current <= until:
            # Find the nth occurrence of the target day in this month
            first_day = current.replace(day=1)
            # Find first occurrence of target day
            days_ahead = (dow - first_day.weekday()) % 7
            first_occurrence = first_day + timedelta(days=days_ahead)

            if nth > 0:
                target = first_occurrence + timedelta(weeks=nth - 1)
            else:
                # Negative: count from end of month
                import calendar
                last_day = calendar.monthrange(current.year, current.month)[1]
                last = current.replace(day=last_day)
                days_back = (last.weekday() - dow) % 7
                target = last - timedelta(days=days_back) + timedelta(weeks=nth + 1)

            if target.month == current.month:
                target = target.replace(
                    hour=time_part.hour,
                    minute=time_part.minute,
                    second=time_part.second,
                    tzinfo=MICHIGAN_TZ,
                )
                # Check EXDATE
                if target.strftime("%Y%m%d") not in exdates:
                    dates.append(target)

            # Move to next month (handle year rollover)
            next_month = current.month + interval
            next_year = current.year + (next_month - 1) // 12
            next_month = ((next_month - 1) % 12) + 1
            current = current.replace(year=next_year, month=next_month)

    elif freq == "WEEKLY":
        byday_list = byday.split(",") if byday else []
        target_days = [DOW_MAP.get(d.strip(), dtstart.weekday()) for d in byday_list] if byday_list else [dtstart.weekday()]
        time_part = dtstart.time()

        current = dtstart
        while current <= until:
            for target_dow in target_days:
                days_ahead = (target_dow - current.weekday()) % 7
                target = current + timedelta(days=days_ahead)
                if target <= until and target >= dtstart:
                    target = target.replace(
                        hour=time_part.hour,
                        minute=time_part.minute,
                        second=time_part.second,
                        tzinfo=MICHIGAN_TZ,
                    )
                    if target.strftime("%Y%m%d") not in exdates:
                        dates.append(target)
            current += timedelta(weeks=interval)

    else:
        dates = [dtstart]

    return sorted(set(dates))


def parse_calendar_events(events, now):
    """Parse calendar JSON events into meeting records.

    Filters to government events, expands recurrences, and returns
    list of meeting dicts.
    """
    meetings = []
    cutoff = now + timedelta(days=LOOKAHEAD_DAYS)
    seen_ids = set()

    for event in events:
        # Filter to government calendar only
        displays = event.get("calendar_displays", [])
        if GOVERNMENT_CALENDAR_ID not in displays:
            continue

        title = event.get("title", "").strip()
        if not title:
            continue

        location = event.get("location", "")
        rrule = event.get("rrule", "")
        start_str = event.get("start", "")
        event_id = event.get("rid", event.get("id", ""))
        desc = unquote(event.get("desc", ""))

        # Expand recurring events
        occurrence_dates = expand_rrule(rrule, start_str)

        for dt in occurrence_dates:
            # Filter to future events within lookahead window
            if dt < now - timedelta(days=1) or dt > cutoff:
                continue

            source_id = f"pontiac-{event_id}-{dt.strftime('%Y%m%d')}"
            if source_id in seen_ids:
                continue
            seen_ids.add(source_id)

            meeting = {
                "title": title,
                "agency": f"City of Pontiac - {title}",
                "meeting_date": dt.strftime("%Y-%m-%d"),
                "meeting_time": dt.strftime("%H:%M"),
                "start_datetime": dt.isoformat(),
                "location": location if location else None,
                "meeting_type": determine_meeting_type(title),
                "source": "pontiac_scraper",
                "source_id": source_id,
                "details_url": event.get("url") or None,
                "agenda_url": None,
                "minutes_url": None,
                "region": "Oakland County",
                "issue_tags": get_issue_tags(title),
            }

            meetings.append(meeting)

    return meetings


def parse_agendas_page(html, page_url):
    """Parse a Revize agendas/minutes page for PDF links.

    Returns list of dicts: {date, meeting_type, agenda_url, minutes_url}
    """
    soup = BeautifulSoup(html, "html.parser")
    entries = []

    # Find all meeting tables (each has border-top style)
    tables = soup.find_all("table", style=lambda s: s and "border-top" in s)

    for table in tables:
        row = table.find("tr")
        if not row:
            continue

        cells = row.find_all("td")
        if not cells:
            continue

        # First cell has date and meeting type
        first_cell = cells[0].get_text(strip=True)
        date_match = re.search(r"(\d{2}/\d{2}/\d{2})", first_cell)
        if not date_match:
            continue

        try:
            dt = datetime.strptime(date_match.group(1), "%m/%d/%y")
            date_str = dt.strftime("%Y-%m-%d")
        except ValueError:
            continue

        # Extract meeting type from text after date
        meeting_type = first_cell[date_match.end():].strip()
        if not meeting_type:
            meeting_type = "Regular Meeting"

        # Find agenda and minutes links in remaining cells
        agenda_url = None
        minutes_url = None
        base_url = page_url.rsplit("/", 1)[0] + "/"

        for cell in cells[1:]:
            link = cell.find("a")
            if not link:
                continue
            href = link.get("href", "")
            link_text = link.get_text(strip=True).lower()

            # Strip cache-busting timestamp from URL
            clean_href = re.sub(r'\?t=\d+', '', href)
            full_url = urljoin(base_url, clean_href)

            if "agenda" in link_text:
                agenda_url = full_url
            elif "minutes" in link_text:
                minutes_url = full_url

        entries.append({
            "date": date_str,
            "meeting_type": meeting_type,
            "agenda_url": agenda_url,
            "minutes_url": minutes_url,
        })

    return entries


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
    """Main entry point — scrape Pontiac meetings."""
    print("=" * 60)
    print("City of Pontiac Meeting Scraper")
    print("=" * 60)

    now = datetime.now(MICHIGAN_TZ)

    async with httpx.AsyncClient(
        follow_redirects=True,
        headers={"User-Agent": "PlanetDetroit-CivicScraper/1.0"}
    ) as client:
        # Step 1: Fetch calendar JSON
        print("\nFetching calendar data...")
        resp = await client.get(CALENDAR_JSON_URL, params=CALENDAR_PARAMS, timeout=30)
        resp.raise_for_status()
        calendar_data = resp.json()
        print(f"  {len(calendar_data)} total calendar events")

        # Parse government events
        meetings = parse_calendar_events(calendar_data, now)
        print(f"  {len(meetings)} upcoming government meetings")

        # Step 2: Fetch agendas/minutes pages for PDF links
        print("\nFetching agendas/minutes pages...")
        agenda_lookup = {}  # date -> {agenda_url, minutes_url}

        for key, config in AGENDA_PAGES.items():
            try:
                print(f"  Fetching {config['body']}...")
                resp = await client.get(config["url"], timeout=30)
                resp.raise_for_status()
                entries = parse_agendas_page(resp.text, config["url"])
                print(f"    Found {len(entries)} entries")

                # Build lookup: body+date -> urls
                for entry in entries:
                    lookup_key = f"{config['body'].lower()}:{entry['date']}"
                    agenda_lookup[lookup_key] = {
                        "agenda_url": entry.get("agenda_url"),
                        "minutes_url": entry.get("minutes_url"),
                    }
            except Exception as e:
                print(f"    Error: {e}")

        # Step 3: Cross-reference meetings with agenda PDFs
        matched = 0
        for meeting in meetings:
            title_lower = meeting["title"].lower()
            date = meeting["meeting_date"]

            for body_key in AGENDA_PAGES:
                body_name = AGENDA_PAGES[body_key]["body"].lower()
                # Match if the meeting title contains the body name
                if body_name in title_lower or (body_key == "zba" and "zoning" in title_lower):
                    lookup_key = f"{body_name}:{date}"
                    if lookup_key in agenda_lookup:
                        urls = agenda_lookup[lookup_key]
                        if urls["agenda_url"]:
                            meeting["agenda_url"] = urls["agenda_url"]
                            matched += 1
                        if urls["minutes_url"]:
                            meeting["minutes_url"] = urls["minutes_url"]
                        break

        print(f"\n  Matched {matched} meetings with agenda PDFs")

    print(f"\nBuilt {len(meetings)} meeting records")
    env_count = sum(1 for m in meetings if m["issue_tags"] != DEFAULT_TAGS)
    print(f"  {env_count} environmentally relevant, {len(meetings) - env_count} general")

    if meetings:
        print("\nUpserting to database...")
        upsert_meetings(meetings)

    print("\nDone!")
    print_result("pontiac", "ok", len(meetings), "meetings")
    return meetings


if __name__ == "__main__":
    import asyncio
    try:
        asyncio.run(main())
    except Exception as e:
        print_result("pontiac", "error", error=str(e))
        raise
