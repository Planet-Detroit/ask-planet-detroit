"""
Macomb County Meeting Scraper
Thin wrapper around civicclerk_scraper for Macomb County.

Source: https://macombcomi.api.civicclerk.com/v1/Events
No authentication required. No browser needed.
"""

from scraper_utils import print_result
from civicclerk_scraper import scrape_source

COUNTY_KEY = "macomb"


async def main():
    """Main entry point."""
    meetings = await scrape_source(COUNTY_KEY)
    print_result(COUNTY_KEY, "ok", len(meetings), "meetings")
    return meetings


if __name__ == "__main__":
    import asyncio
    try:
        asyncio.run(main())
    except Exception as e:
        print_result(COUNTY_KEY, "error", error=str(e))
        raise
