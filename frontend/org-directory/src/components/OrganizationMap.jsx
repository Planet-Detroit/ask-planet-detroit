import React, { useState, useMemo } from 'react';
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

// Fix default marker icons in Leaflet
import icon from 'leaflet/dist/images/marker-icon.png';
import iconShadow from 'leaflet/dist/images/marker-shadow.png';

let DefaultIcon = L.icon({
  iconUrl: icon,
  shadowUrl: iconShadow,
  iconSize: [18, 29],      // Reduced from [25, 41]
  iconAnchor: [9, 29],     // Adjusted anchor
  popupAnchor: [1, -25],   // Adjusted popup
  shadowSize: [29, 29]     // Adjusted shadow
});

L.Marker.prototype.options.icon = DefaultIcon;

const OrganizationMap = ({ organizations, selectedOrg = null, onOrgSelect = null, setViewMode = null }) => {
  const [mapCenter] = useState([44.3148, -85.6024]); // Michigan center
  const [mapZoom] = useState(6.5); // Zoomed out to show full state

  // Filter to only organizations with REAL coordinates
  const orgsWithCoords = useMemo(() => {
    return organizations.filter(org => 
      org.latitude && 
      org.longitude && 
      !isNaN(parseFloat(org.latitude)) && 
      !isNaN(parseFloat(org.longitude))
    );
  }, [organizations]);

  const orgsWithoutCoords = organizations.length - orgsWithCoords.length;

  // Create simple markers for organizations with real coordinates
  const organizationMarkers = useMemo(() => {
    return orgsWithCoords.map(org => ({
      id: org.id,
      lat: parseFloat(org.latitude),
      lng: parseFloat(org.longitude),
      org: org
    }));
  }, [orgsWithCoords]);

  const handleMarkerClick = (org) => {
    if (onOrgSelect) {
      onOrgSelect(org);
    }
  };

  return (
    <div className="map-container">
      {/* Stats Banner */}
      <div className="coord-stats-banner">
        <div className="stats-content">
          <span className="stats-icon">📍</span>
          <div className="stats-text">
            <strong>Showing {orgsWithCoords.length} of {organizations.length} organizations with known locations</strong>
            {orgsWithoutCoords > 0 && (
              <p>
                {orgsWithoutCoords} organizations don't have exact addresses. Use the{' '}
                <button 
                  onClick={() => setViewMode && setViewMode('list')} 
                  className="view-link-btn"
                >
                  Grid view
                </button>
                {' '}to see all organizations.
              </p>
            )}
          </div>
        </div>
      </div>

      {/* The Map */}
      <MapContainer
        center={mapCenter}
        zoom={mapZoom}
        style={{ height: '600px', width: '100%', borderRadius: '8px' }}
        scrollWheelZoom={true}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        
        {organizationMarkers.map((marker) => (
          <Marker
            key={marker.id}
            position={[marker.lat, marker.lng]}
            eventHandlers={{
              click: () => handleMarkerClick(marker.org)
            }}
          >
            <Popup maxWidth={350}>
              <div className="marker-popup">
                <h4>{marker.org.name}</h4>
                {marker.org.city && <p className="org-city">📍 {marker.org.city}</p>}
                
                {marker.org.mission_statement_text && (
                  <p className="org-mission">{marker.org.mission_statement_text.substring(0, 150)}...</p>
                )}
                
                {marker.org.focus && (
                  <p className="org-focus">
                    <strong>Focus:</strong> {Array.isArray(marker.org.focus) ? marker.org.focus.join(', ') : marker.org.focus}
                  </p>
                )}
                
                {marker.org.url && (
                  <a 
                    href={marker.org.url} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="popup-link"
                  >
                    🌐 Visit Website
                  </a>
                )}
                
                {marker.org.ein && (
                  <a 
                    href={`https://projects.propublica.org/nonprofits/organizations/${marker.org.ein}`}
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="popup-link"
                  >
                    📄 View 990 Forms
                  </a>
                )}
              </div>
            </Popup>
          </Marker>
        ))}
      </MapContainer>

      <style jsx>{`
        .map-container {
          background: white;
          border-radius: 12px;
          padding: 20px;
          box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }

        .coord-stats-banner {
          border: 2px solid #b3b8c1ff;
          border-radius: 8px;
          padding: 10px 10px;
          margin-bottom: 10px;
        }

        .stats-content {
          display: flex;
          align-items: flex-start;
          gap: 15px;
        }

        .stats-icon {
          font-size: 24px;
          line-height: 1;
        }

        .stats-text {
          flex: 1;
        }

        .stats-text strong {
          color: #1e40af;
          font-size: 16px;
          display: block;
          margin-bottom: 5px;
        }

        .stats-text p {
          color: #1e3a8a;
          font-size: 13px;
          margin: 0;
          line-height: 1.5;
        }

        .view-link-btn {
          background: none;
          border: none;
          color: #2563eb;
          text-decoration: underline;
          cursor: pointer;
          font-size: 13px;
          padding: 0;
          font-family: inherit;
        }

        .view-link-btn:hover {
          color: #1d4ed8;
        }

        .marker-popup {
          padding: 10px;
        }

        .marker-popup h4 {
          margin: 0 0 8px 0;
          color: #1e293b;
          font-size: 16px;
          font-weight: 600;
        }

        .org-city {
          color: #64748b;
          font-size: 12px;
          margin: 0 0 8px 0;
        }

        .org-mission {
          color: #475569;
          font-size: 13px;
          line-height: 1.5;
          margin: 8px 0;
        }

        .org-focus {
          color: #64748b;
          font-size: 12px;
          margin: 8px 0;
        }

        .org-focus strong {
          color: #1e293b;
        }

        .popup-link {
          display: inline-block;
          color: #2563eb;
          text-decoration: none;
          font-size: 13px;
          font-weight: 600;
          margin-top: 8px;
        }

        .popup-link:hover {
          text-decoration: underline;
        }

        .popup-link-subtle {
          display: inline-block;
          color: #64748b;
          text-decoration: none;
          font-size: 11px;
          font-weight: 400;
          margin-top: 4px;
          margin-left: 12px;
        }

        .popup-link-subtle:hover {
          color: #475569;
          text-decoration: underline;
        }

        @media (max-width: 768px) {
          .map-container {
            padding: 15px;
          }
        }
      `}</style>
    </div>
  );
};

export default OrganizationMap;
