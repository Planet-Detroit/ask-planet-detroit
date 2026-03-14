# Scraper Roadmap — Metro Detroit Civic Data Coverage

**Last Updated:** 2026-03-14
**Coverage Area:** 7 SEMCOG counties (~240 municipalities)

---

## Legend

| Status | Meaning |
|--------|---------|
| LIVE | Scraper built and running in production |
| BUILT | Scraper built, not yet deployed |
| NEXT | High priority, ready to build |
| PLANNED | On the roadmap |
| RESEARCH | Needs investigation before building |

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
| **Scrapers live** | 10 |
| **Municipalities covered** | 8 (Detroit, Washtenaw Co., Oakland Co., Macomb Co., Wayne Co. + cities within) |
| **Platforms built** | 6 (eSCRIBE, Legistar, CivicClerk, Granicus, Trumba, Federal Register API) |
| **Meetings in DB** | ~350 |

---

## Platform Strategy

Building one scraper per platform maximizes coverage. This is the priority order:

| Priority | Platform | Scraper Status | Bodies Covered | Est. Population |
|----------|----------|---------------|----------------|-----------------|
| **P1** | CivicClerk | LIVE (counties) | 15+ municipalities + 4 counties | ~1.5M |
| **P1** | Legistar API | NEXT | Ann Arbor, Rochester Hills, DWSD | ~200K + regional |
| **P2** | Documents-On-Demand | NEXT | 10+ municipalities | ~300K |
| **P2** | eSCRIBE | LIVE (Detroit) | Royal Oak (adapt) | ~60K |
| **P2** | BoardDocs | PLANNED | DPSCD, Dearborn Schools, Hamtramck, Trenton | ~650K (schools) |
| **P2** | CivicEngage Agenda Center | PLANNED | 15+ municipalities | ~500K |
| **P3** | MI Legislature (.ics) | PLANNED | All committee hearings | Statewide |
| **P4** | Hyland OnBase | PLANNED | Sterling Heights | 134K |
| **P4** | Granicus | PLANNED | Southgate, Ferndale | ~50K |
| **P4** | CivicWeb | RESEARCH | Grosse Ile, Chesterfield | ~55K |
| **P4** | BoardBook Premier | RESEARCH | Orion Township | 38K |
| **P5** | Custom/WordPress | Per-city | Warren, Troy, Dearborn, etc. | Varies |

---

## State Agencies

| Source | Platform | Priority | Status | Notes |
|--------|----------|----------|--------|-------|
| MPSC | michigan.gov | — | LIVE | LD+JSON structured data, Teams URLs |
| EGLE (meetings + comment periods) | Trumba RSS | — | LIVE | Dual-table routing |
| EGLE Permit Notices | Trumba RSS | P2 | PLANNED | Extend existing EGLE scraper |
| MI Legislature Committees | legislature.mi.gov | P3 | PLANNED | .ics calendar feeds available |
| Governor's Office | michigan.gov | P5 | RESEARCH | Ad-hoc, low structure — low ROI |

## Regional Bodies

| Source | Platform | Priority | Status | Notes |
|--------|----------|----------|--------|-------|
| GLWA | Legistar (browser) | — | LIVE | RadGrid table scraping |
| DWSD | Legistar API | P1 | NEXT | `webapi.legistar.com/v1/dwsd` — reuse Legistar scraper |
| SEMCOG | Custom WordPress | P3 | PLANNED | Agendas as PDFs |
| Huron-Clinton Metroparks | Custom WordPress | P4 | PLANNED | Monthly board meetings |
| Detroit-Wayne Port Authority | Custom WordPress | P5 | PLANNED | Only 6 meetings/year |

## Federal

| Source | Platform | Priority | Status | Notes |
|--------|----------|----------|--------|-------|
| Federal Register | Federal Register API | — | LIVE | Filtered for Michigan relevance |
| Army Corps - Detroit District | DotNetNuke | P4 | PLANNED | Public notices, low volume |
| EPA Region 5 | epa.gov | P5 | RESEARCH | Dispersed — low ROI |

