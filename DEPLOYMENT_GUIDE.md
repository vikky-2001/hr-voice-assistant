# 🚀 HR Voice Assistant - LiveKit Cloud Deployment Guide
lk agent deploy
lk agent logs
lk agent list

This document provides a step-by-step guide on how we successfully deployed the HR Voice Assistant to LiveKit Cloud using the CLI.

## 📋 Prerequisites

Before deploying, ensure you have the following:

### 1. Required Software
- **LiveKit CLI** (`lk`) - Version 2.6.0 or higher
- **Docker** - For containerization
- **Python 3.11+** - For the agent code
- **Git** - For version control

### 2. Accounts & Credentials
- **LiveKit Cloud Account** - Sign up at [cloud.livekit.io](https://cloud.livekit.io)
- **OpenAI API Key** - For STT, LLM, and TTS services
- **HR API Access** - Your internal HR system API

### 3. Project Structure
```
mobile_hr_worker/
├── agent.py              # Main agent code
├── requirements.txt      # Python dependencies
├── Dockerfile           # Container configuration
├── livekit.toml         # LiveKit configuration
├── secrets.env          # Environment variables
└── LIVEKIT_DEPLOYMENT.md # Original deployment docs
```

## 🔧 Step-by-Step Deployment Process

### Step 1: Verify LiveKit CLI Installation

First, check if the LiveKit CLI is installed:

```bash
lk --version
```

**Expected Output:**
```
lk version 2.6.0
```

If not installed, install it using:
```bash
npm install -g @livekit/cli
```

### Step 2: Authentication with LiveKit Cloud

Authenticate with your LiveKit Cloud account:

```bash
lk cloud auth
```

**Process:**
1. The CLI will open a browser window
2. Visit the provided URL: `https://cloud.livekit.io/cli/confirm-auth?t=<token>`
3. Confirm access in your browser
4. Choose a project alias (we used "mobile-worker")

**Expected Output:**
```
WARNING: config file C:\Users\Vignesh/.livekit/cli-config.yaml should have permissions 600
Saved CLI config to C:\Users\Vignesh/.livekit/cli-config.yaml
Device: vignesh dell
Requesting verification token...
Please confirm access by visiting:
   https://cloud.livekit.io/cli/confirm-auth?t=<token>
```

### Step 3: Verify Project Configuration

Check your existing agents and project status:

```bash
lk agent list
```

**Expected Output:**
```
Using project [mobile-worker]
┌─────────────────┬─────────┬─────────────────┬──────────────────────┐
│ ID              │ Regions │ Version         │ Deployed At          │
├─────────────────┼─────────┼─────────────────┼──────────────────────┤
│ CA_GDnD7evqFSXF │ us-east │ v20251003180143 │ 2025-10-03T18:02:51Z │
└─────────────────┴─────────┴─────────────────┴──────────────────────┘
```

### Step 4: Update Configuration Files

#### 4.1 Update livekit.toml
Ensure the agent ID matches your deployed agent:

```toml
[project]
  subdomain = "mobile-worker-o314phth"

[agent]
  id = "CA_GDnD7evqFSXF"
```

#### 4.2 Verify Environment Variables
Check that `secrets.env` contains all required variables:

```env
LIVEKIT_URL=wss://mobile-worker-o314phth.livekit.cloud
LIVEKIT_API_KEY=APIjPFnhPrsSoqV
LIVEKIT_API_SECRET=Y0KLkZIvg8P35Pj6O788NjAeP1TZuCydxpbffxdYURoB
OPENAI_API_KEY=sk-proj-...
HR_API_BASE_URL=https://dev-hrworkerapi.missionmind.ai/api/kafka
HR_API_ENDPOINT=/getBotResponse
```

### Step 5: Deploy the Agent

Deploy the updated agent code:

```bash
lk agent deploy
```

**Deployment Process:**
1. **Upload**: Code is uploaded to LiveKit Cloud (1.2 MB/s)
2. **Build**: Docker container is built (71.0s total)
3. **Push**: Image is pushed to registry
4. **Deploy**: Agent is deployed and started

**Expected Output:**
```
Using project [mobile-worker]
Using agent [CA_GDnD7evqFSXF]
Uploading 100% [==============================] ======] (1.2 MB/s)        
Updated agent [CA_GDnD7evqFSXF]
[+] Building 71.0s (11/11) FINISHED
 => [internal] load remote build context                                                               0.0s
 => copy /context /                                                                                    0.1s
 => [internal] load metadata for docker.io/library/python:3.11-slim                                    0.1s
 => CACHED [1/7] FROM docker.io/library/python:3.11-slim@sha256:...                                    0.0s
 => [2/7] RUN apt-get update && apt-get install -y gcc g++ git && rm -rf /var/lib/apt/lists/*         17.3s
 => [3/7] WORKDIR /app                                                                                 0.1s
 => [4/7] COPY requirements.txt .                                                                      0.1s
 => [5/7] RUN pip install --no-cache-dir -r requirements.txt                                          28.2s
 => [6/7] COPY . .                                                                                     0.1s
 => [7/7] RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app                              0.2s
 => exporting to image                                                                                22.7s
 => => exporting layers                                                                                18.1s
 => => pushing layers                                                                                  4.4s
 => => pushing manifest for iad.ocir.io/axyci3pr8vxm/production-cloud-agents:...                      0.1s
Deployed agent
```

### Step 6: Verify Deployment

Check the deployment status:

```bash
lk agent status
```

**Expected Output:**
```
Using project [mobile-worker]
Using agent [CA_GDnD7evqFSXF]
┌─────────────────┬─────────────────┬─────────┬────────────┬────────────┬─────────┬───────────┬──────────────────────┐
│ ID              │ Version         │ Region  │ Status     │ CPU        │ Mem     │ Replicas  │ Deployed At          │
├─────────────────┼─────────────────┼─────────┼────────────┼────────────┼─────────┼───────────┼──────────────────────┤
│ CA_GDnD7evqFSXF │ v20251006161552 │ us-east │ Scheduling │ 0m / 2000m │ 0 / 4GB │ 1 / 1 / 1 │ 2025-10-06T16:17:02Z │
└─────────────────┴─────────────────┴─────────┴────────────┴────────────┼─────────┼───────────┼──────────────────────┘
```

### Step 7: Monitor Agent Logs

View real-time logs to ensure everything is working:

```bash
lk agent logs
```

**Expected Log Output:**
```json
{"message": "starting worker", "level": "INFO", "name": "livekit.agents", "version": "1.2.14", "rtc-version": "1.0.13", "timestamp": "2025-10-06T16:17:16.451766+00:00"}
{"message": "preloading plugins", "level": "INFO", "name": "livekit.agents", "packages": ["livekit.plugins.openai", "livekit.plugins.silero", "av"], "timestamp": "2025-10-06T16:17:16.451887+00:00"}
INFO:     Started server process [1]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8080 (Press CTRL+C to quit)
{"message": "initializing process", "level": "INFO", "name": "livekit.agents", "pid": 79, "timestamp": "2025-10-06T16:17:17.694962+00:00"}
{"message": "process initialized", "level": "INFO", "name": "livekit.agents", "pid": 79, "elapsed_time": 0.27, "timestamp": "2025-10-06T16:17:17.961262+00:00"}
{"message": "registered worker", "level": "INFO", "name": "livekit.agents", "id": "CAW_QHGpYggcsjDz", "url": "https://mobile-worker-o314phth.livekit.cloud", "region": "US East B", "protocol": 16, "timestamp": "2025-10-06T16:17:18.023524+00:00"}
```

## 🎯 Deployment Success Indicators

### ✅ Successful Deployment Signs:
1. **Build Completed**: No errors during Docker build process
2. **Agent Status**: Status shows "Scheduling" or "Running"
3. **Worker Registered**: Logs show "registered worker" message
4. **Health Check**: Uvicorn server running on port 8080
5. **Plugins Loaded**: OpenAI and Silero plugins loaded successfully

### 🔍 Key Metrics to Monitor:
- **Version**: `v20251006161552` (increments with each deployment)
- **Region**: `us-east` (deployment region)
- **Status**: `Scheduling` → `Running` (startup sequence)
- **Resources**: CPU and Memory usage
- **Replicas**: 1/1/1 (current/desired/minimum)

## 🧪 Testing the Deployed Agent

### 1. Using LiveKit Playground
1. Go to [LiveKit Cloud Dashboard](https://cloud.livekit.io)
2. Navigate to your project
3. Click "Playground"
4. Join a room and start voice interaction

### 2. Test HR Queries
Try these sample questions:
- "What's our vacation policy?"
- "How do I request time off?"
- "What benefits are available?"
- "Give me my daily briefing"

### 3. Monitor Performance
- Check agent logs for errors
- Monitor resource usage
- Verify HR API connectivity

## 🔧 Troubleshooting

### Common Issues and Solutions:

#### 1. Authentication Failed
```bash
# Re-authenticate
lk cloud auth
```

#### 2. Agent Not Starting
```bash
# Check logs for errors
lk agent logs

# Check status
lk agent status
```

#### 3. Build Failures
- Verify Dockerfile syntax
- Check requirements.txt dependencies
- Ensure all files are present

#### 4. Environment Variables Missing
- Verify secrets.env file
- Check LiveKit Cloud dashboard settings
- Ensure API keys are valid

## 📊 Deployment Summary

### Final Deployment Details:
- **Agent ID**: `CA_GDnD7evqFSXF`
- **Version**: `v20251006161552`
- **Region**: `us-east`
- **Status**: Successfully deployed and running
- **Worker ID**: `CAW_QHGpYggcsjDz`
- **LiveKit URL**: `wss://mobile-worker-o314phth.livekit.cloud`
- **Health Check**: `http://0.0.0.0:8080/health`

### Architecture:
```
User Voice Input → LiveKit Cloud → HR Voice Assistant Agent → OpenAI STT → LLM → HR API → TTS → Voice Output
```

## 🚀 Next Steps

1. **Monitor Performance**: Use `lk agent logs` and dashboard metrics
2. **Scale as Needed**: Adjust replicas based on usage
3. **Update Code**: Use `lk agent deploy` for future updates
4. **Test Thoroughly**: Verify all HR functions work correctly
5. **Set Up Monitoring**: Configure alerts for errors or high usage

## 📚 Additional Resources

- [LiveKit Agents Documentation](https://docs.livekit.io/agents/)
- [LiveKit Cloud Dashboard](https://cloud.livekit.io)
- [CLI Reference](https://docs.livekit.io/cli/)
- [Deployment Best Practices](https://docs.livekit.io/agents/deployment/)

---

**Deployment completed successfully on**: 2025-10-06T16:17:02Z  
**Total deployment time**: ~2 minutes  
**Status**: ✅ Live and ready for voice interactions
