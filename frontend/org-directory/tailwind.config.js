/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  safelist: [
    // Issue tag colors - safelist to prevent Tailwind from purging them
    'bg-pink-200', 'text-pink-700',
    'bg-slate-200', 'text-slate-700',
    'bg-red-200', 'text-red-700',
    'bg-orange-200', 'text-orange-700',
    'bg-indigo-200', 'text-indigo-700',
    'bg-purple-200', 'text-purple-700',
    'bg-green-200', 'text-green-700',
    'bg-emerald-200', 'text-emerald-800',
    'bg-teal-200', 'text-teal-700',
    'bg-cyan-200', 'text-cyan-700',
    'bg-lime-200', 'text-lime-700',
    'bg-rose-200', 'text-rose-700',
    'bg-blue-200', 'text-blue-700',
    'bg-amber-200', 'text-amber-700',
    'bg-gray-200', 'text-gray-700',
    // Auto-assigned colors for new categories
    'bg-violet-200', 'text-violet-700',
    'bg-fuchsia-200', 'text-fuchsia-700',
    'bg-sky-200', 'text-sky-700',
    'bg-yellow-200', 'text-yellow-700',
    'bg-red-100', 'text-red-600',
    'bg-blue-100', 'text-blue-600',
    'bg-purple-100', 'text-purple-600',
    'bg-green-100', 'text-green-600',
  ],
  theme: {
    extend: {
      colors: {
        // Planet Detroit brand colors
        'pd-blue': '#2f80c3',        // Logo/branding ONLY - not for text
        'pd-orange': '#ea5a39',       // DONATE button, CTAs
        'pd-text': '#333333',         // Body text, headlines
        'pd-text-light': '#999999',   // Bylines, meta info
        'pd-bg': '#f5f5f5',          // Page background
        // Additional colors for directory
        'pd-teal': '#14b8a6',        // Teal accent for links/buttons
        'pd-dark-teal': '#0f766e',   // Darker teal for hovers
        'pd-light-teal': '#f0fdfa',  // Light teal background
        'pd-navy': '#1e293b',        // Dark navy for headings
        'pd-gray': '#64748b',        // Mid-gray for secondary text
      },
      fontFamily: {
        'serif': ['Gelasio', 'Georgia', 'serif'],
        'sans': ['Asap', '-apple-system', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
