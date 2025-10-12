# HR Voice Assistant - Visual Workflow Diagrams

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    HR VOICE ASSISTANT SYSTEM                    │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   MOBILE APP    │    │  LIVEKIT CLOUD  │    │  BACKEND APIS   │
│                 │    │                 │    │                 │
│ ┌─────────────┐ │    │ ┌─────────────┐ │    │ ┌─────────────┐ │
│ │   Frontend  │ │    │ │    Room     │ │    │ │   HR API    │ │
│ │   Client    │ │◄──►│ │  Manager    │ │    │ │   System    │ │
│ └─────────────┘ │    │ └─────────────┘ │    │ └─────────────┘ │
│                 │    │                 │    │                 │
│ ┌─────────────┐ │    │ ┌─────────────┐ │    │ ┌─────────────┐ │
│ │   Audio     │ │    │ │   Agent     │ │    │ │   OpenAI    │ │
│ │  Channels   │ │◄──►│ │ Container   │ │◄──►│ │   Services  │ │
│ └─────────────┘ │    │ └─────────────┘ │    │ └─────────────┘ │
│                 │    │                 │    │                 │
│ ┌─────────────┐ │    │ ┌─────────────┐ │    │                 │
│ │   Data      │ │    │ │   Voice     │ │    │                 │
│ │  Channels   │ │◄──►│ │  Pipeline   │ │    │                 │
│ └─────────────┘ │    │ └─────────────┘ │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🔄 User Interaction Flow

```
USER SPEAKS
    │
    ▼
┌─────────────┐
│   Frontend  │ ──► Audio Capture
│   App       │ ──► Token Generation
└─────────────┘
    │
    ▼
┌─────────────┐
│  LiveKit    │ ──► Room Connection
│  Client     │ ──► Audio Stream
└─────────────┘
    │
    ▼
┌─────────────┐
│   Agent     │ ──► Speech-to-Text
│  Container  │ ──► Intent Classification
└─────────────┘
    │
    ▼
┌─────────────┐
│   Function  │ ──► Route to Handler
│   Router    │ ──► Call HR API
└─────────────┘
    │
    ▼
┌─────────────┐
│   Response  │ ──► Generate Answer
│  Generator  │ ──► Text-to-Speech
└─────────────┘
    │
    ▼
┌─────────────┐
│   Audio     │ ──► Stream to User
│  Output     │ ──► Display Data
└─────────────┘
    │
    ▼
USER HEARS RESPONSE
```

## 🎯 Agent Initialization Sequence

```
SYSTEM START
    │
    ▼
┌─────────────┐
│  LiveKit    │ ──► Load Configuration
│  Agent      │ ──► Initialize Models
└─────────────┘
    │
    ▼
┌─────────────┐
│   Voice     │ ──► Load VAD Model
│  Pipeline   │ ──► Initialize STT
│  Setup      │ ──► Initialize TTS
└─────────────┘
    │
    ▼
┌─────────────┐
│   Room      │ ──► Connect to Room
│ Connection  │ ──► Wait for User
└─────────────┘
    │
    ▼
┌─────────────┐
│  Automatic  │ ──► Send Greeting
│  Greeting   │ ──► Start Briefing
└─────────────┘
    │
    ▼
┌─────────────┐
│   Ready     │ ──► Listen for User
│   State     │ ──► Process Queries
└─────────────┘
```

## 🔧 Development Workflow

```
CODE CHANGE
    │
    ▼
┌─────────────┐
│   Local     │ ──► Edit agent.py
│  Testing    │ ──► Test Functions
└─────────────┘
    │
    ▼
┌─────────────┐
│    Git      │ ──► git add .
│  Commit     │ ──► git commit -m "..."
└─────────────┘
    │
    ▼
┌─────────────┐
│   GitHub    │ ──► git push
│   Push      │ ──► Update Repository
└─────────────┘
    │
    ▼
┌─────────────┐
│  LiveKit    │ ──► lk agent deploy
│ Deploy      │ ──► Build Container
└─────────────┘
    │
    ▼
┌─────────────┐
│   Test      │ ──► Create Test Room
│  Production │ ──► Dispatch Agent
└─────────────┘
    │
    ▼
┌─────────────┐
│  Monitor    │ ──► Check Logs
│  Results    │ ──► Verify Function
└─────────────┘
```

## 🚨 Error Handling Flow

```
ERROR OCCURS
    │
    ▼
┌─────────────┐
│   Error     │ ──► Log Error Details
│ Detection   │ ──► Identify Error Type
└─────────────┘
    │
    ▼
┌─────────────┐
│   Error     │ ──► Check Error Category
│Classification│ ──► Determine Severity
└─────────────┘
    │
    ▼
┌─────────────┐
│  Recovery   │ ──► Apply Fix Strategy
│  Strategy   │ ──► Fallback Response
└─────────────┘
    │
    ▼
┌─────────────┐
│   User      │ ──► Provide Feedback
│ Feedback    │ ──► Continue Service
└─────────────┘
```

