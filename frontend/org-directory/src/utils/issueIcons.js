import { 
  Droplet, 
  Wind, 
  Thermometer, 
  Zap, 
  Sprout, 
  Trees, 
  Recycle,
  Scale,
  Factory,
  Home,
  GraduationCap,
  Briefcase,
  Users,
  Navigation
} from 'lucide-react'

// Map issue areas to icons and colors
export const issueIconMap = {
  // Water - Bright blue
  'water': { icon: Droplet, color: 'text-blue-700', bg: 'bg-blue-200' },
  'drinking-water': { icon: Droplet, color: 'text-blue-800', bg: 'bg-blue-200' },
  'water-quality': { icon: Droplet, color: 'text-blue-700', bg: 'bg-blue-200' },
  
  // Air - Bright gray/slate
  'air': { icon: Wind, color: 'text-slate-700', bg: 'bg-slate-200' },
  'air-quality': { icon: Wind, color: 'text-slate-700', bg: 'bg-slate-200' },
  
  // Climate - Bright red
  'climate': { icon: Thermometer, color: 'text-red-700', bg: 'bg-red-200' },
  
  // Energy - Bright yellow/orange
  'energy': { icon: Zap, color: 'text-orange-700', bg: 'bg-orange-200' },
  'dte-energy': { icon: Zap, color: 'text-orange-800', bg: 'bg-orange-200' },
  
  // Food/Agriculture - Bright green
  'food-agriculture': { icon: Sprout, color: 'text-green-700', bg: 'bg-green-200' },
  'food/agriculture': { icon: Sprout, color: 'text-green-700', bg: 'bg-green-200' },
  
  // Land - Darker green
  'land': { icon: Trees, color: 'text-green-800', bg: 'bg-green-200' },
  'habitat': { icon: Trees, color: 'text-green-900', bg: 'bg-green-200' },
  
  // Recycling - Bright emerald
  'recycling': { icon: Recycle, color: 'text-emerald-700', bg: 'bg-emerald-200' },
  
  // Environmental Justice - Bright purple
  'enviro-justice': { icon: Scale, color: 'text-purple-700', bg: 'bg-purple-200' },
  'enviro justice': { icon: Scale, color: 'text-purple-700', bg: 'bg-purple-200' }, // ADD THIS
  'environmental-justice': { icon: Scale, color: 'text-purple-700', bg: 'bg-purple-200' },
  'environmental justice': { icon: Scale, color: 'text-purple-700', bg: 'bg-purple-200' }, // ADD THIS 
  
  // Toxics - Bright orange
  'toxics': { icon: Factory, color: 'text-orange-700', bg: 'bg-orange-200' },
  
  // Recreation - Bright teal
  'recreation': { icon: Navigation, color: 'text-teal-700', bg: 'bg-teal-200' },
  
  // Education - Bright indigo
  'enviro-ed': { icon: GraduationCap, color: 'text-indigo-700', bg: 'bg-indigo-200' },
  'enviro ed': { icon: GraduationCap, color: 'text-indigo-700', bg: 'bg-indigo-200' }, // ADD THIS
  'education': { icon: GraduationCap, color: 'text-indigo-700', bg: 'bg-indigo-200' },

  // Workforce - Bright cyan
  'workforce-development': { icon: Briefcase, color: 'text-cyan-700', bg: 'bg-cyan-200' },
  'workforce development': { icon: Briefcase, color: 'text-cyan-700', bg: 'bg-cyan-200' },
  
  // Advocacy - Bright pink
  'advocacy-cause': { icon: Users, color: 'text-pink-700', bg: 'bg-pink-200' },
  'advocacy/cause': { icon: Users, color: 'text-pink-700', bg: 'bg-pink-200' },
  'policy': { icon: Scale, color: 'text-purple-800', bg: 'bg-purple-200' },
}

// Display name mappings - shows full names instead of abbreviations
export const issueDisplayNames = {
  'enviro-ed': 'Environmental Education',
  'enviro ed': 'Environmental Education',
  'education': 'Environmental Education',
  'enviro-justice': 'Environmental Justice',
  'enviro justice': 'Environmental Justice',
  'environmental-justice': 'Environmental Justice',
  'environmental justice': 'Environmental Justice',
  'food-agriculture': 'Food/Agriculture',
  'food/agriculture': 'Food/Agriculture',
  'dte-energy': 'DTE Energy',
  'dte energy': 'DTE Energy',
  'air-quality': 'Air Quality',
  'air quality': 'Air Quality',
  'water-quality': 'Water Quality',
  'water quality': 'Water Quality',
  'drinking-water': 'Drinking Water',
  'drinking water': 'Drinking Water',
  'advocacy-cause': 'Advocacy/Cause',
  'advocacy/cause': 'Advocacy/Cause',
  'workforce-development': 'Workforce Development',
  'workforce development': 'Workforce Development',
}

// Get display name for an issue
export const getIssueDisplayName = (issue) => {
  const normalized = issue?.toLowerCase().trim()
  return issueDisplayNames[normalized] || issue // Return original if no mapping
}

// Default icon for unknown categories
export const defaultIcon = { 
  icon: Users, 
  color: 'text-gray-400', 
  bg: 'bg-gray-50' 
}

// Get icon config for an issue
export const getIssueIcon = (issue) => {
  const normalized = issue?.toLowerCase().trim()
  return issueIconMap[normalized] || defaultIcon
}