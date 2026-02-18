"""
Ask Planet Detroit - RAG Search API
Complete FastAPI backend with search, meetings, comment periods, and article analysis
"""

import os
import json
import time
from datetime import datetime, timezone
from typing import Optional, List
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from supabase import create_client, Client
import anthropic

# Load environment variables
load_dotenv()

# Initialize clients
supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
)

anthropic_client = anthropic.Anthropic(
    api_key=os.getenv("ANTHROPIC_API_KEY")
)

# FastAPI app
app = FastAPI(
    title="Ask Planet Detroit API",
    description="RAG search API for Planet Detroit journalism",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# Startup: auto-expire past meetings and closed comment periods
# =============================================================================

@app.on_event("startup")
async def expire_stale_records():
    """Mark past meetings and expired comment periods on startup."""
    now = datetime.now(timezone.utc).isoformat()
    today = datetime.now(timezone.utc).date().isoformat()
    try:
        result = supabase.from_("meetings")\
            .update({"status": "past"})\
            .eq("status", "upcoming")\
            .lt("start_datetime", now)\
            .execute()
        count = len(result.data) if result.data else 0
        if count:
            print(f"Startup: marked {count} past meetings")
    except Exception as e:
        print(f"Startup: meetings expire error: {e}")

    try:
        result = supabase.from_("comment_periods")\
            .update({"status": "closed"})\
            .eq("status", "open")\
            .lt("end_date", today)\
            .execute()
        count = len(result.data) if result.data else 0
        if count:
            print(f"Startup: closed {count} expired comment periods")
    except Exception as e:
        print(f"Startup: comment periods expire error: {e}")

# =============================================================================
# Request/Response Models
# =============================================================================

class SearchRequest(BaseModel):
    question: str
    num_results: int = 10
    issues_filter: Optional[List[str]] = None
    synthesize: bool = True

class AnalyzeArticleRequest(BaseModel):
    article_text: str
    article_url: Optional[str] = None

# =============================================================================
# Helper Functions
# =============================================================================

def get_embedding(text: str) -> List[float]:
    """Get embedding from OpenAI"""
    import openai
    openai.api_key = os.getenv("OPENAI_API_KEY")
    
    response = openai.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return response.data[0].embedding

def synthesize_answer(question: str, chunks: List[dict]) -> str:
    """Use Claude to synthesize an answer from retrieved chunks"""
    
    context = "\n\n---\n\n".join([
        f"Source: {c.get('article_title', 'Unknown')}\nDate: {c.get('article_date', 'Unknown')}\nContent: {c.get('content', '')}"
        for c in chunks
    ])
    
    prompt = f"""Based on the following excerpts from Planet Detroit's journalism, answer this question: "{question}"

Context from Planet Detroit articles:
{context}

Instructions:
- Synthesize information from multiple sources when relevant
- Cite specific articles when making claims
- If the sources don't contain enough information, say so
- Keep the answer concise but comprehensive
- Use a journalistic, factual tone

Answer:"""

    response = anthropic_client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}]
    )
    
    return response.content[0].text

def get_all_organizations() -> List[dict]:
    """Fetch all organizations from Supabase."""
    try:
        response = supabase.from_("organizations")\
            .select("name, url, mission_statement_text, focus, region, city")\
            .order("name")\
            .execute()

        if not response.data:
            return []

        skip_names = {"test", "test org", "example", "sample"}
        return [
            org for org in response.data
            if org.get("name", "").strip()
            and org.get("name", "").strip().lower() not in skip_names
        ]

    except Exception as e:
        print(f"Error fetching organizations: {e}")
        return []


