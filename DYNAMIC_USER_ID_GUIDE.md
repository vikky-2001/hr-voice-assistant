# 👤 Dynamic User ID System

This guide explains how the frontend can pass dynamic user IDs and configuration to the HR Voice Assistant agent.

## 🎯 Overview

The system supports multiple approaches for passing user information from the frontend to the agent:

1. **📡 Data Channel Messages** (Primary method)
2. **🎫 Token Metadata** (Alternative method)
3. **🏠 Room-based Identification** (Fallback method)
4. **👤 Identity-based Identification** (Fallback method)

## 🚀 Primary Method: Data Channel Messages

### Frontend Implementation

#### 1. Set User Configuration

```dart
// In your Flutter app
final liveKitService = LiveKitService();

// Set user configuration
liveKitService.setUserConfiguration(
  userId: "user-123-abc",
  chatlogId: 12345,
  agentId: 7,
  userEmail: "john.doe@company.com",
  userName: "John Doe",
);
```

#### 2. Update Configuration Dynamically

```dart
// Update user configuration (automatically sends to agent)
await liveKitService.updateUserConfiguration(
  userId: "new-user-456-def",
  chatlogId: 67890,
  agentId: 8,
  userEmail: "jane.smith@company.com",
  userName: "Jane Smith",
);
```

#### 3. Connect with User Context

```dart
// Set user configuration before connecting
liveKitService.setUserConfiguration(
  userId: "user-123-abc",
  chatlogId: 12345,
  agentId: 7,
  userEmail: "john.doe@company.com",
  userName: "John Doe",
);

// Connect (automatically sends user config to agent)
await liveKitService.connect();
```

### Agent Processing

The agent automatically:
1. **Receives** user configuration via data channel
2. **Updates** global user configuration
3. **Sends** confirmation back to frontend
4. **Uses** the configuration for all HR API calls

## 📊 Configuration Priority

The system uses the following priority order:

| Priority | Source | Description |
|----------|--------|-------------|
| **1** | 📡 Data Channel | Frontend sends user config via data channel |
| **2** | 🌍 Environment Variables | `HR_USER_ID`, `HR_CHATLOG_ID`, `HR_AGENT_ID` |
| **3** | 🏠 Room Name | Extract user ID from room name pattern |
| **4** | 👤 Identity | Extract user ID from participant identity |
| **5** | 🔧 Default Values | Fallback to hardcoded defaults |

## 🔧 Implementation Details

### Frontend Service Methods

```dart
class LiveKitService {
  // Set user configuration
  void setUserConfiguration({
    String? userId,
    int? chatlogId,
    int? agentId,
    String? userEmail,
    String? userName,
  });

  // Update and send to agent
  Future<void> updateUserConfiguration({
    String? userId,
    int? chatlogId,
    int? agentId,
    String? userEmail,
    String? userName,
  });

  // Send configuration to agent
  Future<void> sendUserConfigurationToAgent();

  // Getters for current configuration
  String? get currentUserId;
  int? get currentChatlogId;
  int? get currentAgentId;
  String? get currentUserEmail;
  String? get currentUserName;
}
```

### Agent Configuration Handling

```python
# Global user configuration storage
_current_user_config = {
    "user_id": DEFAULT_USER_ID,
    "chatlog_id": DEFAULT_CHATLOG_ID,
    "agent_id": DEFAULT_AGENT_ID,
    "user_email": "",
    "user_name": "Mobile User"
}

def get_user_config(room_name: str = None, participant_identity: str = None):
    """Get user configuration with priority handling"""
    # 1. Check frontend-provided configuration
    if _current_user_config["user_id"] != DEFAULT_USER_ID:
        return _current_user_config.copy()
    
    # 2. Fall back to other methods...
    # Environment variables, room-based, identity-based, defaults

def update_user_config_from_frontend(config_data: dict):
    """Update configuration from frontend data channel"""
    _current_user_config.update({
        "user_id": config_data.get("user_id", DEFAULT_USER_ID),
        "chatlog_id": int(config_data.get("chatlog_id", DEFAULT_CHATLOG_ID)),
        "agent_id": int(config_data.get("agent_id", DEFAULT_AGENT_ID)),
        "user_email": config_data.get("user_email", ""),
        "user_name": config_data.get("user_name", "Mobile User")
    })
```

## 📱 Usage Examples

### Example 1: Basic User Setup

```dart
// In your Flutter app
class HRAssistantScreen extends StatefulWidget {
  @override
  _HRAssistantScreenState createState() => _HRAssistantScreenState();
}

class _HRAssistantScreenState extends State<HRAssistantScreen> {
  final LiveKitService _liveKitService = LiveKitService();

  @override
  void initState() {
    super.initState();
    _setupUser();
  }

  void _setupUser() {
    // Get user info from your app's authentication system
    final user = AuthService.currentUser;
    
    _liveKitService.setUserConfiguration(
      userId: user.id,
      chatlogId: user.chatlogId,
      agentId: user.agentId,
      userEmail: user.email,
      userName: user.name,
    );
  }

  Future<void> _connectToAssistant() async {
    await _liveKitService.connect();
  }
}
```

