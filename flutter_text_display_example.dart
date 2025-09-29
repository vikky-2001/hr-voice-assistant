// Flutter/Dart example for displaying text from HR Voice Assistant
// This shows how to integrate with LiveKit and display text messages

import 'package:flutter/material.dart';
import 'package:livekit_client/livekit_client.dart';

class HRVoiceAssistantScreen extends StatefulWidget {
  @override
  _HRVoiceAssistantScreenState createState() => _HRVoiceAssistantScreenState();
}

class _HRVoiceAssistantScreenState extends State<HRVoiceAssistantScreen> {
  Room? room;
  bool isConnected = false;
  List<ChatMessage> messages = [];
  String? dailyBriefing;
  bool dailyBriefingReceived = false;

  @override
  void initState() {
    super.initState();
    connectToRoom();
  }

  Future<void> connectToRoom() async {
    try {
      // LiveKit configuration
      const livekitUrl = 'wss://mobile-worker-o314phth.livekit.cloud';
      const roomName = 'test_hr_room';
      
      // Create room
      room = Room();
      
      // Set up event listeners
      room!.on(RoomEvent.connected, () {
        setState(() {
          isConnected = true;
        });
        addMessage('Connected to HR Voice Assistant', MessageType.system);
      });
      
      room!.on(RoomEvent.disconnected, () {
        setState(() {
          isConnected = false;
        });
        addMessage('Disconnected from room', MessageType.system);
      });
      
      room!.on(RoomEvent.participantConnected, (participant) {
        addMessage('${participant.identity} joined', MessageType.system);
      });
      
      room!.on(RoomEvent.participantDisconnected, (participant) {
        addMessage('${participant.identity} left', MessageType.system);
      });
      
      // Handle data messages (text from agent)
      room!.on(RoomEvent.dataReceived, (data, participant) {
        try {
          final messageData = json.decode(String.fromCharCodes(data));
          handleDataMessage(messageData, participant);
        } catch (e) {
          print('Error parsing data message: $e');
        }
      });
      
      // Handle transcript events
      room!.on(RoomEvent.trackSubscribed, (track, publication, participant) {
        if (track.kind == Track.Kind.audio) {
          track.on(TrackEvent.transcriptReceived, (transcript) {
            handleTranscript(transcript, participant);
          });
        }
      });
      
      // Generate token (in production, this should be done server-side)
      final token = await generateToken();
      
      // Connect to room
      await room!.connect(livekitUrl, token);
      
    } catch (e) {
      print('Connection error: $e');
      addMessage('Connection failed: $e', MessageType.error);
    }
  }

  void handleDataMessage(Map<String, dynamic> data, RemoteParticipant participant) {
    final messageType = data['type'] as String?;
    final content = data['content'] as String?;
    final timestamp = data['timestamp'] as String?;
    
    if (messageType == 'daily_briefing') {
      setState(() {
        dailyBriefing = content;
        dailyBriefingReceived = true;
      });
      addMessage('📋 Daily Briefing Received', MessageType.system);
    } else if (messageType == 'agent_response') {
      addMessage(content ?? '', MessageType.agent);
    } else if (messageType == 'message') {
      addMessage(content ?? '', 
          participant.identity.contains('agent') ? MessageType.agent : MessageType.user);
    }
  }

  void handleTranscript(Transcript transcript, RemoteParticipant participant) {
    if (participant.identity.contains('agent')) {
      addMessage(transcript.text, MessageType.agent);
      
      // Check if this is a daily briefing
      if (transcript.text.toLowerCase().contains('daily briefing') && !dailyBriefingReceived) {
        setState(() {
          dailyBriefing = transcript.text;
          dailyBriefingReceived = true;
        });
      }
    } else {
      addMessage(transcript.text, MessageType.user);
    }
  }

  void addMessage(String content, MessageType type) {
    setState(() {
      messages.add(ChatMessage(
        content: content,
        type: type,
        timestamp: DateTime.now(),
      ));
    });
  }

