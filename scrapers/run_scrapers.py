"""
Meeting Scraper Runner — Registry-Driven
Reads registry.yaml, dynamically imports scrapers, runs them in dependency order.

Usage:
    python run_scrapers.py                  # Run all enabled scrapers
    python run_scrapers.py mpsc             # Run only MPSC
    python run_scrapers.py detroit egle     # Run multiple scrapers
    python run_scrapers.py --list           # Show all registered scrapers
"""

import asyncio
import importlib
import json
import sys
import os
from datetime import datetime

import yaml
from dotenv import load_dotenv

load_dotenv()

REGISTRY_PATH = os.path.join(os.path.dirname(__file__), "registry.yaml")


def load_registry():
    """Load scraper definitions from registry.yaml."""
    with open(REGISTRY_PATH) as f:
        data = yaml.safe_load(f)
    return data["scrapers"]


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

        # Get unique source+source_id combinations count (paginated)
        all_meetings_data = []
        offset = 0
        page_size = 1000
        while True:
            page = supabase.table("meetings").select("source,source_id").range(offset, offset + page_size - 1).execute()
            batch = page.data or []
            all_meetings_data.extend(batch)
            if len(batch) < page_size:
                break
            offset += page_size

        unique_combos = set()
        for m in all_meetings_data:
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


def resolve_run_order(registry, requested_keys=None):
    """Return scraper keys in dependency-safe order.

    If requested_keys is None, runs all enabled scrapers.
    If requested_keys is provided, includes those plus any dependencies they need.
    """
    if requested_keys is None:
        keys = [k for k, v in registry.items() if v.get("enabled", True)]
    else:
        # Include requested scrapers plus their dependencies
        keys = set()
        to_process = list(requested_keys)
        while to_process:
            k = to_process.pop()
            if k in keys:
                continue
            if k not in registry:
                print(f"Unknown scraper: {k}")
                continue
            keys.add(k)
            for dep in registry[k].get("depends_on", []):
                if dep not in keys:
                    to_process.append(dep)
        keys = list(keys)

    # Topological sort: scrapers with no deps first, then dependents
    ordered = []
    remaining = set(keys)
    while remaining:
        # Find scrapers whose dependencies are all satisfied
        ready = [
            k for k in remaining
            if all(d in ordered or d not in remaining for d in registry[k].get("depends_on", []))
        ]
        if not ready:
            # Circular dependency — just add remaining in arbitrary order
            ordered.extend(sorted(remaining))
            break
        # Sort ready scrapers for deterministic order
        for k in sorted(ready):
            ordered.append(k)
            remaining.remove(k)

    return ordered


def show_registry(registry):
    """Print a table of all registered scrapers."""
    print(f"\n{'Key':<20} {'Name':<20} {'Platform':<22} {'Table':<18} {'Browser':<8} {'Depends On'}")
    print("-" * 105)
    for key, config in registry.items():
        deps = ", ".join(config.get("depends_on", [])) or "-"
        browser = "yes" if config["needs_browser"] else "no"
        platform = config.get("platform", "-")
        print(f"{key:<20} {config['name']:<20} {platform:<22} {config['table']:<18} {browser:<8} {deps}")
    print()


async def run_scraper(key, config):
    """Dynamically import and run a single scraper.

    Returns (key, results_list, error_string_or_None)
    """
    module_name = config["module"]
    name = config["name"]

    print(f"\n{'=' * 70}")
    print(f"Running: {name} ({key})")
    print("=" * 70)

    try:
        mod = importlib.import_module(module_name)
        config_key = config.get("config_key")
        if config_key:
            results = await mod.main(config_key)
        else:
            results = await mod.main()
        return key, results or [], None
    except Exception as e:
        print(f"ERROR running {name}: {e}")
        return key, [], str(e)