def rank_organizations_with_ai(
    all_orgs: List[dict],
    article_summary: str,
    detected_issues: List[str],
    limit: int = 6
) -> List[dict]:
    """Use Claude to pick the most relevant orgs for an article.

    Sends the full org directory (~600 orgs, ~33K tokens) to Haiku and lets
    it semantically select the best matches. No keyword mapping needed.
    Cost: ~$0.03 per call.
    """

    if not all_orgs or not article_summary:
        return []

    # Build compact org list for the prompt
    org_descriptions = []
    for i, org in enumerate(all_orgs):
        name = org.get("name", "Unknown")
        mission = (org.get("mission_statement_text") or "")[:150]
        focus = ", ".join(org.get("focus") or [])
        city = org.get("city") or ""
        region = org.get("region") or ""
        location = f"{city}, {region}".strip(", ")

        desc = f"{i+1}. {name}"
        if location:
            desc += f" ({location})"
        if focus:
            desc += f" [{focus}]"
        if mission:
            desc += f" — {mission}"
        org_descriptions.append(desc)

    org_list_text = "\n".join(org_descriptions)
    issues_text = ", ".join(detected_issues) if detected_issues else "general"

    ranking_prompt = f"""You are helping a Michigan environmental journalism outlet (Planet Detroit) recommend organizations to readers.

Given this article summary and the full directory of Michigan environmental organizations, pick the {limit} MOST relevant orgs for readers of this article. Prioritize:
- Direct topical relevance to the article's subject matter
- Geographic proximity (local orgs for local stories, statewide for statewide)
- Orgs readers can engage with (advocacy groups, community orgs > industry trade groups)
- Diversity of perspectives (don't pick 6 orgs that all do the same thing)

Article summary: {article_summary}
Detected issues: {issues_text}

Organizations:
{org_list_text}

Return ONLY a JSON array of the numbers of your top {limit} picks, most relevant first.
Example: [3, 7, 1, 12, 5, 9]"""

    try:
        response = anthropic_client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=200,
            messages=[{"role": "user", "content": ranking_prompt}]
        )

        response_text = response.content[0].text.strip()

        # Parse the JSON array
        if "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()
            if response_text.startswith("json"):
                response_text = response_text[4:].strip()

        picks = json.loads(response_text)

        # Convert 1-indexed picks to org objects
        ranked = []
        for pick in picks:
            idx = pick - 1  # Convert to 0-indexed
            if 0 <= idx < len(all_orgs):
                ranked.append(all_orgs[idx])

        return ranked[:limit]

    except Exception as e:
        print(f"AI org ranking error: {e}")
        return []


def get_upcoming_meetings(limit: int = 200) -> List[dict]:
    """Fetch upcoming meetings from Supabase."""
    try:
        response = supabase.from_("meetings")\
            .select("*")\
            .gte("start_datetime", datetime.now(timezone.utc).isoformat())\
            .order("start_datetime", desc=False)\
            .limit(limit)\
            .execute()
        return response.data or []
    except Exception as e:
        print(f"Error fetching meetings: {e}")
        return []


def get_open_comment_periods(limit: int = 50) -> List[dict]:
    """Fetch open comment periods from Supabase."""
    try:
        today = datetime.now(timezone.utc).date().isoformat()
        response = supabase.from_("comment_periods")\
            .select("*")\
            .gte("end_date", today)\
            .eq("status", "open")\
            .order("end_date", desc=False)\
            .limit(limit)\
            .execute()
        return response.data or []
    except Exception as e:
        print(f"Error fetching comment periods: {e}")
        return []


