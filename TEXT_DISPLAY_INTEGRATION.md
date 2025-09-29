# 📝 Text Display Integration for HR Voice Assistant

This document explains how to display text from the HR Voice Assistant in your frontend application.

## 🎯 **Available Text Display Methods**

### **1. Real-time Transcript Display**
LiveKit automatically provides transcript events that capture both user speech and agent responses.

### **2. Structured Data Messages**
The agent sends structured JSON data through LiveKit's data channels for better frontend integration.

### **3. Custom Events**
You can create custom events to send formatted text to the frontend.

## 🚀 **Implementation Options**

### **Option 1: Web Frontend (HTML/JavaScript)**

**File**: `frontend_example.html`

**Features**:
- ✅ Real-time transcript display
- ✅ Daily briefing highlight
- ✅ Conversation history
- ✅ Live transcript feed
- ✅ Structured data messages
- ✅ Visual message bubbles
- ✅ Auto-scroll functionality

**Key Components**:
```javascript
// Handle transcript events
room.on(LiveKit.RoomEvent.TrackSubscribed, (track, publication, participant) => {
    if (track.kind === LiveKit.Track.Kind.Audio) {
        track.on(LiveKit.TrackEvent.TranscriptReceived, (transcript) => {
            // Display transcript text
            addMessage(transcript.text, participant.identity.includes('agent') ? 'agent' : 'user');
        });
    }
});

// Handle data messages
room.on(LiveKit.RoomEvent.DataReceived, (payload, participant) => {
    const data = JSON.parse(new TextDecoder().decode(payload));
    if (data.type === 'daily_briefing') {
        showDailyBriefing(data.content);
    }
});
```

### **Option 2: Flutter/Dart Mobile App**

**File**: `flutter_text_display_example.dart`

**Features**:
- ✅ Mobile-optimized UI
- ✅ Message bubbles
- ✅ Daily briefing section
- ✅ Connection status
- ✅ Real-time updates
- ✅ Material Design

**Key Components**:
```dart
// Handle data messages
room.on(RoomEvent.dataReceived, (data, participant) {
    final messageData = json.decode(String.fromCharCodes(data));
    handleDataMessage(messageData, participant);
});

// Handle transcript events
room.on(RoomEvent.trackSubscribed, (track, publication, participant) {
    if (track.kind == Track.Kind.audio) {
        track.on(TrackEvent.transcriptReceived, (transcript) {
            handleTranscript(transcript, participant);
        });
    }
});
```

### **Option 3: React/Next.js Frontend**

**Key Dependencies**:
```bash
npm install livekit-client
```

**Example Component**:
```jsx
import { Room, RoomEvent, Track } from 'livekit-client';

const HRVoiceAssistant = () => {
    const [messages, setMessages] = useState([]);
    const [dailyBriefing, setDailyBriefing] = useState(null);

    useEffect(() => {
        const room = new Room();
        
        room.on(RoomEvent.dataReceived, (payload, participant) => {
            const data = JSON.parse(new TextDecoder().decode(payload));
            if (data.type === 'daily_briefing') {
                setDailyBriefing(data.content);
            }
        });
        
        room.on(RoomEvent.trackSubscribed, (track, publication, participant) => {
            if (track.kind === Track.Kind.Audio) {
                track.on(TrackEvent.transcriptReceived, (transcript) => {
                    setMessages(prev => [...prev, {
                        text: transcript.text,
                        type: participant.identity.includes('agent') ? 'agent' : 'user',
                        timestamp: new Date()
                    }]);
                });
            }
        });
    }, []);

    return (
        <div>
            {dailyBriefing && (
                <div className="daily-briefing">
                    <h3>📋 Daily Briefing</h3>
                    <p>{dailyBriefing}</p>
                </div>
            )}
            <div className="messages">
                {messages.map((msg, index) => (
                    <div key={index} className={`message ${msg.type}`}>
                        {msg.text}
                    </div>
                ))}
            </div>
        </div>
    );
};
```

