#!/usr/bin/env python3
"""
EGLE MiEnviro Portal Public Notice Scraper

Scrapes public notices and comment periods from:
https://mienviro.michigan.gov/ncore/external/publicnotice/search

This is a JavaScript SPA, so we use Playwright to render and extract data.
"""

import os
import json
import re
from datetime import datetime, timedelta
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

# MiEnviro Portal URL
MIENVIRO_URL = "https://mienviro.michigan.gov/ncore/external/publicnotice/search"

# EGLE headquarters coordinates (Lansing)
EGLE_LAT = 42.7335
EGLE_LNG = -84.5555


def scrape_mienviro_notices():
    """
    Scrape public notices from MiEnviro Portal using Playwright.
    Returns list of notice dictionaries.
    """
    notices = []
    
    print(f"Fetching MiEnviro Portal from {MIENVIRO_URL}")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        page = context.new_page()
        
        # Capture API responses
        api_data = []
        
        def handle_response(response):
            """Intercept API responses to find the data endpoint"""
            url = response.url
            if 'publicnotice' in url.lower() and response.status == 200:
                try:
                    content_type = response.headers.get('content-type', '')
                    if 'json' in content_type:
                        data = response.json()
                        api_data.append({'url': url, 'data': data})
                        print(f"  Captured API response from: {url[:80]}...")
                except Exception as e:
                    pass
        
        page.on("response", handle_response)
        
        try:
            # Navigate to the page
            page.goto(MIENVIRO_URL, wait_until="networkidle", timeout=60000)
            
            # Wait for the page to fully load
            print("  Waiting for page to render...")
            page.wait_for_timeout(5000)  # Give JavaScript time to load
            
            # Try to find and click any "search" or "load" buttons
            try:
                # Look for search button
                search_btn = page.locator("button:has-text('Search'), button:has-text('search'), .search-btn, [type='submit']").first
                if search_btn.is_visible():
                    print("  Clicking search button...")
                    search_btn.click()
                    page.wait_for_timeout(3000)
            except:
                pass
            
            # Wait for results to load
            page.wait_for_timeout(3000)
            
            # Debug: Print page content
            print("\n  Page title:", page.title())
            
            # Try to extract data from rendered HTML
            # Look for common table/list structures
            
            # Method 1: Look for table rows
            rows = page.locator("table tbody tr, .notice-row, .result-row, [class*='notice'], [class*='result']").all()
            print(f"  Found {len(rows)} potential notice rows")
            
            # Method 2: Check if we captured API data
            if api_data:
                print(f"\n  Captured {len(api_data)} API responses")
                for api_response in api_data:
                    print(f"    URL: {api_response['url'][:100]}")
                    data = api_response['data']
                    if isinstance(data, list):
                        print(f"    Contains {len(data)} items")
                        for item in data[:5]:  # Show first 5
                            print(f"      - {item}")
                    elif isinstance(data, dict):
                        print(f"    Keys: {list(data.keys())[:10]}")
            
            # Method 3: Try to find any visible text content with dates
            page_text = page.content()
            
            # Look for date patterns that might indicate notices
            date_pattern = r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b'
            dates_found = re.findall(date_pattern, page_text)
            print(f"  Found {len(dates_found)} date references in page")
            
            # Look for common notice-related text
            notice_keywords = ['public notice', 'comment period', 'hearing', 'permit', 'application']
            for keyword in notice_keywords:
                count = page_text.lower().count(keyword)
                if count > 0:
                    print(f"    '{keyword}': {count} occurrences")
            
            # Try to extract structured data from the page
            # This will need to be customized based on actual page structure
            
            # Look for any data tables
            tables = page.locator("table").all()
            print(f"\n  Found {len(tables)} tables on page")
            
            for i, table in enumerate(tables):
                try:
                    headers = table.locator("th").all_text_contents()
                    if headers:
                        print(f"    Table {i+1} headers: {headers}")
                        
                        # Get rows
                        rows = table.locator("tbody tr").all()
                        print(f"    Table {i+1} has {len(rows)} data rows")
                        
                        # Extract first few rows for debugging
                        for j, row in enumerate(rows[:3]):
                            cells = row.locator("td").all_text_contents()
                            print(f"      Row {j+1}: {cells[:5]}")  # First 5 cells
                except Exception as e:
                    print(f"    Error reading table {i+1}: {e}")
            
            # Try clicking on filters/dropdowns to see options
            try:
                dropdowns = page.locator("select, [class*='dropdown'], [class*='filter']").all()
                print(f"\n  Found {len(dropdowns)} dropdown/filter elements")
            except:
                pass
            
            # Take a screenshot for debugging
            screenshot_path = "/tmp/mienviro_debug.png"
            page.screenshot(path=screenshot_path, full_page=True)
            print(f"\n  Screenshot saved to: {screenshot_path}")
            
            # Get the full HTML for analysis
            html_path = "/tmp/mienviro_debug.html"
            with open(html_path, 'w') as f:
                f.write(page.content())
            print(f"  HTML saved to: {html_path}")
            
        except PlaywrightTimeout as e:
            print(f"  Timeout error: {e}")
        except Exception as e:
            print(f"  Error: {e}")
        finally:
            browser.close()
    
    return notices


def main():
    """Main entry point"""
    print("=" * 60)
    print("EGLE MiEnviro Portal Scraper")
    print("=" * 60)
    
    notices = scrape_mienviro_notices()
    
    print(f"\nFound {len(notices)} public notices")
    
    if notices:
        # Here we would upsert to database
        print("\nSample notices:")
        for notice in notices[:5]:
            print(f"  - {notice.get('title', 'Unknown')}")
    else:
        print("\nNo notices extracted yet.")
        print("Check the debug screenshot and HTML files to understand the page structure.")
        print("Then update the scraper to extract the correct elements.")


if __name__ == "__main__":
    main()
