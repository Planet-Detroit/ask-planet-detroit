# SEMCOG Municipality Meeting Platforms Inventory

**Date:** 2026-03-14
**Purpose:** Identify meeting management platforms used by municipalities in the 7 SEMCOG counties to inform scraper development priorities.

## Platform Summary

| Platform | Count (confirmed) | Scraper Potential |
|---|---|---|
| **CivicClerk** (CivicPlus) | 20+ | High - consistent portal URL pattern |
| **CivicEngage Agenda Center** (CivicPlus) | 15+ | Medium - PDF-based, less structured |
| **Documents-On-Demand** | 8+ | Medium - consistent URL pattern |
| **Legistar** (Granicus) | 3 | High - existing scraper patterns available |
| **BoardDocs** | 2+ | Medium - consistent URL pattern |
| **Granicus** | 2+ | Medium |
| **eSCRIBE** | 1 (Detroit) | Already scraped |
| **Hyland OnBase** | 1 (Sterling Heights) | Low - legacy system |
| **Municode Meetings** | 1+ | Low |
| **BoardBook Premier** | 1 | Low |
| **CivicWeb** | 2+ | Medium |
| **Custom website / PDF posts** | Many | Low - manual per-city |

**Key Finding:** CivicPlus (CivicClerk + CivicEngage) dominates the SEMCOG region. A single CivicClerk scraper could cover 20+ municipalities.

---

## 1. WAYNE COUNTY (43 municipalities)

### Cities (34)

| Municipality | Pop. (est.) | Platform | URL/Notes |
|---|---|---|---|
| **Detroit** | 620,000 | **eSCRIBE** + **Legistar** | `pub-detroitmi.escribemeetings.com`, `detroit.legistar.com` - ALREADY SCRAPED |
| **Livonia** | 95,000 | **CivicClerk** | `livoniami.portal.civicclerk.com` |
| **Dearborn** | 94,000 | **Custom website** | `dearborn.gov` - agendas posted as PDFs |
| **Westland** | 82,000 | **CivicEngage Agenda Center** | `cityofwestland.com/AgendaCenter` |
| **Taylor** | 62,000 | **CivicEngage Agenda Center** | `cityoftaylor.com/AgendaCenter` |
| **Southgate** | 29,000 | **Granicus** | `cityofsouthgate.granicus.com` |
| **Dearborn Heights** | 55,000 | **CivicClerk** | `dearbornheightsmi.portal.civicclerk.com` |
| **Lincoln Park** | 36,000 | **CivicEngage Agenda Center** | `citylp.com/AgendaCenter` |
| **Wyandotte** | 25,000 | **CivicEngage Agenda Center** | `wyandottemi.gov/AgendaCenter` |
| **Romulus** | 23,000 | **CivicClerk** + CivicEngage | `romulusmi.portal.civicclerk.com` |
| **Inkster** | 24,000 | **CivicEngage Agenda Center** | `cityofinkster.com/AgendaCenter` |
| **Garden City** | 26,000 | **CivicEngage Agenda Center** | `gardencitymi.org/AgendaCenter` |
| **Allen Park** | 27,000 | **Revize CMS** | `cityofallenpark.org` - PDFs |
| **Trenton** | 18,000 | **BoardDocs** | `go.boarddocs.com/mi/trentonmi/Board.nsf` |
| **Hamtramck** | 28,000 | **BoardDocs** | `go.boarddocs.com/mi/cohmi/Board.nsf` |
| **Woodhaven** | 12,000 | **Custom website** | `woodhavenmi.org` - Document Center |
| **Harper Woods** | 14,000 | **Custom website** | `harperwoodscity.org` - WordPress-based |
| **Riverview** | 12,000 | Unknown | Need to verify |
| **Ecorse** | 9,000 | Unknown | Small city |
| **Flat Rock** | 10,000 | Unknown | Need to verify |
| **Grosse Pointe Woods** | 16,000 | **Custom website** | `gpwmi.us` |
| **Grosse Pointe Park** | 11,000 | **CivicEngage** | `grossepointepark.org/AgendaCenter` |
| **Grosse Pointe** | 5,000 | **CivicClerk** | `grossepointemi.portal.civicclerk.com` |
| **Grosse Pointe Farms** | 9,000 | Unknown | Likely same as GP cluster |
| **Highland Park** | 9,000 | Unknown | Small city |
| **Melvindale** | 10,000 | Unknown | Small city |
| **River Rouge** | 7,000 | Unknown | Small city |
| **Wayne** | 17,000 | Unknown | Need to verify |
| **Plymouth** | 9,000 | Unknown | Small city |
| **Northville** (partial) | 6,000 | Unknown | Small city |
| **Gibraltar** | 5,000 | Unknown | Small city |
| **Rockwood** | 3,000 | Unknown | Small city |
| **Belleville** | 4,000 | Unknown | Small city |
| **Grosse Pointe Shores** (partial) | 3,000 | Unknown | Small village |