def rank_meetings_with_ai(
    meetings: List[dict],
    article_summary: str,
    detected_issues: List[str],
    limit: int = 5
) -> List[dict]:
    """Use Claude to pick the most relevant meetings for an article.

    Sends upcoming meetings to Haiku and lets it semantically select the best
    matches based on article content, agency relevance, and meeting context.
    Cost: ~$0.01-0.02 per call (meetings are smaller than org directory).
    """

    if not meetings or not article_summary:
        return []

    # Build compact meeting list for the prompt
    meeting_descriptions = []
    for i, m in enumerate(meetings):
        title = m.get("title", "Unknown")
        agency = m.get("agency", "")
        agency_full = m.get("agency_full_name", "")
        date = m.get("meeting_date", "")
        time = m.get("meeting_time", "")
        meeting_type = m.get("meeting_type", "")
        description = (m.get("description") or "")[:150]
        tags = ", ".join(m.get("issue_tags") or [])
        has_agenda = "has agenda" if m.get("agenda_url") else ""
        virtual = "virtual/hybrid" if m.get("virtual_url") else "in-person"

        desc = f"{i+1}. {title} ({agency})"
        if agency_full and agency_full != agency:
            desc += f" [{agency_full}]"
        desc += f" — {date} {time}"
        if meeting_type:
            desc += f", {meeting_type}"
        desc += f", {virtual}"
        if tags:
            desc += f" | tags: {tags}"
        if description and description != f"{agency} {title}":
            desc += f" | {description}"
        meeting_descriptions.append(desc)

    meeting_list_text = "\n".join(meeting_descriptions)
    issues_text = ", ".join(detected_issues) if detected_issues else "general"

    ranking_prompt = f"""You are helping a Michigan environmental journalism outlet (Planet Detroit) recommend upcoming public meetings to readers of an article.

Given this article summary and the list of upcoming public meetings, pick the {limit} MOST relevant meetings for readers. Prioritize:
- Direct relevance to the article's subject matter (e.g., water contamination article → EGLE water quality hearing)
- Meetings where public comment is accepted and reader participation would be meaningful
- Meetings happening sooner (within the next 2 weeks) over far-future ones
- Diversity of engagement opportunities (don't pick 5 meetings from the same committee)
- Prefer meetings with agendas available over placeholder/generated ones
- If a recurring meeting appears multiple times, pick the SOONEST occurrence and deprioritize later instances. Use the remaining slots for different meetings instead.

Article summary: {article_summary}
Detected issues: {issues_text}

Upcoming meetings:
{meeting_list_text}

Return ONLY a JSON array of the numbers of your top {limit} picks, most relevant first.
Example: [3, 7, 1, 12, 5]"""

    try:
        response = anthropic_client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=200,
            messages=[{"role": "user", "content": ranking_prompt}]
        )

        response_text = response.content[0].text.strip()

        # Parse the JSON array
        if "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()
            if response_text.startswith("json"):
                response_text = response_text[4:].strip()

        picks = json.loads(response_text)

        # Convert 1-indexed picks to meeting objects
        ranked = []
        for pick in picks:
            idx = pick - 1
            if 0 <= idx < len(meetings):
                ranked.append(meetings[idx])

        return ranked[:limit]

    except Exception as e:
        print(f"AI meeting ranking error: {e}")
        return []


def rank_comment_periods_with_ai(
    periods: List[dict],
    article_summary: str,
    detected_issues: List[str],
    limit: int = 3
) -> List[dict]:
    """Use Claude to pick the most relevant comment periods for an article.

    Sends open comment periods to Haiku and lets it semantically select the best
    matches based on article content, agency relevance, and deadline urgency.
    Cost: ~$0.01 per call (comment periods are few).
    """

    if not periods or not article_summary:
        return []

    # Build compact period list for the prompt
    today = datetime.now(timezone.utc).date()
    period_descriptions = []
    for i, p in enumerate(periods):
        title = p.get("title", "Unknown")
        agency = p.get("agency", "")
        end_date = p.get("end_date", "")
        description = (p.get("description") or "")[:200]
        tags = ", ".join(p.get("issue_tags") or [])
        comment_url = "has link" if p.get("comment_url") else "no link"

        days_left = ""
        if end_date:
            try:
                end = datetime.fromisoformat(end_date).date()
                days_left = f"{(end - today).days} days left"
            except Exception:
                pass

        desc = f"{i+1}. {title} ({agency})"
        if days_left:
            desc += f" — deadline {end_date}, {days_left}"
        desc += f", {comment_url}"
        if tags:
            desc += f" | tags: {tags}"
        if description:
            desc += f" | {description}"
        period_descriptions.append(desc)

    period_list_text = "\n".join(period_descriptions)
    issues_text = ", ".join(detected_issues) if detected_issues else "general"

    ranking_prompt = f"""You are helping a Michigan environmental journalism outlet (Planet Detroit) recommend open public comment periods to readers of an article.

Given this article summary and the list of open comment periods, pick the {limit} MOST relevant comment periods for readers. Prioritize:
- Direct relevance to the article's subject matter (e.g., air quality article → EGLE air permit comment period)
- Deadline urgency (comment periods closing soon are higher priority)
- Significance of the decision being commented on
- Geographic overlap with the article's focus area
- Accessibility of the comment method (periods with links to submit comments are preferred)

Article summary: {article_summary}
Detected issues: {issues_text}

Open comment periods:
{period_list_text}

Return ONLY a JSON array of the numbers of your top {limit} picks, most relevant first.
Example: [2, 5, 1]"""

    try:
        response = anthropic_client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=200,
            messages=[{"role": "user", "content": ranking_prompt}]
        )

        response_text = response.content[0].text.strip()

        # Parse the JSON array
        if "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()
            if response_text.startswith("json"):
                response_text = response_text[4:].strip()

        picks = json.loads(response_text)

        # Convert 1-indexed picks to period objects
        ranked = []
        for pick in picks:
            idx = pick - 1
            if 0 <= idx < len(periods):
                # Add days_remaining to each selected period
                period = periods[idx]
                if period.get("end_date"):
                    try:
                        end = datetime.fromisoformat(period["end_date"]).date()
                        period["days_remaining"] = max(0, (end - today).days)
                    except Exception:
                        pass
                ranked.append(period)

        return ranked[:limit]

    except Exception as e:
        print(f"AI comment period ranking error: {e}")
        return []


