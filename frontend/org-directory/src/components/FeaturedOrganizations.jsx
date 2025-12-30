import { Star, Award, ChevronRight } from 'lucide-react'

export default function FeaturedOrganizations({ organizations, onOrgClick }) {
  const planetChampions = organizations.filter(org => org.planet_champion)
  const impactPartners = organizations
    .filter(org => org.impact_partner && !org.planet_champion)
    .slice(0, 6)

  if (planetChampions.length === 0 && impactPartners.length === 0) {
    return null
  }

  return (
    <div className="bg-gradient-to-br from-pd-light-teal to-white border-b border-gray-200">
      <div className="max-w-7xl mx-auto px-4 py-12">
        {/* Planet Champions Section */}
        {planetChampions.length > 0 && (
          <div className="mb-12">
            <div className="flex items-center gap-3 mb-6">
              <Star className="w-8 h-8 text-amber-500 fill-amber-400" />
              <div>
                <h2 className="text-3xl font-bold text-pd-navy">Planet Champions</h2>
                <p className="text-pd-gray">Our highest-tier supporters leading environmental action</p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {planetChampions.map((org) => (
                <div
                  key={org.id}
                  onClick={() => onOrgClick(org)}
                  className="bg-white rounded-lg shadow-md hover:shadow-xl transition-all cursor-pointer border-2 border-amber-200 p-6 group"
                >
                  <div className="flex items-start justify-between mb-4">
                    <h3 className="text-xl font-bold text-pd-navy group-hover:text-pd-teal transition-colors">
                      {org.name}
                    </h3>
                    <Star className="w-6 h-6 text-amber-500 fill-amber-400 flex-shrink-0" />
                  </div>

                  {org.mission_statement_text && (
                    <p className="text-sm text-gray-600 mb-4 line-clamp-3">
                      {org.mission_statement_text}
                    </p>
                  )}

                  {org.url && (
                    <a
                      href={org.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      onClick={(e) => e.stopPropagation()}
                      className="inline-flex items-center gap-1 text-sm text-pd-teal hover:text-pd-dark-teal font-medium"
                    >
                      Learn more
                      <ChevronRight className="w-4 h-4" />
                    </a>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Impact Partners Section */}
        {impactPartners.length > 0 && (
          <div>
            <div className="flex items-center gap-3 mb-6">
              <Award className="w-7 h-7 text-pd-teal" />
              <div>
                <h2 className="text-2xl font-bold text-pd-navy">Impact Partners</h2>
                <p className="text-pd-gray">Supporting our mission to inform and engage communities</p>
              </div>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
              {impactPartners.map((org) => (
                <div
                  key={org.id}
                  onClick={() => onOrgClick(org)}
                  className="bg-white rounded-lg shadow-sm hover:shadow-md transition-all cursor-pointer border border-pd-teal/20 p-4 text-center group"
                >
                  <h4 className="text-sm font-semibold text-pd-navy group-hover:text-pd-teal transition-colors line-clamp-2">
                    {org.name}
                  </h4>
                </div>
              ))}
            </div>

            {organizations.filter(org => org.impact_partner && !org.planet_champion).length > 6 && (
              <div className="text-center mt-6">
                <p className="text-sm text-pd-gray">
                  + {organizations.filter(org => org.impact_partner && !org.planet_champion).length - 6} more Impact Partners
                </p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}