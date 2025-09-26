# LiveKit Cloud Deployment Guide

This guide explains how to deploy your HR Voice Assistant to LiveKit Cloud.

## 🚀 Prerequisites

1. **LiveKit Cloud Account** - Sign up at [cloud.livekit.io](https://cloud.livekit.io)
2. **Docker** - For building the container image
3. **GitHub Account** - For repository hosting

## 📦 Step 1: Prepare Your Repository

### 1.1 Create GitHub Repository
```bash
# Initialize git repository
git init
git add .
git commit -m "Initial commit: HR Voice Assistant"

# Create repository on GitHub and push
git remote add origin https://github.com/yourusername/hr-voice-assistant.git
git push -u origin main
```

### 1.2 Set Up Environment Variables
In your LiveKit Cloud dashboard, set these environment variables:

```bash
OPENAI_API_KEY=your_openai_api_key
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=your_livekit_api_key
LIVEKIT_API_SECRET=your_livekit_api_secret
```

## 🐳 Step 2: Deploy to LiveKit Cloud

### Option A: Using LiveKit Cloud Dashboard

1. **Go to LiveKit Cloud Dashboard**
   - Visit [cloud.livekit.io](https://cloud.livekit.io)
   - Sign in to your account

2. **Create New Agent**
   - Click "Agents" in the sidebar
   - Click "Create Agent"
   - Choose "Deploy from GitHub"

3. **Configure Agent**
   - **Repository**: `yourusername/hr-voice-assistant`
   - **Branch**: `main`
   - **Dockerfile Path**: `./Dockerfile`
   - **Port**: `8080`

4. **Set Environment Variables**
   - Add all required environment variables
   - Save configuration

5. **Deploy**
   - Click "Deploy"
   - Wait for deployment to complete

### Option B: Using LiveKit CLI

1. **Install LiveKit CLI**
   ```bash
   npm install -g @livekit/cli
   ```

2. **Login to LiveKit Cloud**
   ```bash
   livekit-cli login
   ```

3. **Deploy Agent**
   ```bash
   livekit-cli agent deploy \
     --repo https://github.com/yourusername/hr-voice-assistant \
     --branch main \
     --dockerfile ./Dockerfile \
     --env OPENAI_API_KEY=your_key \
     --env LIVEKIT_URL=wss://your-project.livekit.cloud \
     --env LIVEKIT_API_KEY=your_key \
     --env LIVEKIT_API_SECRET=your_secret
   ```

## 🔧 Step 3: Configure Agent

### 3.1 Agent Settings
In your LiveKit Cloud dashboard:

- **Name**: `hr-voice-assistant`
- **Image**: Auto-generated from your repository
- **Replicas**: `1` (can scale up as needed)
- **Resources**: 
  - Memory: `512Mi` (minimum)
  - CPU: `250m` (minimum)

### 3.2 Health Checks
The agent includes health check endpoints:
- **Health Check**: `GET /health`
- **Root**: `GET /`

### 3.3 Auto-scaling
Configure auto-scaling based on:
- CPU utilization
- Memory usage
- Number of active rooms

## 🧪 Step 4: Test Deployment

### 4.1 Check Agent Status
```bash
# Check if agent is running
curl https://your-agent-url.livekit.cloud/health

# Expected response:
{
  "status": "healthy",
  "service": "HR Voice Assistant",
  "timestamp": "2024-01-01T00:00:00",
  "version": "1.0.0"
}
```

### 4.2 Test Voice Interaction
1. **Open LiveKit Playground**
   - Go to your LiveKit project dashboard
   - Click "Playground"

2. **Join Room**
   - Room name: `hr-assistant-room`
   - Enable microphone

3. **Test HR Questions**
   - "What's our vacation policy?"
   - "How do I request time off?"
   - "What benefits are available?"

## 📊 Step 5: Monitor and Scale

### 5.1 Monitoring
LiveKit Cloud provides:
- **Real-time metrics** - CPU, memory, connections
- **Logs** - Agent logs and errors
- **Analytics** - Usage statistics

### 5.2 Scaling
- **Manual scaling** - Adjust replicas in dashboard
- **Auto-scaling** - Based on CPU/memory thresholds
- **Load balancing** - Automatic across replicas

## 🔄 Step 6: Continuous Deployment

### 6.1 GitHub Actions (Optional)
Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to LiveKit Cloud

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    
    - name: Deploy to LiveKit Cloud
      run: |
        npm install -g @livekit/cli
        livekit-cli login --api-key ${{ secrets.LIVEKIT_API_KEY }} --api-secret ${{ secrets.LIVEKIT_API_SECRET }}
        livekit-cli agent deploy --repo ${{ github.repository }} --branch main
```

### 6.2 Environment Variables in GitHub
Set these secrets in your GitHub repository:
- `LIVEKIT_API_KEY`
- `LIVEKIT_API_SECRET`
- `OPENAI_API_KEY`

## 🚨 Troubleshooting

### Common Issues

1. **Agent Not Starting**
   - Check logs in LiveKit Cloud dashboard
   - Verify environment variables are set
   - Ensure Dockerfile is correct

2. **Health Check Failing**
   - Verify port 8080 is exposed
   - Check if health endpoint is accessible
   - Review agent logs

3. **Voice Not Working**
   - Check OpenAI API key and quota
   - Verify LiveKit connection
   - Test with LiveKit Playground

### Debug Commands

```bash
# Check agent logs
livekit-cli agent logs hr-voice-assistant

# Check agent status
livekit-cli agent status hr-voice-assistant

# Restart agent
livekit-cli agent restart hr-voice-assistant
```

## 💰 Cost Optimization

### Resource Management
- **Start small** - Use minimum resources initially
- **Monitor usage** - Scale based on actual demand
- **Auto-scaling** - Enable to handle traffic spikes
- **Cleanup** - Remove unused agents

### Pricing
LiveKit Cloud pricing is based on:
- **Compute time** - CPU and memory usage
- **Data transfer** - Audio/video streaming
- **Storage** - Logs and metrics retention

## 🔒 Security

### Best Practices
1. **Environment Variables** - Never commit secrets
2. **API Keys** - Rotate regularly
3. **Access Control** - Limit dashboard access
4. **Monitoring** - Watch for unusual activity

### Network Security
- **HTTPS** - All connections are encrypted
- **WebRTC** - Secure peer-to-peer connections
- **Authentication** - Token-based access control

## 📞 Support

### LiveKit Resources
- **Documentation**: [docs.livekit.io](https://docs.livekit.io)
- **Community**: [Discord](https://discord.gg/livekit)
- **Support**: [support.livekit.io](https://support.livekit.io)

### Getting Help
1. Check LiveKit Cloud dashboard logs
2. Review agent health status
3. Test with LiveKit Playground
4. Contact LiveKit support if needed

Your HR Voice Assistant is now deployed and ready to handle voice interactions! 🎉
