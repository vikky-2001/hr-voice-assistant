# HR Voice Assistant - Setup Guide for New Team Members

## 🚀 Quick Start (5 Minutes)

### Prerequisites
- Windows/Mac/Linux machine
- Git installed
- Basic understanding of Python and APIs

### Step 1: Clone Repository
```bash
git clone https://github.com/vikky-2001/hr-voice-assistant.git
cd hr-voice-assistant
```

### Step 2: Install LiveKit CLI
```bash
# Windows (PowerShell)
winget install LiveKit.LiveKitCLI

# Mac
brew install livekit/tap/livekit

# Linux
curl -sSL https://get.livekit.io | bash
```

### Step 3: Authenticate with LiveKit
```bash
lk cloud auth
# Follow the prompts to authenticate
```

### Step 4: Deploy Agent
```bash
lk agent deploy
```

### Step 5: Test Agent
```bash
# Create a test room
lk room create --name "my-test-room"

# Dispatch agent to room
lk dispatch create --room my-test-room --agent-name CA_9ptBUymQxjAx

# Check if agent is running
lk agent status CA_9ptBUymQxjAx
```

**🎉 You're ready to go! The agent is now deployed and running.**

---

## 📋 Detailed Setup Instructions

### Environment Setup

#### 1. **System Requirements**
- **OS**: Windows 10+, macOS 10.15+, or Linux
- **RAM**: Minimum 4GB (8GB recommended)
- **Storage**: 2GB free space
- **Network**: Stable internet connection

#### 2. **Required Software**
```bash
# Git (if not installed)
# Windows: Download from https://git-scm.com/
# Mac: brew install git
# Linux: sudo apt install git

# Python 3.11+ (for local testing)
# Windows: Download from https://python.org/
# Mac: brew install python@3.11
# Linux: sudo apt install python3.11
```

#### 3. **LiveKit CLI Installation**
```bash
# Verify installation
lk --version

# Should show: lk version 1.x.x
```

### Project Configuration

#### 1. **Environment Variables**
The project uses these environment variables (configured in `secrets.env`):
```env
LIVEKIT_URL=wss://missionmind-gl3d4ero.livekit.cloud
LIVEKIT_API_KEY=your_api_key_here
LIVEKIT_API_SECRET=your_api_secret_here
OPENAI_API_KEY=your_openai_key_here
HR_API_BASE_URL=your_hr_api_url_here
HR_API_ENDPOINT=/api/chat
```

#### 2. **LiveKit Configuration**
The `livekit.toml` file contains:
```toml
[agent]
id = "CA_9ptBUymQxjAx"
subdomain = "missionmind-gl3d4ero"
min_replicas = 1
max_replicas = 1
idle_timeout = 0
keep_alive = true
```

### Development Workflow

#### 1. **Making Changes**
```bash
# 1. Edit agent.py or other files
# 2. Test locally (optional)
python agent.py dev

# 3. Commit changes
git add .
git commit -m "Description of your changes"
git push

# 4. Deploy to production
lk agent deploy
```

#### 2. **Testing Changes**
```bash
# Create test room
lk room create --name "test-$(date +%s)"

# Dispatch agent
lk dispatch create --room test-$(date +%s) --agent-name CA_9ptBUymQxjAx

# Monitor logs
lk agent logs CA_9ptBUymQxjAx --follow
```

#### 3. **Rollback if Needed**
```bash
# Check deployment history
lk agent list

# Rollback to previous version
lk agent rollback CA_9ptBUymQxjAx --version previous
```

---

## 🔧 Common Development Tasks

### **Adding New Functionality**

1. **Add New Function Tool**
```python
@function_tool
async def my_new_function(self, parameter: str):
    """Description of what this function does"""
    logger.info(f"New function called with: {parameter}")
    
    # Your logic here
    result = "Function result"
    
    return result
```

2. **Add New Intent**
```python
# In the intents dictionary
"new_intent": {
    "keywords": ["keyword1", "keyword2"],
    "patterns": [r"pattern1", r"pattern2"],
    "response": "Default response if needed",
    "requires_hr_api": True  # or False
}
```

3. **Modify Voice Pipeline**
```python
# In the AgentSession initialization
session = AgentSession(
    room=ctx.room,
    vad=livekit.plugins.silero.VAD.load(),
    stt=openai.STT(model="whisper-1"),
    llm=openai.LLM(model="gpt-4o-mini"),
    tts=openai.TTS(model="tts-1"),
)
```

