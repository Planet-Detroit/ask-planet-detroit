"""
Michigan Legislature Committee Meeting Scraper
Fetches upcoming committee meetings from the MI Legislature RSS feed,
then enriches each with location/agenda details from .ics calendar files.

Source: https://legislature.mi.gov/Committees/Meetings
RSS: https://legislature.mi.gov/documents/publications/RssFeeds/comschedule.xml
ICS: https://legislature.mi.gov/Committees/AddMeetingToCalendar?meetingID={id}

Updates every 5 minutes on the source. No authentication. No browser needed.
"""

import os
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from zoneinfo import ZoneInfo

import httpx
from dotenv import load_dotenv

from scraper_utils import print_result

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
MICHIGAN_TZ = ZoneInfo("America/Detroit")

RSS_URL = "https://legislature.mi.gov/documents/publications/RssFeeds/comschedule.xml"
ICS_BASE = "https://legislature.mi.gov/Committees/AddMeetingToCalendar?meetingID="
MEETING_BASE = "https://legislature.mi.gov/Committees/Meeting?meetingID="

# Committees with environmental relevance
ENV_COMMITTEES = {
    # Senate
    "energy and environment": ["environment", "energy", "climate"],
    "natural resources and agriculture": ["environment", "natural_resources", "agriculture"],
    "transportation and infrastructure": ["infrastructure"],
    # House
    "energy": ["energy", "climate"],
    "natural resources and tourism": ["environment", "natural_resources"],
    "transportation and infrastructure": ["infrastructure"],
    # Appropriations subcommittees
    "appropriations subcommittee on environment": ["environment", "budget"],
    "appropriations subcommittee on natural resources": ["environment", "natural_resources", "budget"],
}

DEFAULT_TAGS = ["government", "michigan_legislature"]


