-- Generalize agenda_summaries table for multi-source support
-- Previously Detroit-only (escribemeetings_guid). Now supports GLWA, EGLE, MPSC.

-- Add source column to identify which scraper created the summary
ALTER TABLE agenda_summaries ADD COLUMN IF NOT EXISTS source TEXT;

-- Add a generic source_id for non-Detroit sources (reuses the meeting's source_id)
ALTER TABLE agenda_summaries ADD COLUMN IF NOT EXISTS source_meeting_id TEXT;

-- Backfill existing Detroit records
UPDATE agenda_summaries
SET source = 'detroit_agenda',
    source_meeting_id = escribemeetings_guid
WHERE source IS NULL;

-- Make escribemeetings_guid nullable for non-Detroit sources
ALTER TABLE agenda_summaries ALTER COLUMN escribemeetings_guid DROP NOT NULL;

-- Add unique constraint for generic sources
-- Each source + source_meeting_id pair should have at most one summary
CREATE UNIQUE INDEX IF NOT EXISTS idx_agenda_summaries_source_meeting
  ON agenda_summaries(source, source_meeting_id);
