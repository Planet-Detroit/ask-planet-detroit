# Scraper Roadmap — Metro Detroit Civic Data Coverage

**Last Updated:** 2026-03-14
**Coverage Area:** 7 SEMCOG counties (~240 municipalities)

---

## Legend

| Status | Meaning |
|--------|---------|
| LIVE | Scraper built, tested, and running in production |
| BUILT | Scraper built but not yet deployed via GitHub Actions |
| NEXT | High priority, ready to build |
| PLANNED | On the roadmap |
| RESEARCH | Needs investigation before building |
| DEFERRED | Investigated, not feasible or low ROI right now |

## Priority Scheme

We prioritize by **platform leverage x population coverage**:
- **P1:** Platform scraper covers 10+ municipalities or 500K+ population
- **P2:** Platform scraper covers 3-9 municipalities or 100K+ population
- **P3:** Individual high-population city (50K+) needing custom scraper
- **P4:** Smaller municipalities or low-structure platforms
- **P5:** Very small municipalities (<10K) or unstructured sources

---

## Current Coverage Summary

| Metric | Count |
|--------|-------|
| **Scrapers live** | 28 |
| **Platforms built** | 9 (CivicClerk, Legistar HTML, Legistar API, eSCRIBE browser, eSCRIBE API, Granicus, Trumba, Federal Register API, MI Legislature RSS) |
| **Meetings in DB** | ~450+ |
| **Sources** | State agencies (3), regional bodies (3), counties (4), municipalities (17), federal (1) |
| **Tests** | 274 passing |

---

## Platform Strategy

Building one scraper per platform maximizes coverage. This is the priority order:

| Priority | Platform | Scraper Status | Bodies Covered | Est. Population |
|----------|----------|---------------|----------------|-----------------|
| **P1** | CivicClerk | **LIVE** | 16 municipalities + 3 counties + 1 outlying county | ~1.5M |
| **P1** | Legistar API | **LIVE** | Ann Arbor, DWSD | ~125K + regional |
| **P1** | MI Legislature RSS/ICS | **LIVE** | All House/Senate committees | Statewide |
| **P2** | eSCRIBE | LIVE (Detroit only) | Royal Oak next | ~60K additional |
| **P2** | BoardDocs | DEFERRED | DPSCD, Dearborn Schools | ~650K (schools) |
| **P2** | CivicEngage Agenda Center | DEFERRED | 15+ municipalities | ~500K |
| **P2** | Documents-On-Demand | DEFERRED | 10+ municipalities | ~300K |
| **P4** | Granicus | RESEARCH | Southgate, Ferndale | ~50K |

### Platform Notes (from investigation)

- **Legistar API**: Rochester Hills API broken on their end (DB login error). Ann Arbor works great. DWSD works but posts meetings close to date.
- **BoardDocs**: Lotus Domino backend requires browser session. Needs Playwright. DPSCD is the high-value target.
- **CivicEngage**: Has RSS feeds but they're document-publication feeds (no meeting times/locations). Would only get agenda PDFs. Lower value than expected.
- **Documents-On-Demand**: No API, needs browser + FancyTree navigation. No meeting metadata in UI (times, locations, virtual links all in PDFs). High effort, lower value.
- **Granicus**: Ferndale uses it for video archives only. Blocks non-browser access (403). Southgate unconfirmed.
- **Ferndale**: Meetings are in a static PDF calendar. Could generate from schedule template instead of scraping. Very low ROI for custom scraper.

---

## Health Monitoring

| Component | Status | Frequency |
|-----------|--------|-----------|
| Per-run RESULT status | **LIVE** | Every scraper run (daily) |
| Weekly health digest | **LIVE** | Monday 9 AM EST (Slack + GitHub Actions) |
| DOM canary checks | PLANNED | Per-run for HTML scrapers |
| Monthly coverage audit | PLANNED | Manual review of weekly digests |

---

## State Agencies

| Source | Platform | Priority | Status | Notes |
|--------|----------|----------|--------|-------|
| MPSC | michigan.gov | — | **LIVE** | LD+JSON structured data, Teams URLs |
| EGLE (meetings + comment periods) | Trumba RSS | — | **LIVE** | Dual-table routing |
| MI Legislature Committees | legislature.mi.gov | P3 | **LIVE** | RSS feed + .ics enrichment. 21 meetings. Room locations, clerk phones, bill numbers. |
| EGLE Permit Notices | Trumba RSS | P2 | PLANNED | Extend existing EGLE scraper |
| Governor's Office | michigan.gov | P5 | RESEARCH | Ad-hoc, low structure — low ROI |

## Regional Bodies

