# Meeting & Comment Period Scrapers

**Last Updated:** 2026-03-13

Automated scrapers that collect public meeting data, comment period deadlines, and agenda summaries from government bodies at the local, state, and federal level. Data is stored in Supabase and served via the ask-planet-detroit API.

---

## Scraper Registry

### Active Scrapers

| Scraper | File | Agency | What It Collects | Method | Stores In |
|---------|------|--------|-----------------|--------|-----------|
| **Detroit** | `detroit_scraper.py` | Detroit City Council | Meetings (20-50), agendas | Playwright + eSCRIBE calendar API | `meetings` |
| **GLWA** | `glwa_scraper.py` | Great Lakes Water Authority | Meetings (50-70), agendas | Playwright + Legistar RadGrid | `meetings` |
| **EGLE** | `egle_scraper.py` | MI Dept. of Environment, Great Lakes, and Energy | Meetings + comment period deadlines | RSS/XML from Trumba (no browser) | `meetings` + `comment_periods` |
| **MPSC** | `mpsc_scraper.py` | MI Public Service Commission | Meetings (1-2), agendas | Playwright + LD+JSON structured data | `meetings` |
| **Detroit Agendas** | `escribe_agenda_scraper.py` | Detroit City Council | AI agenda summaries | Playwright + Claude Haiku | `agenda_summaries` |
| **Multi-Source Agendas** | `agenda_summarizer.py` | GLWA, EGLE, MPSC | AI agenda summaries (PDF + HTML) | httpx + pdfplumber + Claude Haiku | `agenda_summaries` |
| **Federal Register** | `federal_register_scraper.py` | EPA, FERC, NRC, Army Corps, FWS, Coast Guard | Federal comment periods (MI-relevant) | REST API (no auth) | `comment_periods` |

### Non-Functional

| Scraper | File | Notes |
|---------|------|-------|
| **MiEnviro** | `egle_mienviro_scraper.py` | EGLE public notice portal. JavaScript SPA that resists scraping. In debug mode. |

---

## How Each Scraper Works

### Detroit (`detroit_scraper.py`)

- **Source:** `pub-detroitmi.escribemeetings.com`
- **Method:** Playwright loads the eSCRIBE platform, then calls the internal calendar API (`/MeetingsCalendarView.aspx/GetCalendarMeetings`) via JavaScript `page.evaluate`. Also generates fallback schedule entries for known regular meetings (Tuesday Formal Session, Wednesday committees, etc.).
- **Agenda URLs:** Constructed from eSCRIBE GUIDs: `Meeting.aspx?Id={guid}&Agenda=Agenda&lang=English` (only for meetings where `HasAgenda=true`)
- **Unique ID:** `hashlib.md5` of committee name + date for schedule-generated meetings; eSCRIBE GUID for API-sourced meetings
- **Virtual Info:** All DCC meetings share Zoom ID `85846903626`
- **Issue Tags:** `local_government` + per-committee tags
- **Schedule:** Mon: Public Health & Safety 10AM. Tue: Formal Session 10AM. Wed: Internal Ops 10AM, Budget/Finance 1PM. Thu: Planning 10AM, Neighborhood 1PM.

### GLWA (`glwa_scraper.py`)

- **Source:** `glwater.legistar.com/Calendar.aspx`
- **Method:** Playwright renders the Telerik RadGrid table (`tr.rgRow / tr.rgAltRow`). Parses 13 cells per row: name (0), date (1), time (3), location (4), details link (5), agenda link (7).
- **Agenda URLs:** From Legistar cell 7 (when not "Not available"). Typically PDF files.
- **Virtual Info:** Scrapes detail pages for Zoom URLs, phone numbers, meeting IDs. Detail pages only available for recent/imminent meetings.
- **Unique ID:** `glwa-{YYYYMMDD}-{md5(title)[:12]}`
- **Issue Tags:** `drinking_water`, `water_quality`, `infrastructure`
- **Location:** Water Board Building, 735 Randolph St, Detroit

### EGLE (`egle_scraper.py`)

- **Source:** `trumba.com/calendars/deq-events.rss`
- **Method:** Fetches RSS/XML feed — no browser needed. Classifies items as meetings (hearings, workshops, webinars) or comment periods (deadlines) based on title keywords.
- **Dual routing:** Meetings → `meetings` table. Comment periods → `comment_periods` table.
- **Agenda URLs:** From Trumba `weblink` field (mixed HTML pages and PDFs on michigan.gov)
- **Comment period details:** Extracts facility name, SRN (permit number), start date, comment email, submission instructions.
- **Unique ID:** `egle-event-{trumba_event_id}` (meetings) or `egle-comment-{trumba_event_id}` (comment periods)
- **Issue Tags:** Keyword-mapped from title/description (air_quality, water_quality, pfas, climate, energy, etc.)
- **Region Detection:** Matches county names and city keywords to classify as detroit/southeast_michigan/statewide

