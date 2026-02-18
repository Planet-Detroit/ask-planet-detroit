"""
Import Michigan elected officials from OpenStates bulk CSV + committee YAMLs.

Data sources (CC0 license, no API key needed):
- CSV: https://data.openstates.org/people/current/mi.csv (~147 legislators)
- Committees: https://github.com/openstates/people/tree/main/data/mi/committees/

Usage:
    python scripts/import_officials.py             # Import to Supabase
    python scripts/import_officials.py --dry-run   # Preview without writing
"""

import os
import sys
import csv
import io
import json
import argparse
from datetime import datetime, timezone

import requests
import yaml
from dotenv import load_dotenv
from supabase import create_client

# Load .env from multiple locations (root and api/)
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
load_dotenv(os.path.join(project_root, ".env"))
load_dotenv(os.path.join(project_root, "api", ".env"))

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

CSV_URL = "https://data.openstates.org/people/current/mi.csv"
COMMITTEES_API_URL = "https://api.github.com/repos/openstates/people/contents/data/mi/committees"
COMMITTEES_RAW_BASE = "https://raw.githubusercontent.com/openstates/people/main/data/mi/committees/"


def get_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def create_table_if_needed(supabase):
    """Create the officials table via SQL if it doesn't exist."""
    sql = """
    CREATE TABLE IF NOT EXISTS officials (
        id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
        openstates_id text UNIQUE NOT NULL,
        name text NOT NULL,
        given_name text,
        family_name text,
        chamber text,
        current_district text,
        office text,
        party text,
        email text,
        capitol_voice text,
        capitol_address text,
        image text,
        twitter text,
        facebook text,
        instagram text,
        committees text[] DEFAULT '{}',
        committee_roles jsonb DEFAULT '[]',
        created_at timestamptz DEFAULT now(),
        updated_at timestamptz DEFAULT now()
    );
    """
    try:
        supabase.rpc("exec_sql", {"query": sql}).execute()
        print("Table 'officials' verified/created.")
    except Exception as e:
        # RPC may not exist — table likely already exists
        print(f"Note: Could not run CREATE TABLE via RPC ({e}). Table may already exist.")


def download_csv():
    """Download the OpenStates MI legislators CSV."""
    print(f"Downloading CSV from {CSV_URL}...")
    resp = requests.get(CSV_URL, timeout=30)
    resp.raise_for_status()
    reader = csv.DictReader(io.StringIO(resp.text))
    rows = list(reader)
    print(f"  Got {len(rows)} legislators")
    return rows


def fetch_committee_files():
    """Get list of committee YAML filenames from GitHub API."""
    print(f"Fetching committee file list...")
    resp = requests.get(COMMITTEES_API_URL, timeout=30)
    resp.raise_for_status()
    files = [f["name"] for f in resp.json() if f["name"].endswith(".yml")]
    print(f"  Found {len(files)} committee files")
    return files


def download_committee(filename):
    """Download and parse a single committee YAML file."""
    url = COMMITTEES_RAW_BASE + filename
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    return yaml.safe_load(resp.text)


def build_committee_map(committee_files):
    """Build a map of person_id -> list of {committee, role, chamber}."""
    person_committees = {}  # ocd-person/xxx -> [...]
    total = len(committee_files)

    for i, filename in enumerate(committee_files):
        try:
            data = download_committee(filename)
        except Exception as e:
            print(f"  Warning: failed to fetch {filename}: {e}")
            continue

        committee_name = data.get("name", "Unknown")
        chamber = data.get("chamber", "legislature")

        for member in data.get("members", []):
            person_id = member.get("person_id")
            if not person_id:
                continue
            role = member.get("role", "member")
            entry = {
                "committee": committee_name,
                "role": role,
                "chamber": chamber,
            }
            person_committees.setdefault(person_id, []).append(entry)

        if (i + 1) % 10 == 0 or i + 1 == total:
            print(f"  Processed {i+1}/{total} committee files")

    return person_committees


def normalize_name(name):
    """Normalize a name for fuzzy matching: lowercase, strip suffixes."""
    n = name.lower().strip()
    for suffix in [" jr.", " sr.", " iii", " ii", " iv"]:
        n = n.replace(suffix, "")
    return n.strip()