## Counties

| Source | Platform | Priority | Status | Notes |
|--------|----------|----------|--------|-------|
| Wayne County | Granicus/OpenCities | — | BUILT | Playwright + httpx |
| Oakland County | CivicClerk | — | LIVE | OData API |
| Macomb County | CivicClerk | — | LIVE | OData API |
| Washtenaw County | CivicClerk | — | LIVE | OData API |
| Livingston County | Unknown | P4 | RESEARCH | Need to find platform |
| St. Clair County | CivicClerk | P2 | NEXT | `stclaircomi.portal.civicclerk.com` — just add config |
| Monroe County | CivicEngage | P4 | PLANNED | `co.monroe.mi.us/AgendaCenter` |

---

## Municipalities — CivicClerk (P1: just add configs to existing scraper)

Already built. Each new city = ~10 lines of config in `civicclerk_scraper.py`.

| Municipality | County | Pop. | Portal URL | Status |
|---|---|---|---|---|
| Washtenaw County | Washtenaw | — | `washtenawcomi.portal.civicclerk.com` | LIVE |
| Oakland County | Oakland | — | `oaklandcomi.portal.civicclerk.com` | LIVE |
| Macomb County | Macomb | — | `macombcomi.portal.civicclerk.com` | LIVE |
| Livonia | Wayne | 95K | `livoniami.portal.civicclerk.com` | NEXT |
| Canton Township | Wayne | 98K | `cantonchartertwpmi.portal.civicclerk.com` | NEXT |
| Dearborn Heights | Wayne | 55K | `dearbornheightsmi.portal.civicclerk.com` | NEXT |
| West Bloomfield Twp | Oakland | 65K | `wbtownshipmi.portal.civicclerk.com` | NEXT |
| Macomb Township | Macomb | 91K | `macombtwpmi.portal.civicclerk.com` | NEXT |
| Roseville | Macomb | 47K | `rosevillemi.portal.civicclerk.com` | NEXT |
| Birmingham | Oakland | 21K | `birminghammi.portal.civicclerk.com` | NEXT |
| Oak Park | Oakland | 29K | `oakparkmi.portal.civicclerk.com` | NEXT |
| Romulus | Wayne | 23K | `romulusmi.portal.civicclerk.com` | NEXT |
| Harrison Township | Macomb | 25K | `harrisontownshipmi.portal.civicclerk.com` | NEXT |
| Ypsilanti | Washtenaw | 22K | `ypsilantimi.portal.civicclerk.com` | NEXT |
| Grosse Pointe | Wayne | 5K | `grossepointemi.portal.civicclerk.com` | PLANNED |
| St. Clair County | St. Clair | — | `stclaircomi.portal.civicclerk.com` | NEXT |

**Total additional population covered: ~575K with just config additions**

## Municipalities — Legistar API (P1: build one scraper, covers 3)

| Municipality | County | Pop. | Legistar URL | Status |
|---|---|---|---|---|
| Ann Arbor | Washtenaw | 123K | `a2gov.legistar.com` | NEXT |
| Rochester Hills | Oakland | 76K | `roch.legistar.com` | NEXT |
| DWSD | Wayne | Regional | `dwsd.legistar.com` | NEXT |

## Municipalities — Documents-On-Demand (P2: build one scraper, covers 10+)

| Municipality | County | Pop. | Portal URL | Status |
|---|---|---|---|---|
| Southfield | Oakland | 73K | `southfieldcitymi.documents-on-demand.com` | PLANNED |
| Shelby Township | Macomb | 80K | `shelbytwpmi.documents-on-demand.com` | PLANNED |
| Bloomfield Township | Oakland | 43K | Referenced but URL unconfirmed | RESEARCH |
| Independence Township | Oakland | 37K | `independencetwpmi.documents-on-demand.com` | PLANNED |
| Washington Township | Macomb | 26K | `washingtontwpmi.documents-on-demand.com` | PLANNED |
| Clawson | Oakland | 12K | `clawsoncitymi.documents-on-demand.com` | PLANNED |
| Saline | Washtenaw | 9K | `salinecitymi.documents-on-demand.com` | PLANNED |
| Ann Arbor Township | Washtenaw | 4K | `annarbortwpmi.documents-on-demand.com` | PLANNED |
| Northfield Township | Washtenaw | 9K | `northfieldtwpmi.documents-on-demand.com` | PLANNED |
| Salem Township | Washtenaw | 6K | `salemtwpmi.documents-on-demand.com` | PLANNED |
| Addison Township | Oakland | 7K | `addisontwpmi.documents-on-demand.com` | PLANNED |