  Future<String> generateToken() async {
    // In production, this should be done server-side
    // For now, return a placeholder
    return 'your_generated_token_here';
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('HR Voice Assistant'),
        backgroundColor: Colors.blue,
        foregroundColor: Colors.white,
      ),
      body: Column(
        children: [
          // Connection Status
          Container(
            width: double.infinity,
            padding: EdgeInsets.all(16),
            color: isConnected ? Colors.green : Colors.red,
            child: Text(
              isConnected ? 'Connected' : 'Disconnected',
              style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold),
              textAlign: TextAlign.center,
            ),
          ),
          
          // Daily Briefing Section
          if (dailyBriefingReceived && dailyBriefing != null)
            Container(
              width: double.infinity,
              margin: EdgeInsets.all(16),
              padding: EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: Colors.green.shade50,
                border: Border.all(color: Colors.green),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    '📋 Daily Briefing',
                    style: TextStyle(
                      fontWeight: FontWeight.bold,
                      color: Colors.green.shade800,
                      fontSize: 16,
                    ),
                  ),
                  SizedBox(height: 8),
                  Text(
                    dailyBriefing!,
                    style: TextStyle(fontSize: 14),
                  ),
                ],
              ),
            ),
          
          // Messages List
          Expanded(
            child: ListView.builder(
              itemCount: messages.length,
              itemBuilder: (context, index) {
                final message = messages[index];
                return MessageBubble(message: message);
              },
            ),
          ),
          
          // Controls
          Container(
            padding: EdgeInsets.all(16),
            child: Row(
              children: [
                Expanded(
                  child: ElevatedButton(
                    onPressed: isConnected ? sendTestMessage : null,
                    child: Text('Send Test Message'),
                  ),
                ),
                SizedBox(width: 16),
                ElevatedButton(
                  onPressed: isConnected ? disconnect : null,
                  style: ElevatedButton.styleFrom(backgroundColor: Colors.red),
                  child: Text('Disconnect'),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  void sendTestMessage() {
    if (room != null && isConnected) {
      final testMessage = "Hello, can you help me with my leave balance?";
      addMessage(testMessage, MessageType.user);
      
      // Send as data message
      final messageData = {
        'type': 'message',
        'content': testMessage,
        'timestamp': DateTime.now().toIso8601String(),
      };
      
      room!.localParticipant.publishData(
        utf8.encode(json.encode(messageData)),
        topic: 'chat',
      );
    }
  }

  void disconnect() {
    room?.disconnect();
  }

  @override
  void dispose() {
    room?.disconnect();
    super.dispose();
  }
}

class ChatMessage {
  final String content;
  final MessageType type;
  final DateTime timestamp;

  ChatMessage({
    required this.content,
    required this.type,
    required this.timestamp,
  });
}

enum MessageType {
  user,
  agent,
  system,
  error,
}

class MessageBubble extends StatelessWidget {
  final ChatMessage message;

  const MessageBubble({Key? key, required this.message}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    Color backgroundColor;
    Color textColor;
    CrossAxisAlignment alignment;

    switch (message.type) {
      case MessageType.user:
        backgroundColor = Colors.blue.shade100;
        textColor = Colors.blue.shade900;
        alignment = CrossAxisAlignment.end;
        break;
      case MessageType.agent:
        backgroundColor = Colors.purple.shade100;
        textColor = Colors.purple.shade900;
        alignment = CrossAxisAlignment.start;
        break;
      case MessageType.system:
        backgroundColor = Colors.orange.shade100;
        textColor = Colors.orange.shade900;
        alignment = CrossAxisAlignment.center;
        break;
      case MessageType.error:
        backgroundColor = Colors.red.shade100;
        textColor = Colors.red.shade900;
        alignment = CrossAxisAlignment.center;
        break;
    }

    return Container(
      margin: EdgeInsets.symmetric(vertical: 4, horizontal: 16),
      child: Column(
        crossAxisAlignment: alignment,
        children: [
          Container(
            padding: EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: backgroundColor,
              borderRadius: BorderRadius.circular(12),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  message.content,
                  style: TextStyle(color: textColor),
                ),
                SizedBox(height: 4),
                Text(
                  '${message.timestamp.hour}:${message.timestamp.minute.toString().padLeft(2, '0')}',
                  style: TextStyle(
                    color: textColor.withOpacity(0.7),
                    fontSize: 12,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

// Usage in main.dart
void main() {
  runApp(MaterialApp(
    home: HRVoiceAssistantScreen(),
  ));
}
