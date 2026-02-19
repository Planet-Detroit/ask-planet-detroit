"""
Meeting Scraper Runner
Runs all meeting scrapers and reports results

Usage:
    python run_scrapers.py           # Run all scrapers
    python run_scrapers.py mpsc      # Run only MPSC
    python run_scrapers.py glwa      # Run only GLWA
    python run_scrapers.py detroit   # Run only Detroit
    python run_scrapers.py egle      # Run only EGLE
    python run_scrapers.py all       # Run all scrapers
"""

import asyncio
import sys
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Import individual scrapers
from mpsc_scraper import main as scrape_mpsc
from glwa_scraper import main as scrape_glwa
from detroit_scraper import main as scrape_detroit
from egle_scraper import main as scrape_egle


def ensure_unique_constraint():
    """
    Check for duplicate records in the meetings table.
    If duplicates exist, the unique constraint is missing and we should warn.

    Returns True if safe to proceed, False if there's a problem.
    """
    try:
        from supabase import create_client

        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

        if not supabase_url or not supabase_key:
            print("  Supabase credentials not found. Skipping duplicate check.")
            return True

        supabase = create_client(supabase_url, supabase_key)

        # Get total count
        total_result = supabase.table("meetings").select("id", count="exact").execute()
        total_count = total_result.count or 0

        # Get unique source+source_id combinations count
        all_meetings = supabase.table("meetings").select("source,source_id").execute()
        unique_combos = set()
        for m in all_meetings.data:
            if m.get('source') and m.get('source_id'):
                unique_combos.add((m['source'], m['source_id']))

        unique_count = len(unique_combos)

        if total_count > unique_count:
            duplicate_count = total_count - unique_count
            print(f"  WARNING: Found {duplicate_count} duplicate records in meetings table")
            print(f"  Total: {total_count}, Unique: {unique_count}")
            return False

        print(f"  OK: {total_count} meetings, no duplicates")
        return True

    except ImportError:
        print("  Supabase package not installed. Skipping duplicate check.")
        return True
    except Exception as e:
        print(f"  Could not check for duplicates: {e}")
        return True


async def run_all_scrapers():
    """Run all meeting scrapers and collect results."""
    print("=" * 70)
    print(f"MEETING & COMMENT PERIOD SCRAPER - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # Check database setup before running
    print("\nChecking database setup...")
    if not ensure_unique_constraint():
        print("\n  WARNING: Duplicate records found, but continuing...")

    results = {
        "mpsc": [],
        "glwa": [],
        "detroit": [],
        "egle": [],
    }
    errors = []

    # Run MPSC scraper
    print("\n" + "=" * 70)
    try:
        results["mpsc"] = await scrape_mpsc()
    except Exception as e:
        print(f"ERROR running MPSC scraper: {e}")
        errors.append(f"MPSC: {e}")

    # Run GLWA scraper
    print("\n" + "=" * 70)
    try:
        results["glwa"] = await scrape_glwa()
    except Exception as e:
        print(f"ERROR running GLWA scraper: {e}")
        errors.append(f"GLWA: {e}")

    # Run Detroit scraper
    print("\n" + "=" * 70)
    try:
        results["detroit"] = await scrape_detroit()
    except Exception as e:
        print(f"ERROR running Detroit scraper: {e}")
        errors.append(f"Detroit: {e}")

    # Run EGLE scraper (also populates comment_periods table)
    print("\n" + "=" * 70)
    try:
        results["egle"] = await scrape_egle()
    except Exception as e:
        print(f"ERROR running EGLE scraper: {e}")
        errors.append(f"EGLE: {e}")

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    total = 0
    warnings = []
    for source, meetings in results.items():
        count = len(meetings) if meetings else 0
        total += count
        status_icon = "OK" if count > 0 else "WARN"
        print(f"  {source.upper()}: {count} meetings [{status_icon}]")
        if count == 0 and source not in [e.split(":")[0].strip().lower() for e in errors]:
            warnings.append(f"{source.upper()}: returned 0 meetings (site may have changed or scraper may be broken)")

    print(f"\n  TOTAL: {total} meetings")

    if warnings:
        print(f"\n  WARNINGS: {len(warnings)}")
        for warning in warnings:
            print(f"    ⚠ {warning}")

    if errors:
        print(f"\n  ERRORS: {len(errors)}")
        for error in errors:
            print(f"    ✗ {error}")

    # Exit with non-zero code if any scraper failed or returned 0 results
    # This lets GitHub Actions detect problems
    if errors or warnings:
        print("\n" + "=" * 70)
        print("COMPLETE WITH ISSUES")
        print("=" * 70)
        return results, errors, warnings

    print("\n" + "=" * 70)
    print("COMPLETE")
    print("=" * 70)

    return results, errors, []


async def run_single_scraper(scraper_name):
    """Run a single scraper by name."""
    scrapers = {
        "mpsc": scrape_mpsc,
        "glwa": scrape_glwa,
        "detroit": scrape_detroit,
        "egle": scrape_egle,
    }

    # Handle "all" option
    if scraper_name.lower() == "all":
        await run_all_scrapers()
        return

    if scraper_name.lower() not in scrapers:
        print(f"Unknown scraper: {scraper_name}")
        print(f"Available scrapers: {', '.join(scrapers.keys())}, all")
        return

    # Check database setup before running
    print("Checking database setup...")
    ensure_unique_constraint()

    await scrapers[scraper_name.lower()]()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Run specific scraper
        scraper_name = sys.argv[1]
        asyncio.run(run_single_scraper(scraper_name))
    else:
        # Run all scrapers
        asyncio.run(run_all_scrapers())
