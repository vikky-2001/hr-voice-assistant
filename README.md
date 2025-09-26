# HR Voice Assistant

A LiveKit-based voice AI assistant that integrates with your HR system to answer employee questions about policies, benefits, leave requests, and other HR matters.

## 🚀 Quick Start

### 1. Start the Agent
```bash
python start_agent.py
```

Or manually:
```bash
venv\Scripts\python.exe agent-starter-python\src\agent.py dev
```

### 2. Connect to the Agent
The agent will be available on LiveKit at:
- **LiveKit URL**: `wss://mobile-worker-o314phth.livekit.cloud`
- **Default Room**: `hr-assistant-room`

You can connect using any LiveKit client or the LiveKit Playground.

## 🎯 Features

- **🎤 Voice Input**: Speech-to-text using OpenAI Whisper
- **🧠 AI Processing**: GPT-4o-mini for intelligent responses
- **🔊 Voice Output**: Text-to-speech using OpenAI TTS
- **📞 HR Integration**: Direct API calls to your HR system
- **🎧 Real-time**: Live voice conversation with the agent

## 🔧 Configuration

### HR API Settings
The agent is configured to call your HR API:
- **Base URL**: `https://dev-hrworkerapi.missionmind.ai/api/kafka`
- **Endpoint**: `/getBotResponse`
- **User ID**: `79f2b410-bbbe-43b9-a77f-38a6213ce13d` (hardcoded)
- **Chat Log ID**: `7747` (hardcoded)
- **Agent ID**: `6`

### LiveKit Settings
- **URL**: `wss://mobile-worker-o314phth.livekit.cloud`
- **API Key**: `APItNVuYWvxp62Q`
- **API Secret**: `SHk08v5r7MtUWxZLnxfh07dohp1F4kfTeS2BOEI0RfYD`

## 🎤 How to Use

1. **Start the agent** using the startup script
2. **Connect to the LiveKit room** using any LiveKit client
3. **Start speaking** your HR questions
4. **Listen to responses** from the AI assistant

### Example Questions
- "What's our vacation policy?"
- "How do I request time off?"
- "What benefits are available?"
- "What's the dress code policy?"
- "How do I update my direct deposit?"

## 📁 Project Structure

```
├── agent-starter-python/src/
│   └── agent.py              # Main HR voice agent
├── start_agent.py            # Simple startup script
├── README.md                 # This file
└── venv/                     # Virtual environment
```

## 🔒 Environment Variables

Make sure you have these environment variables set:
- `OPENAI_API_KEY` - Your OpenAI API key for STT, LLM, and TTS
- `LIVEKIT_URL` - LiveKit server URL
- `LIVEKIT_API_KEY` - LiveKit API key
- `LIVEKIT_API_SECRET` - LiveKit API secret

## 🛠️ Development

### Running in Different Modes
```bash
# Development mode (recommended)
venv\Scripts\python.exe agent-starter-python\src\agent.py dev

# Console mode (for testing)
venv\Scripts\python.exe agent-starter-python\src\agent.py console

# Production mode
venv\Scripts\python.exe agent-starter-python\src\agent.py start
```

### Logs
The agent provides detailed logging for:
- HR API calls and responses
- Voice processing events
- Connection status
- Error handling

## 📞 Support

If you encounter any issues:
1. Check the console output for error messages
2. Verify your environment variables are set
3. Ensure your HR API is accessible
4. Check your OpenAI API key and quota

## 🔄 Integration

This agent can be integrated with:
- **LiveKit Playground** - For testing and development
- **Custom LiveKit clients** - For production applications
- **Web applications** - Using LiveKit Web SDK
- **Mobile applications** - Using LiveKit mobile SDKs

The agent handles all the voice processing and HR API integration automatically!
