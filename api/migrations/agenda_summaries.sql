-- Agenda Summaries table
-- Stores AI-generated summaries of Detroit City Council meeting agendas
-- scraped from Detroit's eSCRIBE system.

-- Create the agenda_summaries table
CREATE TABLE IF NOT EXISTS agenda_summaries (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  meeting_id UUID REFERENCES meetings(id),
  escribemeetings_guid TEXT NOT NULL,   -- eSCRIBE meeting GUID for deduplication
  meeting_body TEXT NOT NULL,           -- e.g. "City Council Formal Session"
  meeting_date DATE NOT NULL,
  summary TEXT NOT NULL,                -- AI-generated plain-language summary
  key_topics TEXT[] DEFAULT '{}',       -- extracted topic tags
  agenda_items JSONB NOT NULL,          -- scraped agenda items for reference
  item_count INTEGER NOT NULL,
  ai_model TEXT NOT NULL,               -- e.g. "claude-haiku-4-5-20251001"
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(escribemeetings_guid)
);

-- Index for common queries
CREATE INDEX IF NOT EXISTS idx_agenda_summaries_meeting_date
  ON agenda_summaries(meeting_date DESC);

CREATE INDEX IF NOT EXISTS idx_agenda_summaries_meeting_id
  ON agenda_summaries(meeting_id);
