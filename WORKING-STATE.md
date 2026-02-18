# Working State - Civic Action Builder

**Last Updated:** February 18, 2026
**Status:** MVP Complete

---

## What's Working

### Civic Action Builder Frontend
- **URL:** https://civic-action-builder.vercel.app/
- **Repo:** https://github.com/Planet-Detroit/civic-action-builder
- **Latest Commit:** `ead7d12` - "Replace hardcoded officials with database-backed search + AI ranking"
- **Features:**
  - Three-tab workflow (Input > Builder > Output)
  - Article URL input (fetches from WordPress API) or text paste
  - AI analysis via backend API
  - Detected issues display
  - AI-ranked meetings, comment periods, organizations, and elected officials
  - Editable civic actions (pre-populated with context-aware suggestions)
  - HTML preview and copy for WordPress

### Backend API
- **URL:** https://ask-planet-detroit-production.up.railway.app/
- **Repo:** https://github.com/Planet-Detroit/ask-planet-detroit
- **Latest Commit:** `f2c50a5` - "Generate context-aware civic actions from ranked meetings, comment periods, and officials"
- **Endpoints:**
  - `/api/search` - RAG search with Claude answer synthesis (1,955 articles, 12,041 chunks)
  - `/api/organizations` - List/search organizations (605 orgs)
  - `/api/meetings` - List upcoming meetings
  - `/api/comment-periods` - List open comment periods
  - `/api/officials` - List elected officials (147 MI legislators with committees)
  - `/api/analyze-article` - Full article analysis pipeline (see below)
  - `/api/civic` - Combined civic hub data
  - `/api/stats` - Database statistics

### Article Analysis Pipeline (`/api/analyze-article`)
1. **Sonnet** analyzes article > detected issues, entities, summary
2. **Haiku** ranks organizations (from 605 orgs) > top 5
3. **Haiku** ranks meetings (from upcoming meetings) > top 5
4. **Haiku** ranks comment periods (from open periods) > top 3
5. **Haiku** ranks officials (from 147 legislators) > top 3
6. **Haiku** generates context-aware civic actions using ranked data > 3-5 specific actions

### Meeting Scrapers (Daily via GitHub Actions)
- **MPSC** - Michigan Public Service Commission (Playwright, LD+JSON)
- **GLWA** - Great Lakes Water Authority (Playwright, Legistar)
- **Detroit** - Detroit City Council (Playwright, eSCRIBE calendar API)
- **EGLE** - MI Dept. of Environment, Great Lakes, and Energy (RSS/Trumba, dual-table routing to meetings + comment periods)

### Data in Supabase
- 1,955 articles > 12,041 searchable chunks
- 605 organizations (517 geocoded)
- 147 elected officials with committee assignments
- Meetings populated daily by 4 scrapers
- Comment periods populated by EGLE scraper
- Upserts on `source,source_id` conflict key

---

## MVP Sprint Completed

### High Priority - Done
- [x] Populate meetings table with real data (4 scrapers running daily)
- [x] Test `/api/analyze-article` endpoint thoroughly
- [x] Add comment periods (EGLE scraper populates automatically)
- [x] Verify Claude API key working in Railway

### Medium Priority - Done
- [x] Build elected officials database (147 legislators from OpenStates)
- [x] Add EGLE and Detroit City Council scrapers
- [x] Improve organization matching (AI-ranked with Haiku)
- [x] Context-aware civic actions (references specific meetings, deadlines, officials by name)

---

## Future / Post-MVP
- [ ] WordPress plugin integration
- [ ] Case docket alerts
- [ ] Meeting agenda AI summaries
- [ ] Additional scrapers (EPA Region 5, Wayne County, etc.)

---

## Important URLs

### Production
- Civic Action Builder: https://civic-action-builder.vercel.app/
- Backend API: https://ask-planet-detroit-production.up.railway.app/
- API Docs: https://ask-planet-detroit-production.up.railway.app/docs
- Org Directory: https://planet-detroit.github.io/michigan-environmental-orgs/

### GitHub Repos
- Backend API: https://github.com/Planet-Detroit/ask-planet-detroit
- Civic Action Builder: https://github.com/Planet-Detroit/civic-action-builder
- Org Directory: https://github.com/Planet-Detroit/michigan-environmental-orgs

---

## Environment Variables

### Backend (Railway)
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`

### Frontend (Vercel)
- `VITE_API_URL` = https://ask-planet-detroit-production.up.railway.app

---

## Emergency Recovery

If something breaks:

1. Check Railway/Vercel deployment logs for errors
2. Test locally before pushing (`uvicorn api.main:app --reload` / `npm run dev`)
3. Rollback if needed:

```bash
# Backend - rollback to last known good
cd ~/projects/ask-planet-detroit
git log --oneline -10  # find the commit to rollback to

# Frontend - rollback to last known good
cd ~/projects/civic-action-builder
git log --oneline -10  # find the commit to rollback to
```
