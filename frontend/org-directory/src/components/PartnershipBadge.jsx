import { Award, Star } from 'lucide-react'

export default function PartnershipBadge({ planetChampion, impactPartner }) {
  if (planetChampion) {
    return (
      <a
        href="https://planetdetroit.org/impactpartners/"
        target="_blank"
        rel="noopener noreferrer"
        onClick={(e) => e.stopPropagation()}
        className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-gradient-to-r from-yellow-300 to-yellow-400 border-2 border-yellow-600 rounded-full shadow-md hover:shadow-lg transition-shadow cursor-pointer"
      >
        <Star className="w-4 h-4 fill-yellow-700 text-yellow-900" />
        <span className="text-sm font-bold text-gray-900">Planet Champion</span>
      </a>
    )
  }
  
  if (impactPartner) {
    return (
      <a
        href="https://planetdetroit.org/impactpartners/"
        target="_blank"
        rel="noopener noreferrer"
        onClick={(e) => e.stopPropagation()}
        className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-gradient-to-r from-yellow-200 to-yellow-300 border-2 border-yellow-500 rounded-full shadow-md hover:shadow-lg transition-shadow cursor-pointer"
      >
        <Award className="w-4 h-4 fill-gray-900 text-gray-900" />
        <span className="text-sm font-bold text-gray-900">Impact Partner</span>
      </a>
    )
  }
  
  return null
}