def build_officials(csv_rows, committee_map):
    """Join CSV rows with committee data to build official records."""
    officials = []

    # Build a name-based fallback lookup for committee matching
    name_to_person_id = {}
    for pid, entries in committee_map.items():
        # We don't have names directly in committee_map, but we'll match via CSV
        pass

    for row in csv_rows:
        person_id = row.get("id", "").strip()
        if not person_id:
            continue

        chamber = row.get("current_chamber", "").strip()
        office = "State Senator" if chamber == "upper" else "State Representative"

        # Look up committees by person_id
        memberships = committee_map.get(person_id, [])
        committees = list({m["committee"] for m in memberships})
        committee_roles = [
            {"committee": m["committee"], "role": m["role"]}
            for m in memberships
        ]

        official = {
            "openstates_id": person_id,
            "name": row.get("name", "").strip(),
            "given_name": row.get("given_name", "").strip() or None,
            "family_name": row.get("family_name", "").strip() or None,
            "chamber": chamber or None,
            "current_district": row.get("current_district", "").strip() or None,
            "office": office,
            "party": row.get("current_party", "").strip() or None,
            "email": row.get("email", "").strip() or None,
            "capitol_voice": row.get("capitol_voice", "").strip() or None,
            "capitol_address": row.get("capitol_address", "").strip() or None,
            "image": row.get("image", "").strip() or None,
            "twitter": row.get("twitter", "").strip() or None,
            "facebook": row.get("facebook", "").strip() or None,
            "instagram": row.get("instagram", "").strip() or None,
            "committees": committees,
            "committee_roles": committee_roles,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        officials.append(official)

    return officials


def upsert_officials(supabase, officials):
    """Upsert officials to Supabase."""
    success = 0
    errors = 0

    for official in officials:
        try:
            supabase.table("officials").upsert(
                official,
                on_conflict="openstates_id"
            ).execute()
            success += 1
        except Exception as e:
            print(f"  Error upserting {official['name']}: {e}")
            errors += 1

    return success, errors


def main():
    parser = argparse.ArgumentParser(description="Import MI elected officials from OpenStates")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing to database")
    args = parser.parse_args()

    if not args.dry_run and (not SUPABASE_URL or not SUPABASE_KEY):
        print("Error: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in .env")
        sys.exit(1)

    # Step 1: Download CSV
    csv_rows = download_csv()

    # Step 2: Fetch committee YAMLs
    committee_files = fetch_committee_files()
    committee_map = build_committee_map(committee_files)

    unique_people = len(set(committee_map.keys()))
    print(f"\nCommittee assignments: {unique_people} legislators across {len(committee_files)} committees")

    # Step 3: Join CSV + committees
    officials = build_officials(csv_rows, committee_map)

    with_committees = sum(1 for o in officials if o["committees"])
    print(f"\nBuilt {len(officials)} official records ({with_committees} with committee assignments)")

    if args.dry_run:
        print("\n--- DRY RUN (no database writes) ---")
        # Show sample records
        for o in officials[:5]:
            committees_str = ", ".join(o["committees"][:3]) if o["committees"] else "none"
            roles = [f"{r['committee']} ({r['role']})" for r in o["committee_roles"] if r["role"] != "member"]
            roles_str = "; ".join(roles) if roles else ""
            print(f"  {o['name']} ({o['party']}) — {o['office']}, District {o['current_district']}")
            print(f"    Committees: {committees_str}")
            if roles_str:
                print(f"    Leadership: {roles_str}")
            print(f"    Email: {o['email']}, Phone: {o['capitol_voice']}")
        if len(officials) > 5:
            print(f"  ... and {len(officials) - 5} more")

        # Chamber breakdown
        upper = sum(1 for o in officials if o["chamber"] == "upper")
        lower = sum(1 for o in officials if o["chamber"] == "lower")
        print(f"\n  Senate: {upper}, House: {lower}")
        print(f"  With committees: {with_committees}, Without: {len(officials) - with_committees}")
        return

    # Step 4: Upsert to Supabase
    supabase = get_supabase()
    create_table_if_needed(supabase)

    print(f"\nUpserting {len(officials)} officials to Supabase...")
    success, errors = upsert_officials(supabase, officials)
    print(f"\nDone! {success} upserted, {errors} errors")


if __name__ == "__main__":
    main()