def get_all_officials() -> List[dict]:
    """Fetch all elected officials from Supabase."""
    try:
        response = supabase.from_("officials")\
            .select("*")\
            .order("family_name")\
            .execute()
        return response.data or []
    except Exception as e:
        print(f"Error fetching officials: {e}")
        return []


def rank_officials_with_ai(
    officials: List[dict],
    article_summary: str,
    detected_issues: List[str],
    limit: int = 3
) -> List[dict]:
    """Use Claude to pick the most relevant elected officials for an article.

    Sends all ~147 MI legislators with committee names + roles to Haiku.
    Cost: ~$0.01-0.02 per call.
    """

    if not officials or not article_summary:
        return []

    # Build compact official list for the prompt
    official_descriptions = []
    for i, o in enumerate(officials):
        name = o.get("name", "Unknown")
        party = o.get("party", "")
        chamber = "Senate" if o.get("chamber") == "upper" else "House"
        district = o.get("current_district", "")
        committees = o.get("committees") or []
        roles = o.get("committee_roles") or []

        # Highlight leadership roles
        leadership = [
            f"{r['committee']} ({r['role']})"
            for r in roles
            if r.get("role") and r["role"] != "member"
        ]

        desc = f"{i+1}. {name} ({party}, {chamber} Dist. {district})"
        if committees:
            desc += f" [{', '.join(committees[:5])}]"
        if leadership:
            desc += f" LEADERSHIP: {'; '.join(leadership)}"
        official_descriptions.append(desc)

    official_list_text = "\n".join(official_descriptions)
    issues_text = ", ".join(detected_issues) if detected_issues else "general"

    ranking_prompt = f"""You are helping a Michigan environmental journalism outlet (Planet Detroit) recommend elected officials to readers of an article — officials whose committee jurisdictions are relevant to the article's topic.

Given this article summary and the full list of Michigan state legislators with their committee assignments, pick the {limit} MOST relevant officials for readers. Prioritize:
- Committee jurisdiction match (e.g., energy article → Energy Policy committee members)
- Leadership positions (chairs/vice-chairs of relevant committees carry more weight)
- Geographic relevance to the article's focus area
- Diversity of representation (mix of chambers, parties when relevant)

Article summary: {article_summary}
Detected issues: {issues_text}

Officials:
{official_list_text}

Return ONLY a JSON array of the numbers of your top {limit} picks, most relevant first.
Example: [3, 7, 1]"""

    try:
        response = anthropic_client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=200,
            messages=[{"role": "user", "content": ranking_prompt}]
        )

        response_text = response.content[0].text.strip()

        # Parse the JSON array
        if "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()
            if response_text.startswith("json"):
                response_text = response_text[4:].strip()

        picks = json.loads(response_text)

        # Convert 1-indexed picks to official objects
        ranked = []
        for pick in picks:
            idx = pick - 1
            if 0 <= idx < len(officials):
                ranked.append(officials[idx])

        return ranked[:limit]

    except Exception as e:
        print(f"AI official ranking error: {e}")
        return []


