import { useState, useEffect } from 'react'

// API base URL - change for production
const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// =============================================================================
// API Functions
// =============================================================================

async function searchArticles(question) {
  const response = await fetch(`${API_BASE}/api/search`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, num_results: 10, synthesize: true })
  })
  if (!response.ok) throw new Error('Search failed')
  return response.json()
}

async function fetchMeetings(limit = 5) {
  const response = await fetch(`${API_BASE}/api/meetings?status=upcoming&limit=${limit}`)
  if (!response.ok) throw new Error('Failed to fetch meetings')
  return response.json()
}

async function fetchCommentPeriods(limit = 5) {
  const response = await fetch(`${API_BASE}/api/comment-periods?status=open&limit=${limit}`)
  if (!response.ok) throw new Error('Failed to fetch comment periods')
  return response.json()
}

async function fetchStats() {
  const response = await fetch(`${API_BASE}/api/stats`)
  if (!response.ok) throw new Error('Failed to fetch stats')
  return response.json()
}

// =============================================================================
// Sample Elected Officials Data (placeholder until API is built)
// =============================================================================

const SAMPLE_ELECTED_OFFICIALS = [
  {
    name: "Mallory McMorrow",
    office: "State Senator",
    district: "District 8 (Oakland County)",
    party: "D",
    committees: ["Energy Policy", "Appropriations"],
    email: "SenMMcMorrow@senate.michigan.gov",
    phone: "(517) 373-2523",
    website: "https://senatedems.com/mcmorrow/"
  },
  {
    name: "Darrin Camilleri", 
    office: "State Senator",
    district: "District 4 (Wayne County)",
    party: "D",
    committees: ["Energy Policy", "Environment"],
    email: "SenDCamilleri@senate.michigan.gov",
    phone: "(517) 373-7800",
    website: "https://senatedems.com/camilleri/"
  },
  {
    name: "Sam Singh",
    office: "State Senator", 
    district: "District 21 (Ingham County)",
    party: "D",
    committees: ["Energy Policy Committee Chair"],
    email: "SenSSingh@senate.michigan.gov",
    phone: "(517) 373-1635",
    website: "https://senatedems.com/singh/"
  }
]

// =============================================================================
// Components
// =============================================================================

function Header() {
  return (
    <header className="bg-white shadow-sm border-b border-gray-200">
      <div className="max-w-6xl mx-auto px-4 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-pd-blue rounded-full flex items-center justify-center">
              <span className="text-white font-bold text-lg">🌱</span>
            </div>
            <div>
              <h1 className="font-heading font-bold text-xl text-pd-text">Ask Planet Detroit</h1>
              <p className="text-sm text-pd-text-light">Civic Engagement Hub</p>
            </div>
          </div>
          <a 
            href="https://planetdetroit.org" 
            target="_blank" 
            rel="noopener noreferrer"
            className="text-sm text-pd-text-light hover:text-pd-blue transition-colors"
          >
            planetdetroit.org →
          </a>
        </div>
      </div>
    </header>
  )
}