### **Debugging Issues**

1. **Agent Not Responding**
```bash
# Check agent status
lk agent status CA_9ptBUymQxjAx

# Check logs for errors
lk agent logs CA_9ptBUymQxjAx | grep ERROR

# Check room status
lk room list
```

2. **Voice Issues**
```bash
# Check audio codecs
lk room list

# Test with different audio settings
# Modify agent.py voice pipeline settings
```

3. **API Issues**
```bash
# Check HR API connectivity
curl -X GET "your_hr_api_url/api/health"

# Check OpenAI API status
# Visit: https://status.openai.com/
```

### **Performance Optimization**

1. **Reduce Startup Time**
```python
# Pre-load models in Dockerfile
RUN python -c "import livekit.plugins.silero as silero; silero.VAD.load()" || true
```

2. **Optimize Response Time**
```python
# Reduce timeouts
async with httpx.AsyncClient(timeout=5.0) as client:
    response = await client.get(url, params=params)
```

3. **Memory Management**
```python
# Keep conversation memory limited
if len(self.conversation_memory) > 10:
    self.conversation_memory = self.conversation_memory[-10:]
```

---

## 📊 Monitoring & Maintenance

### **Daily Tasks**
- [ ] Check agent status: `lk agent status CA_9ptBUymQxjAx`
- [ ] Monitor logs for errors: `lk agent logs CA_9ptBUymQxjAx`
- [ ] Verify room activity: `lk room list`

### **Weekly Tasks**
- [ ] Review error logs and fix issues
- [ ] Update dependencies if needed
- [ ] Test with real user scenarios
- [ ] Backup configuration files

### **Monthly Tasks**
- [ ] Review and update documentation
- [ ] Analyze performance metrics
- [ ] Plan feature improvements
- [ ] Security review

---

## 🆘 Getting Help

### **Internal Resources**
- **Architecture Guide**: [ARCHITECTURE_WORKFLOW.md](./ARCHITECTURE_WORKFLOW.md)
- **User ID System**: [DYNAMIC_USER_ID_GUIDE.md](./DYNAMIC_USER_ID_GUIDE.md)
- **Greeting System**: [AUTOMATIC_GREETING_GUIDE.md](./AUTOMATIC_GREETING_GUIDE.md)
- **Messaging System**: [INTERMEDIATE_MESSAGING_GUIDE.md](./INTERMEDIATE_MESSAGING_GUIDE.md)

### **External Resources**
- **LiveKit Docs**: https://docs.livekit.io/
- **OpenAI API**: https://platform.openai.com/docs
- **GitHub Repo**: https://github.com/vikky-2001/hr-voice-assistant

### **Common Commands Reference**
```bash
# Agent Management
lk agent list                    # List all agents
lk agent status <agent-id>       # Check agent status
lk agent logs <agent-id>         # View agent logs
lk agent deploy                  # Deploy agent
lk agent rollback <agent-id>     # Rollback agent

# Room Management
lk room list                     # List all rooms
lk room create --name <name>     # Create room
lk room delete <room-id>         # Delete room

# Dispatch Management
lk dispatch list <room-name>     # List dispatches
lk dispatch create --room <room> --agent-name <agent>  # Create dispatch
lk dispatch delete <dispatch-id> # Delete dispatch

# Authentication
lk cloud auth                    # Authenticate with LiveKit Cloud
lk cloud logout                  # Logout from LiveKit Cloud
```

---

## ✅ Checklist for New Team Members

### **First Day**
- [ ] Clone repository
- [ ] Install LiveKit CLI
- [ ] Authenticate with LiveKit
- [ ] Deploy agent successfully
- [ ] Create test room and dispatch agent
- [ ] Read architecture documentation

### **First Week**
- [ ] Make a small code change and deploy
- [ ] Test agent functionality
- [ ] Understand the voice pipeline
- [ ] Learn about intent classification
- [ ] Practice debugging with logs

### **First Month**
- [ ] Add new functionality
- [ ] Optimize performance
- [ ] Handle production issues
- [ ] Contribute to documentation
- [ ] Mentor other team members

---

**Welcome to the team! 🎉**

*This guide will be updated as the system evolves. Please contribute improvements and corrections.*
