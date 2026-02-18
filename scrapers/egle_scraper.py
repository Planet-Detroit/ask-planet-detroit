"""
EGLE Meeting & Comment Period Scraper
Scrapes Michigan EGLE public meetings and comment periods from the
Trumba RSS feed (deq-events calendar).

Source: https://www.trumba.com/calendars/deq-events.rss
(Embedded on https://www.michigan.gov/egle/outreach/calendar)

Routes items to two Supabase tables:
  - Public hearings / workgroup meetings → meetings table
  - Comment period deadlines → comment_periods table
"""

import os
import re
import html
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from zoneinfo import ZoneInfo
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

# Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
RSS_URL = "https://www.trumba.com/calendars/deq-events.rss"
MICHIGAN_TZ = ZoneInfo("America/Detroit")
TRUMBA_NS = {"trumba": "http://schemas.trumba.com/rss/x-trumba"}

# EGLE headquarters (default location)
EGLE_LAT = 42.7335
EGLE_LNG = -84.5555

# Issue tag mapping based on keywords in title/description
ISSUE_KEYWORDS = {
    "air quality": ["air_quality"],
    "air permit": ["air_quality"],
    "air toxic": ["air_quality"],
    "renewable operating permit": ["air_quality"],
    "rop": ["air_quality"],
    "emissions": ["air_quality"],
    "water": ["water_quality"],
    "drinking water": ["drinking_water"],
    "groundwater": ["drinking_water", "water_quality"],
    "wetland": ["water_quality"],
    "npdes": ["water_quality"],
    "discharge": ["water_quality"],
    "waste": ["waste", "pollution"],
    "hazardous": ["waste", "pollution"],
    "contamination": ["pollution"],
    "pfas": ["pfas", "drinking_water"],
    "remediation": ["pollution"],
    "remedial": ["pollution"],
    "brownfield": ["pollution"],
    "climate": ["climate"],
    "energy": ["energy"],
    "renewable": ["energy", "climate"],
    "pipeline": ["energy", "infrastructure"],
    "compressor": ["energy", "air_quality"],
    "maritime": ["water_quality", "great_lakes"],
    "great lakes": ["great_lakes", "water_quality"],
    "consent order": ["enforcement"],
    "enforcement": ["enforcement"],
    "permit": ["permitting"],
    "dte": ["dte_energy", "energy", "utilities"],
    "consumers energy": ["consumers_energy", "energy", "utilities"],
    "electric": ["energy", "utilities"],
    "power plant": ["energy", "utilities"],
}

# Comment type mapping (checked in order — more specific first)
COMMENT_TYPE_KEYWORDS = [
    ("renewable operating permit", "air_permit"),
    ("rop", "air_permit"),
    ("air permit", "air_permit"),
    ("air toxic", "air_permit"),
    ("emissions", "air_permit"),
    ("wetland", "water_permit"),
    ("npdes", "water_permit"),
    ("discharge", "water_permit"),
    ("water permit", "water_permit"),
    ("consent order", "enforcement"),
    ("remedial", "environmental_review"),
    ("contamination", "environmental_review"),
    ("brownfield", "environmental_review"),
    ("pipeline", "environmental_review"),
    ("maritime", "policy"),
    ("strategy", "policy"),
    ("rule", "rulemaking"),
    ("screening level", "rulemaking"),
    ("power plant", "air_permit"),
    ("electric", "air_permit"),
]


def get_supabase():
    """Initialize Supabase client."""
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def extract_issue_tags(title, description=""):
    """Extract issue tags based on keywords in title and description."""
    # Strip out the EGLE agency name boilerplate to avoid false matches
    # ("Great Lakes" in the agency name, "Renewable" in "Renewable Operating Permit")
    text = f"{title} {description}".lower()
    text = text.replace("michigan department of environment, great lakes, and energy", "")
    text = text.replace("renewable operating permit", "air_permit_rop")  # Prevent "renewable" match

    tags = set()
    for keyword, issue_tags in ISSUE_KEYWORDS.items():
        if keyword in text:
            tags.update(issue_tags)

    if not tags:
        tags.add("environment")

    return list(tags)