### MPSC (`mpsc_scraper.py`)

- **Source:** `michigan.gov/mpsc/commission/events`
- **Method:** Playwright scrapes the events listing page for links, then visits each detail page to extract schema.org LD+JSON structured data. Also extracts Teams URLs, phone numbers, and conference IDs from page content.
- **Agenda URLs:** Searches detail pages for PDF links with "agenda" in the text or href (added in scraper sprint, March 2026).
- **Unique ID:** `mpsc-{YYYY-MM-DD}`
- **Issue Tags:** `energy`, `utilities`, `dte_energy`, `consumers_energy`, `rates`
- **Location:** MPSC HQ, 7109 W. Saginaw Hwy, Lansing
- **Schedule:** Commission meets 1st & 3rd Thursdays (1-2 meetings per scrape)

### Detroit Agenda Summarizer (`escribe_agenda_scraper.py`)

- **Source:** Same eSCRIBE platform as Detroit scraper
- **Method:** Finds meetings with agendas via the calendar API, then uses Playwright to scrape agenda item HTML from each meeting page. Three fallback patterns for different eSCRIBE markup. Filters out procedural items (roll call, adjournment, etc.). Sends substantive items to Claude Haiku for plain-language summarization.
- **AI Model:** `claude-haiku-4-5-20251001`
- **Output:** JSON with `summary` (2-3 sentences) and `key_topics` (lowercase tags like housing, water, zoning, budget, public_hearing)
- **Linking:** Matches summaries to meetings in the `meetings` table by name + date
- **Unique ID:** `escribemeetings_guid` (eSCRIBE meeting GUID)

### Generic Agenda Summarizer (`agenda_summarizer.py`)

- **Source:** Any meeting with an `agenda_url` (GLWA, EGLE, MPSC)
- **Method:** Fetches agenda content via HTTP. Detects format by content-type and URL extension. PDFs extracted with `pdfplumber`. HTML cleaned with `BeautifulSoup` (strips nav, footer, scripts, styles). Truncated to 8000 chars and sent to Claude Haiku.
- **AI Model:** `claude-haiku-4-5-20251001`
- **Skips:** Meetings that already have summaries (avoids re-processing and duplicate API costs)
- **Linking:** Looks up `meeting_id` in the `meetings` table by `source_id`
- **Unique ID:** `source` + `source_meeting_id` (e.g., `glwa_agenda` + `glwa-20260315-abc123`)

### Federal Register (`federal_register_scraper.py`)

- **Source:** `federalregister.gov/api/v1/documents.json`
- **Method:** REST API, no authentication. Two strategies:
  1. **By agency:** Queries 6 federal agencies (EPA, FERC, NRC, Army Corps, FWS, Coast Guard) for notices and proposed rules with open comment periods
  2. **By keyword:** Searches for "Michigan environment", "Great Lakes", "PFAS", "Line 5"
- **Relevance filter:** Only keeps documents mentioning Michigan-relevant keywords (Michigan, Great Lakes, Detroit, PFAS, Line 5, DTE, Consumers Energy, Palisades, Fermi, etc.)
- **Deduplication:** By `document_number` across both search strategies
- **Rate limiting:** 1 second between API calls
- **Unique ID:** `fed-reg-{document_number}`
- **Issue Tags:** Combined from agency mapping + content keyword matching

---

## Database Tables

### `meetings`

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `source` | text | Scraper identifier (e.g., `detroit_scraper`) |
| `source_id` | text | Unique ID from source system |
| `agency` | text | Agency name (e.g., `GLWA`, `EGLE`) |
| `title`, `description` | text | Meeting details |
| `start_datetime` | timestamptz | Meeting start |
| `meeting_date` | date | Date only |
| `meeting_time` | time | Time only |
| `location_name`, `location_address`, `location_city` | text | Physical location |
| `virtual_url`, `virtual_phone`, `virtual_meeting_id` | text | Virtual meeting info |
| `agenda_url`, `details_url` | text | Links to agenda and detail pages |
| `issue_tags` | text[] | Topic tags |
| `meeting_type` | text | e.g., `board_meeting`, `public_hearing` |
| `latitude`, `longitude` | float | Geocoded location |
| **Unique constraint:** `(source, source_id)` | | Prevents duplicates on re-scrape |

### `comment_periods`

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `source` | text | Scraper identifier |
| `source_id` | text | Unique ID from source |
| `agency` | text | Agency name |
| `title`, `description` | text | What the comment period is about |
| `comment_type` | text | e.g., `air_permit`, `federal_comment` |
| `start_date`, `end_date` | date | Comment window |
| `details_url`, `documents_url` | text | Links |
| `comment_instructions`, `comment_email` | text | How to submit |
| `facility_name`, `permit_number` | text | For permit-specific periods |
| `issue_tags` | text[] | Topic tags |
| **Unique constraint:** `(source, source_id)` | | |

