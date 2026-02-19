# Ask Planet Detroit — Maintenance Guide

**Last Updated:** February 19, 2026

---

## What This Tool Does

Ask Planet Detroit is the backend API that powers Planet Detroit's civic engagement tools. It provides:

- **Semantic search** across 1,955 Planet Detroit articles (12,041 text chunks) — readers ask questions, Claude synthesizes answers from relevant articles
- **Public meetings** scraped daily from MPSC, GLWA, Detroit City Council, and EGLE
- **Comment periods** from EGLE environmental proceedings
- **Organization directory** of 605+ Michigan environmental organizations
- **Elected officials** lookup by address
- **Article analysis** — Claude reads an article and identifies civic actions, related meetings, and relevant organizations

**Deployment:** Railway (https://ask-planet-detroit-production.up.railway.app/)
**Database:** Supabase (PostgreSQL + pgvector for embeddings)

---

## How to Tell If It's Working

1. **API health check:** Visit https://ask-planet-detroit-production.up.railway.app/ — should return JSON with `version` and `message`
2. **Meetings endpoint:** Visit `/api/meetings` — should return recent meetings with `count > 0`
3. **Scraper health:** Check GitHub Actions > "Daily Meeting Scraper" — look for green checkmarks and non-zero meeting counts
4. **Tests:** Run `cd ask-planet-detroit && python -m pytest -v` — all 74 tests should pass

---

## Running Locally

```bash
cd ask-planet-detroit

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r api/requirements.txt

# Create .env file with required variables (see below)

# Run the API
cd api && uvicorn main:app --reload --port 8000
```

### Required Environment Variables

| Variable | What It Is | Where to Get It |
|----------|-----------|-----------------|
| `SUPABASE_URL` | Supabase project URL | Supabase dashboard > Settings > API |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase service role key | Same location (NOT the anon key) |
| `OPENAI_API_KEY` | OpenAI API key | Used for text embeddings (search) |
| `ANTHROPIC_API_KEY` | Anthropic API key | Used for Claude answer synthesis and article analysis |
| `API_KEYS` | Comma-separated list of valid API keys | You generate these (see "API Authentication" below) |

---

## API Authentication

API key authentication protects the expensive AI endpoints (`/api/search` and `/api/analyze-article`) from unauthorized use. Public data endpoints (meetings, organizations, officials) remain open.

### How It Works

- Clients send `Authorization: Bearer <key>` header
- Keys are configured via the `API_KEYS` environment variable (comma-separated)
- If `API_KEYS` is not set, auth is disabled (allows local dev without keys)

### Activating in Production

1. **Generate API keys** — use any secure random string generator:
   ```bash
   python3 -c "import secrets; print(secrets.token_urlsafe(32))"
   ```
   Generate one key per client (e.g., one for civic-action-builder, one for newsletter-builder).

2. **Add to Railway:**
   - Go to Railway dashboard > ask-planet-detroit service > Variables
   - Add: `API_KEYS=key-for-civic-builder,key-for-newsletter`
   - Railway will auto-redeploy

3. **Add to Vercel (civic-action-builder):**
   - Go to Vercel dashboard > civic-action-builder > Settings > Environment Variables
   - Add: `VITE_API_KEY=key-for-civic-builder`
   - Redeploy

4. **Add to Vercel (newsletter-builder):** Only needed if newsletter-builder calls the search/analyze endpoints directly.

---

## Scrapers

Four scrapers run daily at 6 AM EST via GitHub Actions:

| Scraper | Source | Method |
|---------|--------|--------|
| MPSC | michigan.gov | Playwright, LD+JSON structured data |
| GLWA | glwater.legistar.com | Playwright, Legistar RadGrid |
| Detroit | detroitmi.gov (eSCRIBE) | Playwright + calendar API |
| EGLE | michigan.gov (Trumba RSS) | HTTP requests (no browser) |

### If a scraper breaks:

1. Check GitHub Actions > "Daily Meeting Scraper" for error logs
2. Look for `[WARN]` flags — means a scraper returned 0 meetings (likely the target website changed)
3. Visit the source website manually to see if the page structure changed
4. Common fix: update CSS selectors or API endpoints in the scraper file
5. Run the scraper locally to test: `cd scrapers && python run_scrapers.py mpsc`

### Scraper files:
- `scrapers/mpsc_scraper.py`
- `scrapers/glwa_scraper.py`
- `scrapers/detroit_scraper.py`
- `scrapers/egle_scraper.py` (meetings + comment periods)
- `scrapers/egle_mienviro_scraper.py` (MiEnviro permits)
- `scrapers/run_scrapers.py` (orchestrator)

---

## Tests

74 automated tests in two files:

- `api/tests/test_api.py` — 40 tests covering all API endpoints, input validation, CORS, and auth
- `scrapers/tests/test_scrapers.py` — 34 tests covering scraper parsing logic

```bash
# Run all tests
cd ask-planet-detroit
source venv/bin/activate
python -m pytest -v

# Run just API tests
python -m pytest api/tests/ -v

# Run just scraper tests
python -m pytest scrapers/tests/ -v
```

Tests run automatically on every push via GitHub Actions (`.github/workflows/ci.yml`).

---

## Common Problems

### "Railway deployment isn't picking up changes"
Railway auto-deploys from the `main` branch. If you pushed but don't see changes:
- Check Railway dashboard for build logs
- Make sure you pushed to `main` (not a feature branch)
- Railway sometimes needs a manual redeploy: Dashboard > Service > Redeploy

### "Search returns no results"
- Check that `OPENAI_API_KEY` is set (embeddings require OpenAI)
- Check that `ANTHROPIC_API_KEY` is set (answer synthesis requires Claude)
- Check Supabase has data: run the `/api/stats` endpoint

### "Meetings list is empty"
- Check if scrapers ran today (GitHub Actions)
- Check Supabase `meetings` table directly
- A scraper might be broken — see "If a scraper breaks" above

### "Rate limit exceeded"
- Search: 30 requests/minute per IP
- Article analysis: 10 requests/minute per IP
- If hitting limits legitimately, adjust in `main.py` (the `@limiter.limit()` decorators)

---

## Dependencies

| Service | Purpose | Cost |
|---------|---------|------|
| **Supabase** | Database (PostgreSQL + pgvector) | Free tier |
| **Railway** | API hosting | ~$5/month |
| **OpenAI** | Text embeddings for search | Pay-per-use |
| **Anthropic** | Claude for answer synthesis + article analysis | Pay-per-use |
| **GitHub Actions** | Scraper scheduling + CI | Free for public repos |