async def run_all_scrapers(registry, requested_keys=None):
    """Run scrapers in dependency order and collect results."""
    print("=" * 70)
    print(f"MEETING & COMMENT PERIOD SCRAPER - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # Pre-flight check
    print("\nChecking database setup...")
    if not ensure_unique_constraint():
        print("\n  WARNING: Duplicate records found, but continuing...")

    run_order = resolve_run_order(registry, requested_keys)
    if not run_order:
        print("No scrapers to run.")
        return {}, [], []

    print(f"\nRun order: {' -> '.join(run_order)}")

    results = {}
    errors = []

    for key in run_order:
        config = registry[key]
        key, items, error = await run_scraper(key, config)
        results[key] = items
        if error:
            errors.append(f"{config['name']}: {error}")

    # Run agenda summarizer (standalone mode — queries DB for unsummarized meetings)
    print(f"\n{'=' * 70}")
    print("AGENDA SUMMARIZATION")
    print("=" * 70)
    try:
        from agenda_summarizer import summarize_unsummarized_meetings
        summaries = summarize_unsummarized_meetings()
        results["agenda_summaries"] = summaries or []
    except Exception as e:
        print(f"ERROR running agenda summarizer: {e}")
        errors.append(f"Agenda Summarizer: {e}")
        results["agenda_summaries"] = []

    # Cleanup expired records
    print(f"\n{'=' * 70}")
    print("CLEANUP")
    print("=" * 70)
    try:
        from cleanup import expire_old_meetings, expire_old_comment_periods
        expired_meetings = expire_old_meetings()
        expired_comments = expire_old_comment_periods()
        if expired_meetings or expired_comments:
            print(f"  Expired {expired_meetings} meetings, {expired_comments} comment periods")
        else:
            print("  No expired records to clean up")
    except Exception as e:
        print(f"  Cleanup error (non-fatal): {e}")

    # Summary table
    print(f"\n{'=' * 70}")
    print("SUMMARY")
    print("=" * 70)

    total = 0
    warnings = []
    # These sources returning 0 is expected and shouldn't warn
    no_warn_keys = {"escribe_agenda", "agenda_summaries", "federal_register"}

    for key, items in results.items():
        count = len(items) if items else 0
        total += count
        status_icon = "OK" if count > 0 else "WARN"

        # Determine label based on table
        if key in registry:
            table = registry[key]["table"]
        elif key == "agenda_summaries":
            table = "agenda_summaries"
        else:
            table = "items"

        print(f"  {key.upper()}: {count} {table} [{status_icon}]")

        # Warn if a core scraper returned 0 and didn't error
        error_keys = {e.split(":")[0].strip().lower() for e in errors}
        if count == 0 and key not in no_warn_keys and key not in error_keys:
            warnings.append(f"{key.upper()}: returned 0 items (site may have changed or scraper may be broken)")

    print(f"\n  TOTAL: {total} items")

    if warnings:
        print(f"\n  WARNINGS: {len(warnings)}")
        for warning in warnings:
            print(f"    - {warning}")

    if errors:
        print(f"\n  ERRORS: {len(errors)}")
        for error in errors:
            print(f"    - {error}")

    # Machine-readable summary line
    from scraper_utils import print_result
    overall_status = "error" if errors else "ok"
    print_result("all", overall_status, total, "all")

    status_label = "COMPLETE WITH ISSUES" if (errors or warnings) else "COMPLETE"
    print(f"\n{'=' * 70}")
    print(status_label)
    print("=" * 70)

    return results, errors, warnings


if __name__ == "__main__":
    registry = load_registry()

    if "--list" in sys.argv:
        show_registry(registry)
        sys.exit(0)

    # Collect scraper names from args (skip --flags)
    requested = [arg for arg in sys.argv[1:] if not arg.startswith("--")]

    if not requested or requested == ["all"]:
        # Run all enabled scrapers
        asyncio.run(run_all_scrapers(registry))
    else:
        # Run only the specified scrapers (plus their dependencies)
        asyncio.run(run_all_scrapers(registry, requested_keys=requested))