| Source | Platform | Priority | Status | Notes |
|--------|----------|----------|--------|-------|
| GLWA | Legistar (browser) | — | **LIVE** | RadGrid table scraping |
| DWSD | Legistar API | P1 | **LIVE** | API works, posts meetings close to date |
| SEMCOG | Custom WordPress | P3 | PLANNED | Agendas as PDFs |
| Huron-Clinton Metroparks | Custom WordPress | P4 | PLANNED | Monthly board meetings |
| Detroit-Wayne Port Authority | Custom WordPress | P5 | PLANNED | Only 6 meetings/year |

## Federal

| Source | Platform | Priority | Status | Notes |
|--------|----------|----------|--------|-------|
| Federal Register | Federal Register API | — | **LIVE** | Filtered for Michigan relevance |
| Army Corps - Detroit District | DotNetNuke | P4 | PLANNED | Public notices, low volume |
| EPA Region 5 | epa.gov | P5 | RESEARCH | Dispersed — low ROI |

## Counties

| Source | Platform | Priority | Status | Notes |
|--------|----------|----------|--------|-------|
| Wayne County | Granicus/OpenCities | — | **BUILT** | Playwright + httpx, 43 tests |
| Oakland County | CivicClerk | — | **LIVE** | OData API |
| Macomb County | CivicClerk | — | **LIVE** | OData API |
| Washtenaw County | CivicClerk | — | **LIVE** | OData API |
| St. Clair County | CivicClerk | — | **LIVE** | OData API |
| Livingston County | Unknown | P4 | RESEARCH | Need to find platform |
| Monroe County | CivicEngage | P4 | DEFERRED | AgendaCenter — no meeting times/locations |

---

## Municipalities — CivicClerk (LIVE — config_key pattern)

Each new city = YAML entry + ~10 lines of config in `CIVICCLERK_CONFIGS`.

| Municipality | County | Pop. | Portal URL | Status |
|---|---|---|---|---|
| Washtenaw County | Washtenaw | — | `washtenawcomi.portal.civicclerk.com` | **LIVE** |
| Oakland County | Oakland | — | `oaklandcomi.portal.civicclerk.com` | **LIVE** |
| Macomb County | Macomb | — | `macombcomi.portal.civicclerk.com` | **LIVE** |
| Livonia | Wayne | 95K | `livoniami.portal.civicclerk.com` | **LIVE** |
| Canton Township | Wayne | 98K | `cantonchartertwpmi.portal.civicclerk.com` | **LIVE** |
| Dearborn Heights | Wayne | 55K | `dearbornheightsmi.portal.civicclerk.com` | **LIVE** |
| West Bloomfield Twp | Oakland | 65K | `wbtownshipmi.portal.civicclerk.com` | **LIVE** |
| Macomb Township | Macomb | 91K | `macombtwpmi.portal.civicclerk.com` | **LIVE** |
| Roseville | Macomb | 47K | `rosevillemi.portal.civicclerk.com` | **LIVE** |
| Birmingham | Oakland | 21K | `birminghammi.portal.civicclerk.com` | **LIVE** |
| Oak Park | Oakland | 29K | `oakparkmi.portal.civicclerk.com` | **LIVE** |
| Romulus | Wayne | 23K | `romulusmi.portal.civicclerk.com` | **LIVE** |
| Harrison Township | Macomb | 25K | `harrisontownshipmi.portal.civicclerk.com` | **LIVE** |
| Ypsilanti | Washtenaw | 22K | `ypsilantimi.portal.civicclerk.com` | **LIVE** |
| Grosse Pointe | Wayne | 5K | `grossepointemi.portal.civicclerk.com` | **LIVE** |
| St. Clair County | St. Clair | — | `stclaircomi.portal.civicclerk.com` | **LIVE** |

**Total population covered by CivicClerk: ~575K municipalities + 3 counties**

## Municipalities — Legistar API (LIVE — config_key pattern)

| Municipality | County | Pop. | Legistar Client | Status | Notes |
|---|---|---|---|---|---|
| Ann Arbor | Washtenaw | 123K | `a2gov` | **LIVE** | 6 meetings, 7 env committee mappings |
| DWSD | Wayne | Regional | `dwsd` | **LIVE** | Working, posts meetings close to date |
| Rochester Hills | Oakland | 76K | `roch` | DEFERRED | API broken on Legistar's end (DB login error) |

## Municipalities — eSCRIBE (adapt existing Detroit scraper)

| Municipality | County | Pop. | eSCRIBE URL | Status |
|---|---|---|---|---|
| Detroit | Wayne | 620K | `pub-detroitmi.escribemeetings.com` | **LIVE** |
| Royal Oak | Oakland | 59K | `pub-royaloak.escribemeetings.com` | **LIVE** (38 meetings, no browser needed) |

## Municipalities — Documents-On-Demand (DEFERRED)