### Townships (9)

| Municipality | Pop. (est.) | Platform | URL/Notes |
|---|---|---|---|
| **Canton Township** | 98,000 | **CivicClerk** + CivicEngage | `cantonchartertwpmi.portal.civicclerk.com` |
| **Redford Township** | 47,000 | **CivicEngage Agenda Center** | `redfordtwp.gov/AgendaCenter` |
| **Plymouth Township** | 27,000 | **Revize CMS** | `plymouthtwp.org` - PDFs via Revize |
| **Northville Township** | 29,000 | **Custom website** | `twp.northville.mi.us` - Diligent mentioned |
| **Van Buren Township** | 29,000 | **Custom website** | `vbtmi.gov` |
| **Brownstown Township** | 31,000 | **Custom website** | `brownstown-mi.org` |
| **Grosse Ile Township** | 10,000 | **CivicWeb** | `grosseile.civicweb.net` |
| **Huron Township** | 16,000 | Unknown | Need to verify |
| **Sumpter Township** | 10,000 | Unknown | Small township |

---

## 2. OAKLAND COUNTY (62 municipalities)

### Cities (18)

| Municipality | Pop. (est.) | Platform | URL/Notes |
|---|---|---|---|
| **Troy** | 87,000 | **Custom web app** | `apps.troymi.gov` - custom portal |
| **Farmington Hills** | 83,000 | **Custom website** (MuniWeb) | `fhgov.com` - organized by year |
| **Rochester Hills** | 76,000 | **Legistar** | `roch.legistar.com` |
| **Novi** | 61,000 | **Custom website** (MuniWeb) | `cityofnovi.org/agendas-minutes` |
| **Royal Oak** | 59,000 | **CivicEngage Agenda Center** | `romi.gov/AgendaCenter` |
| **Southfield** | 73,000 | **Documents-On-Demand** | `southfieldcitymi.documents-on-demand.com` |
| **Pontiac** | 61,000 | **Revize CMS** | `pontiac.mi.us` - PDFs |
| **Auburn Hills** | 24,000 | **Revize CMS** | `auburnhills.org` |
| **Ferndale** | 20,000 | **Granicus** | Vendor confirmed as Granicus |
| **Oak Park** | 29,000 | **CivicClerk** | `oakparkmi.portal.civicclerk.com` |
| **Madison Heights** | 30,000 | **CivicEngage** + Municode | `madison-heights.org/AgendaCenter`, `madisonheights-mi.municodemeetings.com` |
| **Birmingham** | 21,000 | **CivicClerk** | `birminghammi.portal.civicclerk.com` |
| **Berkley** | 15,000 | **Custom website** | `berkleymi.gov` |
| **Clawson** | 12,000 | **Documents-On-Demand** | `clawsoncitymi.documents-on-demand.com` |
| **Farmington** | 11,000 | **Custom website** | `farmgov.com` |
| **Hazel Park** | 16,000 | **Custom website** | `hazelpark.org` |
| **Walled Lake** | 7,000 | Unknown | Small city |
| **Wixom** | 14,000 | **Custom website** | `wixomgov.org` |
| **South Lyon** | 12,000 | Unknown | Need to verify |
| **Lake Orion** (village) | 3,000 | Unknown | Small village |
| **Sylvan Lake** | 2,000 | Unknown | Small city |
| **Keego Harbor** | 3,000 | Unknown | Small city |
| **Orchard Lake Village** | 2,000 | Unknown | Small city |
| **Pleasant Ridge** | 3,000 | Unknown | Small city |
| **Lathrup Village** | 4,000 | Unknown | Small city |
| **Huntington Woods** | 6,000 | Unknown | Small city |
| **Bloomfield Hills** (city) | 4,000 | Unknown | Small city |
| **Franklin** | 3,000 | Unknown | Small village |
| **Bingham Farms** | 1,000 | Unknown | Small village |
| **Beverly Hills** | 10,000 | Unknown | Small village |
| **Lake Angelus** | 300 | Unknown | Tiny city |

