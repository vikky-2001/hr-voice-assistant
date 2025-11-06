-- Additional Database Indexes for Performance Optimization
-- Run this script to add performance indexes to the briefing_cache table

-- Composite index for common queries (user_id, cache_date, cache_type)
CREATE INDEX IF NOT EXISTS idx_briefing_cache_user_date_type 
ON briefing_cache(user_id, cache_date, cache_type);

-- Index for scheduled task queries (by date and type)
CREATE INDEX IF NOT EXISTS idx_briefing_cache_date_type 
ON briefing_cache(cache_date, cache_type);

-- Index for cleanup operations
CREATE INDEX IF NOT EXISTS idx_briefing_cache_updated_at 
ON briefing_cache(updated_at);

-- Note: The base index idx_briefing_cache_user_date is already created 
-- in the table creation script

