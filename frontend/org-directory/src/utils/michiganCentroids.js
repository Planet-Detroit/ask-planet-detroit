/**
 * Geographic Centroids for Michigan
 * Approximate lat/lng centers for regions, metros, and local areas
 */

export const MICHIGAN_CENTROIDS = {
  // State center
  "Michigan": { lat: 44.3148, lng: -85.6024 },
  
  // REGIONS
  "Southeast Michigan": { lat: 42.3314, lng: -83.0458 },
  "West Michigan": { lat: 42.9634, lng: -85.6681 },
  "Central Michigan": { lat: 43.5985, lng: -84.7677 },
  "Upper Peninsula": { lat: 46.5563, lng: -87.3954 },
  "Northwest Michigan": { lat: 44.7631, lng: -85.6206 },
  "Northeast Michigan": { lat: 44.9537, lng: -83.9476 },
  "Southwest Michigan": { lat: 42.0098, lng: -86.2023 },
  
  // METROS - Southeast Michigan
  "Detroit Metro": { lat: 42.3314, lng: -83.0458 },
  "Ann Arbor Area": { lat: 42.2808, lng: -83.7430 },
  "Tri-County Area": { lat: 42.5803, lng: -83.1499 },
  "Monroe Area": { lat: 41.9165, lng: -83.3977 },
  
  // METROS - West Michigan
  "Grand Rapids Metro": { lat: 42.9634, lng: -85.6681 },
  "Kalamazoo Area": { lat: 42.2917, lng: -85.5872 },
  "Muskegon Area": { lat: 43.2342, lng: -86.2484 },
  "Holland Area": { lat: 42.7876, lng: -86.1090 },
  
  // METROS - Central Michigan
  "Lansing-East Lansing Area": { lat: 42.7325, lng: -84.5555 },
  "Flint Area": { lat: 43.0125, lng: -83.6875 },
  "Tri-Cities": { lat: 43.4195, lng: -83.9501 },
  "Jackson Area": { lat: 42.2459, lng: -84.4013 },
  
  // METROS - Upper Peninsula
  "Marquette Area": { lat: 46.5436, lng: -87.3954 },
  "Sault Ste. Marie Area": { lat: 46.4953, lng: -84.3453 },
  "Escanaba Area": { lat: 45.7453, lng: -87.0646 },
  "Houghton-Hancock Area": { lat: 47.1186, lng: -88.5694 },
  "Iron Mountain Area": { lat: 45.8202, lng: -88.0659 },
  
  // METROS - Northwest Michigan
  "Traverse City Area": { lat: 44.7631, lng: -85.6206 },
  "Petoskey-Harbor Springs Area": { lat: 45.3733, lng: -84.9553 },
  "Cadillac Area": { lat: 44.2520, lng: -85.4011 },
  
  // METROS - Northeast Michigan
  "Alpena Area": { lat: 45.0617, lng: -83.4327 },
  "Gaylord Area": { lat: 45.0275, lng: -84.6747 },
  
  // METROS - Southwest Michigan
  "Benton Harbor-St. Joseph Area": { lat: 42.1167, lng: -86.4542 },
  "Niles Area": { lat: 41.8298, lng: -86.2542 },
  
  // CITIES - Southeast Michigan
  "Detroit": { lat: 42.3314, lng: -83.0458 },
  "Dearborn": { lat: 42.3223, lng: -83.1763 },
  "Ann Arbor": { lat: 42.2808, lng: -83.7430 },
  "Ypsilanti": { lat: 42.2411, lng: -83.6130 },
  "Warren": { lat: 42.5145, lng: -83.0146 },
  "Sterling Heights": { lat: 42.5803, lng: -83.0302 },
  "Troy": { lat: 42.6064, lng: -83.1498 },
  "Farmington Hills": { lat: 42.4989, lng: -83.3677 },
  "Pontiac": { lat: 42.6389, lng: -83.2910 },
  "Royal Oak": { lat: 42.4895, lng: -83.1446 },
  "Southfield": { lat: 42.4734, lng: -83.2219 },
  "Livonia": { lat: 42.3684, lng: -83.3527 },
  "Monroe": { lat: 41.9165, lng: -83.3977 },
  
  // CITIES - West Michigan
  "Grand Rapids": { lat: 42.9634, lng: -85.6681 },
  "Kalamazoo": { lat: 42.2917, lng: -85.5872 },
  "Wyoming": { lat: 42.9133, lng: -85.7053 },
  "Kentwood": { lat: 42.8695, lng: -85.6447 },
  "Holland": { lat: 42.7876, lng: -86.1090 },
  "Muskegon": { lat: 43.2342, lng: -86.2484 },
  "Battle Creek": { lat: 42.3211, lng: -85.1797 },
  
  // CITIES - Central Michigan
  "Lansing": { lat: 42.7325, lng: -84.5555 },
  "East Lansing": { lat: 42.7370, lng: -84.4839 },
  "Flint": { lat: 43.0125, lng: -83.6875 },
  "Saginaw": { lat: 43.4195, lng: -83.9501 },
  "Bay City": { lat: 43.5945, lng: -83.8889 },
  "Midland": { lat: 43.6156, lng: -84.2472 },
  "Jackson": { lat: 42.2459, lng: -84.4013 },
  
  // CITIES - Upper Peninsula
  "Marquette": { lat: 46.5436, lng: -87.3954 },
  "Sault Ste. Marie": { lat: 46.4953, lng: -84.3453 },
  "Escanaba": { lat: 45.7453, lng: -87.0646 },
  "Houghton": { lat: 47.1186, lng: -88.5694 },
  "Hancock": { lat: 47.1267, lng: -88.5807 },
  
  // CITIES - Northwest Michigan
  "Traverse City": { lat: 44.7631, lng: -85.6206 },
  "Petoskey": { lat: 45.3733, lng: -84.9553 },
  "Cadillac": { lat: 44.2520, lng: -85.4011 },
  
  // CITIES - Northeast Michigan
  "Alpena": { lat: 45.0617, lng: -83.4327 },
  "Gaylord": { lat: 45.0275, lng: -84.6747 },
  
  // COUNTIES
  "Wayne County": { lat: 42.2808, lng: -83.2430 },
  "Oakland County": { lat: 42.6611, lng: -83.3364 },
  "Macomb County": { lat: 42.7083, lng: -82.9194 },
  "Washtenaw County": { lat: 42.2531, lng: -83.8285 },
  "Kent County": { lat: 43.0305, lng: -85.5497 },
  "Genesee County": { lat: 43.0236, lng: -83.7138 },
  "Ingham County": { lat: 42.6050, lng: -84.3683 },
  "Monroe County": { lat: 41.9553, lng: -83.5138 },
  
  // WATERSHEDS
  "Detroit River": { lat: 42.2808, lng: -83.1000 },
  "Rouge River": { lat: 42.3636, lng: -83.2813 },
  "Huron River": { lat: 42.3200, lng: -83.6500 },
  "Clinton River": { lat: 42.6100, lng: -82.9300 },
  "Grand River": { lat: 42.9500, lng: -85.5000 },
  "Kalamazoo River": { lat: 42.4000, lng: -85.5500 },
  "Saginaw River": { lat: 43.4500, lng: -83.9000 },
  "Flint River": { lat: 43.0500, lng: -83.7000 },
  
  // LAKES (for Great Lakes orgs)
  "Lake Michigan": { lat: 43.5000, lng: -86.5000 },
  "Lake Huron": { lat: 44.5000, lng: -82.5000 },
  "Lake Superior": { lat: 47.5000, lng: -87.5000 },
  "Lake Erie": { lat: 42.2000, lng: -81.2000 },
  "Great Lakes": { lat: 45.0000, lng: -84.0000 },
};

