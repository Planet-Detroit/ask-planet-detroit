"""
Washtenaw County Meeting Scraper
Thin wrapper around civicclerk_scraper for Washtenaw County.

Source: https://washtenawcomi.api.civicclerk.com/v1/Events
No authentication required. No browser needed.
"""

from scraper_utils import print_result
from civicclerk_scraper import scrape_county, COUNTY_CONFIGS

# Re-export parsing functions so existing tests keep working
from civicclerk_scraper import (
    extract_virtual_url,
    extract_zoom_meeting_id,
    extract_dial_in,
    build_location_string,
    get_issue_tags,
    determine_meeting_type,
    determine_format,
    build_meeting,
)

COUNTY_KEY = "washtenaw"
DEFAULT_ISSUE_TAGS = COUNTY_CONFIGS[COUNTY_KEY]["default_tags"]


async def main():
    """Main entry point."""
    meetings = await scrape_county(COUNTY_KEY)
    print_result(COUNTY_KEY, "ok", len(meetings), "meetings")
    return meetings


if __name__ == "__main__":
    import asyncio
    try:
        asyncio.run(main())
    except Exception as e:
        print_result(COUNTY_KEY, "error", error=str(e))
        raise
