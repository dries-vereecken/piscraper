-- Database schema for schedule scraper
-- Run this once in your PostgreSQL database

-- Create scrape_runs table to track each scraping run
CREATE TABLE IF NOT EXISTS scrape_runs (
    run_id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    git_sha TEXT
);

-- Create schedule_snapshots table to store individual class/session data
CREATE TABLE IF NOT EXISTS schedule_snapshots (
    id BIGSERIAL PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES scrape_runs(run_id) ON DELETE CASCADE,
    source TEXT NOT NULL,
    item_uid TEXT,
    class_name TEXT,
    instructor TEXT,
    location TEXT,
    start_ts TIMESTAMPTZ,
    end_ts TIMESTAMPTZ,
    capacity INTEGER,
    spots_available INTEGER,
    status TEXT,
    url TEXT,
    scraped_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    raw JSONB NOT NULL
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS ix_snapshots_source_start ON schedule_snapshots(source, start_ts);
CREATE INDEX IF NOT EXISTS ix_snapshots_uid ON schedule_snapshots(source, item_uid, start_ts);
CREATE INDEX IF NOT EXISTS ix_snapshots_scraped ON schedule_snapshots(scraped_at);
CREATE INDEX IF NOT EXISTS ix_snapshots_run_id ON schedule_snapshots(run_id);
CREATE INDEX IF NOT EXISTS ix_scrape_runs_source ON scrape_runs(source, started_at);

-- Add some useful views for analysis
CREATE OR REPLACE VIEW latest_schedule AS
SELECT DISTINCT ON (s.source, s.item_uid, s.start_ts) 
    s.*
FROM schedule_snapshots s
JOIN scrape_runs r ON s.run_id = r.run_id
ORDER BY s.source, s.item_uid, s.start_ts, r.started_at DESC;

-- View to see the most recent run for each source
CREATE OR REPLACE VIEW latest_runs AS
SELECT DISTINCT ON (source) 
    run_id,
    source,
    started_at,
    git_sha
FROM scrape_runs
ORDER BY source, started_at DESC;