def determine_comment_type(title, description=""):
    """Determine comment type from content."""
    text = f"{title} {description}".lower()

    for keyword, comment_type in COMMENT_TYPE_KEYWORDS:
        if keyword in text:
            return comment_type

    return "public_comment"


def extract_region(title, description=""):
    """Extract geographic region from title/description."""
    text = f"{title} {description}"

    # Look for Michigan counties
    county_match = re.search(r'(\w+(?:\s\w+)?)\s+County', text)
    county = county_match.group(1) if county_match else None

    # Southeast Michigan counties
    se_counties = {
        "Wayne", "Oakland", "Macomb", "Washtenaw", "Livingston",
        "Monroe", "St. Clair", "Lenawee",
    }
    # Detroit area
    detroit_keywords = ["Detroit", "Wayne County", "Dearborn", "Hamtramck", "River Rouge"]

    if any(kw in text for kw in detroit_keywords):
        return "detroit"
    if county and county in se_counties:
        return "southeast_michigan"
    if county:
        return county + " County"

    return "statewide"


def extract_srn(title):
    """Extract SRN (Source Registration Number) from title."""
    match = re.search(r'\(SRN:\s*(\w+)\)', title)
    return match.group(1) if match else None


def extract_facility_name(title):
    """Extract facility/company name from title."""
    # Pattern: "... for FACILITY NAME, CITY, COUNTY, (SRN: ...)"
    match = re.search(r'(?:for|Regarding)\s+(.+?)(?:,\s+\w+(?:\s\w+)?,\s+\w+(?:\s\w+)?\s+County|$)', title)
    if match:
        name = match.group(1).strip()
        # Clean up common prefixes
        name = re.sub(r'^(?:the\s+)?(?:Draft\s+)?', '', name, flags=re.IGNORECASE)
        return name[:200]
    return None


def parse_rss_date(category_text):
    """Parse date from Trumba RSS category field like '2026/02/18 (Wed)'."""
    match = re.search(r'(\d{4}/\d{2}/\d{2})', category_text)
    if match:
        return datetime.strptime(match.group(1), "%Y/%m/%d").date()
    return None


def extract_start_date(desc_text, end_date):
    """
    Try to extract comment period start date from description.
    Looks for patterns like "from January 22, 2026" or "opens on January 27, 2026".
    Falls back to 30 days before end_date.
    """
    patterns = [
        r'from\s+(\w+ \d{1,2},?\s+\d{4})',
        r'open[s]?\s+(?:on\s+)?(\w+ \d{1,2},?\s+\d{4})',
        r'start[s]?\s+(?:on\s+)?(\w+ \d{1,2},?\s+\d{4})',
        r'beginning\s+(\w+ \d{1,2},?\s+\d{4})',
    ]
    for pattern in patterns:
        match = re.search(pattern, desc_text, re.IGNORECASE)
        if match:
            date_str = match.group(1).replace(",", "")
            for fmt in ["%B %d %Y", "%b %d %Y"]:
                try:
                    return datetime.strptime(date_str, fmt).date()
                except ValueError:
                    continue

    # Fallback: 30 days before deadline
    from datetime import timedelta
    return end_date - timedelta(days=30)


def parse_time_from_description(desc_text):
    """Extract start time from description text."""
    # Look for patterns like "6 – 9pm", "10:00 AM – 12:00 PM", "1 pm"
    match = re.search(r'(\d{1,2})(?::(\d{2}))?\s*([–-]\s*\d{1,2}(?::\d{2})?\s*)?([ap]m)', desc_text, re.IGNORECASE)
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2)) if match.group(2) else 0
        ampm = match.group(4).upper()
        if ampm == "PM" and hour != 12:
            hour += 12
        elif ampm == "AM" and hour == 12:
            hour = 0
        return f"{hour:02d}:{minute:02d}"
    return None


