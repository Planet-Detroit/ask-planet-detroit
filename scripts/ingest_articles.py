"""
Planet Detroit Article Ingestion Script

Fetches articles from WordPress, chunks them, generates embeddings,
and stores them in Supabase for RAG retrieval.

Usage:
    python scripts/ingest_articles.py --full          # Import all articles
    python scripts/ingest_articles.py --incremental   # Only new/updated since last run
    python scripts/ingest_articles.py --full --dry-run  # Test without saving
"""

import os
import sys
import json
import argparse
from datetime import datetime, timezone
from pathlib import Path

import httpx
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from openai import OpenAI
from supabase import create_client, Client

# Load environment variables
load_dotenv()

# Configuration
WORDPRESS_BASE_URL = "https://planetdetroit.org/wp-json/wp/v2"
POSTS_PER_PAGE = 100
CHUNK_SIZE = 1500  # characters per chunk
CHUNK_OVERLAP = 200  # overlap between chunks

# HTTP headers to avoid 403 errors
HTTP_HEADERS = {
    "User-Agent": "AskPlanetDetroit/1.0 (https://planetdetroit.org)"
}

# Issue mapping - maps WordPress category/tag slugs to our 4 PRIORITY issue tags
# These are highlighted/filterable, but we now also capture ALL other topics
ISSUE_MAPPING = {
    # Data Centers (category)
    "michigan-data-centers": "data_centers",
    
    # DTE Energy (tags)
    "dte": "dte_energy",
    "dte-energy": "dte_energy",
    
    # Air Quality (tags)
    "michigan-air-quality": "air_quality",
    "air-quality": "air_quality",
    "air-pollution": "air_quality",
    
    # Drinking Water (tags)
    "drinking-water": "drinking_water",
    "water-quality": "drinking_water",
    "water-infrastructure": "drinking_water",
    "water": "drinking_water",
}

# State file for tracking last sync
STATE_FILE = Path(__file__).parent.parent / "data" / "sync_state.json"


def get_supabase_client() -> Client:
    """Initialize Supabase client."""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise ValueError("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY")
    return create_client(url, key)