No API. Needs browser + FancyTree JS navigation. Meeting metadata (times, locations) not in UI.

| Municipality | County | Pop. | Portal URL | Status |
|---|---|---|---|---|
| Southfield | Oakland | 73K | `southfieldcitymi.documents-on-demand.com` | DEFERRED |
| Shelby Township | Macomb | 80K | `shelbytwpmi.documents-on-demand.com` | DEFERRED |
| Independence Township | Oakland | 37K | `independencetwpmi.documents-on-demand.com` | DEFERRED |
| + 8 more | Various | ~100K | Various | DEFERRED |

## Municipalities — CivicEngage Agenda Center (DEFERRED)

Has RSS feeds but they're document-publication feeds (when agenda was uploaded, not meeting date). No meeting times, locations, or virtual info. Could still capture agenda PDFs.

| Municipality | County | Pop. | URL Pattern | Status |
|---|---|---|---|---|
| Sterling Heights | Macomb | 134K | `sterlingheights.gov/AgendaCenter` | DEFERRED |
| Westland | Wayne | 82K | `cityofwestland.com/AgendaCenter` | DEFERRED |
| + 13 more | Various | ~400K | Various | DEFERRED |

## School Boards — BoardDocs (DEFERRED — needs Playwright)

Lotus Domino backend. No public API. Needs browser session for AJAX calls.

| District | County | Students | BoardDocs URL | Status |
|---|---|---|---|---|
| DPSCD | Wayne | 49K | `go.boarddocs.com/mi/detroit/Board.nsf` | DEFERRED |
| Dearborn Public Schools | Wayne | 20K | `go.boarddocs.com/mi/drb/Board.nsf` | DEFERRED |
| Hamtramck | Wayne | — | `go.boarddocs.com/mi/cohmi/Board.nsf` | DEFERRED |
| Trenton | Wayne | — | `go.boarddocs.com/mi/trentonmi/Board.nsf` | DEFERRED |

## Municipalities — Custom/Individual Scrapers (P3-P5)

These need individual scrapers. Prioritized by population.

| Municipality | County | Pop. | Platform | Priority | Status |
|---|---|---|---|---|---|
| Warren | Macomb | 139K | Custom website | P3 | PLANNED |
| Dearborn | Wayne | 94K | Drupal CMS | P3 | PLANNED |
| Troy | Oakland | 87K | Custom web app | P3 | PLANNED |
| Farmington Hills | Oakland | 83K | MuniWeb | P3 | PLANNED |
| Clinton Township | Macomb | 101K | Laserfiche | P3 | PLANNED |
| Novi | Oakland | 61K | MuniWeb | P4 | PLANNED |
| Pontiac | Oakland | 61K | Revize CMS | P4 | PLANNED |
| Ypsilanti Township | Washtenaw | 55K | Custom website | P4 | PLANNED |
| Southgate | Wayne | 29K | Granicus | P4 | RESEARCH |
| Ferndale | Oakland | 20K | Static PDF calendar | P5 | DEFERRED (schedule-based generation possible) |
| Eastpointe | Macomb | 32K | Custom website | P4 | PLANNED |
| Port Huron | St. Clair | 28K | Custom website | P4 | PLANNED |

---

## Recommended Next Steps

### Immediate — Royal Oak eSCRIBE (adapt existing)
Adapt Detroit eSCRIBE scraper for Royal Oak. Same platform, different data.
**Result: +59K population, 1 new source**

### Near-term — High-population custom scrapers
Warren (139K), Dearborn (94K), Troy (87K) — research their specific platforms and build individual scrapers where feasible.

### Medium-term — BoardDocs via Playwright
Build browser-based scraper for DPSCD and other school boards. High civic value for education coverage.

### Long-term — Schedule-based generation
For cities like Ferndale with static PDF calendars, generate meetings from known schedules (e.g., "City Council meets 1st and 3rd Monday at 7 PM") rather than scraping.

---

## Coverage Projections

| Milestone | Sources | Est. Population Covered | Platforms |
|-----------|---------|------------------------|-----------|
| **Current (2026-03-14)** | **28** | **~2.0M + statewide** | **9** |
| + Warren/Dearborn/Troy | 31 | ~2.3M | 9-10 |
| + BoardDocs schools | 35 | ~2.3M + schools | 11 |
| + CivicEngage (if revisited) | 50 | ~2.8M | 12 |
| Full buildout | 60+ | ~3M+ | 12+ |

**Southeast Michigan total population: ~4.7M**
**Current coverage: ~40% of SEMCOG population + statewide legislature**

---

## Detailed Municipality Platform Inventory

See `SEMCOG-MUNICIPALITY-PLATFORMS.md` for the full county-by-county breakdown of all ~240 municipalities with confirmed platforms.