### Example 2: Dynamic User Switching

```dart
class UserSwitcher extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        ElevatedButton(
          onPressed: () => _switchToUser("user-123", "John Doe"),
          child: Text("Switch to John Doe"),
        ),
        ElevatedButton(
          onPressed: () => _switchToUser("user-456", "Jane Smith"),
          child: Text("Switch to Jane Smith"),
        ),
      ],
    );
  }

  Future<void> _switchToUser(String userId, String userName) async {
    await _liveKitService.updateUserConfiguration(
      userId: userId,
      userName: userName,
      // Other parameters will use current values or defaults
    );
  }
}
```

### Example 3: Multi-Tenant Support

```dart
class CompanySelector extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return DropdownButton<String>(
      items: [
        DropdownMenuItem(value: "company-a", child: Text("Company A")),
        DropdownMenuItem(value: "company-b", child: Text("Company B")),
      ],
      onChanged: (companyId) => _switchCompany(companyId!),
    );
  }

  Future<void> _switchCompany(String companyId) async {
    // Different companies might have different agent IDs
    final agentId = companyId == "company-a" ? 6 : 7;
    
    await _liveKitService.updateUserConfiguration(
      agentId: agentId,
      // User ID and other params remain the same
    );
  }
}
```

## 🔄 Message Flow

### 1. Frontend → Agent (User Configuration)

```json
{
  "type": "user_configuration",
  "user_id": "user-123-abc",
  "chatlog_id": 12345,
  "agent_id": 7,
  "user_email": "john.doe@company.com",
  "user_name": "John Doe",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### 2. Agent → Frontend (Confirmation)

```json
{
  "type": "user_config_confirmation",
  "content": "User configuration received: John Doe",
  "timestamp": "2024-01-15T10:30:01Z",
  "metadata": {
    "source": "agent",
    "config_received": true
  }
}
```

## 🎫 Alternative Method: Token Metadata

### Enhanced Token Generation

```dart
// In LiveKitTokenGenerator
static String generateTokenWithMetadata({
  required String roomName,
  required String identity,
  required Map<String, String> metadata,
}) {
  final token = AccessToken(apiKey, apiSecret)
    .with_identity(identity)
    .with_grants(VideoGrants(
      canPublish: true,
      canSubscribe: true,
      roomJoin: true,
      room: roomName,
    ))
    .with_metadata(jsonEncode(metadata))  // Include user metadata
    .with_ttl(Duration(hours: 1))
    .to_jwt();
    
  return token;
}
```

### Agent Token Parsing

```python
def extract_user_config_from_token(session):
    """Extract user configuration from token metadata"""
    try:
        # Get participant metadata from token
        participant = session.room.local_participant
        if participant and participant.metadata:
            metadata = json.loads(participant.metadata)
            return {
                "user_id": metadata.get("user_id"),
                "chatlog_id": int(metadata.get("chatlog_id", 0)),
                "agent_id": int(metadata.get("agent_id", 0)),
                "user_email": metadata.get("user_email", ""),
                "user_name": metadata.get("user_name", ""),
            }
    except Exception as e:
        logger.error(f"Error extracting user config from token: {e}")
    
    return None
```

## 🏠 Room-Based Identification

### Room Naming Convention

```dart
// Use room names that include user information
final roomName = "user-${userId}-session-${sessionId}";
// Example: "user-123-abc-session-456"

final token = LiveKitTokenGenerator.generateToken(
  roomName: roomName,
  identity: 'Mobile-hr-worker',
);
```

### Agent Room Parsing

```python
def lookup_user_by_room(room_name: str) -> str:
    """Extract user ID from room name"""
    # Pattern: "user-{user_id}-session-{session_id}"
    import re
    match = re.match(r"user-([a-zA-Z0-9-]+)-session-(\d+)", room_name)
    if match:
        user_id = match.group(1)
        logger.info(f"Extracted user ID from room '{room_name}': {user_id}")
        return user_id
    
    # Pattern: "user-{user_id}"
    match = re.match(r"user-([a-zA-Z0-9-]+)", room_name)
    if match:
        user_id = match.group(1)
        logger.info(f"Extracted user ID from room '{room_name}': {user_id}")
        return user_id
    
    return None
```

## 👤 Identity-Based Identification

### Identity Naming Convention

```dart
// Use identity that includes user information
final identity = "user-${userId}-${userEmail}";
// Example: "user-123-abc-john.doe@company.com"