## Municipalities — eSCRIBE (P2: adapt existing Detroit scraper)

| Municipality | County | Pop. | eSCRIBE URL | Status |
|---|---|---|---|---|
| Detroit | Wayne | 620K | `pub-detroitmi.escribemeetings.com` | LIVE |
| Royal Oak | Oakland | 59K | `pub-royaloak.escribemeetings.com` | NEXT |

## Municipalities — CivicEngage Agenda Center (P2: build one scraper, covers 15+)

PDF-based agenda posting. Less structured than CivicClerk but widely deployed.

| Municipality | County | Pop. | URL Pattern | Status |
|---|---|---|---|---|
| Westland | Wayne | 82K | `cityofwestland.com/AgendaCenter` | PLANNED |
| Waterford Township | Oakland | 73K | `waterfordmi.gov/AgendaCenter` | PLANNED |
| Taylor | Wayne | 62K | `cityoftaylor.com/AgendaCenter` | PLANNED |
| St. Clair Shores | Macomb | 60K | `scsmi.net/AgendaCenter` | PLANNED |
| Pittsfield Township | Washtenaw | 40K | `pittsfield-mi.gov/AgendaCenter` | PLANNED |
| Lincoln Park | Wayne | 36K | `citylp.com/AgendaCenter` | PLANNED |
| Redford Township | Wayne | 47K | `redfordtwp.gov/AgendaCenter` | PLANNED |
| Madison Heights | Oakland | 30K | `madison-heights.org/AgendaCenter` | PLANNED |
| Sterling Heights | Macomb | 134K | `sterlingheights.gov/AgendaCenter` | PLANNED |
| Wyandotte | Wayne | 25K | `wyandottemi.gov/AgendaCenter` | PLANNED |
| Inkster | Wayne | 24K | `cityofinkster.com/AgendaCenter` | PLANNED |
| Garden City | Wayne | 26K | `gardencitymi.org/AgendaCenter` | PLANNED |
| Grosse Pointe Park | Wayne | 11K | `grossepointepark.org/AgendaCenter` | PLANNED |
| Brighton Township | Livingston | 18K | `brightontwp.com/AgendaCenter` | PLANNED |
| Monroe County | Monroe | — | `co.monroe.mi.us/AgendaCenter` | PLANNED |

## School Boards — BoardDocs (P2: build one scraper, covers 2+)

| District | County | Students | BoardDocs URL | Status |
|---|---|---|---|---|
| DPSCD | Wayne | 49K | `go.boarddocs.com/mi/detroit/Board.nsf` | PLANNED |
| Dearborn Public Schools | Wayne | 20K | `go.boarddocs.com/mi/drb/Board.nsf` | PLANNED |
| Hamtramck | Wayne | — | `go.boarddocs.com/mi/cohmi/Board.nsf` | PLANNED |
| Trenton | Wayne | — | `go.boarddocs.com/mi/trentonmi/Board.nsf` | PLANNED |

## School Boards — Other

| District | Platform | Status | Notes |
|---|---|---|---|
| Ann Arbor Public Schools | Diligent Community | RESEARCH | Migrated from BoardDocs June 2025 |

## Municipalities — Custom/Individual Scrapers (P3-P5)

These need individual scrapers. Prioritized by population.