/**
 * Get coordinates for an organization based on its geographic data
 */
export const getOrganizationCoordinates = (org) => {
  // Priority order: most specific location wins
  
  // 1. Check geo_location array for specific places
  const geoLocations = Array.isArray(org.geo_location) ? org.geo_location : [];
  
  for (const location of geoLocations) {
    if (MICHIGAN_CENTROIDS[location]) {
      return {
        ...MICHIGAN_CENTROIDS[location],
        precision: getPrecisionLevel(location),
        displayName: location
      };
    }
  }
  
  // 2. Try metro_area
  if (org.metro_area && MICHIGAN_CENTROIDS[org.metro_area]) {
    return {
      ...MICHIGAN_CENTROIDS[org.metro_area],
      precision: 'metro',
      displayName: org.metro_area
    };
  }
  
  // 3. Try region
  if (org.region && MICHIGAN_CENTROIDS[org.region]) {
    return {
      ...MICHIGAN_CENTROIDS[org.region],
      precision: 'region',
      displayName: org.region
    };
  }
  
  // 4. Default to Michigan center
  return {
    ...MICHIGAN_CENTROIDS["Michigan"],
    precision: 'state',
    displayName: 'Michigan'
  };
};

/**
 * Determine precision level of a location
 */
const getPrecisionLevel = (location) => {
  const regions = ["Southeast Michigan", "West Michigan", "Central Michigan", 
                  "Upper Peninsula", "Northwest Michigan", "Northeast Michigan", 
                  "Southwest Michigan"];
  
  if (regions.includes(location)) return 'region';
  if (location.includes('Metro') || location.includes('Area')) return 'metro';
  if (location.includes('County')) return 'county';
  if (location.includes('River') || location.includes('Lake')) return 'watershed';
  return 'city'; // cities and other specific locations
};

/**
 * Get zoom level appropriate for precision
 */
export const getZoomForPrecision = (precision) => {
  switch(precision) {
    case 'state': return 7;
    case 'region': return 8;
    case 'metro': return 10;
    case 'county': return 10;
    case 'watershed': return 11;
    case 'city': return 12;
    default: return 10;
  }
};