def extract_zoom_url(desc_html):
    """Extract Zoom or Teams URL from description HTML."""
    zoom = re.search(r'(https?://[^\s"<>]*zoom[^\s"<>]*)', desc_html)
    if zoom:
        return zoom.group(1)
    teams = re.search(r'(https?://teams\.microsoft\.com/[^\s"<>]+)', desc_html)
    if teams:
        return teams.group(1)
    return None


def html_to_text(html_str):
    """Strip HTML tags and clean up text."""
    text = html.unescape(re.sub(r'<[^>]+>', ' ', html_str))
    return re.sub(r'\s+', ' ', text).strip()


def fetch_rss():
    """Fetch and parse the Trumba RSS feed."""
    print(f"Fetching EGLE calendar RSS from {RSS_URL}")
    req = urllib.request.Request(RSS_URL, headers={
        "User-Agent": "Mozilla/5.0 (compatible; PlanetDetroit-Scraper/1.0)"
    })
    resp = urllib.request.urlopen(req, timeout=30)
    data = resp.read().decode("utf-8")

    root = ET.fromstring(data)
    channel = root.find("channel")
    items = channel.findall("item")
    print(f"  Found {len(items)} RSS items")
    return items


def classify_item(title, description):
    """Classify an RSS item as a meeting or comment period."""
    title_lower = title.lower()

    # Meetings: hearings, workgroup meetings, webinars, board meetings
    meeting_keywords = ["hearing", "meeting", "webinar", "workshop", "conference"]
    for kw in meeting_keywords:
        if kw in title_lower:
            return "meeting"

    # Comment periods: deadlines, comment period notices
    if "deadline" in title_lower or "comment" in title_lower:
        return "comment_period"

    # Default based on description
    desc_lower = description.lower()
    if "public hearing" in desc_lower:
        return "meeting"

    return "comment_period"