## 📡 **Data Message Types**

The agent sends the following structured data messages:

### **1. Daily Briefing**
```json
{
    "type": "daily_briefing",
    "content": "Good morning! Here's your daily HR briefing...",
    "timestamp": "2025-09-29T17:30:00.000Z",
    "metadata": {
        "source": "hr_api",
        "query": "System trigger: daily briefing"
    }
}
```

### **2. Agent Response**
```json
{
    "type": "agent_response",
    "content": "I can help you with that. Let me check your leave balance...",
    "timestamp": "2025-09-29T17:30:15.000Z",
    "metadata": {
        "source": "agent_speech",
        "timestamp": 1696005015000
    }
}
```

### **3. User Message**
```json
{
    "type": "message",
    "content": "What's my leave balance?",
    "timestamp": "2025-09-29T17:30:10.000Z",
    "metadata": {}
}
```

## 🎨 **UI/UX Recommendations**

### **Daily Briefing Display**
- **Highlight**: Use a distinct color (green) to make it stand out
- **Icon**: Use 📋 emoji or icon
- **Position**: Show at the top when received
- **Animation**: Fade in effect for better UX

### **Message Bubbles**
- **User messages**: Blue, right-aligned
- **Agent messages**: Purple, left-aligned
- **System messages**: Orange, centered
- **Timestamps**: Small, muted text

### **Live Transcript**
- **Real-time**: Show as messages are spoken
- **Auto-scroll**: Scroll to bottom automatically
- **Typing indicator**: Show when agent is processing

## 🔧 **Technical Implementation**

### **Agent Side (Python)**
The agent automatically sends text data through:
1. **Data channels** for structured messages
2. **Transcript events** for speech-to-text
3. **Custom events** for special notifications

### **Frontend Side**
The frontend receives text through:
1. **LiveKit data events** for structured data
2. **Transcript events** for real-time speech
3. **Participant events** for connection status

## 🚀 **Getting Started**

### **1. Choose Your Frontend**
- **Web**: Use `frontend_example.html`
- **Mobile**: Use `flutter_text_display_example.dart`
- **React**: Use the React example above

### **2. Configure LiveKit**
```javascript
const LIVEKIT_URL = 'wss://mobile-worker-o314phth.livekit.cloud';
const ROOM_NAME = 'test_hr_room';
```

### **3. Handle Events**
Set up event listeners for:
- `dataReceived` - Structured messages
- `transcriptReceived` - Speech transcripts
- `participantConnected/Disconnected` - Connection status

### **4. Display Text**
Implement UI components to show:
- Daily briefing (highlighted)
- Conversation history
- Live transcript
- Connection status

## 📱 **Mobile Considerations**

### **Flutter Integration**
- Use `livekit_client` package
- Handle background/foreground states
- Implement proper error handling
- Use Material Design components

### **React Native Integration**
- Use `livekit-react-native` package
- Handle permissions (microphone, camera)
- Implement proper navigation
- Use native components

## 🔍 **Testing**

### **Test Daily Briefing**
1. Connect to the agent
2. Wait for automatic daily briefing
3. Verify it appears in the UI
4. Check structured data format

### **Test Regular Messages**
1. Send a test message
2. Verify agent response appears
3. Check transcript accuracy
4. Test error handling

## 🎯 **Best Practices**

1. **Always handle errors** gracefully
2. **Show connection status** clearly
3. **Implement auto-scroll** for messages
4. **Use proper timestamps** for messages
5. **Handle network disconnections**
6. **Implement retry logic** for failed connections
7. **Use proper loading states**
8. **Implement message persistence** if needed

## 📞 **Support**

For questions or issues:
1. Check the LiveKit documentation
2. Review the example implementations
3. Test with the deployed agent
4. Check agent logs for debugging

The HR Voice Assistant is now ready to provide both voice and text interactions! 🚀
