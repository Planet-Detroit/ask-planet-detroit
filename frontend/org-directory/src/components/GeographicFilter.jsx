import React, { useState, useMemo } from 'react';
import { 
  MICHIGAN_HIERARCHY, 
  getRegions, 
  getMetrosForRegions, 
  getLocalsForMetros,
  getAllLocals 
} from '../utils/geographicHierarchy';

const GeographicFilter = ({ onChange, organizations }) => {
  const [selectedRegions, setSelectedRegions] = useState([]);
  const [selectedMetros, setSelectedMetros] = useState([]);
  const [selectedLocals, setSelectedLocals] = useState([]);
  const [localSearch, setLocalSearch] = useState('');
  
  const [expandedSections, setExpandedSections] = useState({
    region: true,  // Start with region expanded
    metro: false,
    local: false
  });

  // Get available options based on selections
  const availableRegions = getRegions();
  
  const availableMetros = useMemo(() => {
    return selectedRegions.length > 0 
      ? getMetrosForRegions(selectedRegions)
      : [];
  }, [selectedRegions]);
  
  const availableLocals = useMemo(() => {
    return selectedMetros.length > 0
      ? getLocalsForMetros(selectedMetros)
      : selectedRegions.length > 0
      ? [] // Don't show locals until metro selected
      : getAllLocals();
  }, [selectedMetros, selectedRegions]);

  // Filter locals by search
  const filteredLocals = useMemo(() => {
    if (!localSearch) return availableLocals;
    return availableLocals.filter(local =>
      local.toLowerCase().includes(localSearch.toLowerCase())
    );
  }, [availableLocals, localSearch]);

  // Count orgs for each option
  const countOrgs = (filterType, value) => {
    if (!organizations) return 0;
    
    return organizations.filter(org => {
      if (filterType === 'region') {
        return org.region === value;
      } else if (filterType === 'metro') {
        return org.metro_area === value;
      } else if (filterType === 'local') {
        const geoLocs = Array.isArray(org.geo_location) ? org.geo_location : [];
        return geoLocs.includes(value);
      }
      return false;
    }).length;
  };

  // Handle selections
  const handleRegionChange = (region) => {
    const newRegions = selectedRegions.includes(region)
      ? selectedRegions.filter(r => r !== region)
      : [...selectedRegions, region];
    
    setSelectedRegions(newRegions);
    
    // Clear metros and locals if region deselected
    if (!newRegions.includes(region)) {
      const metrosToRemove = Object.keys(MICHIGAN_HIERARCHY[region] || {});
      setSelectedMetros(prev => prev.filter(m => !metrosToRemove.includes(m)));
      setSelectedLocals([]);
    }
    
    notifyChange(newRegions, selectedMetros, selectedLocals);
  };

  const handleMetroChange = (metro) => {
    const newMetros = selectedMetros.includes(metro)
      ? selectedMetros.filter(m => m !== metro)
      : [...selectedMetros, metro];
    
    setSelectedMetros(newMetros);
    
    // Clear locals if metro deselected
    if (!newMetros.includes(metro)) {
      const localsToRemove = Object.values(MICHIGAN_HIERARCHY)
        .flatMap(region => Object.entries(region))
        .filter(([metroName]) => metroName === metro)
        .flatMap(([, locals]) => locals);
      
      setSelectedLocals(prev => prev.filter(l => !localsToRemove.includes(l)));
    }
    
    notifyChange(selectedRegions, newMetros, selectedLocals);
  };

  const handleLocalChange = (local) => {
    const newLocals = selectedLocals.includes(local)
      ? selectedLocals.filter(l => l !== local)
      : [...selectedLocals, local];
    
    setSelectedLocals(newLocals);
    notifyChange(selectedRegions, selectedMetros, newLocals);
  };

  const notifyChange = (regions, metros, locals) => {
    onChange({
      regions,
      metros,
      locals
    });
  };

  const clearAll = () => {
    setSelectedRegions([]);
    setSelectedMetros([]);
    setSelectedLocals([]);
    setLocalSearch('');
    onChange({
      regions: [],
      metros: [],
      locals: []
    });
  };

  const toggleSection = (section) => {
    setExpandedSections(prev => ({
      ...prev,
      [section]: !prev[section]
    }));
  };

  return (
    <div className="geographic-filter">
      <div className="filter-header">
        <h3>📍 Geographic Filters</h3>
        {(selectedRegions.length > 0 || selectedMetros.length > 0 || selectedLocals.length > 0) && (
          <button className="clear-all-btn" onClick={clearAll}>
            Clear All
          </button>
        )}
      </div>

      {/* Region Section */}
      <div className="filter-section">
        <button 
          className="section-header"
          onClick={() => toggleSection('region')}
        >
          <span className="expand-icon">{expandedSections.region ? '▼' : '▶'}</span>
          <span className="section-title">Region</span>
          {selectedRegions.length > 0 && (
            <span className="selection-badge">{selectedRegions.length} selected</span>
          )}
        </button>
        
        {expandedSections.region && (
          <div className="section-content">
            {availableRegions.map(region => (
              <label key={region} className="filter-checkbox">
                <input
                  type="checkbox"
                  checked={selectedRegions.includes(region)}
                  onChange={() => handleRegionChange(region)}
                />
                <span className="checkbox-label">
                  {region}
                  <span className="org-count">({countOrgs('region', region)})</span>
                </span>
              </label>
            ))}
          </div>
        )}
      </div>

      {/* Metro Area Section */}
      <div className="filter-section">
        <button 
          className="section-header"
          onClick={() => toggleSection('metro')}
          disabled={selectedRegions.length === 0}
        >
          <span className="expand-icon">{expandedSections.metro ? '▼' : '▶'}</span>
          <span className="section-title">Metro Area</span>
          {selectedMetros.length > 0 && (
            <span className="selection-badge">{selectedMetros.length} selected</span>
          )}
          {selectedRegions.length === 0 && (
            <span className="disabled-hint">Select region first</span>
          )}
        </button>
        
        {expandedSections.metro && availableMetros.length > 0 && (
          <div className="section-content">
            {availableMetros.map(metro => (
              <label key={metro} className="filter-checkbox">
                <input
                  type="checkbox"
                  checked={selectedMetros.includes(metro)}
                  onChange={() => handleMetroChange(metro)}
                />
                <span className="checkbox-label">
                  {metro}
                  <span className="org-count">({countOrgs('metro', metro)})</span>
                </span>
              </label>
            ))}
          </div>
        )}
      </div>

      {/* Local Area Section */}
      <div className="filter-section">
        <button 
          className="section-header"
          onClick={() => toggleSection('local')}
          disabled={selectedMetros.length === 0 && selectedRegions.length > 0}
        >
          <span className="expand-icon">{expandedSections.local ? '▼' : '▶'}</span>
          <span className="section-title">Local</span>
          {selectedLocals.length > 0 && (
            <span className="selection-badge">{selectedLocals.length} selected</span>
          )}
          {selectedRegions.length > 0 && selectedMetros.length === 0 && (
            <span className="disabled-hint">Select metro first</span>
          )}
        </button>
        
        {expandedSections.local && availableLocals.length > 0 && (
          <div className="section-content">
            <div className="local-search">
              <input
                type="text"
                placeholder="🔍 Search cities, counties, watersheds..."
                value={localSearch}
                onChange={(e) => setLocalSearch(e.target.value)}
                className="search-input"
              />
            </div>
            
            <div className="local-checkboxes">
              {filteredLocals.length > 0 ? (
                filteredLocals.map(local => (
                  <label key={local} className="filter-checkbox">
                    <input
                      type="checkbox"
                      checked={selectedLocals.includes(local)}
                      onChange={() => handleLocalChange(local)}
                    />
                    <span className="checkbox-label">
                      {local}
                      <span className="org-count">({countOrgs('local', local)})</span>
                    </span>
                  </label>
                ))
              ) : (
                <div className="no-results">No matches for "{localSearch}"</div>
              )}
            </div>
            
            {selectedLocals.length > 0 && (
              <div className="selected-locals">
                <strong>Selected ({selectedLocals.length}):</strong>
                {selectedLocals.map(local => (
                  <span key={local} className="selected-tag">
                    {local}
                    <button onClick={() => handleLocalChange(local)}>×</button>
                  </span>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      <style jsx>{`
        .geographic-filter {
          background: white;
          border-radius: 8px;
          padding: 20px;
          box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        .filter-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 20px;
          padding-bottom: 15px;
          border-bottom: 2px solid #e5e7eb;
        }

        .filter-header h3 {
          margin: 0;
          color: #1e293b;
          font-size: 18px;
        }

        .clear-all-btn {
          background: #ef4444;
          color: white;
          border: none;
          padding: 6px 12px;
          border-radius: 4px;
          font-size: 13px;
          cursor: pointer;
          transition: background 0.2s;
        }

        .clear-all-btn:hover {
          background: #dc2626;
        }

        .filter-section {
          border: 1px solid #e5e7eb;
          border-radius: 6px;
          margin-bottom: 12px;
          overflow: hidden;
        }

        .section-header {
          width: 100%;
          display: flex;
          align-items: center;
          gap: 10px;
          padding: 12px 15px;
          background: #f9fafb;
          border: none;
          cursor: pointer;
          font-size: 14px;
          font-weight: 600;
          color: #1e293b;
          transition: background 0.2s;
        }

        .section-header:hover:not(:disabled) {
          background: #f3f4f6;
        }

        .section-header:disabled {
          cursor: not-allowed;
          opacity: 0.5;
        }

        .expand-icon {
          color: #10b981;
          font-size: 12px;
          min-width: 16px;
        }

        .section-title {
          flex: 1;
          text-align: left;
        }

        .selection-badge {
          background: #10b981;
          color: white;
          padding: 2px 8px;
          border-radius: 12px;
          font-size: 11px;
          font-weight: 600;
        }

        .disabled-hint {
          color: #9ca3af;
          font-size: 12px;
          font-weight: normal;
          font-style: italic;
        }

        .section-content {
          padding: 15px;
          background: white;
        }

        .filter-checkbox {
          display: flex;
          align-items: center;
          padding: 8px 0;
          cursor: pointer;
          user-select: none;
        }

        .filter-checkbox input[type="checkbox"] {
          margin-right: 10px;
          cursor: pointer;
        }

        .checkbox-label {
          flex: 1;
          display: flex;
          justify-content: space-between;
          align-items: center;
          font-size: 14px;
          color: #374151;
        }

        .org-count {
          color: #6b7280;
          font-size: 12px;
          margin-left: 8px;
        }

        .local-search {
          margin-bottom: 12px;
        }

        .search-input {
          width: 100%;
          padding: 8px 12px;
          border: 1px solid #d1d5db;
          border-radius: 4px;
          font-size: 14px;
        }

        .search-input:focus {
          outline: none;
          border-color: #10b981;
          box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.1);
        }

        .local-checkboxes {
          max-height: 300px;
          overflow-y: auto;
        }

        .no-results {
          padding: 20px;
          text-align: center;
          color: #9ca3af;
          font-size: 14px;
        }

        .selected-locals {
          margin-top: 12px;
          padding-top: 12px;
          border-top: 1px solid #e5e7eb;
        }

        .selected-locals strong {
          display: block;
          margin-bottom: 8px;
          font-size: 13px;
          color: #1e293b;
        }

        .selected-tag {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          background: #dbeafe;
          color: #1e40af;
          padding: 4px 8px;
          border-radius: 4px;
          font-size: 12px;
          margin-right: 6px;
          margin-bottom: 6px;
        }

        .selected-tag button {
          background: none;
          border: none;
          color: #1e40af;
          font-size: 16px;
          font-weight: bold;
          cursor: pointer;
          padding: 0;
          width: 16px;
          height: 16px;
          display: flex;
          align-items: center;
          justify-content: center;
          border-radius: 50%;
        }

        .selected-tag button:hover {
          background: #bfdbfe;
        }
      `}</style>
    </div>
  );
};

export default GeographicFilter;
