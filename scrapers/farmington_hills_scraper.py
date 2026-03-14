"""
Farmington Hills Meeting Scraper — thin wrapper around shared MuniWeb scraper.
See muniweb_scraper.py for implementation and MUNIWEB_CONFIGS["farmington_hills"] for config.
"""

from muniweb_scraper import scrape_city
from scraper_utils import print_result


async def main():
    return await scrape_city("farmington_hills")


if __name__ == "__main__":
    import asyncio
    try:
        asyncio.run(main())
    except Exception as e:
        print_result("farmington_hills", "error", error=str(e))
        raise
