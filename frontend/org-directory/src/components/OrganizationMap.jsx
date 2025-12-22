import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { MapPin } from 'lucide-react'

// Create smaller custom markers
const createCustomIcon = (isPartner, isChampion) => {
  const color = isChampion ? '#fbbf24' : isPartner ? '#2f80c3' : '#ef4444'
  
  return L.divIcon({
    className: 'custom-marker',
    html: `
      <div style="
        width: 20px;
        height: 20px;
        background-color: ${color};
        border: 2px solid white;
        border-radius: 50%;
        box-shadow: 0 2px 4px rgba(0,0,0,0.3);
      "></div>
    `,
    iconSize: [20, 20],
    iconAnchor: [10, 10],
    popupAnchor: [0, -10]
  })
}

export default function OrganizationMap({ organizations, onOrgClick }) {
  const geocodedOrgs = organizations.filter(org => org.latitude && org.longitude)
  
  const center = [42.7, -84.5]
  const zoom = 7

  if (geocodedOrgs.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-12 text-center">
        <MapPin className="w-12 h-12 text-gray-400 mx-auto mb-4" />
        <h3 className="text-lg font-semibold text-gray-700 mb-2">No Geocoded Organizations</h3>
        <p className="text-gray-600">None of the filtered organizations have location data.</p>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden" style={{ height: '600px', position: 'relative' }}>
      <MapContainer
        center={center}
        zoom={zoom}
        style={{ height: '100%', width: '100%' }}
        scrollWheelZoom={true}
      >
        <TileLayer
          attribution='&copy; OpenStreetMap contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        
        {geocodedOrgs.map((org) => (
          <Marker
            key={org.id}
            position={[org.latitude, org.longitude]}
            icon={createCustomIcon(org.impact_partner, org.planet_champion)}
          >
            <Popup maxWidth={300}>
              <div className="p-2">
                <div className="flex items-start justify-between gap-2 mb-2">
                  <h3 className="font-bold text-gray-900 text-base">
                    {org.name}
                  </h3>
                  {org.planet_champion && (
                    <span style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '4px',
                      padding: '2px 8px',
                      background: 'linear-gradient(to right, #fcd34d, #fbbf24)',
                      border: '2px solid #ca8a04',
                      borderRadius: '9999px',
                      fontSize: '11px',
                      fontWeight: 'bold',
                      color: '#111827',
                      whiteSpace: 'nowrap'
                    }}>
                      ⭐ Champion
                    </span>
                  )}
                  {!org.planet_champion && org.impact_partner && (
                    <span style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '4px',
                      padding: '2px 8px',
                      background: 'linear-gradient(to right, #fef08a, #fde047)',
                      border: '2px solid #eab308',
                      borderRadius: '9999px',
                      fontSize: '11px',
                      fontWeight: 'bold',
                      color: '#111827',
                      whiteSpace: 'nowrap'
                    }}>
                      🏆 Partner
                    </span>
                  )}
                </div>

                {org.mission_statement_text && (
                  <p className="text-sm text-gray-600 mb-3 line-clamp-3">
                    {org.mission_statement_text}
                  </p>
                )}

                {org.city && (
                  <p className="text-sm text-gray-500 mb-2">
                    📍 {org.city}
                  </p>
                )}

                <button
                  onClick={() => onOrgClick(org)}
                  className="w-full mt-2 px-4 py-2 bg-gray-900 text-white text-sm font-semibold rounded hover:bg-gray-700 transition-colors"
                >
                  View Details
                </button>
                {org.url && (
                  <a
                    href={org.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="block w-full mt-2 px-4 py-2 border border-gray-300 text-sm font-semibold rounded hover:bg-gray-50 transition-colors text-center"
                    style={{ color: '#2f80c3' }}
                  >
                    Visit Website
                  </a>
                )}
              </div>
            </Popup>
          </Marker>
        ))}
      </MapContainer>
      
      <div style={{
        position: 'absolute',
        bottom: '16px',
        right: '16px',
        backgroundColor: 'white',
        padding: '12px',
        borderRadius: '6px',
        boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
        fontSize: '12px',
        zIndex: 1000,
        fontFamily: 'system-ui, sans-serif'
      }}>
        <div style={{ fontWeight: 'bold', marginBottom: '8px', fontSize: '13px' }}>Legend</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div style={{ width: '12px', height: '12px', borderRadius: '50%', backgroundColor: '#fbbf24', boxShadow: '0 1px 3px rgba(0,0,0,0.3)' }}></div>
            <span style={{ whiteSpace: 'nowrap' }}>Planet Champion</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div style={{ width: '12px', height: '12px', borderRadius: '50%', backgroundColor: '#2f80c3', boxShadow: '0 1px 3px rgba(0,0,0,0.3)' }}></div>
            <span style={{ whiteSpace: 'nowrap' }}>Impact Partner</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div style={{ width: '12px', height: '12px', borderRadius: '50%', backgroundColor: '#ef4444', boxShadow: '0 1px 3px rgba(0,0,0,0.3)' }}></div>
            <span style={{ whiteSpace: 'nowrap' }}>Organization</span>
          </div>
        </div>
      </div>
    </div>
  )
}