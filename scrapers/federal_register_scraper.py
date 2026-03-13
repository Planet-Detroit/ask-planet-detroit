"""
Federal Register Scraper
Fetches Michigan-relevant environmental comment periods from the Federal Register API.

Source: https://www.federalregister.gov/api/v1/documents
No authentication required.

Routes results to Supabase table:
  - comment_periods -> Open federal comment periods relevant to Michigan/Great Lakes
"""

import hashlib
import json
import os
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import httpx
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
MICHIGAN_TZ = ZoneInfo("America/Detroit")

FR_API = "https://www.federalregister.gov/api/v1/documents.json"

# Federal agencies relevant to environmental coverage
AGENCIES = [
    "environmental-protection-agency",
    "federal-energy-regulatory-commission",
    "nuclear-regulatory-commission",
    "engineers-corps",
    "fish-and-wildlife-service",
    "coast-guard",
]

# Keywords to filter for Michigan/Great Lakes relevance
MICHIGAN_KEYWORDS = [
    "Michigan",
    "Great Lakes",
    "Detroit",
    "Flint",
    "PFAS",
    "Lake Erie",
    "Lake Huron",
    "Lake Michigan",
    "Lake Superior",
    "Lake St. Clair",
    "Saginaw",
    "Kalamazoo",
    "Grand Rapids",
    "Ann Arbor",
    "Dearborn",
    "Enbridge",
    "Line 5",
    "DTE Energy",
    "Consumers Energy",
    "Palisades",
    "Fermi",
]

# Issue tag mapping based on agency
AGENCY_TAGS = {
    "environmental-protection-agency": ["environment", "epa"],
    "federal-energy-regulatory-commission": ["energy", "utilities"],
    "nuclear-regulatory-commission": ["energy", "nuclear"],
    "engineers-corps": ["infrastructure", "water_quality", "great_lakes"],
    "fish-and-wildlife-service": ["environment", "wildlife"],
    "coast-guard": ["great_lakes", "maritime"],
}

AI_MODEL = "claude-haiku-4-5-20251001"


def get_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def get_anthropic():
    import anthropic
    return anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def extract_issue_tags(title, abstract, agencies):
    """Extract issue tags from content and agency."""
    tags = set()

    # Agency-based tags
    for agency in agencies:
        slug = agency.get("slug", "")
        if slug in AGENCY_TAGS:
            tags.update(AGENCY_TAGS[slug])

    # Keyword-based tags
    text = f"{title} {abstract}".lower()
    keyword_map = {
        "pfas": ["pfas", "drinking_water"],
        "water quality": ["water_quality"],
        "drinking water": ["drinking_water"],
        "air quality": ["air_quality"],
        "clean air": ["air_quality"],
        "emissions": ["air_quality", "climate"],
        "climate": ["climate"],
        "pipeline": ["energy", "infrastructure"],
        "nuclear": ["energy", "nuclear"],
        "hazardous waste": ["waste", "pollution"],
        "superfund": ["pollution"],
        "great lakes": ["great_lakes"],
        "wetland": ["water_quality"],
    }
    for keyword, issue_tags in keyword_map.items():
        if keyword in text:
            tags.update(issue_tags)

    if not tags:
        tags.add("environment")

    return list(tags)


def is_michigan_relevant(doc):
    """Check if a Federal Register document is relevant to Michigan/Great Lakes."""
    text = f"{doc.get('title', '')} {doc.get('abstract', '')}".lower()
    return any(kw.lower() in text for kw in MICHIGAN_KEYWORDS)


def summarize_document(title, abstract):
    """Generate a plain-language summary of the comment period using Claude Haiku."""
    if not ANTHROPIC_API_KEY or not abstract:
        return None

    try:
        client = get_anthropic()
        response = client.messages.create(
            model=AI_MODEL,
            max_tokens=300,
            system="You are a local government reporter summarizing federal actions for Michigan residents. Write clear, jargon-free summaries.",
            messages=[{
                "role": "user",
                "content": f"""Summarize this federal action in 2-3 sentences for Michigan residents. Focus on why it matters locally.

Title: {title}
Abstract: {abstract[:4000]}

Return only the summary, no formatting."""
            }]
        )
        return response.content[0].text.strip()
    except Exception as e:
        print(f"    AI summary error: {e}")
        return None