## 📊 Data Flow Architecture

```
USER DATA
    │
    ▼
┌─────────────┐
│   Token     │ ──► Embed User Info
│ Generation  │ ──► Include Metadata
└─────────────┘
    │
    ▼
┌─────────────┐
│   Data      │ ──► Send via Data Channel
│  Channel    │ ──► Receive in Agent
└─────────────┘
    │
    ▼
┌─────────────┐
│   User      │ ──► Store Configuration
│  Config     │ ──► Update Context
└─────────────┘
    │
    ▼
┌─────────────┐
│   HR API    │ ──► Query with User ID
│   Query     │ ──► Get Personalized Data
└─────────────┘
    │
    ▼
┌─────────────┐
│  Response   │ ──► Personalized Answer
│ Generation  │ ──► Send to User
└─────────────┘
```

## 🔄 Intent Classification Flow

```
USER INPUT
    │
    ▼
┌─────────────┐
│   Text      │ ──► Clean Input
│ Processing  │ ──► Normalize Text
└─────────────┘
    │
    ▼
┌─────────────┐
│   Keyword   │ ──► Check Keywords
│ Matching    │ ──► Pattern Matching
└─────────────┘
    │
    ▼
┌─────────────┐
│   Intent    │ ──► Classify Intent
│Classification│ ──► Calculate Confidence
└─────────────┘
    │
    ▼
┌─────────────┐
│   Function  │ ──► Route to Handler
│   Router    │ ──► Execute Function
└─────────────┘
    │
    ▼
┌─────────────┐
│   Response  │ ──► Generate Answer
│ Generation  │ ──► Return Result
└─────────────┘
```

## 🎤 Voice Processing Pipeline

```
AUDIO INPUT
    │
    ▼
┌─────────────┐
│   VAD       │ ──► Voice Activity Detection
│ Detection   │ ──► Start/Stop Detection
└─────────────┘
    │
    ▼
┌─────────────┐
│    STT      │ ──► Speech-to-Text
│ Processing  │ ──► OpenAI Whisper
└─────────────┘
    │
    ▼
┌─────────────┐
│   Intent    │ ──► Classify Intent
│Processing   │ ──► Extract Meaning
└─────────────┘
    │
    ▼
┌─────────────┐
│   Function  │ ──► Execute Function
│ Execution   │ ──► Get Response
└─────────────┘
    │
    ▼
┌─────────────┐
│    TTS      │ ──► Text-to-Speech
│ Processing  │ ──► OpenAI TTS
└─────────────┘
    │
    ▼
┌─────────────┐
│   Audio     │ ──► Stream Audio
│  Output     │ ──► Send to User
└─────────────┘
```

## 🔧 Troubleshooting Decision Tree

```
ISSUE REPORTED
    │
    ▼
┌─────────────┐
│   Check     │ ──► Agent Status
│   Status    │ ──► Room Status
└─────────────┘
    │
    ▼
┌─────────────┐
│   Agent     │ ──► YES: Check Logs
│  Running?   │ ──► NO: Redeploy
└─────────────┘
    │
    ▼
┌─────────────┐
│   Room      │ ──► YES: Check Dispatch
│  Active?    │ ──► NO: Create Room
└─────────────┘
    │
    ▼
┌─────────────┐
│  Dispatch   │ ──► YES: Check Logs
│  Active?    │ ──► NO: Create Dispatch
└─────────────┘
    │
    ▼
┌─────────────┐
│   Logs      │ ──► Check for Errors
│ Analysis    │ ──► Identify Issue
└─────────────┘
    │
    ▼
┌─────────────┐
│   Fix       │ ──► Apply Solution
│ Applied     │ ──► Test Result
└─────────────┘
```

## 📈 Performance Monitoring

```
SYSTEM METRICS
    │
    ▼
┌─────────────┐
│  Response   │ ──► < 5s: Good
│   Time      │ ──► 5-10s: Warning
└─────────────┘    ──► > 10s: Critical
    │
    ▼
┌─────────────┐
│   Error     │ ──► < 1%: Good
│   Rate      │ ──► 1-5%: Warning
└─────────────┘    ──► > 5%: Critical
    │
    ▼
┌─────────────┐
│   Memory    │ ──► < 2GB: Good
│   Usage     │ ──► 2-3GB: Warning
└─────────────┘    ──► > 3GB: Critical
    │
    ▼
┌─────────────┐
│   Uptime    │ ──► > 99%: Good
│   Status    │ ──► 95-99%: Warning
└─────────────┘    ──► < 95%: Critical
```

---

**These diagrams provide a visual representation of how the HR Voice Assistant system works. Use them as reference when explaining the system to new team members or troubleshooting issues.**
