# Meeting Scrapers

Automated scrapers for Michigan public meeting data.

## Scrapers Status

| Agency | Full Name | Platform | Status |
|--------|-----------|----------|--------|
| **MPSC** | Michigan Public Service Commission | michigan.gov | ✅ Working |
| **GLWA** | Great Lakes Water Authority | Legistar | ✅ Working |
| **Detroit** | Detroit City Council | Legistar | ✅ Working |
| **EGLE** | Dept. of Environment, Great Lakes, and Energy | MiEnviro Portal | 🔄 Pending |

## Setup

### 1. Install Dependencies

```bash
cd scrapers
pip install -r requirements.txt
playwright install chromium
```

### 2. Set Environment Variables

Create a `.env` file or set these variables:

```bash
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-key-here
```

## Usage

### Run All Scrapers

```bash
python run_scrapers.py
```

### Run Specific Scraper

```bash
python run_scrapers.py mpsc
python run_scrapers.py glwa
python run_scrapers.py detroit
```

### Run Individual Scraper Directly

```bash
python mpsc_scraper.py
python glwa_scraper.py
python detroit_scraper.py
```

## Expected Results

| Scraper | Typical Meeting Count | Notes |
|---------|----------------------|-------|
| MPSC | 1-2 | 1st & 3rd Thursdays |
| GLWA | 50-70 | Board + committees |
| Detroit | 20-50 | City Council + committees |

## GitHub Actions

The `daily-meetings-sync.yml` workflow:
- Runs daily at 6 AM EST
- Can be triggered manually from GitHub Actions tab
- Sends Slack notifications (if webhook configured)

### Setup GitHub Actions

1. Copy `daily-meetings-sync.yml` to `.github/workflows/`
2. Add secrets in GitHub repo settings:
   - `SUPABASE_URL`
   - `SUPABASE_SERVICE_ROLE_KEY`
   - `SLACK_WEBHOOK_URL` (optional)

## Database Schema

Meetings are stored in the `meetings` table with these key fields:

| Field | Description |
|-------|-------------|
| `source` | Scraper identifier (e.g., "mpsc_scraper") |
| `source_id` | Unique ID from source (prevents duplicates) |
| `agency` | Agency name (MPSC, GLWA, City of Detroit) |
| `title` | Meeting title |
| `start_datetime` | Meeting start time (with timezone) |
| `latitude` / `longitude` | Geocoded location |
| `issue_tags` | Array of relevant topics |
| `status` | "upcoming", "past", "cancelled" |

### Required: Unique Constraint

**IMPORTANT:** The `meetings` table MUST have a unique constraint on `(source, source_id)` to prevent duplicates when scrapers run multiple times.

```sql
-- Run this ONCE in Supabase SQL Editor:
ALTER TABLE meetings 
ADD CONSTRAINT meetings_source_source_id_key 
UNIQUE (source, source_id);
```

The scraper will check for duplicates before running and warn you if this constraint is missing.

## Scraper Details

### MPSC Scraper
- **Strategy**: Date-based (generates expected 1st/3rd Thursday dates)
- **Location**: MPSC HQ, Lansing (42.7325, -84.6358)
- **Issue Tags**: dte_energy, utilities, energy_policy

### GLWA Scraper
- **Strategy**: Legistar calendar scraping
- **Location**: Water Board Building, Detroit (42.3350, -83.0456)
- **Issue Tags**: drinking_water, water_quality, infrastructure

### Detroit Scraper
- **Strategy**: Legistar calendar scraping
- **Location**: Coleman A. Young Municipal Center (42.3293, -83.0448)
- **Issue Tags**: local_government, varies by committee

### EGLE Scraper (Pending)
- **Challenge**: Uses MiEnviro Portal (JavaScript SPA)
- **Approach**: May need direct API access or Playwright with network interception
- **Target URL**: https://mienviro.michigan.gov/ncore/external/publicnotice/search

## Adding New Scrapers

1. Create a new file: `{agency}_scraper.py`
2. Follow the pattern from existing scrapers:
   - `async def scrape_{agency}_meetings()` - Main scrape function
   - `def upsert_meetings(meetings)` - Database insert
   - `async def main()` - Entry point
3. Add to `run_scrapers.py`:
   - Import the scraper
   - Add to `run_all_scrapers()` and `scrapers` dict
4. Test locally before pushing

## Troubleshooting

### "No meetings found"

Michigan.gov sites can be slow or use dynamic loading. Try:
- Increasing `wait_for_selector` timeout
- Adding explicit `asyncio.sleep()` delays
- Checking if the page structure changed

### Playwright Issues

```bash
# Reinstall browsers
playwright install chromium

# Install system dependencies (Linux)
playwright install-deps chromium
```

### Database Errors

- Check Supabase credentials
- Verify the `meetings` table exists
- Check for constraint violations (duplicate source_id)

### Duplicate Records

If you see more records than expected, the unique constraint is missing:

```sql
-- 1. Check for duplicates:
SELECT source, source_id, COUNT(*) 
FROM meetings 
GROUP BY source, source_id 
HAVING COUNT(*) > 1;

-- 2. Delete duplicates (keeps newest):
DELETE FROM meetings WHERE id IN (
  SELECT id FROM (
    SELECT id, ROW_NUMBER() OVER (
      PARTITION BY source, source_id ORDER BY created_at DESC
    ) as rn FROM meetings
  ) t WHERE rn > 1
);

-- 3. Add the unique constraint:
ALTER TABLE meetings 
ADD CONSTRAINT meetings_source_source_id_key 
UNIQUE (source, source_id);
```

## Future Scrapers to Add

- [ ] EGLE MiEnviro Portal (public notices)
- [ ] Wayne County Commission
- [ ] Oakland County Board
- [ ] Macomb County Board
- [ ] Detroit Planning Commission
- [ ] Detroit Documenters API (if available)