def fetch_comment_periods():
    """Fetch open comment periods from the Federal Register API."""
    print("=" * 60)
    print("Federal Register Scraper")
    print("=" * 60)

    all_results = []

    # Strategy 1: Fetch by agency (environmental agencies)
    for agency_slug in AGENCIES:
        print(f"\n  Fetching: {agency_slug}")
        params = {
            "conditions[agencies][]": agency_slug,
            "conditions[type][]": ["NOTICE", "PROPOSED_RULE"],
            "conditions[comment_date][gte]": datetime.now().strftime("%m/%d/%Y"),
            "fields[]": [
                "title", "abstract", "document_number", "type",
                "publication_date", "html_url",
                "agencies", "comment_url", "comments_close_on",
            ],
            "per_page": 50,
            "order": "newest",
        }

        try:
            resp = httpx.get(FR_API, params=params, timeout=30)
            if resp.status_code != 200:
                print(f"    API error: {resp.status_code}")
                continue

            data = resp.json()
            docs = data.get("results", [])
            print(f"    Found {len(docs)} documents")

            # Filter for Michigan relevance
            relevant = [d for d in docs if is_michigan_relevant(d)]
            print(f"    {len(relevant)} Michigan-relevant")
            all_results.extend(relevant)

        except Exception as e:
            print(f"    Error: {e}")

        time.sleep(1)  # Rate limit: be polite to the API

    # Strategy 2: Search by Michigan keywords directly
    # These keywords are inherently Michigan-relevant, so we trust the API's
    # full-text search and skip our own relevance filter here.
    print(f"\n  Searching by keywords...")
    for keyword in ["Michigan environment", "Great Lakes", "PFAS", "Line 5"]:
        params = {
            "conditions[term]": keyword,
            "conditions[type][]": ["NOTICE", "PROPOSED_RULE"],
            "conditions[comment_date][gte]": datetime.now().strftime("%m/%d/%Y"),
            "fields[]": [
                "title", "abstract", "document_number", "type",
                "publication_date", "html_url",
                "agencies", "comment_url", "comments_close_on",
            ],
            "per_page": 25,
            "order": "newest",
        }

        try:
            resp = httpx.get(FR_API, params=params, timeout=30)
            if resp.status_code == 200:
                docs = resp.json().get("results", [])
                added = 0
                for doc in docs:
                    # Deduplicate by document_number
                    if not any(r.get("document_number") == doc.get("document_number") for r in all_results):
                        all_results.append(doc)
                        added += 1
                print(f"    '{keyword}': {len(docs)} docs, {added} new")
        except Exception as e:
            print(f"    Error searching '{keyword}': {e}")

        time.sleep(1)

    print(f"\n  Total unique Michigan-relevant documents: {len(all_results)}")
    return all_results


def build_comment_period(doc):
    """Convert a Federal Register document into a comment_periods table record."""
    title = doc.get("title", "Untitled")
    abstract = doc.get("abstract", "")
    doc_number = doc.get("document_number", "")
    comment_end = doc.get("comments_close_on")
    pub_date = doc.get("publication_date", "")
    html_url = doc.get("html_url", "")
    agencies = doc.get("agencies", [])

    # Agency name for display
    agency_names = [a.get("name", "") for a in agencies if a.get("name")]
    agency_display = agency_names[0] if agency_names else "Federal Government"

    # Stable source ID from document number
    source_id = f"fed-reg-{doc_number}" if doc_number else f"fed-reg-{hashlib.md5(title.encode()).hexdigest()[:12]}"

    # Parse dates
    end_date = comment_end or (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    start_date = pub_date or datetime.now().strftime("%Y-%m-%d")

    # Build description — use AI summary if available, else truncated abstract
    description = abstract[:500] if abstract else title

    issue_tags = extract_issue_tags(title, abstract, agencies)

    return {
        "title": title[:500],
        "description": description,
        "agency": agency_display[:100],
        "agency_full_name": agency_display,
        "comment_type": "federal_comment",
        "start_date": start_date,
        "end_date": end_date,
        "details_url": html_url,
        "documents_url": html_url,
        "comment_instructions": f"Submit comments at {html_url} or via regulations.gov",
        "comment_email": None,
        "issue_tags": issue_tags,
        "region": "federal",
        "source": "federal_register",
        "source_url": html_url,
        "source_id": source_id,
        "status": "open",
        "featured": False,
    }


def upsert_comment_periods(periods):
    """Upsert comment periods to Supabase."""
    if not periods:
        print("  No comment periods to upsert")
        return

    supabase = get_supabase()
    for period in periods:
        try:
            supabase.table("comment_periods").upsert(
                period,
                on_conflict="source,source_id"
            ).execute()
            print(f"  Upserted: {period['title'][:60]}")
        except Exception as e:
            print(f"  Error upserting: {e}")


async def main():
    """Main entry point."""
    docs = fetch_comment_periods()

    periods = []
    for doc in docs:
        period = build_comment_period(doc)
        periods.append(period)

    print(f"\nUpserting {len(periods)} comment periods...")
    upsert_comment_periods(periods)

    print(f"\nDone! {len(periods)} federal comment periods processed")
    return periods


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
