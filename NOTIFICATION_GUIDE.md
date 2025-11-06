# Email Notification Guide

## 📧 When Email Notifications Are Sent

Email notifications are sent automatically when errors reach certain thresholds based on their severity level.

### Notification Thresholds

| Severity | Threshold | When Email is Sent |
|----------|-----------|-------------------|
| **CRITICAL** | 1 occurrence | ✅ **Immediately** - First time the error occurs |
| **HIGH** | 3 occurrences | ✅ After the error happens **3 times** |
| **MEDIUM** | 5 occurrences | ✅ After the error happens **5 times** |
| **LOW** | 10 occurrences | ✅ After the error happens **10 times** |

### Example Scenarios

**Scenario 1: Critical Error**
- Error occurs: `DATABASE_SAVE_FAILED` (CRITICAL)
- **Email sent immediately** on the 1st occurrence
- No need to wait for multiple occurrences

**Scenario 2: High Severity Error**
- Error occurs: `HR_API_ERROR` (HIGH)
- 1st occurrence: No email (just logged)
- 2nd occurrence: No email (just logged)
- 3rd occurrence: ✅ **Email sent** (threshold reached)

**Scenario 3: Medium Severity Error**
- Error occurs: `HR_API_TIMEOUT` (MEDIUM)
- Errors 1-4: No email (just logged)
- 5th occurrence: ✅ **Email sent** (threshold reached)

**Scenario 4: Low Severity Error**
- Error occurs: `SCHEDULED_TASK_NO_USERS` (LOW)
- Errors 1-9: No email (just logged)
- 10th occurrence: ✅ **Email sent** (threshold reached)

## 🔔 Error Types That Trigger Notifications

### Critical Errors (Email Sent Immediately)
- `DB_POOL_CREATE_FAILED` - Cannot create database connection pool
- `SCHEDULED_TASK_CRITICAL_FAILURE` - Scheduled task completely failed
- `DB_POOL_HEALTH_CHECK_FAILED` - Database health check failed

### High Severity Errors (Email After 3 Occurrences)
- `DATABASE_SAVE_FAILED` - Failed to save briefing to database
- `DATABASE_FETCH_USERS_FAILED` - Failed to fetch active users
- `HR_API_ERROR` - HR API returned error status
- `HR_API_REQUEST_FAILED` - HR API request failed
- `BRIEFING_FETCH_FAILED` - Error fetching briefing
- `FETCH_USER_DETAILS_FAILED` - Failed to fetch user details
- `DB_POOL_EXHAUSTED` - Database connection pool exhausted

### Medium Severity Errors (Email After 5 Occurrences)
- `DATABASE_LOAD_FAILED` - Failed to load briefing from database
- `DATABASE_CHECK_FAILED` - Failed to check if user has briefing
- `HR_API_TIMEOUT` - HR API request timed out
- `TENANT_NOT_FOUND` - No tenant found for user
- `DB_POOL_BELOW_MIN` - Connection pool below minimum size
- `SCHEDULED_TASK_PARTIAL_FAILURE` - Some users failed in scheduled task

### Low Severity Errors (Email After 10 Occurrences)
- `SCHEDULED_TASK_NO_USERS` - No active users found for briefing generation

## 📋 Email Notification Content

Each email notification includes:
- **Subject:** 🚨 HR Worker Alert: [Error Type] - [Severity]
- **Error Type:** Type of error (e.g., DATABASE_SAVE_FAILED)
- **Message:** Human-readable error message
- **Severity:** CRITICAL, HIGH, MEDIUM, or LOW
- **Timestamp:** When the error occurred
- **Occurrence Count:** How many times this error has occurred
- **Context:** Additional context information (user_id, cache_type, etc.)
- **Exception:** Full exception details (if available)

## ⚙️ Configuration

### Required Environment Variables

```bash
# Email sender configuration
ALERT_EMAIL_FROM=alerts@yourcompany.com
ALERT_EMAIL_PASSWORD=your_email_password

# Email recipients (comma-separated)
ALERT_EMAIL_TO=admin@company.com,devops@company.com

# SMTP server (optional, defaults to Gmail)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
```

### Setup Steps

1. **Set environment variables:**
   ```bash
   export ALERT_EMAIL_FROM="alerts@yourcompany.com"
   export ALERT_EMAIL_PASSWORD="your_password"
   export ALERT_EMAIL_TO="admin@company.com,devops@company.com"
   ```

2. **For Gmail:**
   - Use an App Password (not your regular password)
   - Enable "Less secure app access" or use App Passwords
   - Set `SMTP_SERVER=smtp.gmail.com` and `SMTP_PORT=587`

3. **For other email providers:**
   - Update `SMTP_SERVER` and `SMTP_PORT` accordingly
   - Check your email provider's SMTP settings

## 📊 Notification Frequency

### Important Notes

1. **Threshold-Based:** Notifications are sent when the error count reaches the threshold, not on every occurrence
2. **Per Error Type:** Each error type is tracked separately
   - Example: `DATABASE_SAVE_FAILED` and `HR_API_ERROR` are tracked independently
3. **Reset:** Error counts are maintained in memory (reset on restart)
4. **Immediate for Critical:** CRITICAL errors always trigger immediate notification

### Example Timeline

**Day 1:**
- 9:00 AM: `HR_API_TIMEOUT` (MEDIUM) - 1st occurrence → No email
- 9:05 AM: `HR_API_TIMEOUT` - 2nd occurrence → No email
- 9:10 AM: `HR_API_TIMEOUT` - 5th occurrence → ✅ **Email sent**

**Day 2:**
- 10:00 AM: `DATABASE_SAVE_FAILED` (HIGH) - 1st occurrence → No email
- 10:05 AM: `DATABASE_SAVE_FAILED` - 2nd occurrence → No email
- 10:10 AM: `DATABASE_SAVE_FAILED` - 3rd occurrence → ✅ **Email sent**

**Day 3:**
- 11:00 AM: `DB_POOL_CREATE_FAILED` (CRITICAL) - 1st occurrence → ✅ **Email sent immediately**

## 🔍 Monitoring

### Check if Email is Configured

On startup, you'll see one of these messages:
- ✅ `Email notifications configured` - Email is set up correctly
- ⚠️ `Email notifications not configured` - Set environment variables to enable

### View Error Logs

All errors are still logged to the application logs regardless of whether email is sent:
```bash
# Check logs for error details
grep "\[HIGH\]\|\[CRITICAL\]" your_log_file.log
```

## 🎯 Summary

- **CRITICAL errors:** Email sent immediately (1st occurrence)
- **HIGH errors:** Email sent after 3 occurrences
- **MEDIUM errors:** Email sent after 5 occurrences  
- **LOW errors:** Email sent after 10 occurrences
- **All errors:** Always logged to application logs
- **Email only:** Slack and file notifications removed
- **Configurable:** Set via environment variables

