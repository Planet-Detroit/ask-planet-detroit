/**
 * Michigan Geographic Hierarchy
 * Used for cascading geographic filters in the directory
 */

export const MICHIGAN_HIERARCHY = {
  "Southeast Michigan": {
    "Detroit Metro": [
      "Detroit", "Dearborn", "Dearborn Heights", "Livonia", "Westland",
      "Taylor", "Southgate", "Allen Park", "Lincoln Park", "Wyandotte",
      "Wayne County", "Detroit River", "Rouge River"
    ],
    "Ann Arbor Area": [
      "Ann Arbor", "Ypsilanti", "Saline", "Chelsea", "Dexter",
      "Washtenaw County", "Huron River"
    ],
    "Tri-County Area": [
      "Warren", "Sterling Heights", "Troy", "Farmington Hills", "Pontiac",
      "Royal Oak", "Southfield", "Rochester", "Auburn Hills", "Novi",
      "Oakland County", "Macomb County", "Clinton River"
    ],
    "Monroe Area": [
      "Monroe", "Monroe County", "River Raisin"
    ]
  },
  
  "West Michigan": {
    "Grand Rapids Metro": [
      "Grand Rapids", "Wyoming", "Kentwood", "Walker", "Grandville",
      "Kent County", "Grand River"
    ],
    "Kalamazoo Area": [
      "Kalamazoo", "Portage", "Battle Creek",
      "Kalamazoo County", "Calhoun County", "Kalamazoo River"
    ],
    "Muskegon Area": [
      "Muskegon", "Muskegon Heights", "Norton Shores",
      "Muskegon County"
    ],
    "Holland Area": [
      "Holland", "Zeeland", "Ottawa County", "Allegan County"
    ]
  },
  
  "Central Michigan": {
    "Lansing-East Lansing Area": [
      "Lansing", "East Lansing", "Okemos", "Holt", "Mason",
      "Ingham County", "Eaton County", "Clinton County"
    ],
    "Flint Area": [
      "Flint", "Burton", "Flushing", "Davison",
      "Genesee County", "Flint River"
    ],
    "Tri-Cities": [
      "Saginaw", "Bay City", "Midland",
      "Saginaw County", "Bay County", "Midland County",
      "Saginaw River"
    ],
    "Jackson Area": [
      "Jackson", "Jackson County"
    ]
  },
  
  "Upper Peninsula": {
    "Marquette Area": [
      "Marquette", "Negaunee", "Ishpeming", "Marquette County"
    ],
    "Sault Ste. Marie Area": [
      "Sault Ste. Marie", "Chippewa County"
    ],
    "Escanaba Area": [
      "Escanaba", "Gladstone", "Delta County"
    ],
    "Houghton-Hancock Area": [
      "Houghton", "Hancock", "Calumet",
      "Houghton County", "Keweenaw County"
    ],
    "Iron Mountain Area": [
      "Iron Mountain", "Kingsford", "Dickinson County"
    ]
  },
  
  "Northwest Michigan": {
    "Traverse City Area": [
      "Traverse City", "Grand Traverse County", "Leelanau County", "Benzie County"
    ],
    "Petoskey-Harbor Springs Area": [
      "Petoskey", "Harbor Springs", "Charlevoix",
      "Emmet County", "Charlevoix County"
    ],
    "Cadillac Area": [
      "Cadillac", "Wexford County"
    ]
  },
  
  "Northeast Michigan": {
    "Alpena Area": [
      "Alpena", "Alpena County", "Thunder Bay River"
    ],
    "Gaylord Area": [
      "Gaylord", "Otsego County"
    ]
  },
  
  "Southwest Michigan": {
    "Benton Harbor-St. Joseph Area": [
      "Benton Harbor", "St. Joseph", "Berrien County", "St. Joseph River"
    ],
    "Niles Area": [
      "Niles", "Cass County"
    ]
  }
};

/**
 * Get all regions
 */
export const getRegions = () => Object.keys(MICHIGAN_HIERARCHY);

/**
 * Get metro areas for selected regions
 */
export const getMetrosForRegions = (selectedRegions) => {
  if (!selectedRegions || selectedRegions.length === 0) {
    return [];
  }
  
  const metros = [];
  selectedRegions.forEach(region => {
    if (MICHIGAN_HIERARCHY[region]) {
      Object.keys(MICHIGAN_HIERARCHY[region]).forEach(metro => {
        if (!metros.includes(metro)) {
          metros.push(metro);
        }
      });
    }
  });
  
  return metros.sort();
};

/**
 * Get local areas for selected metro areas
 */
export const getLocalsForMetros = (selectedMetros) => {
  if (!selectedMetros || selectedMetros.length === 0) {
    return [];
  }
  
  const locals = new Set();
  
  Object.values(MICHIGAN_HIERARCHY).forEach(metros => {
    Object.entries(metros).forEach(([metroName, localAreas]) => {
      if (selectedMetros.includes(metroName)) {
        localAreas.forEach(local => locals.add(local));
      }
    });
  });
  
  return Array.from(locals).sort();
};

/**
 * Get all local areas (for when no metros selected)
 */
export const getAllLocals = () => {
  const locals = new Set();
  
  Object.values(MICHIGAN_HIERARCHY).forEach(metros => {
    Object.values(metros).forEach(localAreas => {
      localAreas.forEach(local => locals.add(local));
    });
  });
  
  return Array.from(locals).sort();
};

/**
 * Check if an organization matches the geographic filters
 */
export const matchesGeographicFilter = (org, filters) => {
  const { regions, metros, locals } = filters;
  
  // If no filters selected, show all
  if (
    (!regions || regions.length === 0) &&
    (!metros || metros.length === 0) &&
    (!locals || locals.length === 0)
  ) {
    return true;
  }
  
  // Check region match
  if (regions && regions.length > 0) {
    if (!org.region || !regions.includes(org.region)) {
      return false;
    }
  }
  
  // Check metro match
  if (metros && metros.length > 0) {
    if (!org.metro_area || !metros.includes(org.metro_area)) {
      return false;
    }
  }
  
  // Check local match (geo_location array)
  if (locals && locals.length > 0) {
    const orgLocals = Array.isArray(org.geo_location) ? org.geo_location : [];
    const hasMatch = locals.some(local => orgLocals.includes(local));
    if (!hasMatch) {
      return false;
    }
  }
  
  return true;
};
