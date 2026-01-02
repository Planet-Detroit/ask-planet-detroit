"""
Meeting Scraper Runner
Runs all meeting scrapers and reports results

Usage:
    python run_scrapers.py           # Run all scrapers
    python run_scrapers.py mpsc      # Run only MPSC
    python run_scrapers.py glwa      # Run only GLWA
    python run_scrapers.py detroit   # Run only Detroit
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

# EGLE scraper is currently a placeholder - skip for now
# from egle_scraper import main as scrape_egle


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
            print("⚠️  Supabase credentials not found. Skipping duplicate check.")
            return True
        
        supabase = create_client(supabase_url, supabase_key)
        
        # Get total count
        total_result = supabase.table("meetings").select("id", count="exact").execute()
        total_count = total_result.count or 0
        
        # Get unique source+source_id combinations count
        # We'll fetch all and count unique combos (not ideal for huge tables but fine for <1000)
        all_meetings = supabase.table("meetings").select("source,source_id").execute()
        unique_combos = set()
        for m in all_meetings.data:
            if m.get('source') and m.get('source_id'):
                unique_combos.add((m['source'], m['source_id']))
        
        unique_count = len(unique_combos)
        
        if total_count > unique_count:
            duplicate_count = total_count - unique_count
            print(f"❌ ERROR: Found {duplicate_count} duplicate records in meetings table!")
            print(f"   Total records: {total_count}, Unique source+source_id: {unique_count}")
            print("")
            print("   The unique constraint is missing. Run this SQL in Supabase:")
            print("")
            print("   -- 1. Delete duplicates (keeps newest):")
            print("   DELETE FROM meetings WHERE id IN (")
            print("     SELECT id FROM (")
            print("       SELECT id, ROW_NUMBER() OVER (")
            print("         PARTITION BY source, source_id ORDER BY created_at DESC")
            print("       ) as rn FROM meetings")
            print("     ) t WHERE rn > 1")
            print("   );")
            print("")
            print("   -- 2. Add constraint to prevent future duplicates:")
            print("   ALTER TABLE meetings")
            print("   ADD CONSTRAINT meetings_source_source_id_key")
            print("   UNIQUE (source, source_id);")
            print("")
            return False
        
        print("✅ No duplicate records found")
        return True
        
    except ImportError:
        print("⚠️  Supabase package not installed. Skipping duplicate check.")
        return True
    except Exception as e:
        print(f"⚠️  Could not check for duplicates: {e}")
        return True


async def run_all_scrapers():
    """Run all meeting scrapers and collect results."""
    print("=" * 70)
    print(f"MEETING SCRAPER - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    # Check database setup before running
    print("\nChecking database setup...")
    if not ensure_unique_constraint():
        print("\n❌ Aborting: Fix database issues before running scrapers.")
        return {}, ["Database constraint missing"]
    
    results = {
        "mpsc": [],
        "glwa": [],
        "detroit": [],
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
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    total = 0
    for source, meetings in results.items():
        count = len(meetings) if meetings else 0
        total += count
        print(f"  {source.upper()}: {count} meetings")
    
    print(f"\n  TOTAL: {total} meetings")
    
    if errors:
        print(f"\n  ERRORS: {len(errors)}")
        for error in errors:
            print(f"    - {error}")
    
    print("\n" + "=" * 70)
    print("COMPLETE")
    print("=" * 70)
    
    return results, errors


async def run_single_scraper(scraper_name):
    """Run a single scraper by name."""
    scrapers = {
        "mpsc": scrape_mpsc,
        "glwa": scrape_glwa,
        "detroit": scrape_detroit,
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
    if not ensure_unique_constraint():
        print("\n❌ Aborting: Fix database issues before running scrapers.")
        return
    
    await scrapers[scraper_name.lower()]()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Run specific scraper
        scraper_name = sys.argv[1]
        asyncio.run(run_single_scraper(scraper_name))
    else:
        # Run all scrapers
        asyncio.run(run_all_scrapers())
