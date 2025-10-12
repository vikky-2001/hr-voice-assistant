# HR Voice Assistant - Troubleshooting Guide

## 🚨 Emergency Response

### **Agent Completely Down**
```bash
# 1. Check agent status
lk agent status CA_9ptBUymQxjAx

# 2. If not running, redeploy immediately
lk agent deploy

# 3. Create new room and dispatch
lk room create --name "emergency-room"
lk dispatch create --room emergency-room --agent-name CA_9ptBUymQxjAx

# 4. Monitor logs
lk agent logs CA_9ptBUymQxjAx --follow
```

### **No Voice Response**
```bash
# 1. Check room participants
lk room list

# 2. Verify dispatch exists
lk dispatch list <room-name>

# 3. Check agent logs for errors
lk agent logs CA_9ptBUymQxjAx | grep -i "error\|exception\|failed"

# 4. Test with new room
lk room create --name "voice-test"
lk dispatch create --room voice-test --agent-name CA_9ptBUymQxjAx
```

---

## 🔍 Common Issues & Solutions

### **1. Agent Not Connecting to Room**

#### **Symptoms:**
- Room shows 1 participant (user only)
- No agent in room
- "No agent available" error

#### **Diagnosis:**
```bash
# Check agent status
lk agent status CA_9ptBUymQxjAx

# Check room status
lk room list

# Check dispatch status
lk dispatch list <room-name>
```

#### **Solutions:**
```bash
# Solution 1: Create new dispatch
lk dispatch create --room <room-name> --agent-name CA_9ptBUymQxjAx

# Solution 2: Redeploy agent
lk agent deploy

# Solution 3: Create new room
lk room create --name "new-room"
lk dispatch create --room new-room --agent-name CA_9ptBUymQxjAx
```

#### **Prevention:**
- Always verify dispatch after room creation
- Monitor agent status regularly
- Use descriptive room names

---

### **2. Slow Response Times**

#### **Symptoms:**
- Greeting takes >10 seconds
- Daily briefing takes >15 seconds
- User queries take >20 seconds

#### **Diagnosis:**
```bash
# Check agent logs for timing
lk agent logs CA_9ptBUymQxjAx | grep -i "timeout\|slow\|delay"

# Check HR API response time
curl -w "@curl-format.txt" -o /dev/null -s "your_hr_api_url/api/health"
```

#### **Solutions:**
```python
# Reduce timeouts in agent.py
async with httpx.AsyncClient(timeout=5.0) as client:  # Was 10.0
    response = await client.get(url, params=params)

# Add timeout to daily briefing
try:
    briefing_content = await asyncio.wait_for(self.get_daily_briefing(), timeout=8.0)
except asyncio.TimeoutError:
    briefing_content = "Fallback message"
```

#### **Prevention:**
- Monitor API response times
- Set appropriate timeouts
- Use fallback responses

---

### **3. Voice Quality Issues**

#### **Symptoms:**
- Distorted audio
- No audio output
- Audio cutting out
- Echo or feedback

#### **Diagnosis:**
```bash
# Check room audio codecs
lk room list

# Check agent logs for audio errors
lk agent logs CA_9ptBUymQxjAx | grep -i "audio\|codec\|voice"
```

#### **Solutions:**
```python
# Optimize voice pipeline in agent.py
session = AgentSession(
    room=ctx.room,
    vad=livekit.plugins.silero.VAD.load(),
    stt=openai.STT(model="whisper-1"),
    llm=openai.LLM(model="gpt-4o-mini"),
    tts=openai.TTS(model="tts-1", voice="alloy"),  # Specify voice
)
```

#### **Prevention:**
- Test with different audio inputs
- Monitor audio codec compatibility
- Use consistent voice settings

---

### **4. Daily Briefing Not Working**

#### **Symptoms:**
- No automatic briefing after greeting
- Manual briefing requests fail
- Briefing content is empty or generic

#### **Diagnosis:**
```bash
# Check for briefing-related logs
lk agent logs CA_9ptBUymQxjAx | grep -i "briefing\|daily"

# Check HR API connectivity
curl -X GET "your_hr_api_url/api/chat?query=System trigger: daily briefing"
```

#### **Solutions:**
```python
# Verify get_daily_briefing_with_speech is called
# In entrypoint function:
asyncio.create_task(assistant.get_daily_briefing_with_speech())

# Check HR API parameters
params = {
    "query": "System trigger: daily briefing",
    "user_id": user_config["user_id"],
    "chatlog_id": user_config["chatlog_id"],
    "agent_id": user_config["agent_id"],
    "mobile_request": True
}
```

#### **Prevention:**
- Test HR API regularly
- Monitor briefing logs
- Verify user configuration

---

### **5. Authentication Issues**

#### **Symptoms:**
- "Unauthorized" errors
- Agent deployment fails
- Cannot access LiveKit services

#### **Diagnosis:**
```bash
# Check authentication status
lk cloud auth --check

# Verify API keys
echo $LIVEKIT_API_KEY
echo $OPENAI_API_KEY
```

#### **Solutions:**
```bash
# Re-authenticate
lk cloud logout
lk cloud auth

# Check environment variables
cat secrets.env

# Verify API keys are valid
curl -H "Authorization: Bearer $OPENAI_API_KEY" https://api.openai.com/v1/models
```