### Townships (15)

| Municipality | Pop. (est.) | Platform | URL/Notes |
|---|---|---|---|
| **West Bloomfield Township** | 65,000 | **CivicClerk** | `wbtownshipmi.portal.civicclerk.com` |
| **Waterford Township** | 73,000 | **CivicEngage Agenda Center** | `waterfordmi.gov/AgendaCenter` |
| **Bloomfield Township** | 43,000 | **Documents-On-Demand** | Referenced on township website |
| **Orion Township** | 38,000 | **BoardBook Premier** | `meetings.boardbook.org/public/Organization/1374` |
| **Independence Township** | 37,000 | **Documents-On-Demand** | `independencetwpmi.documents-on-demand.com` |
| **Commerce Township** | 43,000 | **Custom website** | `commercetwp.com` |
| **White Lake Township** | 31,000 | **Custom website** | `whitelaketwp.com` |
| **Highland Township** | 20,000 | **Custom website** (Joomla) | `highlandtwp.net` |
| **Milford Township** | 16,000 | Unknown | Need to verify |
| **Lyon Township** | 18,000 | Unknown | Need to verify |
| **Oxford Township** | 21,000 | Unknown | Need to verify |
| **Brandon Township** | 15,000 | Unknown | Need to verify |
| **Addison Township** | 7,000 | **Documents-On-Demand** | `addisontwpmi.documents-on-demand.com` |
| **Springfield Township** | 14,000 | Unknown | Need to verify |
| **Rose Township** | 6,000 | Unknown | Small township |
| **Holly Township** | 12,000 | Unknown | Need to verify |
| **Groveland Township** | 5,000 | Unknown | Small township |
| **Novi Township** | 600 | N/A | Tiny, no services |
| **Southfield Township** | 3,000 | Unknown | Small township |
| **Royal Oak Township** | 3,000 | Unknown | Small township |

---

## 3. MACOMB COUNTY (27 municipalities)

### Cities (11)

| Municipality | Pop. (est.) | Platform | URL/Notes |
|---|---|---|---|
| **Warren** | 139,000 | **Custom website** | `cityofwarren.org` - PDFs on website |
| **Sterling Heights** | 134,000 | **Hyland OnBase** + CivicEngage | `publicdocs.sterling-heights.net/onbaseagendaonline`, `sterlingheights.gov/AgendaCenter` |
| **St. Clair Shores** | 60,000 | **CivicEngage Agenda Center** | `scsmi.net/AgendaCenter` |
| **Roseville** | 47,000 | **CivicClerk** + CivicEngage | `rosevillemi.portal.civicclerk.com` |
| **Eastpointe** | 32,000 | **Custom website** | `eastpointemi.gov` |
| **Mount Clemens** | 17,000 | **Custom website** | `mountclemens.gov` |
| **Center Line** | 8,000 | Unknown | Small city |
| **Fraser** | 15,000 | Unknown | Need to verify |
| **Utica** | 5,000 | Unknown | Small city |
| **Richmond** | 6,000 | Unknown | Small city |
| **New Baltimore** | 14,000 | Unknown | Need to verify |
| **Memphis** (partial) | 1,000 | Unknown | Small city |