def generate_civic_actions(issues: List[str], question: str) -> List[dict]:
    """Generate relevant civic actions based on issues"""
    
    actions = []
    
    if "dte_energy" in issues or "data_centers" in issues:
        actions.extend([
            {
                "action_type": "comment",
                "title": "Submit comments to MPSC",
                "description": "File public comments on utility rate cases and energy policy decisions",
                "url": "https://michigan.gov/mpsc"
            },
            {
                "action_type": "attend",
                "title": "Attend MPSC public hearings",
                "description": "Participate in Michigan Public Service Commission meetings",
                "url": None
            }
        ])
    
    if "air_quality" in issues:
        actions.extend([
            {
                "action_type": "monitor",
                "title": "Check local air quality",
                "description": "Monitor AQI levels in your area using EPA's AirNow",
                "url": "https://www.airnow.gov/"
            },
            {
                "action_type": "comment",
                "title": "Comment on air permits",
                "description": "Submit comments on EGLE air quality permit applications",
                "url": "https://www.michigan.gov/egle/about/organization/air-quality"
            }
        ])
    
    if "drinking_water" in issues:
        actions.extend([
            {
                "action_type": "test",
                "title": "Test your water",
                "description": "Request a water quality test from your local utility",
                "url": None
            },
            {
                "action_type": "check",
                "title": "Check for lead service lines",
                "description": "Find out if your home has lead pipes that need replacement",
                "url": "https://www.michigan.gov/egle/about/organization/drinking-water-and-environmental-health/community-water-supply/lead-service-line-replacement"
            }
        ])
    
    # Always include these
    actions.extend([
        {
            "action_type": "follow",
            "title": "Follow Planet Detroit's coverage",
            "description": "Stay informed on this issue with ongoing journalism",
            "url": "https://planetdetroit.org"
        },
        {
            "action_type": "subscribe",
            "title": "Subscribe to Planet Detroit newsletter",
            "description": "Get environmental news delivered to your inbox",
            "url": "https://planetdetroit.org/newsletter"
        }
    ])
    
    return actions[:6]

# =============================================================================
# API Endpoints
# =============================================================================

@app.get("/")
async def root():
    return {"message": "Ask Planet Detroit API", "version": "1.0.0"}

@app.get("/api/stats")
async def get_stats():
    """Get database statistics"""
    try:
        # Get article chunks count
        chunks_response = supabase.from_("article_chunks")\
            .select("id", count="exact")\
            .execute()
        
        # Get organizations count
        orgs_response = supabase.from_("organizations")\
            .select("id", count="exact")\
            .execute()
        
        # Get upcoming meetings count
        meetings_response = supabase.from_("meetings")\
            .select("id", count="exact")\
            .gte("start_datetime", datetime.now(timezone.utc).isoformat())\
            .execute()
        
        # Get open comment periods count
        periods_response = supabase.from_("comment_periods")\
            .select("id", count="exact")\
            .gte("end_date", datetime.now(timezone.utc).date().isoformat())\
            .execute()
        
        return {
            "total_chunks": chunks_response.count or 0,
            "total_organizations": orgs_response.count or 0,
            "upcoming_meetings": meetings_response.count or 0,
            "open_comment_periods": periods_response.count or 0
        }
    except Exception as e:
        print(f"Stats error: {e}")
        return {
            "total_chunks": 0,
            "total_organizations": 0,
            "upcoming_meetings": 0,
            "open_comment_periods": 0
        }

@app.post("/api/search")
async def search(request: SearchRequest):
    """Search articles and synthesize an answer"""
    start_time = time.time()
    
    question = request.question
    num_results = request.num_results
    
    # Get embedding for question
    try:
        query_embedding = get_embedding(question)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Embedding error: {str(e)}")
    
    # Search using Supabase RPC function
    try:
        response = supabase.rpc(
            "match_articles_simple",
            {
                "query_embedding": query_embedding,
                "match_count": num_results
            }
        ).execute()
        
        chunks = response.data or []
    except Exception as e:
        print(f"Search error: {e}")
        chunks = []
    
    # Detect issues from question
    detected_issues = []
    question_lower = question.lower()
    
    if any(w in question_lower for w in ["data center", "tech", "server", "computing"]):
        detected_issues.append("data_centers")
    if any(w in question_lower for w in ["dte", "utility", "power outage", "electric", "rate"]):
        detected_issues.append("dte_energy")
    if any(w in question_lower for w in ["air", "pollution", "emissions", "smog", "breathe"]):
        detected_issues.append("air_quality")
    if any(w in question_lower for w in ["water", "drink", "pfas", "lead", "contamination"]):
        detected_issues.append("drinking_water")
    if any(w in question_lower for w in ["climate", "warming", "carbon", "renewable"]):
        detected_issues.append("climate")
    
    # Synthesize answer
    answer = None
    if request.synthesize and chunks:
        try:
            answer = synthesize_answer(question, chunks)
        except Exception as e:
            print(f"Synthesis error: {e}")
            answer = "Unable to synthesize answer at this time."
    
    # Get related organizations via AI ranking
    all_orgs = get_all_organizations()
    related_orgs = rank_organizations_with_ai(all_orgs, answer, detected_issues, limit=5)
    
    # Generate civic actions
    civic_actions = generate_civic_actions(detected_issues, question)
    
    # Calculate unique articles
    unique_articles = len(set(c.get("article_id") for c in chunks))
    
    elapsed_time = int((time.time() - start_time) * 1000)
    
    return {
        "question": question,
        "answer": answer,
        "sources": chunks,
        "unique_articles": unique_articles,
        "detected_issues": detected_issues,
        "related_organizations": related_orgs,
        "civic_actions": civic_actions,
        "search_time_ms": elapsed_time
    }

