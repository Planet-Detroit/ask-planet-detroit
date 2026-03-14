# Scraper Sprint Log

**Started:** 2026-03-13
**Branch:** `feature/scraper-sprint`

---

## Phase 1: Detroit Pipeline — ALREADY COMPLETE

No work needed. The full pipeline exists:
- `scrapers/escribe_agenda_scraper.py` — scrapes eSCRIBE agendas, summarizes with Claude Haiku
- `api/migrations/agenda_summaries.sql` — table created
- `api/main.py` — 3 API endpoints serving summaries
- `run_scrapers.py` — wired into daily run
- `.github/workflows/daily-meetings-sync.yml` — runs daily, reports to Slack (if webhook configured)

## Phase 2: Extend Summarization to GLWA, EGLE, MPSC — IN PROGRESS

### What was built

**`scrapers/agenda_summarizer.py`** (new) — Generic agenda summarizer that works with any source:
- Fetches agenda content via HTTP (PDF or HTML)
- PDF extraction via `pdfplumber`
- HTML extraction via `BeautifulSoup` (strips nav, footer, scripts)
- Summarization via Claude Haiku (`claude-haiku-4-5-20251001`)
- Stores in `agenda_summaries` table with `source` + `source_meeting_id` unique constraint
- Skips meetings that already have summaries (avoids re-summarizing)
- Links summaries back to meetings table via `source_id` lookup

**`api/migrations/agenda_summaries_generic.sql`** (new) — Migration to generalize the agenda_summaries table:
- Adds `source` and `source_meeting_id` columns
- Backfills existing Detroit records
- Makes `escribemeetings_guid` nullable for non-Detroit sources
- Adds unique index on `(source, source_meeting_id)`

**`scrapers/mpsc_scraper.py`** (updated) — Added agenda URL extraction:
- Searches meeting detail pages for PDF links with "agenda" in text or href
- Falls back to any PDF link on the page
- Populates `agenda_url` field (was always null before)

**`scrapers/run_scrapers.py`** (updated) — Wires summarization into the pipeline:
- After all scrapers run, summarizes GLWA, EGLE, and MPSC meetings with agendas
- Reports summary counts in output

**`scrapers/requirements.txt`** (updated) — Added: `anthropic`, `pdfplumber`, `httpx`, `beautifulsoup4`

**`scrapers/test_agenda_summarizer.py`** (new) — 12 tests covering HTML extraction, PDF extraction, URL fetching

### What's working
- HTML text extraction with boilerplate stripping
- PDF text extraction via pdfplumber
- URL dispatch (detects PDF vs HTML by content-type and extension)
- Full pipeline integration in run_scrapers.py
- MPSC now captures agenda URLs from detail pages
- 12 new tests passing, 59 existing API tests still passing

### What's not yet tested end-to-end
- Need to run the migration on Supabase before the new upsert pattern works
- GLWA PDF agendas — need to verify pdfplumber handles Legistar PDFs
- EGLE mixed content — need to verify michigan.gov event page extraction
- MPSC agenda links — need to verify PDF links exist on current event pages

### Commits
- `cbf0271` — Add generic agenda summarizer for GLWA, EGLE, and MPSC
- `9a836d2` — Add agenda summarizer tests and sprint log

---

## Phase 3: Federal Register API — COMPLETE

### What was built

**`scrapers/federal_register_scraper.py`** (new) — Fetches open comment periods from federalregister.gov:
- Two search strategies: by agency (EPA, FERC, NRC, Army Corps, FWS, Coast Guard) and by keyword (Michigan, Great Lakes, PFAS, Line 5, DTE, etc.)
- Deduplicates results across strategies
- Extracts issue tags from agency + content keywords
- Stores in `comment_periods` table alongside EGLE comment periods
- AI summary of abstracts via Claude Haiku (optional, uses ANTHROPIC_API_KEY)
- Rate-limited (1s between API calls)
- No authentication required

**`scrapers/test_federal_register.py`** (new) — 13 tests covering relevance filtering, tag extraction, record building

### Commits
- `7f48b32` — Add Federal Register scraper for Michigan environmental comment periods

### Skipped: Regulations.gov
Requires API key (`REGULATIONS_GOV_API_KEY`). Overlaps significantly with Federal Register for comment period tracking. Can add later if needed for tracking individual comments on dockets.

---

## TODO: Remaining phases

### Phase 4: Local Bodies
- [ ] Wayne County Commission
- [ ] Detroit Planning Commission
- [ ] Detroit Board of Police Commissioners
- [ ] Oakland + Macomb County (CivicClerk)

### Phase 5: State Bodies
- [ ] MI Legislature Committee Hearings
- [ ] MI Natural Resources Commission (DNR)
- [ ] MI Council on Climate Solutions
