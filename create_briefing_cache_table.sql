-- Briefing Cache Table Creation Script
-- This table stores daily briefings for users with morning and evening cache types
-- Run this script to create the briefing_cache table in your PostgreSQL database

-- Create the briefing_cache table
CREATE TABLE IF NOT EXISTS briefing_cache (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    briefing_content TEXT NOT NULL,
    cache_type VARCHAR(20) NOT NULL DEFAULT 'general',  -- 'morning', 'evening', or 'general'
    cache_date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, cache_date, cache_type)
);

-- Create index for faster lookups by user_id and cache_date
CREATE INDEX IF NOT EXISTS idx_briefing_cache_user_date ON briefing_cache(user_id, cache_date);

-- Create index for cache_type lookups
CREATE INDEX IF NOT EXISTS idx_briefing_cache_type ON briefing_cache(cache_type);

-- Create index for date-based queries
CREATE INDEX IF NOT EXISTS idx_briefing_cache_date ON briefing_cache(cache_date);

-- Add comment to table
COMMENT ON TABLE briefing_cache IS 'Stores daily briefings for users. Supports morning and evening briefings with automatic updates via scheduled tasks.';

-- Add comments to columns
COMMENT ON COLUMN briefing_cache.user_id IS 'Unique identifier for the user';
COMMENT ON COLUMN briefing_cache.briefing_content IS 'The actual briefing text content';
COMMENT ON COLUMN briefing_cache.cache_type IS 'Type of briefing: morning (5 AM), evening (5 PM), or general';
COMMENT ON COLUMN briefing_cache.cache_date IS 'Date for which the briefing is valid (allows one briefing per day per type per user)';
COMMENT ON COLUMN briefing_cache.created_at IS 'Timestamp when the record was first created';
COMMENT ON COLUMN briefing_cache.updated_at IS 'Timestamp when the record was last updated';