# =============================================================================
# Meetings Endpoints
# =============================================================================

@app.get("/api/meetings")
async def list_meetings(
    status: Optional[str] = Query(None, description="Filter by status: upcoming, past, all"),
    agency: Optional[str] = Query(None, description="Filter by agency"),
    issue: Optional[str] = Query(None, description="Filter by issue tag"),
    limit: int = Query(50, le=500),
    offset: int = Query(0)
):
    """List meetings with optional filters"""
    try:
        query = supabase.from_("meetings")\
            .select("*")\
            .order("start_datetime", desc=False)
        
        # Status filter
        if status == "upcoming":
            query = query.gte("start_datetime", datetime.now(timezone.utc).isoformat())
        elif status == "past":
            query = query.lt("start_datetime", datetime.now(timezone.utc).isoformat())
        
        # Agency filter
        if agency:
            query = query.eq("agency", agency)
        
        # Pagination
        query = query.range(offset, offset + limit - 1)
        
        response = query.execute()
        meetings = response.data or []
        
        # Filter by issue in Python (Supabase doesn't support array contains well)
        if issue:
            meetings = [m for m in meetings if issue in (m.get("issue_tags") or [])]
        
        return {"meetings": meetings, "count": len(meetings)}
        
    except Exception as e:
        print(f"Meetings error: {e}")
        return {"meetings": [], "count": 0}

@app.get("/api/meetings/{meeting_id}")
async def get_meeting(meeting_id: str):
    """Get a single meeting by ID"""
    try:
        response = supabase.from_("meetings")\
            .select("*")\
            .eq("id", meeting_id)\
            .single()\
            .execute()
        
        return response.data
    except Exception as e:
        raise HTTPException(status_code=404, detail="Meeting not found")

# =============================================================================
# Comment Periods Endpoints
# =============================================================================

@app.get("/api/comment-periods")
async def list_comment_periods(
    status: Optional[str] = Query(None, description="Filter by status: open, closed, all"),
    agency: Optional[str] = Query(None, description="Filter by agency"),
    limit: int = Query(25, le=100),
    offset: int = Query(0)
):
    """List comment periods with optional filters"""
    try:
        query = supabase.from_("comment_periods")\
            .select("*")\
            .order("end_date", desc=False)
        
        today = datetime.now(timezone.utc).date().isoformat()
        
        if status == "open":
            query = query.gte("end_date", today)
        elif status == "closed":
            query = query.lt("end_date", today)
        
        if agency:
            query = query.eq("agency", agency)
        
        query = query.range(offset, offset + limit - 1)
        
        response = query.execute()
        periods = response.data or []
        
        # Add days_remaining calculation
        for period in periods:
            if period.get("end_date"):
                end = datetime.fromisoformat(period["end_date"])
                now = datetime.now(timezone.utc)
                if end.tzinfo is None:
                    end = end.replace(tzinfo=timezone.utc)
                days = (end - now).days
                period["days_remaining"] = max(0, days)
        
        return {"comment_periods": periods, "count": len(periods)}
        
    except Exception as e:
        print(f"Comment periods error: {e}")
        return {"comment_periods": [], "count": 0}

