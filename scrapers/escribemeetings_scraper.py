"""
eSCRIBE Meetings API Scraper (multi-source)
Fetches upcoming meetings from any municipality using the eSCRIBE calendar API.

API endpoint: POST /MeetingsCalendarView.aspx/GetCalendarMeetings
No authentication required. No browser needed (despite eSCRIBE being JS-heavy).

Supports: Royal Oak (and any future eSCRIBE municipality).
Note: Detroit uses a separate Playwright-based scraper due to its schedule-generation
fallback and DCC-specific logic. If more eSCRIBE cities are added, they use this scraper.
"""

import os
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import httpx
from dotenv import load_dotenv

from scraper_utils import print_result

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
MICHIGAN_TZ = ZoneInfo("America/Detroit")

LOOKAHEAD_DAYS = 90


# --- eSCRIBE configurations ---

ESCRIBEMEETINGS_CONFIGS = {
    "royal_oak": {
        "name": "City of Royal Oak",
        "base_url": "https://pub-royaloak.escribemeetings.com",
        "region": "Oakland County",
        "source": "royal_oak_scraper",
        "location_default": "Royal Oak City Hall, 203 S Troy St, Royal Oak, MI 48067",
        # Committee names with environmental relevance
        "env_committees": {
            "parks and recreation advisory board": ["parks", "environment"],
            "planning commission": ["planning", "zoning"],
            "environmental advisory committee": ["environment", "sustainability"],
        },
        "default_tags": ["government", "royal_oak"],
    },
}


def extract_virtual_url(text):
    """Extract Zoom or Teams URL from free text."""
    if not text:
        return None
    match = re.search(r'https?://[\w.-]*zoom\.us/\S+', text)
    if match:
        return match.group(0).rstrip('.,;)')
    match = re.search(r'https?://teams\.microsoft\.com/\S+', text)
    if match:
        return match.group(0).rstrip('.,;)')
    return None


def extract_meeting_id(text):
    """Extract Zoom meeting ID from URL or text."""
    if not text:
        return None
    match = re.search(r'zoom\.us/[jw]/(\d+)', text)
    if match:
        return match.group(1)
    return None


def extract_dial_in(text):
    """Extract phone dial-in number from text."""
    if not text:
        return None
    match = re.search(r'(\+?1?\s*[\(\-]?\d{3}[\)\-\s]+\d{3}[\-\s]+\d{4})', text)
    if match:
        return match.group(1).strip()
    return None


def get_issue_tags(meeting_name, config):
    """Determine issue tags based on meeting/committee name."""
    name_lower = meeting_name.lower()
    for pattern, tags in config["env_committees"].items():
        if pattern in name_lower:
            return tags
    return config["default_tags"]


def determine_meeting_type(meeting_name):
    """Determine meeting type from meeting name."""
    name = meeting_name.lower()
    if "public hearing" in name or "hearing" in name:
        return "public_hearing"
    if "work session" in name or "workshop" in name:
        return "workshop"
    if "special" in name:
        return "special_meeting"
    if "city commission" in name or "city council" in name:
        return "board_meeting"
    if "committee" in name or "commission" in name or "board" in name:
        return "committee_meeting"
    return "public_meeting"


def parse_location(description):
    """Parse address from eSCRIBE Description field (contains HTML line breaks)."""
    if not description:
        return None
    # Strip HTML tags and join parts
    text = re.sub(r'<br\s*/?>', ', ', description)
    text = re.sub(r'<[^>]+>', '', text)
    text = text.strip().strip(',')
    return text if text else None


