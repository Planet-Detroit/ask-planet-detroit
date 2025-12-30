import { MapPin, ExternalLink, Heart } from 'lucide-react'
import PartnershipBadge from './PartnershipBadge'
import IssueTag from './IssueTag'

export default function OrganizationCard({ org, onClick }) {
  const hasLocation = org.city || org.geo_location?.length > 0
  const location = org.city || org.geo_location?.[0] || ''
  
  return (
    <div 
      onClick={() => onClick(org)}
      className="bg-white rounded-lg shadow-sm hover:shadow-md transition-shadow cursor-pointer border border-gray-200 p-5"
    >
      {/* Header with badges */}
      <div className="flex items-start justify-between gap-4 mb-3">
        <h3 className="text-3xl font-bold text-pd-navy flex-1">
          {org.name}
        </h3>
        {(org.planet_champion || org.impact_partner) && (
          <PartnershipBadge 
            planetChampion={org.planet_champion} 
            impactPartner={org.impact_partner} 
          />
        )}
      </div>

      {/* Location */}
      {hasLocation && (
        <div className="flex items-center gap-1 text-sm text-pd-gray mb-3">
          <MapPin className="w-4 h-4" />
          <span>{location}</span>
        </div>
      )}

      {/* Mission statement preview */}
      {org.mission_statement_text && (
        <p className="text-sm text-gray-600 mb-3 line-clamp-2">
          {org.mission_statement_text}
        </p>
      )}

      {/* Issue tags */}
      {org.focus && org.focus.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-3">
          {org.focus.slice(0, 3).map((issue, idx) => (
            <IssueTag key={idx} issue={issue} />
          ))}
          {org.focus.length > 3 && (
            <span className="px-2 py-1 bg-gray-100 text-gray-600 rounded text-xs">
              +{org.focus.length - 3} more
            </span>
          )}
        </div>
      )}

      {/* Volunteer opportunities indicator */}
      {org.volunteer_opportunities && (
        <div className="flex items-center gap-1 text-sm text-pd-teal mt-3 pt-3 border-t border-gray-100">
          <Heart className="w-4 h-4" />
          <span className="font-medium">Volunteer opportunities available</span>
        </div>
      )}

        {/* Website link */}
      {org.url && (
        <a
          href={org.url}
          target="_blank"
          rel="noopener noreferrer"
          onClick={(e) => e.stopPropagation()}
          className="flex items-center gap-1 text-sm font-semibold mt-3 hover:underline transition-colors"
          style={{ color: '#2f80c3' }}
        >
          <ExternalLink className="w-4 h-4" />
          <span>Visit website</span>
        </a>
      )}
    </div>
  )
}