function SearchBox({ onSearch, isLoading }) {
  const [query, setQuery] = useState('')

  const handleSubmit = (e) => {
    e.preventDefault()
    if (query.trim()) {
      onSearch(query)
    }
  }

  const exampleQueries = [
    "Why are people concerned about data centers?",
    "What is DTE doing about power outages?",
    "Is my drinking water safe?",
    "What are the air quality issues in Detroit?"
  ]

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <h2 className="font-heading font-bold text-lg mb-4 text-pd-text">
        Ask a question about Michigan environmental issues
      </h2>
      
      <form onSubmit={handleSubmit} className="flex gap-3">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="What would you like to know?"
          className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-pd-blue focus:border-transparent text-pd-text"
          disabled={isLoading}
        />
        <button
          type="submit"
          disabled={isLoading || !query.trim()}
          className="px-6 py-3 bg-pd-orange text-white font-heading font-semibold rounded-lg hover:bg-orange-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isLoading ? 'Searching...' : 'Search'}
        </button>
      </form>
      
      <div className="mt-4">
        <p className="text-sm text-pd-text-light mb-2">Try asking:</p>
        <div className="flex flex-wrap gap-2">
          {exampleQueries.map((q, i) => (
            <button
              key={i}
              onClick={() => setQuery(q)}
              className="text-sm px-3 py-1 bg-gray-100 hover:bg-gray-200 rounded-full text-pd-text-light transition-colors"
            >
              {q}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}

function SearchResults({ results }) {
  if (!results) return null

  const { answer, sources, unique_articles, search_time_ms } = results

  // Function to format answer with better styling
  const formatAnswer = (text) => {
    if (!text) return null
    
    // Split into paragraphs
    const paragraphs = text.split('\n\n')
    
    return paragraphs.map((para, i) => {
      // Check if it's a header (starts with **)
      if (para.startsWith('**') && para.includes('**')) {
        const headerMatch = para.match(/^\*\*(.+?)\*\*(.*)/)
        if (headerMatch) {
          return (
            <div key={i} className="mt-4 first:mt-0">
              <h3 className="font-heading font-bold text-pd-text mb-2">{headerMatch[1]}</h3>
              {headerMatch[2] && <p className="text-pd-text leading-relaxed">{headerMatch[2]}</p>}
            </div>
          )
        }
      }
      
      // Regular paragraph - look for article references and make them links
      let formattedPara = para
      
      // Find article references and link them
      sources?.forEach(source => {
        const titlePattern = new RegExp(`"${source.article_title.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}"`, 'g')
        if (formattedPara.includes(`"${source.article_title}"`)) {
          formattedPara = formattedPara.replace(
            `"${source.article_title}"`,
            `<a href="${source.article_url}" target="_blank" rel="noopener noreferrer" class="text-pd-blue hover:underline">"${source.article_title}"</a>`
          )
        }
      })
      
      return (
        <p 
          key={i} 
          className="text-pd-text leading-relaxed mt-3 first:mt-0"
          dangerouslySetInnerHTML={{ __html: formattedPara }}
        />
      )
    })
  }

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="font-heading font-bold text-lg text-pd-text">Answer</h2>
        <span className="text-xs text-pd-text-light">
          Based on {unique_articles} sources
        </span>
      </div>
      
      {answer && (
        <div className="prose prose-lg max-w-none mb-6">
          {formatAnswer(answer)}
        </div>
      )}
      
      {sources && sources.length > 0 && (
        <div className="border-t border-gray-200 pt-4 mt-4">
          <h3 className="font-heading font-semibold text-sm text-pd-text-light mb-3">
            📰 Sources from Planet Detroit
          </h3>
          <div className="space-y-2">
            {sources.slice(0, 5).map((source, i) => (
              <a
                key={i}
                href={source.article_url}
                target="_blank"
                rel="noopener noreferrer"
                className="block p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors group"
              >
                <div className="font-heading font-semibold text-sm text-pd-text group-hover:text-pd-blue">
                  {source.article_title.replace(/<[^>]*>/g, '')}
                </div>
                <div className="text-xs text-pd-text-light mt-1">
                  {source.article_date?.split('T')[0]}
                </div>
              </a>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function OrganizationsCard({ organizations }) {
  if (!organizations || organizations.length === 0) return null

  return (
    <div className="bg-white rounded-lg shadow-md p-5">
      <h2 className="font-heading font-bold text-base text-pd-text mb-3 flex items-center gap-2">
        <span>🏢</span> Organizations Working on This
      </h2>
      <div className="space-y-3">
        {organizations.slice(0, 4).map((org, i) => (
          <div key={i} className="border-b border-gray-100 pb-3 last:border-0 last:pb-0">
            <a
              href={org.url || '#'}
              target="_blank"
              rel="noopener noreferrer"
              className="font-heading font-semibold text-sm text-pd-text hover:text-pd-blue block"
            >
              {org.name}
            </a>
            {org.mission_statement_text && (
              <p className="text-xs text-pd-text-light mt-1 line-clamp-2">
                {org.mission_statement_text.slice(0, 120)}...
              </p>
            )}
            {org.focus && org.focus.length > 0 && (
              <div className="flex flex-wrap gap-1 mt-2">
                {org.focus.slice(0, 2).map((f, j) => (
                  <span key={j} className="text-xs px-2 py-0.5 bg-blue-50 text-pd-blue rounded">
                    {f}
                  </span>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
      <a 
        href="https://planet-detroit.github.io/michigan-environmental-orgs/"
        target="_blank"
        rel="noopener noreferrer"
        className="block mt-3 text-xs text-pd-blue hover:underline font-semibold"
      >
        View all 605 organizations →
      </a>
    </div>
  )
}

function ElectedOfficialsCard({ issue }) {
  // Filter officials by relevant committees based on issue
  const relevantOfficials = SAMPLE_ELECTED_OFFICIALS.filter(official => 
    official.committees.some(c => 
      c.toLowerCase().includes('energy') || c.toLowerCase().includes('environment')
    )
  )

  return (
    <div className="bg-white rounded-lg shadow-md p-5">
      <h2 className="font-heading font-bold text-base text-pd-text mb-3 flex items-center gap-2">
        <span>🏛️</span> Contact Your Representatives
      </h2>
      <p className="text-xs text-pd-text-light mb-3">
        State legislators on Energy & Environment committees:
      </p>
      <div className="space-y-3">
        {relevantOfficials.slice(0, 3).map((official, i) => (
          <div key={i} className="border-b border-gray-100 pb-3 last:border-0 last:pb-0">
            <div className="flex items-start justify-between">
              <div>
                <a
                  href={official.website}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="font-heading font-semibold text-sm text-pd-text hover:text-pd-blue"
                >
                  {official.name}
                </a>
                <span className="text-xs text-pd-text-light ml-1">({official.party})</span>
                <div className="text-xs text-pd-text-light">{official.office}</div>
                <div className="text-xs text-pd-text-light">{official.district}</div>
              </div>
            </div>
            <div className="flex gap-2 mt-2">
              <a
                href={`mailto:${official.email}`}
                className="text-xs px-2 py-1 bg-pd-blue text-white rounded hover:bg-blue-700 transition-colors"
              >
                Email
              </a>
              <a
                href={`tel:${official.phone}`}
                className="text-xs px-2 py-1 bg-gray-200 text-pd-text rounded hover:bg-gray-300 transition-colors"
              >
                {official.phone}
              </a>
            </div>
            <div className="text-xs text-pd-text-light mt-1">
              {official.committees.join(', ')}
            </div>
          </div>
        ))}
      </div>
      <p className="mt-3 text-xs text-pd-text-light italic">
        💡 Tip: Find your specific representatives at{' '}
        <a href="https://www.house.mi.gov/AllRepresentatives" target="_blank" rel="noopener noreferrer" className="text-pd-blue hover:underline">
          house.mi.gov
        </a>
      </p>
    </div>
  )
}

function CivicActionsCard({ actions }) {
  if (!actions || actions.length === 0) return null

  const iconMap = {
    attend: '📅',
    comment: '💬',
    follow: '📰',
    petition: '✍️',
    report: '📋',
    monitor: '📊',
    test: '🧪',
    check: '✅',
    subscribe: '📧'
  }

  return (
    <div className="bg-white rounded-lg shadow-md p-5">
      <h2 className="font-heading font-bold text-base text-pd-text mb-3 flex items-center gap-2">
        <span>✊</span> Take Action
      </h2>
      <div className="space-y-3">
        {actions.slice(0, 4).map((action, i) => (
          <div key={i} className="flex gap-3 items-start">
            <span className="text-base">{iconMap[action.action_type] || '📌'}</span>
            <div>
              {action.url ? (
                <a
                  href={action.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="font-heading font-semibold text-sm text-pd-text hover:text-pd-blue"
                >
                  {action.title}
                </a>
              ) : (
                <span className="font-heading font-semibold text-sm text-pd-text">
                  {action.title}
                </span>
              )}
              <p className="text-xs text-pd-text-light mt-0.5">{action.description}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function MeetingsCard({ meetings, isLoading }) {
  return (
    <div className="bg-white rounded-lg shadow-md p-5">
      <h2 className="font-heading font-bold text-base text-pd-text mb-3 flex items-center gap-2">
        <span>📅</span> Upcoming Meetings
      </h2>
      
      {isLoading ? (
        <p className="text-sm text-pd-text-light">Loading...</p>
      ) : meetings && meetings.length > 0 ? (
        <div className="space-y-3">
          {meetings.slice(0, 3).map((meeting, i) => (
            <div key={i} className="border-l-3 border-pd-blue pl-3 py-1">
              <div className="font-heading font-semibold text-sm text-pd-text">
                {meeting.title}
              </div>
              <div className="text-xs text-pd-text-light mt-1">
                {new Date(meeting.start_datetime).toLocaleDateString('en-US', {
                  weekday: 'short',
                  month: 'short',
                  day: 'numeric',
                  hour: 'numeric',
                  minute: '2-digit'
                })}
              </div>
              <div className="text-xs text-pd-text-light">
                📍 {meeting.location_city || 'TBD'}
                {meeting.is_hybrid && ' • Hybrid'}
              </div>
              <div className="flex gap-2 mt-2">
                {meeting.details_url && (
                  <a
                    href={meeting.details_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs px-2 py-1 bg-pd-blue text-white rounded hover:bg-blue-700 transition-colors"
                  >
                    Details
                  </a>
                )}
                {meeting.accepts_public_comment && (
                  <a
                    href={meeting.public_comment_url || '#'}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs px-2 py-1 bg-pd-orange text-white rounded hover:bg-orange-600 transition-colors"
                  >
                    Comment
                  </a>
                )}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-sm text-pd-text-light">No upcoming meetings.</p>
      )}
    </div>
  )
}

function CommentPeriodsCard({ periods, isLoading }) {
  return (
    <div className="bg-white rounded-lg shadow-md p-5">
      <h2 className="font-heading font-bold text-base text-pd-text mb-3 flex items-center gap-2">
        <span>💬</span> Open Comment Periods
      </h2>
      
      {isLoading ? (
        <p className="text-sm text-pd-text-light">Loading...</p>
      ) : periods && periods.length > 0 ? (
        <div className="space-y-3">
          {periods.slice(0, 3).map((period, i) => (
            <div key={i} className="border-l-3 border-pd-orange pl-3 py-1">
              <div className="font-heading font-semibold text-sm text-pd-text">
                {period.title}
              </div>
              <div className="text-xs text-pd-text-light mt-1">
                {period.agency} • Deadline: {period.end_date}
              </div>
              {period.days_remaining !== null && period.days_remaining <= 14 && (
                <div className={`text-xs font-semibold mt-1 ${period.days_remaining <= 7 ? 'text-red-600' : 'text-pd-orange'}`}>
                  ⚠️ {period.days_remaining} days remaining
                </div>
              )}
              {period.submit_comment_url && (
                <a
                  href={period.submit_comment_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-block mt-2 text-xs px-2 py-1 bg-pd-orange text-white rounded hover:bg-orange-600 transition-colors"
                >
                  Submit Comment
                </a>
              )}
            </div>
          ))}
        </div>
      ) : (
        <p className="text-sm text-pd-text-light">No open comment periods.</p>
      )}
    </div>
  )
}

function StatsBar({ stats }) {
  if (!stats) return null

  return (
    <div className="bg-white border-b border-gray-200 py-2">
      <div className="max-w-6xl mx-auto px-4">
        <div className="flex items-center justify-center gap-6 text-xs text-pd-text-light">
          <span>📰 {stats.total_chunks?.toLocaleString()} searchable passages</span>
          <span>🏢 {stats.total_organizations} organizations</span>
          <span>📅 {stats.upcoming_meetings} meetings</span>
          <span>💬 {stats.open_comment_periods} comment periods</span>
        </div>
      </div>
    </div>
  )
}

function Footer() {
  return (
    <footer className="bg-white border-t border-gray-200 mt-12">
      <div className="max-w-6xl mx-auto px-4 py-8">
        <div className="text-center">
          <p className="text-sm text-pd-text-light mb-2">
            Powered by{' '}
            <a href="https://planetdetroit.org" className="text-pd-blue hover:underline">
              Planet Detroit
            </a>
            {' '}— Independent nonprofit environmental journalism for Michigan
          </p>
          <p className="text-xs text-pd-text-light">
            "Hold power accountable. Uncover solutions. Uplift and empower the community."
          </p>
        </div>
      </div>
    </footer>
  )
}

// =============================================================================
// Main App
// =============================================================================

export default function App() {
  const [searchResults, setSearchResults] = useState(null)
  const [isSearching, setIsSearching] = useState(false)
  const [searchError, setSearchError] = useState(null)
  
  const [meetings, setMeetings] = useState([])
  const [meetingsLoading, setMeetingsLoading] = useState(true)
  
  const [commentPeriods, setCommentPeriods] = useState([])
  const [periodsLoading, setPeriodsLoading] = useState(true)
  
  const [stats, setStats] = useState(null)

  // Load initial data
  useEffect(() => {
    fetchMeetings(5)
      .then(data => setMeetings(data.meetings || []))
      .catch(err => console.error('Failed to load meetings:', err))
      .finally(() => setMeetingsLoading(false))

    fetchCommentPeriods(5)
      .then(data => setCommentPeriods(data.comment_periods || []))
      .catch(err => console.error('Failed to load comment periods:', err))
      .finally(() => setPeriodsLoading(false))

    fetchStats()
      .then(data => setStats(data))
      .catch(err => console.error('Failed to load stats:', err))
  }, [])

  const handleSearch = async (query) => {
    setIsSearching(true)
    setSearchError(null)
    setSearchResults(null)

    try {
      const results = await searchArticles(query)
      setSearchResults(results)
    } catch (err) {
      console.error('Search error:', err)
      setSearchError('Failed to search. Please try again.')
    } finally {
      setIsSearching(false)
    }
  }

  return (
    <div className="min-h-screen flex flex-col">
      <Header />
      <StatsBar stats={stats} />
      
      <main className="flex-1 max-w-6xl mx-auto px-4 py-8 w-full">
        {/* Two Column Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          
          {/* Left Column - Search */}
          <div className="lg:col-span-2">
            {/* Hero / Search Section */}
            <div className="mb-6">
              <div className="text-center mb-6">
                <h2 className="font-heading font-bold text-2xl text-pd-text mb-2">
                  Your guide to Michigan's environmental issues
                </h2>
                <p className="text-pd-text-light">
                  Search Planet Detroit's reporting, find organizations, and take civic action.
                </p>
              </div>
              
              <SearchBox onSearch={handleSearch} isLoading={isSearching} />
              
              {searchError && (
                <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
                  {searchError}
                </div>
              )}
            </div>

            {/* Search Results */}
            {searchResults && (
              <SearchResults results={searchResults} />
            )}
          </div>

          {/* Right Column - Civic Data (Always Visible) */}
          <div className="space-y-6">
            <MeetingsCard meetings={meetings} isLoading={meetingsLoading} />
            <CommentPeriodsCard periods={commentPeriods} isLoading={periodsLoading} />
            
            {/* Show these when search results exist */}
            {searchResults && (
              <>
                <OrganizationsCard organizations={searchResults.related_organizations} />
                <ElectedOfficialsCard />
                <CivicActionsCard actions={searchResults.civic_actions} />
              </>
            )}
            
            {/* Quick Links */}
            <div className="bg-white rounded-lg shadow-md p-5">
              <h2 className="font-heading font-bold text-base text-pd-text mb-3 flex items-center gap-2">
                <span>🔗</span> Quick Links
              </h2>
              <div className="space-y-2">
                <a href="https://planetdetroit.org/category/michigan-data-centers/" target="_blank" rel="noopener noreferrer" className="block text-sm text-pd-text hover:text-pd-blue">
                  → Data Centers Coverage
                </a>
                <a href="https://planetdetroit.org/category/dte-energy/" target="_blank" rel="noopener noreferrer" className="block text-sm text-pd-text hover:text-pd-blue">
                  → DTE Energy Coverage
                </a>
                <a href="https://planetdetroit.org/category/air-quality/" target="_blank" rel="noopener noreferrer" className="block text-sm text-pd-text hover:text-pd-blue">
                  → Air Quality Coverage
                </a>
                <a href="https://planetdetroit.org/category/drinking-water/" target="_blank" rel="noopener noreferrer" className="block text-sm text-pd-text hover:text-pd-blue">
                  → Drinking Water Coverage
                </a>
                <a href="https://planet-detroit.github.io/michigan-environmental-orgs/" target="_blank" rel="noopener noreferrer" className="block text-sm text-pd-blue font-semibold hover:underline mt-3">
                  → Full Organization Directory
                </a>
              </div>
            </div>
          </div>
        </div>
      </main>
      
      <Footer />
    </div>
  )
}
