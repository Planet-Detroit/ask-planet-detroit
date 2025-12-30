import { 
  Droplet, 
  Wind, 
  Thermometer, 
  Zap, 
  Sprout, 
  Trees, 
  Recycle,
  Scale,
  GraduationCap,
  Users,
  Navigation,
  Leaf,
  Bird
} from 'lucide-react'

// EXACT MATCHES for your database values
const FOCUS_CONFIGS = {
  'Advocacy': { icon: Users, color: 'text-pink-700', bg: 'bg-pink-200' },
  'Air Quality': { icon: Wind, color: 'text-slate-700', bg: 'bg-slate-200' },
  'Climate': { icon: Thermometer, color: 'text-red-700', bg: 'bg-red-200' },
  'Energy': { icon: Zap, color: 'text-orange-700', bg: 'bg-orange-200' },
  'Environmental Education': { icon: GraduationCap, color: 'text-indigo-700', bg: 'bg-indigo-200' },
  'Environmental Justice': { icon: Scale, color: 'text-purple-700', bg: 'bg-purple-200' },
  'Food & Agriculture': { icon: Sprout, color: 'text-green-700', bg: 'bg-green-200' },
  'Land Conservation': { icon: Trees, color: 'text-emerald-800', bg: 'bg-emerald-200' },
  'Outdoor Recreation': { icon: Navigation, color: 'text-teal-700', bg: 'bg-teal-200' },
  'Recycling': { icon: Recycle, color: 'text-cyan-700', bg: 'bg-cyan-200' },
  'Stewardship': { icon: Leaf, color: 'text-lime-700', bg: 'bg-lime-200' },
  'Sustainability': { icon: Leaf, color: 'text-rose-700', bg: 'bg-rose-200' },
  'Water': { icon: Droplet, color: 'text-blue-700', bg: 'bg-blue-200' },
  'Wildlife': { icon: Bird, color: 'text-amber-700', bg: 'bg-amber-200' },
}

// Default for unknown values
const DEFAULT_CONFIG = { 
  icon: Users, 
  color: 'text-gray-700', 
  bg: 'bg-gray-200' 
}

// Main function - just looks up the focus area
export const getIssueIcon = (focus) => {
  if (!focus) {
    console.log('getIssueIcon called with empty focus')
    return DEFAULT_CONFIG
  }
  
  const result = FOCUS_CONFIGS[focus] || DEFAULT_CONFIG
  console.log(`getIssueIcon("${focus}"):`, result ? 'FOUND' : 'DEFAULT', result)
  
  return result
}

// Display name is just the focus area itself (no transformation needed)
export const getIssueDisplayName = (focus) => {
  return focus || ''
}

// For backward compatibility
export const issueIconMap = FOCUS_CONFIGS
export const defaultIcon = DEFAULT_CONFIG

// Official categories list
export const OFFICIAL_CATEGORIES = [
  'Advocacy',
  'Air Quality',
  'Climate',
  'Energy',
  'Environmental Education',
  'Environmental Justice',
  'Food & Agriculture',
  'Land Conservation',
  'Outdoor Recreation',
  'Recycling',
  'Stewardship',
  'Sustainability',
  'Water',
  'Wildlife'
]