### Townships (11)

| Municipality | Pop. (est.) | Platform | URL/Notes |
|---|---|---|---|
| **Clinton Township** | 101,000 | **CivicEngage** + Laserfiche | `clintontownship.com` - Laserfiche portal |
| **Shelby Township** | 80,000 | **Documents-On-Demand** + iQM2 | `shelbytwpmi.documents-on-demand.com` |
| **Macomb Township** | 91,000 | **CivicClerk** + CivicEngage | `macombtwpmi.portal.civicclerk.com` |
| **Chesterfield Township** | 47,000 | **CivicWeb** + CivicEngage | `chesterfieldtwp.civicweb.net` |
| **Harrison Township** | 25,000 | **CivicClerk** | `harrisontownshipmi.portal.civicclerk.com` |
| **Washington Township** | 26,000 | **Documents-On-Demand** | `washingtontwpmi.documents-on-demand.com` |
| **Lenox Township** | 9,000 | Unknown | Small township |
| **Bruce Township** | 8,000 | Unknown | Small township |
| **Ray Township** | 4,000 | Unknown | Small township |
| **Armada Township** | 5,000 | Unknown | Small township |
| **Richmond Township** | 5,000 | Unknown | Small township |

### Villages (3)

| Municipality | Pop. (est.) | Platform | URL/Notes |
|---|---|---|---|
| **Romeo** | 4,000 | Unknown | Small village |
| **Armada** | 2,000 | Unknown | Small village |
| **New Haven** | 5,000 | Unknown | Small village |

---

## 4. WASHTENAW COUNTY (~29 municipalities)

### Cities (6)

| Municipality | Pop. (est.) | Platform | URL/Notes |
|---|---|---|---|
| **Ann Arbor** | 123,000 | **Legistar** | `a2gov.legistar.com` |
| **Ypsilanti** | 22,000 | **CivicClerk** + CivicEngage | `ypsilantimi.portal.civicclerk.com` |
| **Saline** | 9,000 | **Documents-On-Demand** | `salinecitymi.documents-on-demand.com` |
| **Chelsea** | 5,000 | **Custom website** | `city-chelsea.org` |
| **Dexter** | 5,000 | **Custom website** | `dextermi.gov` - PDFs |
| **Milan** (partial) | 6,000 | Unknown | Small city |

### Townships (20)

| Municipality | Pop. (est.) | Platform | URL/Notes |
|---|---|---|---|
| **Ypsilanti Township** | 55,000 | **Custom website** | `ypsitownship.org` - searchable archive |
| **Pittsfield Township** | 40,000 | **CivicEngage Agenda Center** | `pittsfield-mi.gov/AgendaCenter` |
| **Scio Township** | 18,000 | **CivicPlus** | `sciotownshipmi.gov` |
| **Superior Township** | 14,000 | **Custom website** | `superiortownship.org` |
| **Ann Arbor Township** | 4,000 | **Documents-On-Demand** | `annarbortwpmi.documents-on-demand.com` |
| **Northfield Township** | 9,000 | **Documents-On-Demand** | `northfieldtwpmi.documents-on-demand.com` |
| **Salem Township** | 6,000 | **Documents-On-Demand** | `salemtwpmi.documents-on-demand.com` |
| **Augusta Township** | 7,000 | Unknown | Need to verify |
| **Bridgewater Township** | 2,000 | Unknown | Small township |
| **Dexter Township** | 6,000 | Unknown | Need to verify |
| **Freedom Township** | 2,000 | Unknown | Small township |
| **Lima Township** | 4,000 | Unknown | Small township |
| **Lodi Township** | 6,000 | Unknown | Need to verify |
| **Lyndon Township** | 3,000 | Unknown | Small township |
| **Manchester Township** | 5,000 | Unknown | Need to verify |
| **Saline Township** | 2,000 | Unknown | Small township |
| **Sharon Township** | 2,000 | Unknown | Small township |
| **Sylvan Township** | 3,000 | Unknown | Small township |
| **Webster Township** | 7,000 | Unknown | Need to verify |
| **York Township** | 8,000 | Unknown | Need to verify |