### `agenda_summaries`

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `meeting_id` | UUID (FK) | Links to `meetings.id` |
| `source` | text | Summarizer identifier (e.g., `detroit_agenda`, `glwa_agenda`) |
| `source_meeting_id` | text | Matches source's meeting ID |
| `escribemeetings_guid` | text | eSCRIBE GUID (Detroit only) |
| `meeting_body` | text | e.g., `City Council Formal Session` |
| `meeting_date` | date | Meeting date |
| `summary` | text | AI-generated plain-language summary |
| `key_topics` | text[] | Extracted topic tags |
| `agenda_items` | jsonb | Raw scraped agenda items |
| `item_count` | int | Number of agenda items |
| `ai_model` | text | Model used for summarization |
| **Unique constraints:** `(escribemeetings_guid)` for Detroit, `(source, source_meeting_id)` for others | | |

---

## Running the Scrapers

### Setup

```bash
cd scrapers
pip install -r requirements.txt
playwright install chromium
```

Environment variables (in `.env` or set directly):
```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-key
ANTHROPIC_API_KEY=your-key          # Required for agenda summarization
```

### Run All

```bash
python run_scrapers.py
```

### Run Individual

```bash
python run_scrapers.py detroit
python run_scrapers.py glwa
python run_scrapers.py egle
python run_scrapers.py mpsc
python run_scrapers.py legistar_agenda
python run_scrapers.py federal_register
```

### Run Order (when running all)

1. MPSC, GLWA, Detroit, EGLE (meeting scrapers — parallel-safe)
2. Detroit agenda summarizer (needs Detroit meetings to exist for linking)
3. Generic agenda summarizer (GLWA, EGLE, MPSC — needs meetings to exist)
4. Federal Register (independent, no browser needed)

---

## GitHub Actions

**Workflow:** `.github/workflows/daily-meetings-sync.yml`
- **Schedule:** Daily at 6 AM EST (11:00 UTC)
- **Manual trigger:** Actions tab → Daily Meeting Scraper → Run workflow (can select individual scraper)
- **Slack notifications:** Sends results if `SLACK_WEBHOOK_URL` secret is configured

### Required GitHub Secrets

| Secret | Purpose |
|--------|---------|
| `SUPABASE_URL` | Database connection |
| `SUPABASE_SERVICE_ROLE_KEY` | Database auth |
| `ANTHROPIC_API_KEY` | AI agenda summarization |
| `SLACK_WEBHOOK_URL` | Slack notifications (optional) |

---

## API Endpoints

These endpoints serve scraped data. See `api/main.py` for full details.

| Endpoint | Returns |
|----------|---------|
| `GET /api/meetings` | Upcoming meetings (filterable by source, agency, date) |
| `GET /api/comment-periods` | Open comment periods |
| `GET /api/agenda-summaries` | AI-generated agenda summaries |
| `GET /api/agenda-summaries/{id}` | Single summary with raw items |
| `GET /api/meetings/{id}/agenda-summary` | Summary for a specific meeting |

---

## Tests

```bash
# Agenda summarizer tests (12 tests)
cd scrapers && python -m pytest test_agenda_summarizer.py -v

# Federal Register tests (13 tests)
cd scrapers && python -m pytest test_federal_register.py -v

# API tests (59 tests)
cd .. && python -m pytest api/tests/ -v
```

---

## Adding a New Scraper

1. Create `scrapers/{agency}_scraper.py` following existing patterns
2. Implement: `async def main()` → scrape → upsert to `meetings` or `comment_periods`
3. Use `source = "{agency}_scraper"` and stable `source_id` values
4. Add to `run_scrapers.py` (import + add to `run_all_scrapers` + `scrapers` dict)
5. Add to `.github/workflows/daily-meetings-sync.yml` options
6. Write tests
7. If agendas are available, wire into `agenda_summarizer.summarize_meetings()`

---

## Troubleshooting

| Problem | Likely Cause | Fix |
|---------|-------------|-----|
| "No meetings found" | Site structure changed or slow load | Check the source URL manually, increase timeouts |
| Playwright errors | Browser not installed | `playwright install chromium` |
| Duplicate records | Unique constraint missing | Run: `ALTER TABLE meetings ADD CONSTRAINT meetings_source_source_id_key UNIQUE (source, source_id);` |
| Agenda summaries empty | ANTHROPIC_API_KEY not set | Add to `.env` or GitHub secrets |
| Federal Register returns 0 | No current MI-relevant comment periods | Normal — check manually at federalregister.gov |
| Stale data | Scraper hasn't run | Check GitHub Actions run history |
