export default function Header() {
  return (
    <header className="bg-blue-100 border-b border-gray-200 sticky top-0 z-50 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 py-4">
        <div className="flex items-center justify-between">
          {/* Left spacer for balance */}
          <div className="w-32"></div>

          {/* Centered Logo */}
          <a href="https://planetdetroit.org" className="flex-1 flex justify-center">
            <img 
              src="/images/planet-detroit-logo.png" 
              alt="Planet Detroit" 
              className="h-20"
              onError={(e) => {
                // Fallback if logo doesn't exist yet
                e.target.style.display = 'none'
                e.target.nextSibling.style.display = 'block'
              }}
            />
            <div 
              className="text-2xl font-bold hidden"
              style={{ color: '#2f80c3' }}
            >
              Planet Detroit
            </div>
          </a>

          {/* Donate Button */}
          <div className="w-32 flex justify-end">
            <a
              href="https://planetdetroit.org/donate"
              target="_blank"
              rel="noopener noreferrer"
              className="px-10 py-2 font-semibold text-m text-white rounded transition-colors uppercase tracking-wide text-center"
              style={{ backgroundColor: '#ea5a39' }}
              onMouseEnter={(e) => e.target.style.backgroundColor = '#d14a2a'}
              onMouseLeave={(e) => e.target.style.backgroundColor = '#ea5a39'}
            >
              Donate Now
            </a>
          </div>
        </div>
      </div>
    </header>
  )
}