### Villages (3)

| Municipality | Pop. (est.) | Platform | URL/Notes |
|---|---|---|---|
| **Manchester** | 2,000 | Unknown | Small village |
| **Barton Hills** | 300 | Unknown | Tiny village |

---

## 5. LIVINGSTON COUNTY (20 municipalities)

### Cities (2)

| Municipality | Pop. (est.) | Platform | URL/Notes |
|---|---|---|---|
| **Howell** | 10,000 | **Revize CMS** | `howellmi.gov` - PDFs |
| **Brighton** | 8,000 | **Custom website** | `brightoncitymi.gov` |

### Townships (16)

| Municipality | Pop. (est.) | Platform | URL/Notes |
|---|---|---|---|
| **Genoa Township** | 22,000 | **Custom website** | `genoa.org` - custom with app |
| **Brighton Township** | 18,000 | **CivicEngage Agenda Center** | `brightontwp.com/AgendaCenter` |
| **Green Oak Township** | 19,000 | Unknown | Need to verify |
| **Hamburg Township** | 21,000 | Unknown | Need to verify |
| **Hartland Township** | 15,000 | **Custom website** | `hartlandtwp.com` |
| **Howell Township** | 7,000 | Unknown | Small township |
| **Marion Township** | 9,000 | Unknown | Need to verify |
| **Oceola Township** | 13,000 | Unknown | Need to verify |
| **Tyrone Township** | 10,000 | Unknown | Need to verify |
| **Cohoctah Township** | 4,000 | Unknown | Small township |
| **Conway Township** | 3,000 | Unknown | Small township |
| **Deerfield Township** | 4,000 | Unknown | Small township |
| **Handy Township** | 7,000 | Unknown | Need to verify |
| **Iosco Township** | 4,000 | Unknown | Small township |
| **Putnam Township** | 6,000 | Unknown | Need to verify |
| **Unadilla Township** | 3,000 | Unknown | Small township |

### Villages (2)

| Municipality | Pop. (est.) | Platform | URL/Notes |
|---|---|---|---|
| **Fowlerville** | 3,000 | Unknown | Small village |
| **Pinckney** | 2,000 | Unknown | Small village |

---

## 6. ST. CLAIR COUNTY (~34 municipalities)

### Cities (6)

| Municipality | Pop. (est.) | Platform | URL/Notes |
|---|---|---|---|
| **Port Huron** | 28,000 | **Custom website** | `porthuron.org` |
| **Marysville** | 10,000 | **Revize CMS** | `cityofmarysvillemi.com` |
| **St. Clair** | 5,000 | Unknown | Small city |
| **Marine City** | 4,000 | Unknown | Small city |
| **Yale** | 2,000 | Unknown | Small city |
| **Algonac** | 4,000 | Unknown | Small city |
| **Memphis** (partial) | 1,000 | Unknown | Small city |
| **Richmond** (partial) | 6,000 | Unknown | Small city |

**St. Clair County (county level):** Uses **CivicClerk** at `stclaircomi.portal.civicclerk.com`

### Townships (23)

| Municipality | Pop. (est.) | Platform | URL/Notes |
|---|---|---|---|
| **Fort Gratiot Township** | 11,000 | Unknown | Need to verify |
| **East China Township** | 4,000 | Unknown | Need to verify |
| **Kimball Township** | 9,000 | Unknown | Need to verify |
| **Clay Township** | 9,000 | Unknown | Need to verify |
| **Cottrellville Township** | 4,000 | Unknown | Small township |
| **Berlin Township** | 6,000 | Unknown | Need to verify |
| **Casco Township** | 5,000 | Unknown | Small township |
| **Clyde Township** | 4,000 | Unknown | Small township |
| **Columbus Township** | 5,000 | Unknown | Small township |
| **Emmett Township** | 3,000 | Unknown | Small township |
| **Grant Township** | 2,000 | Unknown | Small township |
| **Greenwood Township** | 2,000 | Unknown | Small township |
| **Ira Township** | 5,000 | Unknown | Small township |
| **Kenockee Township** | 3,000 | Unknown | Small township |
| **Lynn Township** | 2,000 | Unknown | Small township |
| **Mussey Township** | 4,000 | Unknown | Small township |
| **Port Huron Township** | 10,000 | Unknown | Need to verify |
| **Riley Township** | 3,000 | Unknown | Small township |
| **St. Clair Township** | 7,000 | Unknown | Need to verify |
| **Wales Township** | 4,000 | Unknown | Small township |
| **Brockway Township** | 2,000 | Unknown | Small township |
| **Burtchville Township** | 3,000 | Unknown | Small township |
| **China Township** | 3,000 | Unknown | Small township |