def build_meeting(event, config):
    """Convert an eSCRIBE calendar event to our meetings table format."""
    meeting_id = event.get("ID", "")
    meeting_name = event.get("MeetingName", "").strip()
    base_url = config["base_url"]

    # Parse date — eSCRIBE returns "2026/03/18 16:00:00"
    start_str = event.get("StartDate", "")
    try:
        dt = datetime.strptime(start_str, "%Y/%m/%d %H:%M:%S")
        local_dt = dt.replace(tzinfo=MICHIGAN_TZ)
        meeting_date = local_dt.strftime("%Y-%m-%d")
        meeting_time = local_dt.strftime("%H:%M")
        start_datetime = local_dt.isoformat()
    except (ValueError, AttributeError):
        meeting_date = ""
        meeting_time = ""
        start_datetime = ""

    # Location from Description field (contains address with HTML breaks)
    location = parse_location(event.get("Description", ""))
    if not location:
        location = event.get("Location", "").strip() or config.get("location_default")

    # Virtual meeting info from description
    description = event.get("Description", "") or ""
    virtual_url = extract_virtual_url(description)
    zoom_id = extract_meeting_id(description)
    dial_in = extract_dial_in(description)

    # Agenda URL — find PDF agenda in MeetingDocumentLink list
    agenda_url = None
    docs = event.get("MeetingDocumentLink", [])
    for doc in docs:
        if doc.get("Type") == "Agenda" and doc.get("Format") == ".pdf":
            doc_url = doc.get("Url", "")
            if doc_url:
                agenda_url = f"{base_url}/{doc_url}" if not doc_url.startswith("http") else doc_url
            break

    # Detail/meeting page URL
    details_url = event.get("Url", "")
    if not details_url and meeting_id:
        details_url = f"{base_url}/Meeting.aspx?Id={meeting_id}&lang=English"

    meeting = {
        "title": meeting_name,
        "agency": config["name"],
        "meeting_date": meeting_date,
        "meeting_time": meeting_time,
        "start_datetime": start_datetime,
        "location": location,
        "meeting_type": determine_meeting_type(meeting_name),
        "source": config["source"],
        "source_id": f"escribemeetings-{meeting_id[:20]}",
        "details_url": details_url,
        "agenda_url": agenda_url,
        "virtual_url": virtual_url,
        "virtual_meeting_id": zoom_id,
        "virtual_phone": dial_in,
        "region": config["region"],
        "issue_tags": get_issue_tags(meeting_name, config),
    }

    return meeting


def fetch_upcoming_events(config):
    """Fetch upcoming events from an eSCRIBE calendar API."""
    base_url = config["base_url"]
    now = datetime.now(MICHIGAN_TZ)
    start_str = now.strftime("%Y-%m-%dT00:00:00-05:00")
    end_str = (now + timedelta(days=LOOKAHEAD_DAYS)).strftime("%Y-%m-%dT00:00:00-05:00")

    url = f"{base_url}/MeetingsCalendarView.aspx/GetCalendarMeetings"

    print(f"Fetching {config['name']} events from eSCRIBE API...")
    print(f"  Date range: {now.strftime('%Y-%m-%d')} to {(now + timedelta(days=LOOKAHEAD_DAYS)).strftime('%Y-%m-%d')}")

    resp = httpx.post(
        url,
        json={
            "calendarStartDate": start_str,
            "calendarEndDate": end_str,
        },
        headers={
            "Content-Type": "application/json",
            "X-Requested-With": "XMLHttpRequest",
        },
        timeout=30,
        verify=False,  # Some eSCRIBE instances have SSL cert issues
    )
    resp.raise_for_status()

    import json
    data = resp.json()
    inner = json.loads(data["d"]) if isinstance(data.get("d", ""), str) else data.get("d", [])

    # Filter out past meetings
    events = [e for e in inner if not e.get("MeetingPassed", False)]

    print(f"  Found {len(events)} upcoming events")
    return events


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


async def scrape_source(key):
    """Scrape meetings for a single eSCRIBE source. Returns list of meeting dicts."""
    config = ESCRIBEMEETINGS_CONFIGS[key]

    print("=" * 60)
    print(f"{config['name']} Meeting Scraper (eSCRIBE API)")
    print("=" * 60)

    events = fetch_upcoming_events(config)

    meetings = []
    for event in events:
        meeting = build_meeting(event, config)
        meetings.append(meeting)

        if meeting["agenda_url"]:
            print(f"  AGENDA: {meeting['title'][:40]} — {meeting['agenda_url'][:60]}")

    print(f"\nBuilt {len(meetings)} meeting records")

    if meetings:
        print("\nUpserting to database...")
        upsert_meetings(meetings)

    print("\nDone!")
    print_result(key, "ok", len(meetings), "meetings")
    return meetings


async def main(key):
    """Main entry point — called by run_scrapers.py with config_key from registry."""
    return await scrape_source(key)
