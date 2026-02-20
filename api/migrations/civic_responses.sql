-- Civic Responses table
-- Tracks reader engagement with civic action checkboxes embedded in articles
-- Created: 2026-02-19

CREATE TABLE civic_responses (
    id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
    email text NOT NULL,
    article_url text NOT NULL,
    actions_taken jsonb NOT NULL DEFAULT '[]',
    article_title text,
    user_agent text,
    created_at timestamptz DEFAULT now()
);

-- Index for querying responses by article (e.g., "how many readers engaged with this article?")
CREATE INDEX idx_civic_responses_article ON civic_responses(article_url);

-- Index for querying by email (e.g., "what has this reader engaged with?")
CREATE INDEX idx_civic_responses_email ON civic_responses(email);

-- Row Level Security: service role can insert/read, anon cannot
ALTER TABLE civic_responses ENABLE ROW LEVEL SECURITY;

-- Allow service role to do everything (API uses service role key)
CREATE POLICY "Service role full access" ON civic_responses
    FOR ALL
    USING (true)
    WITH CHECK (true);