### Villages (5+)

| Municipality | Pop. (est.) | Platform | URL/Notes |
|---|---|---|---|
| **Emmett** | 300 | Unknown | Small village |
| **Capac** | 2,000 | Unknown | Small village |

---

## 7. MONROE COUNTY (24 municipalities)

### Cities (4)

| Municipality | Pop. (est.) | Platform | URL/Notes |
|---|---|---|---|
| **Monroe** | 20,000 | **Custom website** | `monroemi.gov` |
| **Milan** (partial) | 6,000 | Unknown | Shared with Washtenaw |
| **Luna Pier** | 1,000 | Unknown | Small city |
| **Petersburg** | 1,000 | Unknown | Small city |

**Monroe County (county level):** Uses **CivicEngage Agenda Center** at `co.monroe.mi.us/AgendaCenter`

### Townships (15)

| Municipality | Pop. (est.) | Platform | URL/Notes |
|---|---|---|---|
| **Bedford Township** | 30,000 | **Custom website** | `bedfordmi.org` |
| **Frenchtown Township** | 21,000 | **CivicPlus** | `frenchtownmi.gov` |
| **Monroe Charter Township** | 14,000 | Unknown | Need to verify |
| **LaSalle Township** | 8,000 | Unknown | Need to verify |
| **Erie Township** | 5,000 | Unknown | Small township |
| **Dundee Township** | 4,000 | Unknown | Small township |
| **Ash Township** | 7,000 | Unknown | Need to verify |
| **Berlin Township** | 5,000 | Unknown | Small township |
| **Exeter Township** | 3,000 | Unknown | Small township |
| **Ida Township** | 5,000 | Unknown | Small township |
| **London Township** | 3,000 | Unknown | Small township |
| **Milan Township** | 2,000 | Unknown | Small township |
| **Raisinville Township** | 6,000 | Unknown | Need to verify |
| **Summerfield Township** | 3,000 | Unknown | Small township |
| **Whiteford Township** | 4,000 | Unknown | Small township |

### Villages (5)

| Municipality | Pop. (est.) | Platform | URL/Notes |
|---|---|---|---|
| **Dundee** | 4,000 | Unknown | Small village |
| **Carleton** | 2,000 | Unknown | Small village |
| **South Rockwood** | 1,000 | Unknown | Small village |
| **Maybee** | 600 | Unknown | Small village |
| **Estral Beach** | 400 | Unknown | Small village |

---

## Platform Dominance by County

| County | Dominant Platform(s) | Notes |
|---|---|---|
| **Wayne** | CivicClerk, CivicEngage, BoardDocs | CivicPlus products dominate |
| **Oakland** | Documents-On-Demand, CivicClerk, Custom | More fragmented |
| **Macomb** | CivicClerk, CivicEngage, Documents-On-Demand | Mixed |
| **Washtenaw** | Legistar (Ann Arbor), Documents-On-Demand | Ann Arbor is the big one |
| **Livingston** | Custom websites | No dominant platform |
| **St. Clair** | Custom websites, CivicClerk (county) | Mostly manual posting |
| **Monroe** | Custom websites | No dominant platform |

---

## Scraper Development Priority

