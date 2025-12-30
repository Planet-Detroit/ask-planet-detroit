import React, { useState, useMemo } from 'react';

const RegionTable = ({ organizations, onOrgClick }) => {
  const [expandedRegion, setExpandedRegion] = useState(null);
  const [expandedMetro, setExpandedMetro] = useState(null);
  const [sortBy, setSortBy] = useState('region'); // region, count, name

  // Group organizations by region and metro
  const regionData = useMemo(() => {
    const data = {};
    
    organizations.forEach(org => {
      const region = org.region || 'Unspecified';
      const metro = org.metro_area || 'No Metro';
      
      if (!data[region]) {
        data[region] = {
          name: region,
          metros: {},
          totalOrgs: 0
        };
      }
      
      if (!data[region].metros[metro]) {
        data[region].metros[metro] = {
          name: metro,
          orgs: []
        };
      }
      
      data[region].metros[metro].orgs.push(org);
      data[region].totalOrgs++;
    });
    
    return data;
  }, [organizations]);

  // Sort regions
  const sortedRegions = useMemo(() => {
    const regions = Object.values(regionData);
    
    if (sortBy === 'count') {
      return regions.sort((a, b) => b.totalOrgs - a.totalOrgs);
    } else if (sortBy === 'name') {
      return regions.sort((a, b) => a.name.localeCompare(b.name));
    }
    
    return regions;
  }, [regionData, sortBy]);

  const toggleRegion = (regionName) => {
    if (expandedRegion === regionName) {
      setExpandedRegion(null);
      setExpandedMetro(null);
    } else {
      setExpandedRegion(regionName);
      setExpandedMetro(null);
    }
  };

  const toggleMetro = (metroName) => {
    setExpandedMetro(expandedMetro === metroName ? null : metroName);
  };

  // Get focus tags for display
  const parseFocusArray = (focus) => {
    try {
      if (Array.isArray(focus)) return focus;
      if (typeof focus === 'string' && focus.startsWith('[')) {
        return JSON.parse(focus.replace(/'/g, '"'));
      }
      if (focus) return [focus];
    } catch (e) {}
    return [];
  };

  return (
    <div className="region-table">
      <div className="table-header">
        <h2>Organizations by Region</h2>
        <div className="sort-controls">
          <label>Sort by:</label>
          <button 
            className={`sort-btn ${sortBy === 'region' ? 'active' : ''}`}
            onClick={() => setSortBy('region')}
          >
            Region
          </button>
          <button 
            className={`sort-btn ${sortBy === 'count' ? 'active' : ''}`}
            onClick={() => setSortBy('count')}
          >
            Count
          </button>
          <button 
            className={`sort-btn ${sortBy === 'name' ? 'active' : ''}`}
            onClick={() => setSortBy('name')}
          >
            A-Z
          </button>
        </div>
      </div>

      <div className="regions-list">
        {sortedRegions.map(region => {
          const isExpanded = expandedRegion === region.name;
          const metros = Object.values(region.metros);
          
          return (
            <div key={region.name} className="region-section">
              <button 
                className="region-header"
                onClick={() => toggleRegion(region.name)}
              >
                <span className="expand-icon">{isExpanded ? '▼' : '▶'}</span>
                <span className="region-name">{region.name}</span>
                <span className="region-count">{region.totalOrgs} organizations</span>
              </button>

              {isExpanded && (
                <div className="region-content">
                  {metros.map(metro => {
                    const isMetroExpanded = expandedMetro === metro.name;
                    
                    return (
                      <div key={metro.name} className="metro-section">
                        <button 
                          className="metro-header"
                          onClick={() => toggleMetro(metro.name)}
                        >
                          <span className="expand-icon">{isMetroExpanded ? '▼' : '▶'}</span>
                          <span className="metro-name">{metro.name}</span>
                          <span className="metro-count">{metro.orgs.length}</span>
                        </button>

                        {isMetroExpanded && (
                          <div className="org-list">
                            {metro.orgs.map(org => (
                              <div 
                                key={org.id} 
                                className="org-row"
                                onClick={() => onOrgClick && onOrgClick(org)}
                              >
                                <div className="org-main">
                                  <h4>{org.name}</h4>
                                  {org.city && <span className="org-city">📍 {org.city}</span>}
                                </div>
                                
                                {org.mission_statement_text && (
                                  <p className="org-mission">{org.mission_statement_text}</p>
                                )}
                                
                                {org.focus && (
                                  <div className="org-focus">
                                    <strong>Focus:</strong> {parseFocusArray(org.focus).join(', ')}
                                  </div>
                                )}
                                
                                {org.url && (
                                  <a 
                                    href={org.url} 
                                    target="_blank" 
                                    rel="noopener noreferrer"
                                    className="org-link"
                                    onClick={(e) => e.stopPropagation()}
                                  >
                                    🌐 Visit Website
                                  </a>
                                )}
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </div>

      <style jsx>{`
        .region-table {
          background: white;
          border-radius: 12px;
          padding: 30px;
          box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }

        .table-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 30px;
          padding-bottom: 20px;
          border-bottom: 2px solid #e5e7eb;
        }

        .table-header h2 {
          margin: 0;
          font-size: 24px;
          color: #1e293b;
        }

        .sort-controls {
          display: flex;
          align-items: center;
          gap: 10px;
        }

        .sort-controls label {
          font-size: 14px;
          color: #64748b;
          font-weight: 500;
        }

        .sort-btn {
          background: white;
          border: 1px solid #d1d5db;
          padding: 6px 12px;
          border-radius: 6px;
          cursor: pointer;
          font-size: 13px;
          transition: all 0.2s;
        }

        .sort-btn:hover {
          background: #f3f4f6;
        }

        .sort-btn.active {
          background: #10b981;
          color: white;
          border-color: #10b981;
        }

        .regions-list {
          display: flex;
          flex-direction: column;
          gap: 10px;
        }

        .region-section {
          border: 1px solid #e5e7eb;
          border-radius: 8px;
          overflow: hidden;
        }

        .region-header {
          width: 100%;
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 16px 20px;
          background: #f9fafb;
          border: none;
          cursor: pointer;
          font-size: 16px;
          font-weight: 600;
          color: #1e293b;
          transition: background 0.2s;
        }

        .region-header:hover {
          background: #f3f4f6;
        }

        .expand-icon {
          color: #10b981;
          font-size: 12px;
          width: 20px;
        }

        .region-name {
          flex: 1;
          text-align: left;
        }

        .region-count {
          background: #10b981;
          color: white;
          padding: 4px 12px;
          border-radius: 12px;
          font-size: 12px;
          font-weight: 600;
        }

        .region-content {
          padding: 10px;
          background: white;
        }

        .metro-section {
          margin-bottom: 8px;
          border: 1px solid #e5e7eb;
          border-radius: 6px;
          overflow: hidden;
        }

        .metro-header {
          width: 100%;
          display: flex;
          align-items: center;
          gap: 10px;
          padding: 12px 16px;
          background: white;
          border: none;
          cursor: pointer;
          font-size: 14px;
          font-weight: 500;
          color: #475569;
          transition: background 0.2s;
        }

        .metro-header:hover {
          background: #f9fafb;
        }

        .metro-name {
          flex: 1;
          text-align: left;
        }

        .metro-count {
          background: #3b82f6;
          color: white;
          padding: 2px 8px;
          border-radius: 10px;
          font-size: 11px;
          font-weight: 600;
        }

        .org-list {
          padding: 10px;
          background: #f9fafb;
          display: flex;
          flex-direction: column;
          gap: 10px;
        }

        .org-row {
          background: white;
          border: 1px solid #e5e7eb;
          border-radius: 6px;
          padding: 15px;
          cursor: pointer;
          transition: all 0.2s;
        }

        .org-row:hover {
          border-color: #10b981;
          box-shadow: 0 2px 8px rgba(16, 185, 129, 0.1);
        }

        .org-main {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          margin-bottom: 8px;
        }

        .org-row h4 {
          margin: 0;
          font-size: 16px;
          color: #1e293b;
        }

        .org-city {
          font-size: 12px;
          color: #64748b;
          white-space: nowrap;
        }

        .org-mission {
          font-size: 13px;
          color: #475569;
          line-height: 1.5;
          margin: 8px 0;
        }

        .org-focus {
          font-size: 12px;
          color: #64748b;
          margin: 8px 0;
        }

        .org-focus strong {
          color: #1e293b;
        }

        .org-link {
          display: inline-block;
          color: #2563eb;
          text-decoration: none;
          font-size: 13px;
          font-weight: 600;
          margin-top: 8px;
        }

        .org-link:hover {
          text-decoration: underline;
        }

        @media (max-width: 768px) {
          .table-header {
            flex-direction: column;
            align-items: flex-start;
            gap: 15px;
          }

          .sort-controls {
            width: 100%;
            justify-content: space-between;
          }

          .region-header,
          .metro-header {
            font-size: 14px;
          }

          .org-main {
            flex-direction: column;
            gap: 5px;
          }
        }
      `}</style>
    </div>
  );
};

export default RegionTable;
