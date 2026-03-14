"""
CivicClerk Meeting Scraper (multi-county)
Fetches upcoming public meetings from any county using the CivicClerk OData API.

Supports: Washtenaw, Oakland, Macomb counties (and any future CivicClerk county).
Configuration is passed in — each county defines its API base URL, site key,
region name, and environmentally relevant category IDs.

No authentication required. No browser needed.
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

# How far ahead to look for meetings (days)
LOOKAHEAD_DAYS = 90


# --- CivicClerk configurations (counties and municipalities) ---

CIVICCLERK_CONFIGS = {
    "washtenaw": {
        "name": "Washtenaw County",
        "api_base": "https://washtenawcomi.api.civicclerk.com/v1",
        "portal_base": "https://washtenawcomi.portal.civicclerk.com",
        "site_key": "WASHTENAWCOMI",
        "region": "Washtenaw County",
        "source": "washtenaw_scraper",
        # Category IDs with environmental relevance
        "env_categories": {
            58: ["environment", "climate"],                    # Environmental Council
            64: ["environment", "water_quality", "pfas"],      # Dioxane Coalition
            41: ["environment", "infrastructure"],             # Brownfield Authority
            36: ["water_quality", "drinking_water"],           # Water Resources
            72: ["environment", "infrastructure"],             # Material Management
            40: ["environment", "great_lakes"],                # Conservation District
            39: ["environment", "infrastructure"],             # Solid Waste Consortium
            53: ["environment", "great_lakes"],                # Natural Areas
            71: ["environment", "agriculture"],                # Ag Lands Preservation
            68: ["infrastructure"],                            # Board of Public Works
            69: ["public_health"],                             # Board of Health
            45: ["water_quality", "infrastructure"],           # Drainage Board
            29: ["parks", "environment"],                      # Parks & Recreation
        },
        "default_tags": ["government", "washtenaw_county"],
    },
    "oakland": {
        "name": "Oakland County",
        "api_base": "https://oaklandcomi.api.civicclerk.com/v1",
        "portal_base": "https://oaklandcomi.portal.civicclerk.com",
        "site_key": "OAKLANDCOMI",
        "region": "Oakland County",
        "source": "oakland_scraper",
        "env_categories": {
            52: ["environment", "infrastructure"],             # Materials Management
        },
        "default_tags": ["government", "oakland_county"],
    },
    "macomb": {
        "name": "Macomb County",
        "api_base": "https://macombcomi.api.civicclerk.com/v1",
        "portal_base": "https://macombcomi.portal.civicclerk.com",
        "site_key": "MACOMBCOMI",
        "region": "Macomb County",
        "source": "macomb_scraper",
        "env_categories": {
            49: ["environment", "infrastructure"],             # Brownfield Authority
            56: ["environment", "infrastructure"],             # Materials Management
            64: ["environment", "infrastructure"],             # Solid Waste Planning
        },
        "default_tags": ["government", "macomb_county"],
    },
    # --- Municipalities ---
    "livonia": {
        "name": "City of Livonia",
        "api_base": "https://livoniami.api.civicclerk.com/v1",
        "portal_base": "https://livoniami.portal.civicclerk.com",
        "site_key": "LIVONIAMI",
        "region": "Wayne County",
        "source": "livonia_scraper",
        "env_categories": {},
        "default_tags": ["government", "livonia"],
    },
    "canton": {
        "name": "Canton Township",
        "api_base": "https://cantonchartertwpmi.api.civicclerk.com/v1",
        "portal_base": "https://cantonchartertwpmi.portal.civicclerk.com",
        "site_key": "CANTONCHARTERTWPMI",
        "region": "Wayne County",
        "source": "canton_scraper",
        "env_categories": {},
        "default_tags": ["government", "canton"],
    },
    "dearborn_heights": {
        "name": "City of Dearborn Heights",
        "api_base": "https://dearbornheightsmi.api.civicclerk.com/v1",
        "portal_base": "https://dearbornheightsmi.portal.civicclerk.com",
        "site_key": "DEARBORNHEIGHTSMI",
        "region": "Wayne County",
        "source": "dearborn_heights_scraper",
        "env_categories": {},
        "default_tags": ["government", "dearborn_heights"],
    },
    "west_bloomfield": {
        "name": "West Bloomfield Township",
        "api_base": "https://wbtownshipmi.api.civicclerk.com/v1",
        "portal_base": "https://wbtownshipmi.portal.civicclerk.com",
        "site_key": "WBTOWNSHIPMI",
        "region": "Oakland County",
        "source": "west_bloomfield_scraper",
        "env_categories": {
            27: ["environment"],                                 # Environmental Commission
        },
        "default_tags": ["government", "west_bloomfield"],
    },
    "macomb_twp": {
        "name": "Macomb Township",
        "api_base": "https://macombtwpmi.api.civicclerk.com/v1",
        "portal_base": "https://macombtwpmi.portal.civicclerk.com",
        "site_key": "MACOMBTWPMI",
        "region": "Macomb County",
        "source": "macomb_twp_scraper",
        "env_categories": {},
        "default_tags": ["government", "macomb_township"],
    },
    "roseville": {
        "name": "City of Roseville",
        "api_base": "https://rosevillemi.api.civicclerk.com/v1",
        "portal_base": "https://rosevillemi.portal.civicclerk.com",
        "site_key": "ROSEVILLEMI",
        "region": "Macomb County",
        "source": "roseville_scraper",
        "env_categories": {},
        "default_tags": ["government", "roseville"],
    },
    "birmingham": {
        "name": "City of Birmingham",
        "api_base": "https://birminghammi.api.civicclerk.com/v1",
        "portal_base": "https://birminghammi.portal.civicclerk.com",
        "site_key": "BIRMINGHAMMI",
        "region": "Oakland County",
        "source": "birmingham_scraper",
        "env_categories": {
            33: ["parks", "environment"],                        # Parks and Recreation Board
        },
        "default_tags": ["government", "birmingham"],
    },
    "oak_park": {
        "name": "City of Oak Park",
        "api_base": "https://oakparkmi.api.civicclerk.com/v1",
        "portal_base": "https://oakparkmi.portal.civicclerk.com",
        "site_key": "OAKPARKMI",
        "region": "Oakland County",
        "source": "oak_park_scraper",
        "env_categories": {
            40: ["environment", "recycling"],                    # Recycling and Environmental Conservation
            37: ["parks", "environment"],                        # Parks and Recreation Commission
        },
        "default_tags": ["government", "oak_park"],
    },
    "romulus": {
        "name": "City of Romulus",
        "api_base": "https://romulusmi.api.civicclerk.com/v1",
        "portal_base": "https://romulusmi.portal.civicclerk.com",
        "site_key": "ROMULUSMI",
        "region": "Wayne County",
        "source": "romulus_scraper",
        "env_categories": {},
        "default_tags": ["government", "romulus"],
    },
    "harrison_twp": {
        "name": "Harrison Township",
        "api_base": "https://harrisontownshipmi.api.civicclerk.com/v1",
        "portal_base": "https://harrisontownshipmi.portal.civicclerk.com",
        "site_key": "HARRISONTOWNSHIPMI",
        "region": "Macomb County",
        "source": "harrison_twp_scraper",
        "env_categories": {},
        "default_tags": ["government", "harrison_township"],
    },
    "ypsilanti": {
        "name": "City of Ypsilanti",
        "api_base": "https://ypsilantimi.api.civicclerk.com/v1",
        "portal_base": "https://ypsilantimi.portal.civicclerk.com",
        "site_key": "YPSILANTIMI",
        "region": "Washtenaw County",
        "source": "ypsilanti_scraper",
        "env_categories": {},
        "default_tags": ["government", "ypsilanti"],
    },
    "grosse_pointe": {
        "name": "City of Grosse Pointe",
        "api_base": "https://grossepointemi.api.civicclerk.com/v1",
        "portal_base": "https://grossepointemi.portal.civicclerk.com",
        "site_key": "GROSSEPOINTEMI",
        "region": "Wayne County",
        "source": "grosse_pointe_scraper",
        "env_categories": {
            32: ["environment"],                                 # Beautification Commission
        },
        "default_tags": ["government", "grosse_pointe"],
    },
    "eastpointe": {
        "name": "City of Eastpointe",
        "api_base": "https://eastpointemi.api.civicclerk.com/v1",
        "portal_base": "https://eastpointemi.portal.civicclerk.com",
        "site_key": "EASTPOINTEMI",
        "region": "Macomb County",
        "source": "eastpointe_scraper",
        "env_categories": {},
        "default_tags": ["government", "eastpointe"],
    },
    "st_clair_county": {
        "name": "St. Clair County",
        "api_base": "https://stclaircomi.api.civicclerk.com/v1",
        "portal_base": "https://stclaircomi.portal.civicclerk.com",
        "site_key": "STCLAIRCOMI",
        "region": "St. Clair County",
        "source": "st_clair_county_scraper",
        "env_categories": {
            30: ["environment", "infrastructure"],               # Environmental/Public Works
        },
        "default_tags": ["government", "st_clair_county"],
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


def extract_zoom_meeting_id(text):
    """Extract Zoom meeting ID from URL or text."""
    if not text:
        return None
    match = re.search(r'zoom\.us/j/(\d+)', text)
    if match:
        return match.group(1)
    return None


def extract_dial_in(text):
    """Extract phone dial-in number from text."""
    if not text:
        return None
    match = re.search(r'(\+?1?\s*[\(\-]?\d{3}[\)\-\s]*\d{3}[\-\s]*\d{4})', text)
    if match:
        return match.group(1).strip()
    return None


def build_location_string(loc):
    """Build a readable location string from the eventLocation object."""
    if not loc:
        return None
    parts = []
    if loc.get("address1"):
        parts.append(loc["address1"])
    if loc.get("address2"):
        parts.append(loc["address2"])
    city_parts = []
    if loc.get("city"):
        city_parts.append(loc["city"])
    if loc.get("state"):
        city_parts.append(loc["state"])
    if loc.get("zipCode"):
        city_parts.append(loc["zipCode"])
    if city_parts:
        parts.append(", ".join(city_parts))
    return ", ".join(parts) if parts else None


def get_issue_tags(category_id, config):
    """Determine issue tags based on category and county config."""
    return config["env_categories"].get(category_id, config["default_tags"])


def determine_meeting_type(event_name, category_name):
    """Determine meeting type from event/category name."""
    name = (event_name + " " + (category_name or "")).lower()
    if "working session" in name or "workshop" in name:
        return "workshop"
    if "public hearing" in name or "hearing" in name:
        return "public_hearing"
    if "special" in name:
        return "special_meeting"
    if "board of commissioners" in name or "full board" in name:
        return "board_meeting"
    if "committee" in name or "commission" in name or "council" in name:
        return "committee_meeting"
    return "public_meeting"


def determine_format(event_name, virtual_url):
    """Determine if meeting is in-person, virtual, or hybrid."""
    name = event_name.lower()
    has_virtual = virtual_url is not None
    if "virtual" in name and "in person" in name:
        return "hybrid"
    if "virtual" in name and not has_virtual:
        return "virtual"
    if has_virtual:
        if "virtual" in name and "in person" not in name:
            return "virtual"
        return "hybrid"
    return "in_person"


def fetch_upcoming_events(config):
    """Fetch upcoming events from a county's CivicClerk OData API."""
    today = datetime.now(MICHIGAN_TZ)
    start_date = today.strftime("%Y-%m-%dT00:00:00Z")
    end_date = (today + timedelta(days=LOOKAHEAD_DAYS)).strftime("%Y-%m-%dT00:00:00Z")

    url = (
        f"{config['api_base']}/Events"
        f"?$filter=eventDate gt {start_date} and eventDate lt {end_date}"
        f"&$orderby=eventDate asc"
        f"&$top=200"
    )

    print(f"Fetching {config['name']} events from CivicClerk API...")
    print(f"  Date range: {today.strftime('%Y-%m-%d')} to {(today + timedelta(days=LOOKAHEAD_DAYS)).strftime('%Y-%m-%d')}")

    resp = httpx.get(url, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    events = data.get("value", [])

    # Filter to published events only
    events = [e for e in events if e.get("isPublished") == "Published"]

    print(f"  Found {len(events)} published upcoming events")
    return events


def build_meeting(event, config):
    """Convert a CivicClerk event to our meetings table format."""
    event_id = event["id"]
    event_name = event.get("eventName", "").strip()
    category_name = event.get("eventCategoryName", "")
    category_id = event.get("categoryId")

    # Parse date — API returns UTC, convert to Michigan time
    event_date_str = event.get("eventDate", "")
    try:
        event_dt = datetime.fromisoformat(event_date_str.replace("Z", "+00:00"))
        local_dt = event_dt.astimezone(MICHIGAN_TZ)
        meeting_date = local_dt.strftime("%Y-%m-%d")
        meeting_time = local_dt.strftime("%H:%M")
        start_datetime = local_dt.isoformat()
    except (ValueError, AttributeError):
        meeting_date = ""
        meeting_time = ""
        start_datetime = ""

    # Virtual meeting info from description and notice
    description = event.get("eventDescription", "") or ""
    notice = event.get("eventNotice", "") or ""
    combined_text = f"{description} {notice}"

    virtual_url = extract_virtual_url(combined_text)
    zoom_id = extract_zoom_meeting_id(combined_text)
    dial_in = extract_dial_in(combined_text)

    # Location
    location = build_location_string(event.get("eventLocation"))

    # Detail URL — portal event page
    details_url = f"{config['portal_base']}/event/{event_id}"

    # Direct agenda PDF if available
    agenda_url = None
    published_files = event.get("publishedFiles", [])
    for f in published_files:
        if f.get("fileType") == 1 or f.get("type") == "Agenda":
            relative_url = f.get("url", "")
            if relative_url:
                agenda_url = f"{config['portal_base']}/{relative_url}"
            break

    # Minutes PDF if available
    minutes_url = None
    for f in published_files:
        if f.get("fileType") == 4 or f.get("type") == "Minutes":
            relative_url = f.get("url", "")
            if relative_url:
                minutes_url = f"{config['portal_base']}/{relative_url}"
            break

    # County-specific source key (e.g., "washtenaw" from "washtenaw_scraper")
    county_key = config["source"].replace("_scraper", "")

    meeting = {
        "title": event_name,
        "agency": f"{config['name']} - {category_name}" if category_name else config["name"],
        "meeting_date": meeting_date,
        "meeting_time": meeting_time,
        "start_datetime": start_datetime,
        "location": location,
        "meeting_type": determine_meeting_type(event_name, category_name),
        "source": config["source"],
        "source_id": f"{county_key}-{event_id}",
        "details_url": details_url,
        "agenda_url": agenda_url,
        "minutes_url": minutes_url,
        "virtual_url": virtual_url,
        "virtual_meeting_id": zoom_id,
        "virtual_phone": dial_in,
        "region": config["region"],
        "issue_tags": get_issue_tags(category_id, config),
    }

    return meeting


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
    """Scrape meetings for a single CivicClerk source. Returns list of meeting dicts."""
    config = CIVICCLERK_CONFIGS[key]

    print("=" * 60)
    print(f"{config['name']} Meeting Scraper (CivicClerk API)")
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
    print(f"  {env_count} environmentally relevant, {len(meetings) - env_count} general government")

    if meetings:
        print("\nUpserting to database...")
        upsert_meetings(meetings)

    print("\nDone!")
    print_result(key, "ok", len(meetings), "meetings")
    return meetings


async def main(key):
    """Main entry point — called by run_scrapers.py with config_key from registry."""
    return await scrape_source(key)