def parse_rss(xml_text):
    """Parse the MI Legislature committee meetings RSS feed.

    Returns a list of dicts with: meeting_id, title, chamber, committee, date_str, time_str, link
    """
    root = ET.fromstring(xml_text)
    meetings = []

    for item in root.findall(".//item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        description = (item.findtext("description") or "").strip()
        guid = (item.findtext("guid") or "").strip()

        if not guid:
            continue

        meeting_id = guid

        # Parse title: "House Meeting - Energy 3/17/2026 09:00 AM"
        # or "Senate Meeting - Natural Resources and Agriculture 3/18/2026 10:30 AM"
        chamber, committee, date_str, time_str = parse_title(title)

        meetings.append({
            "meeting_id": meeting_id,
            "title": title,
            "chamber": chamber,
            "committee": committee,
            "date_str": date_str,
            "time_str": time_str,
            "link": link,
            "description": description,
        })

    return meetings


def parse_title(title):
    """Parse meeting title into chamber, committee, date, and time.

    Examples:
        "House Meeting - Energy 3/17/2026 09:00 AM"
        "Senate Meeting - Appropriations Subcommittee on DHHS 3/17/2026 03:00 PM"
    """
    chamber = ""
    committee = ""
    date_str = ""
    time_str = ""

    # Extract chamber
    if title.startswith("House"):
        chamber = "House"
    elif title.startswith("Senate"):
        chamber = "Senate"

    # Extract date and time from end of title
    date_match = re.search(r'(\d{1,2}/\d{1,2}/\d{4})\s+(\d{1,2}:\d{2}\s*[AP]M)', title)
    if date_match:
        date_str = date_match.group(1)
        time_str = date_match.group(2)

        # Committee is between "Meeting - " and the date
        meeting_match = re.search(r'Meeting\s*-\s*(.+?)\s+\d{1,2}/', title)
        if meeting_match:
            committee = meeting_match.group(1).strip()

    return chamber, committee, date_str, time_str


def parse_ics(ics_text):
    """Parse an .ics calendar file for location and agenda details.

    Returns a dict with: location, description, agenda_text, clerk_phone
    """
    result = {
        "location": None,
        "agenda_text": None,
        "clerk_phone": None,
    }

    # Un-fold ICS lines (continuation lines start with space/tab)
    unfolded = re.sub(r'\r?\n[ \t]', '', ics_text)

    for line in unfolded.split('\n'):
        line = line.strip()
        if line.startswith("LOCATION:"):
            result["location"] = line[len("LOCATION:"):].strip()
        elif line.startswith("DESCRIPTION:"):
            desc = line[len("DESCRIPTION:"):].strip()
            # ICS uses \n for newlines in DESCRIPTION
            desc = desc.replace("\\n", "\n")
            result["agenda_text"] = desc

            # Extract clerk phone
            phone_match = re.search(r'CLERK:\s*([\d-]+)', desc)
            if phone_match:
                result["clerk_phone"] = phone_match.group(1)

    return result


def extract_agenda_bills(agenda_text):
    """Extract bill numbers from agenda text (e.g., HB 5710, SB 123)."""
    if not agenda_text:
        return []
    return re.findall(r'[HS]B\s+\d+', agenda_text)


def get_issue_tags(committee):
    """Determine issue tags based on committee name."""
    committee_lower = committee.lower()
    for pattern, tags in ENV_COMMITTEES.items():
        if pattern in committee_lower:
            return tags
    return DEFAULT_TAGS


def build_meeting(rss_entry, ics_data):
    """Convert an RSS entry + ICS data into our meetings table format."""
    meeting_id = rss_entry["meeting_id"]
    chamber = rss_entry["chamber"]
    committee = rss_entry["committee"]
    date_str = rss_entry["date_str"]
    time_str = rss_entry["time_str"]

    # Parse date and time
    try:
        dt = datetime.strptime(f"{date_str} {time_str}", "%m/%d/%Y %I:%M %p")
        local_dt = dt.replace(tzinfo=MICHIGAN_TZ)
        meeting_date = local_dt.strftime("%Y-%m-%d")
        meeting_time = local_dt.strftime("%H:%M")
        start_datetime = local_dt.isoformat()
    except (ValueError, AttributeError):
        meeting_date = ""
        meeting_time = ""
        start_datetime = ""

    # Agency
    agency = f"Michigan {chamber}" if chamber else "Michigan Legislature"
    title = f"{chamber} {committee}" if chamber else committee

    # Location from ICS
    location = ics_data.get("location")

    # Agenda info
    agenda_text = ics_data.get("agenda_text", "")
    bills = extract_agenda_bills(agenda_text)

    meeting = {
        "title": title,
        "agency": agency,
        "meeting_date": meeting_date,
        "meeting_time": meeting_time,
        "start_datetime": start_datetime,
        "location": location,
        "meeting_type": "committee_meeting",
        "source": "mi_legislature_scraper",
        "source_id": f"mileg-{meeting_id}",
        "details_url": f"{MEETING_BASE}{meeting_id}",
        "agenda_url": None,  # Agenda is in-line text, not a PDF
        "virtual_url": None,  # Legislature meetings are in-person at Capitol
        "virtual_meeting_id": None,
        "virtual_phone": None,
        "region": "Michigan",
        "issue_tags": get_issue_tags(committee),
    }

    return meeting


async def main():
    """Main entry point — fetch RSS, enrich with ICS, upsert to Supabase."""
    print("=" * 60)
    print("Michigan Legislature Committee Meeting Scraper")
    print("=" * 60)

    # Fetch RSS feed
    print(f"\nFetching RSS feed...")
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(RSS_URL)
        resp.raise_for_status()
        rss_entries = parse_rss(resp.text)
        print(f"  Found {len(rss_entries)} meetings in RSS feed")

        # Fetch ICS for each meeting to get location/agenda details
        meetings = []
        for entry in rss_entries:
            ics_url = f"{ICS_BASE}{entry['meeting_id']}"
            try:
                ics_resp = await client.get(ics_url)
                ics_data = parse_ics(ics_resp.text) if ics_resp.status_code == 200 else {}
            except Exception as e:
                print(f"  Warning: Could not fetch ICS for {entry['committee']}: {e}")
                ics_data = {}

            meeting = build_meeting(entry, ics_data)
            meetings.append(meeting)

    print(f"\nBuilt {len(meetings)} meeting records")
    env_count = sum(1 for m in meetings if m["issue_tags"] != DEFAULT_TAGS)
    print(f"  {env_count} environmentally relevant, {len(meetings) - env_count} general")

    # Upsert to Supabase
    if meetings:
        from supabase import create_client
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

        print("\nUpserting to database...")
        for meeting in meetings:
            try:
                supabase.table("meetings").upsert(
                    meeting,
                    on_conflict="source,source_id"
                ).execute()
                print(f"  Upserted: {meeting['title'][:50]} ({meeting['meeting_date']})")
            except Exception as e:
                print(f"  Error upserting {meeting['title'][:30]}: {e}")

    print("\nDone!")
    print_result("mi_legislature", "ok", len(meetings), "meetings")
    return meetings


if __name__ == "__main__":
    import asyncio
    try:
        asyncio.run(main())
    except Exception as e:
        print_result("mi_legislature", "error", error=str(e))
        raise
