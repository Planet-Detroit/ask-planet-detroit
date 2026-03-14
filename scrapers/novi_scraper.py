"""
Novi Meeting Scraper — thin wrapper around shared MuniWeb scraper.
See muniweb_scraper.py for implementation and MUNIWEB_CONFIGS["novi"] for config.
"""

from muniweb_scraper import (
    MUNIWEB_CONFIGS,
    determine_meeting_type,
    get_issue_tags,
    parse_listing_page,
    scrape_city,
    _parse_date_text,
    _parse_generic_format,
    DATE_PATTERNS,
    ENV_BODIES,
)

from scraper_utils import print_result

# Re-export for backward compatibility with tests
BOARD_CONFIGS = MUNIWEB_CONFIGS["novi"]["boards"]
DEFAULT_TAGS = MUNIWEB_CONFIGS["novi"]["default_tags"]
BASE_URL = MUNIWEB_CONFIGS["novi"]["base_url"]


async def main():
    return await scrape_city("novi")


if __name__ == "__main__":
    import asyncio
    try:
        asyncio.run(main())
    except Exception as e:
        print_result("novi", "error", error=str(e))
        raise
