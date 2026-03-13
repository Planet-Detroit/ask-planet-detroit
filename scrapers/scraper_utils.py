"""
Shared utilities for all scrapers.

Provides structured output so run_scrapers.py and GitHub Actions can
reliably parse results without fragile regex on log text.
"""

import json


def print_result(scraper, status, count=0, table="meetings", error=None):
    """Print a machine-readable result line at the end of a scraper run.

    Format: RESULT:{"scraper":"mpsc","status":"ok","count":4,"table":"meetings"}

    Args:
        scraper: Short key for this scraper (e.g., "mpsc", "glwa")
        status: "ok" or "error"
        count: Number of records upserted
        table: Target table name
        error: Error message string (only when status="error")
    """
    result = {
        "scraper": scraper,
        "status": status,
        "count": count,
        "table": table,
    }
    if error:
        result["error"] = str(error)
    print(f"RESULT:{json.dumps(result)}")