def get_openai_client() -> OpenAI:
    """Initialize OpenAI client."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("Missing OPENAI_API_KEY")
    return OpenAI(api_key=api_key)


def fetch_taxonomy_mapping(taxonomy: str) -> dict:
    """
    Fetch WordPress taxonomy (categories or tags) and return id -> slug mapping.
    
    Args:
        taxonomy: Either 'categories' or 'tags'
    """
    mapping = {}
    page = 1
    while True:
        response = httpx.get(
            f"{WORDPRESS_BASE_URL}/{taxonomy}",
            params={"per_page": 100, "page": page},
            headers=HTTP_HEADERS,
            timeout=30
        )
        if response.status_code != 200:
            break
        data = response.json()
        if not data:
            break
        for item in data:
            mapping[item["id"]] = item["slug"]
        page += 1
    return mapping


def fetch_articles(since: datetime = None) -> list:
    """
    Fetch articles from WordPress REST API.
    
    Args:
        since: If provided, only fetch articles modified after this datetime
    """
    articles = []
    page = 1
    
    # Fetch both categories and tags mappings
    print("Fetching WordPress taxonomies...")
    categories = fetch_taxonomy_mapping("categories")
    tags = fetch_taxonomy_mapping("tags")
    print(f"  Found {len(categories)} categories and {len(tags)} tags")
    
    print(f"Fetching articles from WordPress...")
    if since:
        print(f"  Only articles modified after: {since.isoformat()}")
    
    while True:
        params = {
            "per_page": POSTS_PER_PAGE,
            "page": page,
            "status": "publish",
            "_fields": "id,date,modified,slug,title,content,excerpt,link,categories,tags"
        }
        
        if since:
            params["modified_after"] = since.isoformat()
        
        response = httpx.get(
            f"{WORDPRESS_BASE_URL}/posts",
            params=params,
            headers=HTTP_HEADERS,
            timeout=30
        )
        
        if response.status_code != 200:
            print(f"  Error fetching page {page}: {response.status_code}")
            break
            
        data = response.json()
        if not data:
            break
        
        for post in data:
            # Collect ALL category slugs
            article_categories = [
                categories.get(cat_id, "") 
                for cat_id in post.get("categories", [])
                if categories.get(cat_id)
            ]
            
            # Collect ALL tag slugs
            article_tags = [
                tags.get(tag_id, "")
                for tag_id in post.get("tags", [])
                if tags.get(tag_id)
            ]
            
            # Map to our 4 priority issues (for highlighting/filtering)
            issues = set()
            for slug in article_categories + article_tags:
                if slug in ISSUE_MAPPING:
                    issues.add(ISSUE_MAPPING[slug])
            
            # Combine all topics (categories + tags)
            all_topics = list(set(article_categories + article_tags))
            
            articles.append({
                "id": str(post["id"]),
                "title": post["title"]["rendered"],
                "content": post["content"]["rendered"],
                "excerpt": post["excerpt"]["rendered"],
                "url": post["link"],
                "date": post["date"],
                "modified": post["modified"],
                "issues": list(issues),  # Our 4 priority issues
                "categories": article_categories,  # All WP categories
                "tags": article_tags,  # All WP tags
                "all_topics": all_topics  # Combined for easy searching
            })
        
        print(f"  Fetched page {page} ({len(data)} articles)")
        page += 1
        
        # Check if there are more pages
        total_pages = int(response.headers.get("X-WP-TotalPages", 1))
        if page > total_pages:
            break
    
    print(f"  Total articles fetched: {len(articles)}")
    
    # Show better stats now that we have all topics
    issue_counts = {}
    for article in articles:
        for issue in article["issues"]:
            issue_counts[issue] = issue_counts.get(issue, 0) + 1
    
    if issue_counts:
        print(f"  Articles by priority issue: {issue_counts}")
    
    # Show most common topics (top 10)
    topic_counts = {}
    for article in articles:
        for topic in article["all_topics"]:
            topic_counts[topic] = topic_counts.get(topic, 0) + 1
    
    if topic_counts:
        top_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        print(f"  Top 10 topics: {dict(top_topics)}")
    
    return articles


def clean_html(html: str) -> str:
    """Strip HTML tags and clean up text."""
    soup = BeautifulSoup(html, "lxml")
    
    # Remove script and style elements
    for element in soup(["script", "style", "nav", "footer", "header"]):
        element.decompose()
    
    # Get text
    text = soup.get_text(separator=" ")
    
    # Clean up whitespace
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    text = " ".join(chunk for chunk in chunks if chunk)
    
    return text


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list:
    """
    Split text into overlapping chunks.
    
    Tries to break at sentence boundaries when possible.
    """
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        
        # If we're not at the end, try to find a good break point
        if end < len(text):
            # Look for sentence endings
            for sep in [". ", ".\n", "? ", "!\n", "\n\n"]:
                last_sep = text[start:end].rfind(sep)
                if last_sep != -1 and last_sep > chunk_size // 2:
                    end = start + last_sep + len(sep)
                    break
        
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        
        # Move start position, accounting for overlap
        start = end - overlap
    
    return chunks


def generate_embedding(client: OpenAI, text: str) -> list:
    """Generate embedding for text using OpenAI."""
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return response.data[0].embedding


def process_article(article: dict, openai_client: OpenAI) -> list:
    """
    Process a single article into embedded chunks.
    
    Returns list of chunk records ready for database insertion.
    """
    # Clean the content
    clean_content = clean_html(article["content"])
    
    # Skip if content is too short
    if len(clean_content) < 100:
        return []
    
    # Create chunks
    chunks = chunk_text(clean_content)
    
    # Prepare records
    records = []
    for i, chunk_text_content in enumerate(chunks):
        # Create context-rich chunk by prepending title
        enriched_text = f"Title: {article['title']}\n\n{chunk_text_content}"
        
        # Generate embedding
        embedding = generate_embedding(openai_client, enriched_text)
        
        records.append({
            "article_id": article["id"],
            "article_title": article["title"],
            "article_url": article["url"],
            "article_date": article["date"],
            "chunk_index": i,
            "content": chunk_text_content,
            "issues": article["issues"],
            "categories": article["categories"],
            "tags": article["tags"],
            "all_topics": article["all_topics"],
            "embedding": embedding
        })
    
    return records


def save_to_supabase(supabase: Client, records: list, article_id: str):
    """Save chunk records to Supabase, replacing any existing chunks for this article."""
    # Delete existing chunks for this article
    supabase.table("article_chunks").delete().eq("article_id", article_id).execute()
    
    # Insert new chunks
    if records:
        supabase.table("article_chunks").insert(records).execute()


def load_sync_state() -> dict:
    """Load the sync state from file."""
    if STATE_FILE.exists():
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {}


def save_sync_state(state: dict):
    """Save the sync state to file."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def main():
    parser = argparse.ArgumentParser(description="Ingest Planet Detroit articles")
    parser.add_argument(
        "--full",
        action="store_true",
        help="Full import of all articles"
    )
    parser.add_argument(
        "--incremental",
        action="store_true", 
        help="Only import articles modified since last sync"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and process but don't save to database"
    )
    args = parser.parse_args()
    
    if not args.full and not args.incremental:
        parser.error("Must specify either --full or --incremental")
    
    # Initialize clients
    print("Initializing clients...")
    supabase = get_supabase_client()
    openai_client = get_openai_client()
    
    # Determine date filter
    since = None
    if args.incremental:
        state = load_sync_state()
        if "last_sync" in state:
            since = datetime.fromisoformat(state["last_sync"])
        else:
            print("No previous sync found. Running full import instead.")
    
    # Record start time for next sync
    sync_start = datetime.now(timezone.utc)
    
    # Fetch articles
    articles = fetch_articles(since=since)
    
    if not articles:
        print("No articles to process.")
        return
    
    # Process each article
    total_chunks = 0
    errors = 0
    for i, article in enumerate(articles):
        print(f"Processing {i+1}/{len(articles)}: {article['title'][:60]}...")
        
        try:
            records = process_article(article, openai_client)
            total_chunks += len(records)
            
            if not args.dry_run and records:
                save_to_supabase(supabase, records, article["id"])
            
            if records:
                # Show issues if any, otherwise show top 3 topics
                if article['issues']:
                    print(f"  → {len(records)} chunks, issues: {article['issues']}")
                else:
                    topics_preview = article['all_topics'][:3]
                    if len(article['all_topics']) > 3:
                        topics_preview.append(f"... +{len(article['all_topics']) - 3} more")
                    print(f"  → {len(records)} chunks, topics: {topics_preview}")
                
        except Exception as e:
            print(f"  ✗ Error: {e}")
            errors += 1
            continue
    
    # Save sync state
    if not args.dry_run:
        save_sync_state({"last_sync": sync_start.isoformat()})
    
    print(f"\n{'DRY RUN ' if args.dry_run else ''}Complete!")
    print(f"  Processed: {len(articles)} articles → {total_chunks} chunks")
    print(f"  Errors: {errors}")


if __name__ == "__main__":
    main()