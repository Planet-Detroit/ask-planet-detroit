import React, { useState, useEffect, useMemo } from 'react';
import { createClient } from '@supabase/supabase-js';
import { NavLink } from 'react-router-dom';
import { matchesGeographicFilter } from '../utils/geographicHierarchy';
import OrganizationMap from '../components/OrganizationMap';
import RegionTable from '../components/RegionTable';

// Import Lucide icons
import { 
  Droplet, Wind, Thermometer, Zap, Sprout, Trees, 
  Recycle, Scale, Factory, Navigation, GraduationCap, 
  Briefcase, Users, Bug, Bird, Leaf, Flower2, Fish,
  Sun, CloudRain, Mountain, Heart
} from 'lucide-react';

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
const supabaseKey = import.meta.env.VITE_SUPABASE_ANON_KEY;
const supabase = createClient(supabaseUrl, supabaseKey);

const COLOR_PALETTE = [
  { bg: '#dbeafe', color: '#1d4ed8' }, { bg: '#bbf7d0', color: '#15803d' },
  { bg: '#fecaca', color: '#b91c1c' }, { bg: '#fed7aa', color: '#c2410c' },
  { bg: '#e9d5ff', color: '#6b21a8' }, { bg: '#a5f3fc', color: '#0e7490' },
  { bg: '#fbcfe8', color: '#be185d' }, { bg: '#fef3c7', color: '#ca8a04' },
  { bg: '#c7d2fe', color: '#4338ca' }, { bg: '#99f6e4', color: '#0f766e' },
  { bg: '#a7f3d0', color: '#047857' }, { bg: '#fde68a', color: '#92400e' },
];

const hashStringToColor = (str) => {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = str.charCodeAt(i) + ((hash << 5) - hash);
  }
  return COLOR_PALETTE[Math.abs(hash) % COLOR_PALETTE.length];
};

// SMART ICON MATCHING - automatically picks icons based on keywords!
const getIconFromKeywords = (issue) => {
  const n = (issue || '').toLowerCase();
  
  if (n.includes('water') || n.includes('aquatic') || n.includes('river') || n.includes('lake') || n.includes('wetland')) return Droplet;
  if (n.includes('air') || n.includes('wind')) return Wind;
  if (n.includes('climate') || n.includes('temperature') || n.includes('warming')) return Thermometer;
  if (n.includes('energy') || n.includes('solar') || n.includes('power') || n.includes('electric')) return Zap;
  if (n.includes('food') || n.includes('farm') || n.includes('agriculture') || n.includes('garden')) return Sprout;
  if (n.includes('tree') || n.includes('forest') || n.includes('wood') || n.includes('park') || n.includes('land') || n.includes('habitat')) return Trees;
  if (n.includes('bird') || n.includes('wildlife') || n.includes('animal')) return Bird;
  if (n.includes('pollinator') || n.includes('bee') || n.includes('insect') || n.includes('butterfly')) return Bug;
  if (n.includes('fish')) return Fish;
  if (n.includes('biodiversity') || n.includes('conservation') || n.includes('ecosystem') || n.includes('nature')) return Leaf;
  if (n.includes('recycl') || n.includes('waste') || n.includes('compost') || n.includes('trash')) return Recycle;
  if (n.includes('justice') || n.includes('equity') || n.includes('rights') || n.includes('fair')) return Scale;
  if (n.includes('toxic') || n.includes('pollut') || n.includes('contaminat') || n.includes('brownfield') || n.includes('chemical')) return Factory;
  if (n.includes('recreation') || n.includes('trail') || n.includes('outdoor') || n.includes('hik')) return Navigation;
  if (n.includes('educat') || n.includes('learn') || n.includes('teach') || n.includes('school')) return GraduationCap;
  if (n.includes('workforce') || n.includes('job') || n.includes('employ') || n.includes('career')) return Briefcase;
  if (n.includes('advocat') || n.includes('policy') || n.includes('organiz') || n.includes('activis') || n.includes('campaign') || n.includes('legislation')) return Users;
  if (n.includes('health') || n.includes('medical') || n.includes('wellness')) return Heart;
  if (n.includes('storm') || n.includes('rain') || n.includes('flood')) return CloudRain;
  if (n.includes('mountain') || n.includes('hill')) return Mountain;
  
  return Flower2; // Default
};

