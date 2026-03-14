"""Waterford Township meeting scraper — thin wrapper around CivicPlus AgendaCenter."""
from civicplus_agenda_scraper import scrape_city
from scraper_utils import print_result


async def main():
    return await scrape_city("waterford")


if __name__ == "__main__":
    import asyncio
    try:
        asyncio.run(main())
    except Exception as e:
        print_result("waterford", "error", error=str(e))
        raise