#### **Prevention:**
- Regularly rotate API keys
- Monitor API usage limits
- Use environment variable validation

---

### **6. Memory/Performance Issues**

#### **Symptoms:**
- Agent crashes or restarts
- Slow response times
- High memory usage

#### **Diagnosis:**
```bash
# Check agent resource usage
lk agent status CA_9ptBUymQxjAx

# Monitor logs for memory errors
lk agent logs CA_9ptBUymQxjAx | grep -i "memory\|oom\|crash"
```

#### **Solutions:**
```python
# Limit conversation memory
if len(self.conversation_memory) > 10:
    self.conversation_memory = self.conversation_memory[-10:]

# Optimize data structures
# Use efficient data types
# Clear unused variables
```

#### **Prevention:**
- Monitor memory usage
- Implement memory limits
- Regular performance testing

---

## 🔧 Debugging Commands

### **Log Analysis**
```bash
# View all logs
lk agent logs CA_9ptBUymQxjAx

# Filter for errors only
lk agent logs CA_9ptBUymQxjAx | grep -i "error"

# Filter for specific function
lk agent logs CA_9ptBUymQxjAx | grep "get_daily_briefing"

# Follow logs in real-time
lk agent logs CA_9ptBUymQxjAx --follow

# Get last 100 lines
lk agent logs CA_9ptBUymQxjAx | tail -100
```

### **System Status Checks**
```bash
# Check all agents
lk agent list

# Check specific agent
lk agent status CA_9ptBUymQxjAx

# Check all rooms
lk room list

# Check dispatches for specific room
lk dispatch list <room-name>

# Check authentication
lk cloud auth --check
```

### **Network Diagnostics**
```bash
# Test HR API connectivity
curl -v "your_hr_api_url/api/health"

# Test OpenAI API
curl -H "Authorization: Bearer $OPENAI_API_KEY" https://api.openai.com/v1/models

# Test LiveKit connectivity
curl -v "wss://missionmind-gl3d4ero.livekit.cloud"
```

---

## 📊 Performance Monitoring

### **Key Metrics to Track**
- **Response Time**: < 5 seconds for greetings, < 10 seconds for queries
- **Uptime**: > 99% availability
- **Error Rate**: < 1% of requests
- **Memory Usage**: < 2GB per agent instance

### **Monitoring Commands**
```bash
# Check agent performance
lk agent status CA_9ptBUymQxjAx

# Monitor resource usage
lk agent logs CA_9ptBUymQxjAx | grep -i "cpu\|memory\|performance"

# Track response times
lk agent logs CA_9ptBUymQxjAx | grep -i "time\|duration\|latency"
```

### **Alerting Thresholds**
- **Response Time**: > 15 seconds
- **Error Rate**: > 5%
- **Memory Usage**: > 3GB
- **Downtime**: > 5 minutes

---

## 🚀 Recovery Procedures

### **Complete System Recovery**
```bash
# 1. Stop all services
lk agent delete CA_9ptBUymQxjAx

# 2. Clean up rooms
lk room list | grep -v "active" | xargs -I {} lk room delete {}

# 3. Redeploy agent
lk agent deploy

# 4. Create new room
lk room create --name "recovery-room"

# 5. Dispatch agent
lk dispatch create --room recovery-room --agent-name CA_9ptBUymQxjAx

# 6. Verify functionality
lk agent status CA_9ptBUymQxjAx
```

### **Partial Recovery (Agent Only)**
```bash
# 1. Redeploy agent
lk agent deploy

# 2. Wait for deployment
sleep 30

# 3. Create new dispatch
lk dispatch create --room <room-name> --agent-name CA_9ptBUymQxjAx

# 4. Test functionality
lk agent logs CA_9ptBUymQxjAx --follow
```

### **Data Recovery**
```bash
# 1. Check git history
git log --oneline -10

# 2. Rollback to working version
git checkout <commit-hash>

# 3. Redeploy
lk agent deploy

# 4. Test
lk agent status CA_9ptBUymQxjAx
```

---

## 📞 Escalation Procedures

### **Level 1: Basic Issues**
- Agent not responding
- Slow performance
- Minor voice issues

**Action**: Follow troubleshooting guide, redeploy if needed

### **Level 2: Service Issues**
- Complete agent failure
- Authentication problems
- API connectivity issues

**Action**: Contact system administrator, check external services

### **Level 3: Critical Issues**
- Data loss
- Security breaches
- Extended downtime

**Action**: Contact development team lead, implement emergency procedures

---

## 📚 Additional Resources

- **Architecture Guide**: [ARCHITECTURE_WORKFLOW.md](./ARCHITECTURE_WORKFLOW.md)
- **Setup Guide**: [SETUP_GUIDE.md](./SETUP_GUIDE.md)
- **LiveKit Documentation**: https://docs.livekit.io/
- **OpenAI Status**: https://status.openai.com/
- **GitHub Issues**: https://github.com/vikky-2001/hr-voice-assistant/issues

---

**Remember**: When in doubt, redeploy the agent. It's the quickest way to resolve most issues.

**Last Updated**: January 12, 2025  
**Version**: 1.0
