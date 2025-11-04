# Briefing Cache Implementation

## Overview
This implementation adds a database-backed caching mechanism for HR worker briefings with scheduled tasks that run at 5 AM and 5 PM for all active users.

## Features

### 1. Database Storage
- **Table**: `briefing_cache`
  - `id`: Primary key
  - `user_id`: User identifier
  - `briefing_content`: The briefing text
  - `cache_type`: 'morning', 'evening', or 'general'
  - `cache_date`: Date of the briefing (for daily filtering)
  - `created_at`: Timestamp when record was created
  - `updated_at`: Timestamp when record was last updated
  - Unique constraint on `(user_id, cache_date, cache_type)`

### 2. Scheduled Tasks
- **Morning Briefing**: Runs at 5:00 AM daily
- **Evening Briefing**: Runs at 5:00 PM daily
- Both tasks:
  - Fetch all active users from the database
  - Generate briefings for each user by calling the HR API
  - Store briefings in the database
  - Process users in batches of 10 to avoid API rate limits

### 3. Cache Strategy
The system uses a multi-tier caching approach:
1. **Database** (most reliable) - Checked first
2. **In-memory** (fastest) - For active sessions
3. **File** (backup) - For persistence across restarts

### 4. User Onboarding (First-Time vs Existing Users)
**First-Time Users:**
- When a user logs in for the first time and has no briefing record in the table:
  - System detects this is a first-time user
  - Automatically fetches briefing from HR API
  - Creates a new record in the `briefing_cache` table
  - Uses scheduler/async task to fetch and store

**Existing Users:**
- When a user already has a briefing record in the table:
  - System retrieves briefing directly from the database table
  - No API call needed - instant response
  - Fast and efficient data retrieval

## Key Functions

### Database Functions
- `ensure_briefing_table_exists()`: Creates the briefing_cache table if it doesn't exist
- `user_has_briefing_in_db(user_id)`: Checks if user has a briefing record in the table (for first-time detection)
- `save_briefing_to_db(user_id, briefing_content, cache_type)`: Saves or updates briefing in database
- `load_briefing_from_db(user_id, cache_type)`: Loads briefing from database table
- `get_all_active_users()`: Retrieves all active users from database

### Scheduled Task Functions
- `fetch_and_cache_briefing_for_user(user_id, cache_type)`: Fetches briefing from HR API and caches it
- `scheduled_briefing_task(cache_type)`: Main scheduled task that processes all users
- `start_scheduled_briefing_tasks()`: Initializes and starts the scheduler

### Cache Functions
- `load_briefing_cache_async()`: Async version that checks database first
- `save_briefing_cache_async()`: Async version that saves to database
- `get_cached_briefing_async()`: Async version that checks database first

## How It Works

### Scheduled Generation
1. At 5 AM and 5 PM, scheduled tasks trigger
2. System fetches all active users from database
3. For each user, calls HR API to get briefing
4. Stores briefing in database with appropriate cache_type
5. Updates in-memory cache for fast access

### User Request Flow

**For Existing Users (with briefing in table):**
1. User requests briefing
2. System checks database table first
3. If briefing record exists, returns immediately from table (fast response)
4. Updates in-memory cache for even faster future access

**For First-Time Users (no briefing in table):**
1. User requests briefing or starts app
2. System checks database table - no record found
3. System detects this is a first-time user
4. Fetches briefing from HR API
5. Creates new record in `briefing_cache` table
6. Returns briefing to user
7. Future requests will use the table (existing user flow)

**Fallback Mechanism:**
- If database check fails, falls back to in-memory cache
- If in-memory cache fails, falls back to file cache
- If all caches fail, fetches from HR API and creates record

## Database Schema

```sql
CREATE TABLE IF NOT EXISTS briefing_cache (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    briefing_content TEXT NOT NULL,
    cache_type VARCHAR(20) NOT NULL DEFAULT 'general',
    cache_date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, cache_date, cache_type)
);

CREATE INDEX idx_briefing_cache_user_date ON briefing_cache(user_id, cache_date);
```

## Configuration

The database connection uses the same configuration as the existing `fetch_user_details_from_db` function:
- Host: `acabot-dbcluster-dev.cluster-cp2eea8yihxz.us-east-1.rds.amazonaws.com`
- Database: `acabotdb-dev`
- User: `AN24_Acabot`
- Port: `5432`

## Dependencies

- `apscheduler~=3.10`: For scheduled task management
- `asyncpg`: Already included for database operations

## Usage

The system automatically:
- Creates the database table on startup
- Starts scheduled tasks when the agent starts
- Checks and creates briefings when users connect
- Caches briefings whenever they're fetched

No manual intervention required - the system handles everything automatically!

## Notes

- The scheduler runs in the background and persists across agent sessions
- Briefings are stored per user, per day, per type (morning/evening/general)
- The system handles concurrent requests efficiently
- Failed briefing fetches are logged but don't crash the system
- Database operations are non-blocking and use connection pooling