const getIssueConfig = (issue) => {
  return {
    icon: getIconFromKeywords(issue),
    ...hashStringToColor((issue || '').toLowerCase().trim())
  };
};

const getDisplayName = (issue) => {
  const names = {
    'enviro-ed': 'Environmental Education', 'enviro ed': 'Environmental Education',
    'enviro-justice': 'Environmental Justice', 'enviro justice': 'Environmental Justice',
    'food/agriculture': 'Food/Agriculture', 'dte energy': 'DTE Energy',
    'air quality': 'Air Quality', 'water quality': 'Water Quality',
    'drinking water': 'Drinking Water', 'workforce development': 'Workforce Development',
  };
  return names[(issue || '').toLowerCase().trim()] || issue;
};

const Organizations = () => {
  const [organizations, setOrganizations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedFocus, setSelectedFocus] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [geographicFilters, setGeographicFilters] = useState({ regions: [], metros: [], locals: [] });
  const [expandedSections, setExpandedSections] = useState({ focus: false, geography: false });
  const [viewMode, setViewMode] = useState('map'); // 'list' or 'map' or 'regions' - DEFAULT TO MAP

  useEffect(() => { fetchOrganizations(); }, []);

  const fetchOrganizations = async () => {
    try {
      setLoading(true);
      const { data, error } = await supabase.from('organizations').select('*').eq('status', 'approved').order('name');
      if (error) throw error;
      setOrganizations(data || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const parseFocusArray = (f) => {
    try {
      if (Array.isArray(f)) return f;
      if (typeof f === 'string' && f.startsWith('[')) return JSON.parse(f.replace(/'/g, '"'));
      if (f) return [f];
    } catch (e) {}
    return [];
  };

  const allFocusAreas = useMemo(() => {
    const s = new Set();
    organizations.forEach(o => parseFocusArray(o.focus).forEach(f => s.add(f)));
    return Array.from(s).sort();
  }, [organizations]);

  const filteredOrganizations = useMemo(() => {
    return organizations.filter(o => {
      if (searchQuery) {
        const q = searchQuery.toLowerCase();
        if (!(o.name || '').toLowerCase().includes(q) && !(o.mission_statement_text || '').toLowerCase().includes(q) && !(o.city || '').toLowerCase().includes(q)) return false;
      }
      if (selectedFocus.length > 0 && !selectedFocus.some(s => parseFocusArray(o.focus).includes(s))) return false;
      if (!matchesGeographicFilter(o, geographicFilters)) return false;
      return true;
    });
  }, [organizations, searchQuery, selectedFocus, geographicFilters]);

  const toggleSection = (s) => setExpandedSections(p => ({ ...p, [s]: !p[s] }));
  const handleFocusChange = (f) => setSelectedFocus(p => p.includes(f) ? p.filter(x => x !== f) : [...p, f]);
  const clearAllFilters = () => { setSelectedFocus([]); setSearchQuery(''); setGeographicFilters({ regions: [], metros: [], locals: [] }); };

  const handleFocusTagClick = (f) => {
    handleFocusChange(f);
    setExpandedSections(p => ({ ...p, focus: true }));
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleRegionClick = (r) => {
    setGeographicFilters({ regions: [r], metros: [], locals: [] });
    setExpandedSections(p => ({ ...p, geography: true }));
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleMetroClick = (m) => {
    const H = {
      "Southeast Michigan": ["Detroit Metro", "Ann Arbor Area", "Tri-County Area", "Monroe Area"],
      "West Michigan": ["Grand Rapids Metro", "Kalamazoo Area", "Muskegon Area", "Holland Area"],
      "Central Michigan": ["Lansing-East Lansing Area", "Flint Area", "Tri-Cities", "Jackson Area"],
      "Upper Peninsula": ["Marquette Area", "Sault Ste. Marie Area", "Escanaba Area", "Houghton-Hancock Area", "Iron Mountain Area"],
      "Northwest Michigan": ["Traverse City Area", "Petoskey-Harbor Springs Area", "Cadillac Area"],
      "Northeast Michigan": ["Alpena Area", "Gaylord Area"],
      "Southwest Michigan": ["Benton Harbor-St. Joseph Area", "Niles Area"]
    };
    let pr = null;
    for (const [r, ms] of Object.entries(H)) { if (ms.includes(m)) { pr = r; break; } }
    setGeographicFilters({ regions: pr ? [pr] : [], metros: [m], locals: [] });
    setExpandedSections(p => ({ ...p, geography: true }));
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const hasActiveFilters = selectedFocus.length > 0 || geographicFilters.regions.length > 0 || geographicFilters.metros.length > 0 || geographicFilters.locals.length > 0 || searchQuery;

  if (loading) return (<div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '100vh' }}><div style={{ border: '4px solid #f3f4f6', borderTop: '4px solid #10b981', borderRadius: '50%', width: '50px', height: '50px', animation: 'spin 1s linear infinite' }}></div><p>Loading...</p></div>);
  if (error) return (<div style={{ textAlign: 'center', padding: '40px' }}><p>Error: {error}</p><button onClick={fetchOrganizations}>Retry</button></div>);

  return (
    <div className="page-container">
      <aside className="sidebar">
        {/* Navigation Buttons */}
        <div className="sidebar-nav">
          <NavLink 
            to="/" 
            className={({ isActive }) => `sidebar-nav-btn ${isActive ? 'active' : ''}`}
          >
            <span className="nav-emoji">🏠</span>
            <span>Browse Directory</span>
          </NavLink>
          <NavLink 
            to="/submit" 
            className={({ isActive }) => `sidebar-nav-btn sidebar-nav-submit ${isActive ? 'active' : ''}`}
          >
            <span className="nav-emoji">➕</span>
            <span>Submit Organization</span>
          </NavLink>
        </div>

        <div className="sidebar-header">
          <h2>Filters</h2>
          {hasActiveFilters && <button className="clear-all-btn" onClick={clearAllFilters}>Clear All</button>}
        </div>
        <div className="search-section">
          <input type="text" placeholder="Search..." value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} className="search-input" />
        </div>
        <div className="filter-section">
          <button className="section-toggle" onClick={() => toggleSection('focus')}>
            <span className="toggle-icon">{expandedSections.focus ? '▼' : '▶'}</span>
            <span className="section-title">Focus Areas</span>
            {selectedFocus.length > 0 && <span className="active-count">{selectedFocus.length}</span>}
          </button>
          {expandedSections.focus && (
            <div className="section-content">
              {allFocusAreas.map(f => (
                <label key={f} className="filter-checkbox">
                  <input type="checkbox" checked={selectedFocus.includes(f)} onChange={() => handleFocusChange(f)} />
                  <span>{getDisplayName(f)}</span>
                </label>
              ))}
            </div>
          )}
        </div>
        <div className="filter-section">
          <button className="section-toggle" onClick={() => toggleSection('geography')}>
            <span className="toggle-icon">{expandedSections.geography ? '▼' : '▶'}</span>
            <span className="section-title">Geography</span>
            {(geographicFilters.regions.length + geographicFilters.metros.length + geographicFilters.locals.length) > 0 && (
              <span className="active-count">{geographicFilters.regions.length + geographicFilters.metros.length + geographicFilters.locals.length}</span>
            )}
          </button>
          {expandedSections.geography && <GeographicFilterContent geographicFilters={geographicFilters} setGeographicFilters={setGeographicFilters} organizations={organizations} />}
        </div>
      </aside>

      <main className="main-content">
        <div className="content-header">
          <div className="header-row">
            <div>
              <h1>Michigan Environmental Organizations Directory</h1>
              <p className="subtitle">Connect with others on the issues you care about</p>
              <p className="results-count">Showing <strong>{filteredOrganizations.length}</strong> of <strong>{organizations.length}</strong></p>
            </div>
            <div className="view-toggle">
              <button 
                className={`toggle-btn ${viewMode === 'list' ? 'active' : ''}`}
                onClick={() => setViewMode('list')}
              >
                📋 List
              </button>
              <button 
                className={`toggle-btn ${viewMode === 'map' ? 'active' : ''}`}
                onClick={() => setViewMode('map')}
              >
                🗺️ Map
              </button>
              <button 
                className={`toggle-btn ${viewMode === 'regions' ? 'active' : ''}`}
                onClick={() => setViewMode('regions')}
              >
                📊 Regions
              </button>
            </div>
          </div>
        </div>
        {filteredOrganizations.length === 0 ? (
          <div className="no-results"><p>No organizations found.</p><button onClick={clearAllFilters}>Clear filters</button></div>
        ) : viewMode === 'map' ? (
          <OrganizationMap organizations={filteredOrganizations} setViewMode={setViewMode} />
        ) : viewMode === 'regions' ? (
          <RegionTable organizations={filteredOrganizations} />
        ) : (
          <div className="organizations-grid">
            {filteredOrganizations.map(o => <OrganizationCard key={o.id} organization={o} onFocusClick={handleFocusTagClick} onRegionClick={handleRegionClick} onMetroClick={handleMetroClick} />)}
          </div>
        )}
      </main>

      <style jsx>{`
        .page-container { display: flex; min-height: 100vh; background: #f9fafb; }
        .sidebar { width: 300px; background: white; border-right: 1px solid #e5e7eb; padding: 20px; position: sticky; top: 0; height: 100vh; overflow-y: auto; }
        
        /* Sidebar Navigation */
        .sidebar-nav { display: flex; flex-direction: column; gap: 8px; margin-bottom: 20px; padding-bottom: 20px; border-bottom: 2px solid #e5e7eb; }
        .sidebar-nav-btn { display: flex; align-items: center; gap: 10px; padding: 12px 16px; background: #f1f5f9; border: 2px solid #e2e8f0; border-radius: 8px; text-decoration: none; color: #64748b; font-weight: 600; font-size: 14px; transition: all 0.2s; }
        .sidebar-nav-btn:hover { background: #e2e8f0; color: #1e293b; transform: translateX(2px); }
        .sidebar-nav-btn.active { background: white; color: #14b8a6; border-color: #14b8a6; }
        .sidebar-nav-submit { background: #e0f2fe; color: #08143d; border-color: #bae6fd; }
        .sidebar-nav-submit:hover { background: #bae6fd; }
        .sidebar-nav-submit.active { background: #bae6fd; color: #08143d; border-color: #08143d; }
        .nav-emoji { font-size: 18px; }
        
        .sidebar-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; padding-bottom: 15px; border-bottom: 2px solid #e5e7eb; }
        .sidebar-header h2 { margin: 0; font-size: 20px; color: #1e293b; }
        .clear-all-btn { background: #ef4444; color: white; border: none; padding: 6px 12px; border-radius: 4px; font-size: 12px; cursor: pointer; }
        .search-section { margin-bottom: 20px; }
        .search-input { width: 100%; padding: 10px 12px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 14px; }
        .filter-section { margin-bottom: 10px; border: 1px solid #e5e7eb; border-radius: 6px; overflow: hidden; }
        .section-toggle { width: 100%; display: flex; align-items: center; gap: 10px; padding: 12px 15px; background: #f9fafb; border: none; cursor: pointer; font-size: 14px; font-weight: 600; color: #1e293b; }
        .toggle-icon { color: #10b981; font-size: 12px; }
        .section-title { flex: 1; text-align: left; }
        .active-count { background: #10b981; color: white; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: 600; }
        .section-content { padding: 15px; background: white; max-height: 400px; overflow-y: auto; }
        .filter-checkbox { display: flex; align-items: center; padding: 6px 0; cursor: pointer; font-size: 14px; color: #374151; }
        .filter-checkbox input { margin-right: 10px; cursor: pointer; }
        .main-content { flex: 1; padding: 30px; }
        .content-header h1 { font-size: 32px; color: #1e293b; margin: 0 0 8px 0; }
        .subtitle { font-size: 18px; color: #64748b; font-style: italic; margin: 0 0 10px 0; }
        .header-row { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px; }
        .view-toggle { display: flex; gap: 8px; }
        .toggle-btn { background: white; border: 1px solid #d1d5db; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-size: 14px; transition: all 0.2s; }
        .toggle-btn:hover { background: #f3f4f6; }
        .toggle-btn.active { background: #10b981; color: white; border-color: #10b981; }
        .results-count { color: #64748b; font-size: 16px; }
        .organizations-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(350px, 1fr)); gap: 24px; margin-top: 30px; }
        .no-results { text-align: center; padding: 60px 20px; color: #64748b; }
        @media (max-width: 768px) { .page-container { flex-direction: column; } .sidebar { width: 100%; position: static; height: auto; } }
      `}</style>
    </div>
  );
};

const GeographicFilterContent = ({ geographicFilters, setGeographicFilters, organizations }) => {
  const [expandedGeo, setExpandedGeo] = useState({ region: false, metro: false, local: false });
  const [localSearch, setLocalSearch] = useState('');
  const H = { "Southeast Michigan": ["Detroit Metro", "Ann Arbor Area", "Tri-County Area", "Monroe Area"], "West Michigan": ["Grand Rapids Metro", "Kalamazoo Area", "Muskegon Area", "Holland Area"], "Central Michigan": ["Lansing-East Lansing Area", "Flint Area", "Tri-Cities", "Jackson Area"], "Upper Peninsula": ["Marquette Area", "Sault Ste. Marie Area", "Escanaba Area", "Houghton-Hancock Area", "Iron Mountain Area"], "Northwest Michigan": ["Traverse City Area", "Petoskey-Harbor Springs Area", "Cadillac Area"], "Northeast Michigan": ["Alpena Area", "Gaylord Area"], "Southwest Michigan": ["Benton Harbor-St. Joseph Area", "Niles Area"] };
  const availableRegions = Object.keys(H);
  const availableMetros = geographicFilters.regions.length > 0 ? geographicFilters.regions.flatMap(r => H[r] || []) : [];
  const availableLocals = geographicFilters.metros.length > 0 ? organizations.filter(o => geographicFilters.metros.includes(o.metro_area)).flatMap(o => Array.isArray(o.geo_location) ? o.geo_location : []).filter((v, i, a) => a.indexOf(v) === i).sort() : [];
  const filteredLocals = availableLocals.filter(l => l.toLowerCase().includes(localSearch.toLowerCase()));
  const handleRegionChange = (r) => { const n = geographicFilters.regions.includes(r) ? geographicFilters.regions.filter(x => x !== r) : [...geographicFilters.regions, r]; setGeographicFilters({ regions: n, metros: n.length === 0 ? [] : geographicFilters.metros, locals: n.length === 0 ? [] : geographicFilters.locals }); };
  const handleMetroChange = (m) => { const n = geographicFilters.metros.includes(m) ? geographicFilters.metros.filter(x => x !== m) : [...geographicFilters.metros, m]; setGeographicFilters({ ...geographicFilters, metros: n, locals: n.length === 0 ? [] : geographicFilters.locals }); };
  const handleLocalChange = (l) => { const n = geographicFilters.locals.includes(l) ? geographicFilters.locals.filter(x => x !== l) : [...geographicFilters.locals, l]; setGeographicFilters({ ...geographicFilters, locals: n }); };

  return (
    <div className="geo-content">
      <div className="geo-subsection">
        <button className="geo-toggle" onClick={() => setExpandedGeo(p => ({ ...p, region: !p.region }))}><span>{expandedGeo.region ? '▼' : '▶'}</span> Region</button>
        {expandedGeo.region && (<div className="geo-list">{availableRegions.map(r => (<label key={r} className="geo-checkbox"><input type="checkbox" checked={geographicFilters.regions.includes(r)} onChange={() => handleRegionChange(r)} /><span>{r}</span></label>))}</div>)}
      </div>
      <div className="geo-subsection">
        <button className="geo-toggle" onClick={() => setExpandedGeo(p => ({ ...p, metro: !p.metro }))} disabled={geographicFilters.regions.length === 0}><span>{expandedGeo.metro ? '▼' : '▶'}</span> Metro</button>
        {expandedGeo.metro && availableMetros.length > 0 && (<div className="geo-list">{availableMetros.map(m => (<label key={m} className="geo-checkbox"><input type="checkbox" checked={geographicFilters.metros.includes(m)} onChange={() => handleMetroChange(m)} /><span>{m}</span></label>))}</div>)}
      </div>
      <div className="geo-subsection">
        <button className="geo-toggle" onClick={() => setExpandedGeo(p => ({ ...p, local: !p.local }))} disabled={geographicFilters.metros.length === 0}><span>{expandedGeo.local ? '▼' : '▶'}</span> Local</button>
        {expandedGeo.local && availableLocals.length > 0 && (<div className="geo-list"><input type="text" placeholder="Search..." value={localSearch} onChange={(e) => setLocalSearch(e.target.value)} className="local-search" />{filteredLocals.map(l => (<label key={l} className="geo-checkbox"><input type="checkbox" checked={geographicFilters.locals.includes(l)} onChange={() => handleLocalChange(l)} /><span>{l}</span></label>))}</div>)}
      </div>
      <style jsx>{`.geo-content { display: flex; flex-direction: column; gap: 10px; } .geo-subsection { border: 1px solid #e5e7eb; border-radius: 4px; overflow: hidden; } .geo-toggle { width: 100%; display: flex; align-items: center; gap: 8px; padding: 8px 12px; background: #f9fafb; border: none; cursor: pointer; font-size: 13px; } .geo-toggle:disabled { opacity: 0.5; cursor: not-allowed; } .geo-list { padding: 10px 12px; background: white; max-height: 200px; overflow-y: auto; } .geo-checkbox { display: flex; align-items: center; padding: 4px 0; cursor: pointer; font-size: 13px; } .geo-checkbox input { margin-right: 8px; } .local-search { width: 100%; padding: 6px 8px; border: 1px solid #d1d5db; border-radius: 4px; font-size: 12px; margin-bottom: 8px; }`}</style>
    </div>
  );
};

const OrganizationCard = ({ organization, onFocusClick, onRegionClick, onMetroClick }) => {
  const parseFocusArray = (f) => { try { if (Array.isArray(f)) return f; if (typeof f === 'string' && f.startsWith('[')) return JSON.parse(f.replace(/'/g, '"')); if (f) return [f]; } catch (e) {} return []; };
  const focusAreas = parseFocusArray(organization.focus);
  const isPlanetChampion = organization.planet_champion === true || organization.planet_champion === 'true';
  const isImpactPartner = !isPlanetChampion && (organization.impact_partner === true || organization.impact_partner === 'true');

  return (
    <div className="org-card">
      <div className="card-header">
        <h3>{organization.name}</h3>
        {(isImpactPartner || isPlanetChampion) && (
          <div className="partnership-badges">
            {isPlanetChampion && <a href="https://planetdetroit.org/impactpartners/" target="_blank" rel="noopener noreferrer" className="partner-badge planet-champion">🌟 Planet Champion</a>}
            {isImpactPartner && <a href="https://planetdetroit.org/impactpartners/" target="_blank" rel="noopener noreferrer" className="partner-badge impact-partner">⭐ Impact Partner</a>}
          </div>
        )}
      </div>
      {organization.city && <p className="city">📍 {organization.city}</p>}
      {organization.mission_statement_text && <p className="mission">{organization.mission_statement_text}</p>}
      {(organization.region || organization.metro_area) && (
        <div className="geo-badges">
          {organization.region && <button className="badge region" onClick={() => onRegionClick(organization.region)}>{organization.region}</button>}
          {organization.metro_area && <button className="badge metro" onClick={() => onMetroClick(organization.metro_area)}>{organization.metro_area}</button>}
        </div>
      )}
      {focusAreas.length > 0 && (
        <div className="tags">
          <div className="tag-label">Focus:</div>
          {focusAreas.map(f => {
            const { icon: Icon, color, bg } = getIssueConfig(f);
            const dn = getDisplayName(f);
            return (<button key={f} className="tag" onClick={() => onFocusClick(f)} style={{ backgroundColor: bg, color: color, border: `1px solid ${color}` }} title={`Filter by ${dn}`}><Icon size={14} style={{ marginRight: '4px', display: 'inline-block', verticalAlign: 'middle' }} /><span style={{ display: 'inline-block', verticalAlign: 'middle' }}>{dn}</span></button>);
          })}
        </div>
      )}
      {organization.url && (<div className="org-footer"><a href={organization.url} target="_blank" rel="noopener noreferrer" className="website-link">🌐 Visit Website</a></div>)}
      {organization.ein && (
        <div className="org-footer">
          <a href={`https://projects.propublica.org/nonprofits/organizations/${organization.ein}`} target="_blank" rel="noopener noreferrer" className="propublica-link">
            📄 990 Forms
          </a>
        </div>
      )}
      <style jsx>{`.org-card { background: white; border-radius: 8px; padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); transition: transform 0.2s, box-shadow 0.2s; } .org-card:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.15); } .card-header { margin-bottom: 8px; } .org-card h3 { margin: 0 0 8px 0; color: #1e293b; font-size: 18px; } .partnership-badges { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 8px; } .partner-badge { display: inline-block; padding: 4px 10px; border-radius: 4px; font-size: 11px; font-weight: 600; text-decoration: none; } .impact-partner { background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: white; } .planet-champion { background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); color: white; } .city { color: #64748b; font-size: 13px; margin: 0 0 12px 0; } .mission { color: #475569; font-size: 14px; line-height: 1.5; margin: 0 0 12px 0; } .geo-badges { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 12px; } .badge { padding: 4px 10px; border-radius: 4px; font-size: 11px; font-weight: 500; border: none; cursor: pointer; transition: all 0.2s; } .badge.region { background: #fef3c7; color: #92400e; border: 1px solid #f59e0b; } .badge.region:hover { background: #f59e0b; color: white; } .badge.metro { background: #dbeafe; color: #1e40af; border: 1px solid #3b82f6; } .badge.metro:hover { background: #3b82f6; color: white; } .tags { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; margin-bottom: 12px; } .tag-label { font-size: 11px; font-weight: 600; color: #64748b; text-transform: uppercase; } .tag { padding: 5px 10px; border-radius: 4px; font-size: 12px; font-weight: 500; display: inline-flex; align-items: center; cursor: pointer; transition: all 0.2s; } .tag:hover { opacity: 0.8; transform: translateY(-1px); box-shadow: 0 2px 4px rgba(0,0,0,0.15); } .org-footer { margin-top: 12px; padding-top: 12px; border-top: 1px solid #e5e7eb; } .website-link { display: inline-block; color: #2563eb; text-decoration: none; font-size: 15px; font-weight: 700; } .website-link:hover { color: #1d4ed8; text-decoration: underline; } .propublica-link { display: inline-block; color: #64748b; text-decoration: none; font-size: 12px; font-weight: 400; margin-left: 15px; } .propublica-link:hover { color: #475569; text-decoration: underline; }`}</style>
    </div>
  );
};

export default Organizations;
