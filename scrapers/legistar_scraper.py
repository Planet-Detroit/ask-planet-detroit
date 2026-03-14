"""
Legistar API Meeting Scraper (multi-source)
Fetches upcoming public meetings from any municipality using the Legistar Web API.

Supports: Ann Arbor, DWSD (and any future Legistar source).
Configuration is passed in — each source defines its API client key,
region name, and environmentally relevant body IDs.

API: https://webapi.legistar.com/v1/{client}/Events
No authentication required. No browser needed.
"""

import os
import re
import hashlib
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import httpx
from dotenv import load_dotenv

from scraper_utils import print_result

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
MICHIGAN_TZ = ZoneInfo("America/Detroit")

# How far ahead to look for meetings (days)
LOOKAHEAD_DAYS = 90

API_BASE = "https://webapi.legistar.com/v1"


# --- Legistar configurations ---

LEGISTAR_CONFIGS = {
    "ann_arbor": {
        "name": "City of Ann Arbor",
        "client": "a2gov",
        "region": "Washtenaw County",
        "source": "ann_arbor_scraper",
        # Body IDs with environmental relevance
        "env_bodies": {
            220: ["environment", "energy"],                        # Energy Commission
            222: ["environment"],                                  # Environmental Commission
            223: ["environment", "great_lakes", "greenbelt"],      # Greenbelt Advisory Commission
            230: ["water_quality", "great_lakes"],                 # Huron River Watershed Council
            240: ["parks", "environment"],                         # Park Advisory Commission
            1377: ["water_quality", "drinking_water"],             # Water System Advisory Council
            1385: ["environment", "climate", "sustainability"],    # Sustainability Commission
            153: ["planning", "zoning"],                           # City Planning Commission
        },
        "default_tags": ["government", "ann_arbor"],
    },
    "dwsd": {
        "name": "DWSD",
        "full_name": "Detroit Water and Sewerage Department",
        "client": "dwsd",
        "region": "Wayne County",
        "source": "dwsd_scraper",
        "env_bodies": {
            # All DWSD bodies are water/infrastructure relevant
        },
        "default_tags": ["water_quality", "drinking_water", "infrastructure", "dwsd"],
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
    # Webex
    match = re.search(r'https?://[\w.-]*webex\.com/\S+', text)
    if match:
        return match.group(0).rstrip('.,;)')
    return None


def extract_meeting_id(text):
    """Extract Zoom/webinar meeting ID from URL or text."""
    if not text:
        return None
    # Zoom URL meeting ID
    match = re.search(r'zoom\.us/[jw]/(\d+)', text)
    if match:
        return match.group(1)
    # Webinar ID in text (e.g., "Webinar ID: 943 5402 4789")
    match = re.search(r'(?:Webinar|Meeting)\s+ID[:\s]+(\d[\d\s]+\d)', text, re.IGNORECASE)
    if match:
        return match.group(1).replace(" ", "")
    return None


def extract_dial_in(text):
    """Extract phone dial-in number from text."""
    if not text:
        return None
    # Match phone numbers like +1 301 715 8592 or 877-853-5247
    match = re.search(r'(\+?1?\s*[\(\-]?\d{3}[\)\-\s]+\d{3}[\-\s]+\d{4})', text)
    if match:
        return match.group(1).strip()
    return None


def determine_meeting_type(body_name, comment=""):
    """Determine meeting type from body name and comment."""
    text = (body_name + " " + (comment or "")).lower()
    if "public hearing" in text or "hearing" in text:
        return "public_hearing"
    if "work session" in text or "workshop" in text:
        return "workshop"
    if "special" in text:
        return "special_meeting"
    if "city council" in text or "board of commissioners" in text:
        return "board_meeting"
    if "committee" in text or "commission" in text or "advisory" in text:
        return "committee_meeting"
    return "public_meeting"


def determine_format(location, comment):
    """Determine if meeting is in-person, virtual, or hybrid based on location and comment."""
    loc_lower = (location or "").lower()
    comment_lower = (comment or "").lower()
    combined = loc_lower + " " + comment_lower

    has_virtual_indicator = (
        "electronic meeting" in loc_lower
        or "virtual" in combined
        or "zoom" in combined
        or "webex" in combined
        or "webinar" in combined
    )
    # Check for physical address indicators: street number + name, or keywords like "hall", "building"
    has_physical = (
        bool(re.search(r'\d+\s+[\w\s]+(st\b|street|ave|road|rd\b|blvd|dr\b|place|way|ln\b|lane)', loc_lower))
        or "hall" in loc_lower
        or "building" in loc_lower
        or "office" in loc_lower
        or "room" in loc_lower
    )

    if has_virtual_indicator and has_physical:
        return "hybrid"
    if has_virtual_indicator:
        return "virtual"
    return "in_person"


def generate_source_id(client, event_id):
    """Generate a stable source_id from the Legistar client and event ID."""
    return f"{client}-{event_id}"


def get_issue_tags(body_id, config):
    """Determine issue tags based on body ID and config."""
    return config["env_bodies"].get(body_id, config["default_tags"])


def build_meeting(event, config):
    """Convert a Legistar API event to our meetings table format."""
    event_id = event["EventId"]
    body_name = event.get("EventBodyName", "").strip()
    body_id = event.get("EventBodyId")
    location = event.get("EventLocation", "") or ""
    comment = event.get("EventComment", "") or ""
    combined_text = f"{location} {comment}"

    # Parse date and time
    event_date_str = event.get("EventDate", "")
    event_time_str = event.get("EventTime", "")
    try:
        # EventDate is like "2026-03-19T00:00:00", EventTime is like "8:30 AM"
        date_part = event_date_str[:10]  # "2026-03-19"
        dt = datetime.strptime(f"{date_part} {event_time_str}", "%Y-%m-%d %I:%M %p")
        local_dt = dt.replace(tzinfo=MICHIGAN_TZ)
        meeting_date = local_dt.strftime("%Y-%m-%d")
        meeting_time = local_dt.strftime("%H:%M")
        start_datetime = local_dt.isoformat()
    except (ValueError, AttributeError):
        meeting_date = event_date_str[:10] if event_date_str else ""
        meeting_time = ""
        start_datetime = ""

    # Virtual meeting info
    virtual_url = extract_virtual_url(combined_text)
    meeting_id = extract_meeting_id(combined_text)
    dial_in = extract_dial_in(combined_text)

    # Meeting format
    fmt = determine_format(location, comment)

    # Agenda and minutes PDFs (direct from API)
    agenda_url = event.get("EventAgendaFile")
    # minutes_url = event.get("EventMinutesFile")  # Column not yet in Supabase

    # Detail page on Legistar InSite portal
    details_url = event.get("EventInSiteURL", "")

    # Agency name
    full_name = config.get("full_name", config["name"])
    agency = f"{full_name} - {body_name}" if body_name else full_name

    client = config["client"]

    meeting = {
        "title": body_name,
        "agency": agency,
        "meeting_date": meeting_date,
        "meeting_time": meeting_time,
        "start_datetime": start_datetime,
        "location": location if fmt != "virtual" else None,
        "meeting_type": determine_meeting_type(body_name, comment),
        "source": config["source"],
        "source_id": generate_source_id(client, event_id),
        "details_url": details_url,
        "agenda_url": agenda_url,
        "virtual_url": virtual_url,
        "virtual_meeting_id": meeting_id,
        "virtual_phone": dial_in,
        "region": config["region"],
        "issue_tags": get_issue_tags(body_id, config),
    }

    return meeting


def fetch_upcoming_events(config):
    """Fetch upcoming events from a source's Legistar API."""
    client = config["client"]
    today = datetime.now(MICHIGAN_TZ)
    start_date = today.strftime("%Y-%m-%dT00:00:00")
    end_date = (today + timedelta(days=LOOKAHEAD_DAYS)).strftime("%Y-%m-%dT00:00:00")

    url = (
        f"{API_BASE}/{client}/Events"
        f"?$filter=EventDate gt datetime'{start_date}' and EventDate lt datetime'{end_date}'"
        f"&$orderby=EventDate asc"
        f"&$top=200"
    )

    print(f"Fetching {config['name']} events from Legistar API...")
    print(f"  Client: {client}")
    print(f"  Date range: {today.strftime('%Y-%m-%d')} to {(today + timedelta(days=LOOKAHEAD_DAYS)).strftime('%Y-%m-%d')}")

    resp = httpx.get(url, timeout=30)
    resp.raise_for_status()
    events = resp.json()

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
    """Scrape meetings for a single Legistar source. Returns list of meeting dicts."""
    config = LEGISTAR_CONFIGS[key]

    print("=" * 60)
    print(f"{config['name']} Meeting Scraper (Legistar API)")
    print("=" * 60)

    events = fetch_upcoming_events(config)

    meetings = []
    for event in events:
        meeting = build_meeting(event, config)
        meetings.append(meeting)

        if meeting["virtual_url"]:
            print(f"  VIRTUAL: {meeting['title'][:50]} — {meeting['virtual_url'][:60]}")

    print(f"\nBuilt {len(meetings)} meeting records")
    env_count = sum(1 for m in meetings if m["issue_tags"] != config["default_tags"])
    print(f"  {env_count} environmentally relevant, {len(meetings) - env_count} general")

    if meetings:
        print("\nUpserting to database...")
        upsert_meetings(meetings)

    print("\nDone!")
    print_result(key, "ok", len(meetings), "meetings")
    return meetings


async def main(key):
    """Main entry point — called by run_scrapers.py with config_key from registry."""
    return await scrape_source(key)
