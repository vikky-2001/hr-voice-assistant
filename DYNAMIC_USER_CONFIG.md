# 🔄 Dynamic User Configuration Guide

This guide explains how to configure dynamic user_id and chatlog_id for the HR Voice Assistant.

## 🎯 Overview

The HR Voice Assistant now supports dynamic user identification through multiple methods:

1. **Environment Variables** (Highest Priority)
2. **Room-based Lookup** (Medium Priority)
3. **Identity-based Lookup** (Medium Priority)
4. **Default Fallback** (Lowest Priority)

## 🔧 Configuration Methods

### 1. Environment Variables (Recommended)

Set these environment variables in your deployment:

```bash
# Required: User identification
HR_USER_ID=your-user-id-here

# Optional: Chat log and agent configuration
HR_CHATLOG_ID=12345
HR_AGENT_ID=6
```

**Example:**
```bash
HR_USER_ID=79f2b410-bbbe-43b9-a77f-38a6213ce13d
HR_CHATLOG_ID=7747
HR_AGENT_ID=6
```

### 2. Room-based User Lookup

The system can automatically determine the user based on the LiveKit room name.

#### Supported Room Name Patterns:

**Pattern 1: User ID in Room Name**
```
Room Name: "user-12345"
→ User ID: "12345"
```

**Pattern 2: Named Room Mapping**
```python
room_user_mapping = {
    "john-doe-room": "user-john-doe-123",
    "jane-smith-room": "user-jane-smith-456",
    "hr-demo-room": "demo-user-789"
}
```

**Pattern 3: Custom Database Lookup**
```python
# Implement in lookup_user_by_room() function
user_id = database.lookup_user_by_room(room_name)
```

### 3. Identity-based User Lookup

The system can determine the user based on the participant identity.

#### Supported Identity Patterns:

**Pattern 1: User ID in Identity**
```
Identity: "user-12345"
→ User ID: "12345"
```

**Pattern 2: Email-based Lookup**
```
Identity: "john.doe@company.com"
→ User ID: lookup in database by email
```

**Pattern 3: Named Identity Mapping**
```python
identity_user_mapping = {
    "john.doe": "user-john-doe-123",
    "jane.smith": "user-jane-smith-456",
    "hr-demo": "demo-user-789"
}
```

## 🚀 Usage Examples

### Example 1: Environment Variable Configuration

```bash
# Set environment variables
export HR_USER_ID="user-abc123"
export HR_CHATLOG_ID="9999"
export HR_AGENT_ID="6"

# Deploy agent
lk agent deploy
```

### Example 2: Room-based Configuration

```bash
# Create room with user ID in name
Room Name: "user-abc123"
Identity: "Mobile-hr-worker"

# System will automatically extract user ID: "abc123"
```

### Example 3: Identity-based Configuration

```bash
# Use identity with user ID
Room Name: "Tester-room1"
Identity: "user-abc123"

# System will automatically extract user ID: "abc123"
```

### Example 4: Custom Mapping

```python
# Add to lookup_user_by_room() function
room_user_mapping = {
    "employee-john": "user-john-doe-123",
    "employee-jane": "user-jane-smith-456",
    "hr-demo": "demo-user-789"
}

# Add to lookup_user_by_identity() function
identity_user_mapping = {
    "john.doe": "user-john-doe-123",
    "jane.smith": "user-jane-smith-456",
    "hr-demo": "demo-user-789"
}
```

## 🔍 Priority Order

The system resolves user configuration in this order:

1. **Environment Variables** (`HR_USER_ID`, `HR_CHATLOG_ID`, `HR_AGENT_ID`)
2. **Room-based Lookup** (if room name is not default)
3. **Identity-based Lookup** (if identity is not default)
4. **Default Fallback** (hardcoded values)

## 📊 Configuration Resolution Logs

The system logs the configuration resolution process:

```
INFO: User config resolved: user_id=abc123, chatlog_id=9999, agent_id=6
INFO: User ID resolved from room 'user-abc123': abc123
INFO: User ID resolved from identity 'john.doe': user-john-doe-123
```

## 🛠️ Customization

### Adding New Room Patterns

Edit the `lookup_user_by_room()` function in `agent.py`:

```python
def lookup_user_by_room(room_name: str) -> str:
    # Add your custom patterns here
    
    # Pattern: employee-{id}
    if room_name.startswith("employee-"):
        employee_id = room_name.replace("employee-", "")
        return f"employee-{employee_id}"
    
    # Pattern: session-{user_id}-{timestamp}
    if room_name.startswith("session-"):
        parts = room_name.split("-")
        if len(parts) >= 3:
            return parts[1]  # Return user_id part
    
    # Your custom logic here
    return None
```

### Adding New Identity Patterns

Edit the `lookup_user_by_identity()` function in `agent.py`:

```python
def lookup_user_by_identity(participant_identity: str) -> str:
    # Add your custom patterns here
    
    # Pattern: {firstname}.{lastname}
    if "." in participant_identity and "@" not in participant_identity:
        # Look up user by name
        return lookup_user_by_name(participant_identity)
    
    # Pattern: employee-{id}
    if participant_identity.startswith("employee-"):
        return participant_identity
    
    # Your custom logic here
    return None
```

### Database Integration

To integrate with a database, modify the lookup functions:

```python
def lookup_user_by_room(room_name: str) -> str:
    try:
        # Example database lookup
        user_id = database.execute(
            "SELECT user_id FROM room_mappings WHERE room_name = ?",
            (room_name,)
        ).fetchone()
        return user_id[0] if user_id else None
    except Exception as e:
        logger.error(f"Database lookup failed: {e}")
        return None

def lookup_user_by_identity(participant_identity: str) -> str:
    try:
        # Example database lookup
        user_id = database.execute(
            "SELECT user_id FROM user_identities WHERE identity = ?",
            (participant_identity,)
        ).fetchone()
        return user_id[0] if user_id else None
    except Exception as e:
        logger.error(f"Database lookup failed: {e}")
        return None
```

## 🔒 Security Considerations

1. **Environment Variables**: Store sensitive user IDs in secure environment variables
2. **Room Names**: Avoid putting sensitive information in room names
3. **Identity Validation**: Validate user identities before lookup
4. **Database Security**: Use parameterized queries to prevent SQL injection

## 🧪 Testing

### Test Environment Variables

```bash
# Test with environment variables
export HR_USER_ID="test-user-123"
export HR_CHATLOG_ID="9999"
python agent.py
```

### Test Room-based Lookup

```bash
# Test with room name pattern
Room Name: "user-test123"
# Should resolve to user_id: "test123"
```

### Test Identity-based Lookup

```bash
# Test with identity pattern
Identity: "user-test123"
# Should resolve to user_id: "test123"
```

## 📝 Configuration Examples

### Development Environment

```bash
# .env.local
HR_USER_ID=dev-user-123
HR_CHATLOG_ID=1000
HR_AGENT_ID=6
```

### Production Environment

```bash
# Production environment variables
HR_USER_ID=prod-user-abc123
HR_CHATLOG_ID=5000
HR_AGENT_ID=6
```

### Multi-tenant Setup

```python
# Custom room mapping for multi-tenant
room_user_mapping = {
    "tenant1-room": "tenant1-user-123",
    "tenant2-room": "tenant2-user-456",
    "tenant3-room": "tenant3-user-789"
}
```

## 🚨 Troubleshooting

### Common Issues

1. **User ID Not Found**
   - Check environment variables are set correctly
   - Verify room name or identity patterns
   - Check logs for resolution process

2. **Default Values Used**
   - Environment variables not set
   - Room/identity patterns don't match
   - Lookup functions return None

3. **Database Connection Issues**
   - Check database connectivity
   - Verify query syntax
   - Check error logs

### Debug Logs

Enable debug logging to see the resolution process:

```python
logger.setLevel(logging.DEBUG)
```

## 📚 API Reference

### get_user_config(room_name, participant_identity)

**Parameters:**
- `room_name` (str, optional): LiveKit room name
- `participant_identity` (str, optional): Participant identity

**Returns:**
- `dict`: Configuration with user_id, chatlog_id, agent_id

**Example:**
```python
config = get_user_config(room_name="user-123", participant_identity="john.doe")
# Returns: {"user_id": "123", "chatlog_id": 7747, "agent_id": 6}
```

### lookup_user_by_room(room_name)

**Parameters:**
- `room_name` (str): LiveKit room name

**Returns:**
- `str`: User ID if found, None otherwise

### lookup_user_by_identity(participant_identity)

**Parameters:**
- `participant_identity` (str): Participant identity

**Returns:**
- `str`: User ID if found, None otherwise

---

**Dynamic user configuration is now fully implemented and ready for use!** 🎉