@app.get("/api/comment-periods/{period_id}")
async def get_comment_period(period_id: str):
    """Get a single comment period by ID"""
    try:
        response = supabase.from_("comment_periods")\
            .select("*")\
            .eq("id", period_id)\
            .single()\
            .execute()
        
        return response.data
    except Exception as e:
        raise HTTPException(status_code=404, detail="Comment period not found")

# =============================================================================
# Organizations Endpoints
# =============================================================================

@app.get("/api/organizations")
async def list_organizations(
    search: Optional[str] = Query(None, description="Search by name or focus"),
    focus: Optional[str] = Query(None, description="Filter by focus area"),
    region: Optional[str] = Query(None, description="Filter by region"),
    limit: int = Query(100, le=700),
    offset: int = Query(0)
):
    """List organizations with optional filters"""
    try:
        query = supabase.from_("organizations")\
            .select("name, url, mission_statement_text, focus, region, city, state")\
            .order("name")
        
        # Text search on name
        if search:
            query = query.ilike("name", f"%{search}%")
        
        # Region filter
        if region:
            query = query.eq("region", region)
        
        # Pagination
        query = query.range(offset, offset + limit - 1)
        
        response = query.execute()
        organizations = response.data or []
        
        # Filter by focus in Python (array field)
        if focus:
            organizations = [
                org for org in organizations 
                if org.get("focus") and any(focus.lower() in f.lower() for f in org["focus"])
            ]
        
        return {"organizations": organizations, "count": len(organizations)}
        
    except Exception as e:
        print(f"Organizations error: {e}")
        return {"organizations": [], "count": 0}

@app.get("/api/organizations/{org_id}")
async def get_organization(org_id: str):
    """Get a single organization by ID"""
    try:
        response = supabase.from_("organizations")\
            .select("*")\
            .eq("id", org_id)\
            .single()\
            .execute()
        
        return response.data
    except Exception as e:
        raise HTTPException(status_code=404, detail="Organization not found")

# =============================================================================
# Officials Endpoints
# =============================================================================

@app.get("/api/officials")
async def list_officials(
    chamber: Optional[str] = Query(None, description="Filter by chamber: upper, lower"),
    search: Optional[str] = Query(None, description="Search by name or committee"),
    party: Optional[str] = Query(None, description="Filter by party"),
    limit: int = Query(200, le=500),
    offset: int = Query(0)
):
    """List elected officials with optional filters"""
    try:
        query = supabase.from_("officials")\
            .select("*")\
            .order("family_name")

        if chamber:
            query = query.eq("chamber", chamber)

        if party:
            query = query.eq("party", party)

        if search:
            query = query.ilike("name", f"%{search}%")

        query = query.range(offset, offset + limit - 1)

        response = query.execute()
        officials = response.data or []

        return {"officials": officials, "count": len(officials)}

    except Exception as e:
        print(f"Officials error: {e}")
        return {"officials": [], "count": 0}

@app.get("/api/officials/{official_id}")
async def get_official(official_id: str):
    """Get a single official by ID"""
    try:
        response = supabase.from_("officials")\
            .select("*")\
            .eq("id", official_id)\
            .single()\
            .execute()

        return response.data
    except Exception as e:
        raise HTTPException(status_code=404, detail="Official not found")

# =============================================================================
# Civic Hub Combined Endpoint
# =============================================================================

@app.get("/api/civic")
async def get_civic_data():
    """Get combined civic data for the hub"""
    meetings = await list_meetings(status="upcoming", limit=5, offset=0)
    periods = await list_comment_periods(status="open", limit=5, offset=0)
    
    return {
        "meetings": meetings.get("meetings", []),
        "comment_periods": periods.get("comment_periods", [])
    }

# =============================================================================
# Article Analysis Endpoint (for Civic Action Box Builder)
# =============================================================================