| Municipality | County | Pop. | Platform | Priority | Status |
|---|---|---|---|---|---|
| Warren | Macomb | 139K | Custom website | P3 | PLANNED |
| Sterling Heights | Macomb | 134K | Hyland OnBase | P3 | PLANNED |
| Dearborn | Wayne | 94K | Drupal CMS | P3 | PLANNED |
| Troy | Oakland | 87K | Custom web app | P3 | PLANNED |
| Farmington Hills | Oakland | 83K | MuniWeb | P3 | PLANNED |
| Clinton Township | Macomb | 101K | Laserfiche | P3 | PLANNED |
| Novi | Oakland | 61K | MuniWeb | P4 | PLANNED |
| Pontiac | Oakland | 61K | Revize CMS | P4 | PLANNED |
| Ypsilanti Township | Washtenaw | 55K | Custom website | P4 | PLANNED |
| Southgate | Wayne | 29K | Granicus | P4 | PLANNED |
| Ferndale | Oakland | 20K | Granicus | P4 | PLANNED |
| Eastpointe | Macomb | 32K | Custom website | P4 | PLANNED |
| Port Huron | St. Clair | 28K | Custom website | P4 | PLANNED |
| Flint | Genesee | 97K | WordPress | P4 | PLANNED (outside SEMCOG but important) |

---

## Recommended Build Order

### Batch 1 — CivicClerk Expansion (P1, ~1 hour of work)
Add configs for 12 municipalities to existing `civicclerk_scraper.py`:
Livonia, Canton, Dearborn Heights, West Bloomfield, Macomb Twp, Roseville, Birmingham, Oak Park, Romulus, Harrison Twp, Ypsilanti, St. Clair County.
**Result: +575K population, 12 new sources, no new code**

### Batch 2 — Legistar API Scraper (P1, new scraper)
Build generic Legistar REST API scraper covering Ann Arbor, Rochester Hills, DWSD.
**Result: +200K population, 3 new sources, 1 new scraper**

### Batch 3 — Royal Oak eSCRIBE (P2, adapt existing)
Adapt Detroit eSCRIBE scraper for Royal Oak.
**Result: +59K population, 1 new source**

### Batch 4 — Documents-On-Demand Scraper (P2, new scraper)
Build scraper for Southfield, Shelby Twp, and 8+ other municipalities.
**Result: +300K population, 10+ new sources, 1 new scraper**

### Batch 5 — BoardDocs Scraper (P2, new scraper)
Build scraper for DPSCD, Dearborn Schools, Hamtramck, Trenton.
**Result: school board coverage, 4 new sources, 1 new scraper**

### Batch 6 — CivicEngage Agenda Center (P2, new scraper)
Build scraper for Westland, Waterford, Taylor, St. Clair Shores, and 10+ others.
**Result: +500K population, 15+ new sources, 1 new scraper**

### Batch 7 — State Legislature (P3)
Parse .ics calendar feeds from legislature.mi.gov for committee hearings.
**Result: statewide legislative coverage**

### Batch 8+ — Custom Scrapers (P3-P5)
Individual scrapers for Warren, Sterling Heights, Dearborn, Troy, etc.
**Built as needed based on editorial priorities.**

---

## Coverage Projections

| After Batch | Sources | Est. Population Covered | Platform Scrapers |
|-------------|---------|------------------------|-------------------|
| Current | 10 | ~1M | 6 |
| Batch 1 | 22 | ~1.6M | 6 (reuse CivicClerk) |
| Batch 2 | 25 | ~1.8M | 7 (+Legistar API) |
| Batch 3 | 26 | ~1.9M | 7 (reuse eSCRIBE) |
| Batch 4 | 36 | ~2.2M | 8 (+Documents-On-Demand) |
| Batch 5 | 40 | ~2.2M + schools | 9 (+BoardDocs) |
| Batch 6 | 55 | ~2.7M | 10 (+CivicEngage) |
| All batches | 60+ | ~3M+ | 11+ platform scrapers |

**Southeast Michigan total population: ~4.7M**
**Projected coverage after Batch 6: ~60% of SEMCOG population**

---

## Detailed Municipality Platform Inventory

See `SEMCOG-MUNICIPALITY-PLATFORMS.md` for the full county-by-county breakdown of all ~240 municipalities with confirmed platforms.