### Tier 1 - Highest Impact (build these first)
1. **CivicClerk scraper** - Would cover: Livonia, Dearborn Heights, Canton, Romulus, West Bloomfield, Birmingham, Oak Park, Macomb Township, Harrison Township, Roseville, Ypsilanti, Grosse Pointe, and more. ~20 municipalities, ~1.5M population covered.
2. **Legistar scraper** - Would cover: Ann Arbor, Rochester Hills, Detroit (already exists). ~250K population.

### Tier 2 - Good Coverage
3. **Documents-On-Demand scraper** - Would cover: Southfield, Shelby Township, Washington Township, Bloomfield Township, Independence Township, Clawson, Saline, Ann Arbor Township, Northfield Township, Salem Township, Addison Township. ~300K population.
4. **BoardDocs scraper** - Would cover: Hamtramck, Trenton, potentially others. ~45K population.

### Tier 3 - Individual High-Value Targets
5. **Warren custom scraper** - 139K population, custom website
6. **Sterling Heights OnBase scraper** - 134K population, Hyland OnBase
7. **Troy custom scraper** - 87K population, custom app

### Tier 4 - CivicEngage Agenda Center
Many municipalities use CivicEngage Agenda Center (CivicPlus), but it primarily hosts PDFs rather than structured data. A PDF-download scraper could parse these, but would need agenda summarization (already built).

---

## Confirmed CivicClerk Portal URLs

These all follow the pattern `{subdomain}.portal.civicclerk.com`:

| Municipality | Portal URL |
|---|---|
| Livonia | `livoniami.portal.civicclerk.com` |
| Dearborn Heights | `dearbornheightsmi.portal.civicclerk.com` |
| Canton Township | `cantonchartertwpmi.portal.civicclerk.com` |
| Romulus | `romulusmi.portal.civicclerk.com` |
| Roseville | `rosevillemi.portal.civicclerk.com` |
| West Bloomfield Township | `wbtownshipmi.portal.civicclerk.com` |
| Oak Park | `oakparkmi.portal.civicclerk.com` |
| Birmingham | `birminghammi.portal.civicclerk.com` |
| Macomb Township | `macombtwpmi.portal.civicclerk.com` |
| Harrison Township | `harrisontownshipmi.portal.civicclerk.com` |
| Ypsilanti | `ypsilantimi.portal.civicclerk.com` |
| Grosse Pointe | `grossepointemi.portal.civicclerk.com` |
| St. Clair County | `stclaircomi.portal.civicclerk.com` |
| Macomb County | `macombcomi.portal.civicclerk.com` |
| Washtenaw County | `washtenawcomi.portal.civicclerk.com` |

---

## Confirmed Documents-On-Demand URLs

These all follow the pattern `{subdomain}.documents-on-demand.com`:

| Municipality | Portal URL |
|---|---|
| Southfield | `southfieldcitymi.documents-on-demand.com` |
| Shelby Township | `shelbytwpmi.documents-on-demand.com` |
| Washington Township | `washingtontwpmi.documents-on-demand.com` |
| Clawson | `clawsoncitymi.documents-on-demand.com` |
| Independence Township | `independencetwpmi.documents-on-demand.com` |
| Addison Township | `addisontwpmi.documents-on-demand.com` |
| Saline | `salinecitymi.documents-on-demand.com` |
| Ann Arbor Township | `annarbortwpmi.documents-on-demand.com` |
| Northfield Township | `northfieldtwpmi.documents-on-demand.com` |
| Salem Township | `salemtwpmi.documents-on-demand.com` |
| Bloomfield Township | Referenced but URL not confirmed |

---

## Confirmed Legistar URLs

| Municipality | Portal URL |
|---|---|
| Detroit | `detroit.legistar.com` |
| Ann Arbor | `a2gov.legistar.com` |
| Rochester Hills | `roch.legistar.com` |

---

## Confirmed BoardDocs URLs

| Municipality | Portal URL |
|---|---|
| Hamtramck | `go.boarddocs.com/mi/cohmi/Board.nsf` |
| Trenton | `go.boarddocs.com/mi/trentonmi/Board.nsf` |