@app.post("/api/analyze-article")
async def analyze_article(request: AnalyzeArticleRequest):
    """
    Analyze an article and return detected issues, related organizations,
    and suggested civic actions for the Civic Action Box Builder.
    """
    start_time = time.time()
    
    article_text = request.article_text[:15000]  # Limit length
    
    # Use Claude to analyze the article
    analysis_prompt = f"""Analyze this news article and extract:

1. DETECTED_ISSUES: Which of these priority issues does the article cover? Return as a list.
   - data_centers (Michigan data centers, tech infrastructure, energy demand)
   - dte_energy (DTE, utility rates, power outages, energy policy)
   - air_quality (air pollution, emissions, respiratory health)
   - drinking_water (water quality, PFAS, lead, contamination)
   - climate (climate change, renewable energy, sustainability)
   - housing (housing policy, development, zoning)
   - transportation (transit, roads, EV infrastructure)
   - environmental_justice (pollution burden, equity, frontline communities)

2. ENTITIES: Key organizations, agencies, companies, or officials mentioned (max 10)

3. SUMMARY: One paragraph summary of what the article is about (2-3 sentences)

4. CIVIC_ACTIONS: 3-5 actions that connect readers to civic infrastructure related to this article.

   IMPORTANT EDITORIAL GUIDELINES — this is for a journalism outlet, not an advocacy organization:
   - YES: Actions that connect people to democratic processes, public information, and civic institutions
     (attend a public meeting, submit a public comment, look up your representative, check a public database,
     read a government report, find your polling place, request public records, test your water, check air quality)
   - NO: Actions that advocate for specific policy positions or tell readers what to support/oppose
     (sign a petition, call your representative to demand X, support/oppose a bill, join a campaign)
   - The goal is to INFORM and CONNECT, not to PERSUADE. Show readers WHERE decisions are being made
     and HOW to participate — never tell them WHAT position to take.
   - Be specific: name the actual agency, docket, database, or government body. Avoid vague actions.
   - If the article mentions a specific public proceeding (rate case, permit application, rulemaking),
     reference it by name and tell readers where to find it.

   For each action, provide:
   - action_type: one of [attend, comment, learn, monitor, check, lookup, request, vote]
   - title: Short action title (imperative verb)
   - description: One concrete sentence telling the reader exactly what to do and where
   - url: A relevant government or institutional URL (or null if not applicable)

Article text:
{article_text}

Respond in this exact JSON format:
{{
  "detected_issues": ["issue1", "issue2"],
  "entities": ["Entity 1", "Entity 2"],
  "summary": "Summary text here...",
  "civic_actions": [
    {{"action_type": "attend", "title": "Action title", "description": "Description", "url": null}}
  ]
}}"""

    try:
        response = anthropic_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=[{"role": "user", "content": analysis_prompt}]
        )
        
        response_text = response.content[0].text.strip()
        
        # Parse JSON from response
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()
        
        analysis = json.loads(response_text)
        
    except Exception as e:
        print(f"Claude analysis error: {e}")
        # Fallback analysis
        analysis = {
            "detected_issues": [],
            "entities": [],
            "summary": "Could not analyze article.",
            "civic_actions": []
        }
    
    # AI-powered org matching: send all orgs to Haiku for semantic ranking
    all_orgs = get_all_organizations()
    related_organizations = rank_organizations_with_ai(
        all_orgs,
        analysis.get("summary", ""),
        analysis.get("detected_issues", []),
        limit=5
    )

    # AI-powered meeting matching: send upcoming meetings to Haiku for ranking
    upcoming_meetings = get_upcoming_meetings(limit=200)
    related_meetings = rank_meetings_with_ai(
        upcoming_meetings,
        analysis.get("summary", ""),
        analysis.get("detected_issues", []),
        limit=5
    )

    # AI-powered comment period matching: send open periods to Haiku for ranking
    open_periods = get_open_comment_periods(limit=50)
    related_comment_periods = rank_comment_periods_with_ai(
        open_periods,
        analysis.get("summary", ""),
        analysis.get("detected_issues", []),
        limit=3
    )

    # AI-powered official matching: send all officials to Haiku for ranking
    all_officials = get_all_officials()
    related_officials = rank_officials_with_ai(
        all_officials,
        analysis.get("summary", ""),
        analysis.get("detected_issues", []),
        limit=3
    )

    elapsed_time = int((time.time() - start_time) * 1000)

    return {
        "detected_issues": analysis.get("detected_issues", []),
        "entities": analysis.get("entities", []),
        "summary": analysis.get("summary", ""),
        "civic_actions": analysis.get("civic_actions", []),
        "related_organizations": related_organizations,
        "related_meetings": related_meetings,
        "related_comment_periods": related_comment_periods,
        "related_officials": related_officials,
        "analysis_time_ms": elapsed_time
    }

# =============================================================================
# Run server
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