def parse_items(items):
    """Parse RSS items into meetings and comment periods."""
    meetings = []
    comment_periods = []
    now = datetime.now(MICHIGAN_TZ)

    for item in items:
        title = (item.find("title").text or "").strip()
        desc_html = item.find("description").text or ""
        link = (item.find("link").text or "").strip()
        category = (item.find("category").text or "").strip()
        guid = (item.find("guid").text or "").strip()

        weblink_el = item.find("trumba:weblink", TRUMBA_NS)
        weblink = weblink_el.text.strip() if weblink_el is not None and weblink_el.text else None

        # Parse date
        event_date = parse_rss_date(category)
        if not event_date:
            print(f"  Skipping (no date): {title[:60]}")
            continue

        # Clean description
        desc_text = html_to_text(desc_html)

        # Extract Trumba event ID for stable source_id
        event_id_match = re.search(r'event/(\d+)', guid)
        event_id = event_id_match.group(1) if event_id_match else str(hash(title) % 100000)

        # Classify
        item_type = classify_item(title, desc_text)

        issue_tags = extract_issue_tags(title, desc_text)
        region = extract_region(title, desc_text)

        if item_type == "meeting":
            # Skip past meetings
            meeting_time = parse_time_from_description(desc_text) or "10:00"
            hour, minute = map(int, meeting_time.split(":"))
            meeting_dt = datetime(
                event_date.year, event_date.month, event_date.day,
                hour, minute, tzinfo=MICHIGAN_TZ
            )
            if meeting_dt < now:
                continue

            virtual_url = extract_zoom_url(desc_html)
            # Also check weblink for Teams URLs
            if not virtual_url and weblink and "teams.microsoft.com" in weblink:
                virtual_url = weblink

            meeting_type = "public_hearing"
            if "workgroup" in title.lower() or "advisory" in title.lower():
                meeting_type = "committee_meeting"
            elif "webinar" in title.lower():
                meeting_type = "webinar"
            elif "workshop" in title.lower():
                meeting_type = "workshop"

            meeting = {
                "title": title,
                "description": desc_text[:500],
                "agency": "EGLE",
                "agency_full_name": "Michigan Department of Environment, Great Lakes, and Energy",
                "department": None,
                "meeting_type": meeting_type,
                "start_datetime": meeting_dt.isoformat(),
                "timezone": "America/Detroit",
                "meeting_date": event_date.isoformat(),
                "meeting_time": meeting_time,
                "location_name": "EGLE - Online" if virtual_url else "EGLE Headquarters",
                "location_address": None if virtual_url else "525 W. Allegan St.",
                "location_city": "Lansing",
                "location_state": "Michigan",
                "location_zip": "48933",
                "latitude": EGLE_LAT,
                "longitude": EGLE_LNG,
                "is_virtual": bool(virtual_url),
                "is_hybrid": False,
                "virtual_url": virtual_url,
                "accepts_public_comment": True,
                "public_comment_instructions": "Check the event details for public comment information.",
                "contact_email": "EGLE-Assist@Michigan.gov",
                "contact_phone": "800-662-9278",
                "issue_tags": issue_tags,
                "region": region,
                "source": "egle_scraper",
                "source_url": link,
                "source_id": f"egle-event-{event_id}",
                "status": "upcoming",
                "details_url": link,
                "agenda_url": weblink,
            }
            meetings.append(meeting)
            print(f"  MEETING: {title[:70]} ({event_date})")

        else:
            # Comment period - the RSS date is the deadline (end_date)
            # Skip expired comment periods
            if event_date < now.date():
                continue

            facility = extract_facility_name(title)
            srn = extract_srn(title)
            comment_type = determine_comment_type(title, desc_text)
            start_date = extract_start_date(desc_text, event_date)

            # Try to find submission instructions in description
            comment_email = None
            email_match = re.search(r'[\w.+-]+@[\w-]+\.[\w.-]+', desc_text)
            if email_match:
                comment_email = email_match.group(0)

            comment_period = {
                "title": title,
                "description": desc_text[:500],
                "agency": "EGLE",
                "agency_full_name": "Michigan Department of Environment, Great Lakes, and Energy",
                "comment_type": comment_type,
                "start_date": start_date.isoformat(),
                "end_date": event_date.isoformat(),
                "facility_name": facility,
                "permit_number": srn,
                "details_url": link,
                "documents_url": weblink,
                "comment_instructions": "Submit written comments to EGLE. See event details for specific instructions.",
                "comment_email": comment_email or "EGLE-Assist@Michigan.gov",
                "issue_tags": issue_tags,
                "region": region,
                "source": "egle_scraper",
                "source_url": link,
                "source_id": f"egle-comment-{event_id}",
                "status": "open",
                "featured": False,
            }
            comment_periods.append(comment_period)
            print(f"  COMMENT: {title[:70]} (deadline {event_date})")

    return meetings, comment_periods


def upsert_meetings(meetings):
    """Insert or update meetings in Supabase."""
    if not meetings:
        print("No meetings to upsert")
        return

    supabase = get_supabase()
    for meeting in meetings:
        try:
            supabase.table("meetings").upsert(
                meeting,
                on_conflict="source,source_id"
            ).execute()
            print(f"  Upserted meeting: {meeting['title'][:50]}")
        except Exception as e:
            print(f"  Error upserting meeting: {e}")


def upsert_comment_periods(periods):
    """Insert or update comment periods in Supabase."""
    if not periods:
        print("No comment periods to upsert")
        return

    supabase = get_supabase()
    for period in periods:
        try:
            supabase.table("comment_periods").upsert(
                period,
                on_conflict="source,source_id"
            ).execute()
            print(f"  Upserted comment period: {period['title'][:50]}")
        except Exception as e:
            print(f"  Error upserting comment period: {e}")


async def main():
    """Main entry point."""
    print("=" * 60)
    print("EGLE Meeting & Comment Period Scraper")
    print("=" * 60)

    items = fetch_rss()
    meetings, comment_periods = parse_items(items)

    print(f"\nFound {len(meetings)} meetings, {len(comment_periods)} comment periods")

    if meetings:
        print("\nUpserting meetings...")
        upsert_meetings(meetings)

    if comment_periods:
        print("\nUpserting comment periods...")
        upsert_comment_periods(comment_periods)

    print("\nDone!")
    return meetings


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
