# Briefing Flow Summary

## ✅ Confirmed Flow

### 1. **First-Time User Requests Briefing**
```
User asks for briefing
    ↓
System checks database table → No record found
    ↓
Fetches briefing from HR API
    ↓
Creates new record in briefing_cache table ✅
    ↓
Returns briefing to user
```

**Code Flow:**
- `get_daily_briefing()` → checks `load_briefing_from_db()` → returns `None`
- Fetches from HR API
- Calls `save_briefing_cache_async()` → `save_briefing_to_db()` → **INSERT INTO briefing_cache** ✅

---

### 2. **Scheduled Background Tasks (5 AM & 5 PM)**
```
Scheduler triggers at 5 AM / 5 PM
    ↓
Gets all active users from database
    ↓
For each user:
    - Fetches briefing from HR API
    - Updates/Creates record in briefing_cache table ✅
```

**Code Flow:**
- `scheduled_briefing_task()` → `get_all_active_users()`
- For each user: `fetch_and_cache_briefing_for_user()`
- Calls `save_briefing_to_db()` → **INSERT ... ON CONFLICT UPDATE** ✅
- Updates existing records or creates new ones

---

### 3. **User Requests Briefing (After First Time)**
```
User asks for briefing
    ↓
System checks database table → Record found ✅
    ↓
Retrieves briefing directly from table (instant response)
    ↓
Returns briefing to user (no API call needed)
```

**Code Flow:**
- `get_daily_briefing()` → checks `load_briefing_from_db()`
- Returns briefing from database immediately ✅
- No HR API call needed - fast response!

---

## Key Points

✅ **First-time user**: Creates record when they ask for briefing  
✅ **Scheduled tasks**: Update/refresh briefings at 5 AM and 5 PM for all users  
✅ **Subsequent requests**: Always retrieved from table (fast, no API call)  
✅ **Database is source of truth**: All briefings stored and retrieved from `briefing_cache` table

## Database Operations

| Scenario | Operation | Result |
|----------|-----------|--------|
| First-time user asks | `INSERT INTO briefing_cache` | Creates new record |
| Scheduled task (5 AM/5 PM) | `INSERT ... ON CONFLICT UPDATE` | Updates existing or creates new |
| User asks later | `SELECT FROM briefing_cache` | Retrieves from table |

## Example Timeline

**Day 1 - Morning:**
- 5:00 AM: Scheduler runs → Updates briefings for all users
- 9:00 AM: User A asks for briefing → Retrieved from table (fast)
- 10:00 AM: User B (first-time) asks → Fetches from API → Creates record

**Day 1 - Evening:**
- 5:00 PM: Scheduler runs → Updates briefings for all users
- 6:00 PM: User A asks → Retrieved from table (fast)
- 7:00 PM: User B asks → Retrieved from table (fast)

**Day 2:**
- 5:00 AM: Scheduler runs → Updates briefings for all users
- All users: Briefings retrieved from table (fast)

---

## Summary

✅ **Yes, you're correct!**

1. First-time user asks → Creates record in table
2. Background scheduler at 5 AM/5 PM → Updates records in table
3. User asks later → Retrieved from table (instant response)

The database table is the single source of truth, and all operations work with it! 🎯