final token = LiveKitTokenGenerator.generateToken(
  roomName: 'Tester-room1',
  identity: identity,
);
```

### Agent Identity Parsing

```python
def lookup_user_by_identity(participant_identity: str) -> str:
    """Extract user ID from participant identity"""
    # Pattern: "user-{user_id}-{email}"
    import re
    match = re.match(r"user-([a-zA-Z0-9-]+)-(.+)", participant_identity)
    if match:
        user_id = match.group(1)
        email = match.group(2)
        logger.info(f"Extracted user ID from identity '{participant_identity}': {user_id}")
        return user_id
    
    # Pattern: "user-{user_id}"
    match = re.match(r"user-([a-zA-Z0-9-]+)", participant_identity)
    if match:
        user_id = match.group(1)
        logger.info(f"Extracted user ID from identity '{participant_identity}': {user_id}")
        return user_id
    
    return None
```

## 🔍 Debugging & Monitoring

### Frontend Logging

```dart
// Enable detailed logging
Logger.level = Level.debug;

// Check current configuration
print('Current User ID: ${liveKitService.currentUserId}');
print('Current Chatlog ID: ${liveKitService.currentChatlogId}');
print('Current Agent ID: ${liveKitService.currentAgentId}');
```

### Agent Logging

```python
# Check configuration resolution
logger.info(f"User config resolved: {get_user_config()}")

# Monitor data channel messages
logger.info(f"Data received from frontend: {ev.data[:100]}...")
logger.info(f"User configuration updated: {_current_user_config}")
```

## 🚀 Best Practices

### 1. Configuration Management

- **Set Early**: Configure user information before connecting
- **Update Dynamically**: Allow real-time user switching
- **Validate Data**: Ensure user IDs are valid before sending
- **Handle Errors**: Gracefully handle configuration failures

### 2. Security Considerations

- **Validate User IDs**: Ensure user IDs are properly formatted
- **Sanitize Input**: Clean user data before sending
- **Use HTTPS**: Always use secure connections
- **Token Expiration**: Set appropriate token expiration times

### 3. Performance Optimization

- **Cache Configuration**: Store user config locally
- **Batch Updates**: Group configuration changes
- **Minimize Messages**: Only send when configuration changes
- **Error Recovery**: Handle network failures gracefully

## 📊 Configuration Examples

### Example 1: Single User App

```dart
// Simple single-user setup
liveKitService.setUserConfiguration(
  userId: "user-123",
  chatlogId: 7747,
  agentId: 6,
  userEmail: "user@company.com",
  userName: "John Doe",
);
```

### Example 2: Multi-User App

```dart
// User selection from list
void _selectUser(User user) {
  liveKitService.setUserConfiguration(
    userId: user.id,
    chatlogId: user.chatlogId,
    agentId: user.agentId,
    userEmail: user.email,
    userName: user.name,
  );
}
```

### Example 3: Company-Specific Configuration

```dart
// Different companies, different agents
void _selectCompany(Company company) {
  liveKitService.setUserConfiguration(
    userId: currentUser.id,
    chatlogId: currentUser.chatlogId,
    agentId: company.agentId,  // Company-specific agent
    userEmail: currentUser.email,
    userName: currentUser.name,
  );
}
```

## 🔮 Advanced Features

### 1. Session Management

```dart
// Create new session for each user interaction
void _startNewSession() {
  final sessionId = DateTime.now().millisecondsSinceEpoch;
  liveKitService.setUserConfiguration(
    chatlogId: sessionId,  // Use timestamp as session ID
    // Other parameters remain the same
  );
}
```

### 2. User Preferences

```dart
// Include user preferences in configuration
void _setUserPreferences(UserPreferences prefs) {
  liveKitService.setUserConfiguration(
    userId: currentUser.id,
    chatlogId: currentUser.chatlogId,
    agentId: prefs.agentId,
    userEmail: currentUser.email,
    userName: currentUser.name,
    // Additional preferences can be sent via data channel
  );
}
```

### 3. Real-time Updates

```dart
// Update configuration during conversation
void _updateUserContext(String newContext) {
  // Send additional context via data channel
  liveKitService.sendDataToAgent({
    'type': 'user_context_update',
    'context': newContext,
    'timestamp': DateTime.now().toIso8601String(),
  });
}
```

---

**The dynamic user ID system is now fully implemented and ready for production!** 🎉

- 📡 **Data Channel**: Primary method for real-time user configuration
- 🎫 **Token Metadata**: Alternative method for initial configuration
- 🏠 **Room-based**: Fallback method using room naming
- 👤 **Identity-based**: Fallback method using participant identity
- 🔄 **Real-time Updates**: Dynamic configuration changes during conversation
- 📊 **Priority System**: Intelligent fallback hierarchy
- 🛡️ **Error Handling**: Graceful handling of configuration failures
