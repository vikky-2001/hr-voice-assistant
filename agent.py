import logging
import asyncio
import time
import json
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    JobProcess,
    RoomInputOptions,
    WorkerOptions,
    cli,
    function_tool,
)
from livekit import rtc
from livekit.plugins import silero, openai as livekit_openai
from openai import OpenAI  # ✅ use the official OpenAI SDK
import httpx
from fastapi import FastAPI
import uvicorn
import noisereduce as nr
import jwt
import asyncpg
import os
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from typing import Dict, List, Optional
from enum import Enum
from abc import ABC, abstractmethod

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("agent")

# HR API Configuration
HR_API_BASE_URL = "https://dev-hrworkerapi.missionmind.ai/api/kafka"
# HR_API_BASE_URL = "https://acarin-hrworkerapi.missionmind.ai/api/kafka"
HR_API_ENDPOINT = "/getBotResponse"

# Dynamic user configuration - can be overridden by environment variables
DEFAULT_USER_ID = "79f2b410-bbbe-43b9-a77f-38a6213ce13d"  # Fallback user
# DEFAULT_USER_ID = "da7fdc93-eb67-45cc-b8a9-dedf23cb8bca"

DEFAULT_CHATLOG_ID = 7747  # Fallback chatlog
DEFAULT_AGENT_ID = 6  # Fallback agent

# Daily Briefing Cache Configuration
BRIEFING_CACHE_DURATION = 30  # Cache briefing for 30 minutes
BRIEFING_CACHE_FILE = "briefing_cache.json"  # Single file with user-specific data

# In-memory cache for better performance in containerized environments
_briefing_cache = {}  # Global in-memory cache: {user_id: {briefing, timestamp}}

# Database configuration (using same connection details as fetch_user_details_from_db)
DB_CONFIG = {
    'user': 'AN24_Acabot',
    'password': 'lAyWkB5FIXghQpvNYM5ggpITC',
    'database': 'acabotdb-dev',
    'host': 'acabot-dbcluster-dev.cluster-cp2eea8yihxz.us-east-1.rds.amazonaws.com',
    'port': 5432
}

# Scheduler for scheduled briefing tasks
scheduler = AsyncIOScheduler()

# Database connection pool (initialized on first use)
_db_pool = None
_table_exists_cache = False

load_dotenv(".env.local")

# ✅ Initialize OpenAI client globally
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Intent Classification System
class IntentClassifier:
    """Classifies user intents to enable smarter conversation flow"""
    
    def __init__(self):
        # Define intent categories
        self.intents = {
            "greeting": {
                "keywords": ["hello", "hi", "hey", "good morning", "good afternoon", "good evening", "greetings"],
                "patterns": [r"\b(hello|hi|hey)\b", r"good (morning|afternoon|evening)", r"how are you"],
                "response": "Hello! I'm your HR assistant. How can I help you today?",
                "requires_hr_api": False
            },
            "farewell": {
                "keywords": ["bye", "goodbye", "see you", "thanks", "thank you", "have a good day"],
                "patterns": [r"\b(bye|goodbye|see you)\b", r"thank you", r"have a good"],
                "response": "You're welcome! Have a great day!",
                "requires_hr_api": False
            },
            "status_check": {
                "keywords": ["how are you", "what can you do", "what do you do", "capabilities"],
                "patterns": [r"how are you", r"what can you do", r"what do you do", r"your capabilities"],
                "response": "I'm doing great! I can help you with HR-related questions like company policies, benefits, leave requests, payroll, and more. What would you like to know?",
                "requires_hr_api": False
            },
            "daily_briefing": {
                "keywords": ["daily briefing", "briefing", "today's updates", "what's new", "updates"],
                "patterns": [r"daily briefing", r"briefing", r"today's updates", r"what's new"],
                "response": None,  # Will trigger get_daily_briefing function
                "requires_hr_api": True
            },
            "hr_query": {
                "keywords": ["policy", "policies", "benefits", "leave", "vacation", "sick", "payroll", "salary", "insurance", "retirement", "workflow", "workflows", "process", "procedure", "how to", "what is", "tell me about", "explain"],
                "patterns": [r"policy", r"policies", r"benefits", r"leave", r"vacation", r"sick", r"payroll", r"salary", r"insurance", r"retirement", r"workflow", r"workflows", r"process", r"procedure", r"how to", r"what is", r"tell me about", r"explain"],
                "response": None,  # Will trigger query_hr_system function
                "requires_hr_api": True
            },
            "help": {
                "keywords": ["help", "assistance", "support", "don't understand", "confused"],
                "patterns": [r"help", r"assistance", r"support", r"don't understand", r"confused"],
                "response": "I'm here to help! You can ask me about company policies, benefits, leave requests, payroll, or any other HR-related questions. What would you like to know?",
                "requires_hr_api": False
            },
            "complaint": {
                "keywords": ["complaint", "issue", "problem", "concern", "unhappy", "dissatisfied"],
                "patterns": [r"complaint", r"issue", r"problem", r"concern", r"unhappy", r"dissatisfied"],
                "response": "I understand you have a concern. Let me help you with that. Can you tell me more details about the issue?",
                "requires_hr_api": True
            },
            "appreciation": {
                "keywords": ["great", "excellent", "wonderful", "amazing", "love", "appreciate", "fantastic", "awesome"],
                "patterns": [r"great", r"excellent", r"wonderful", r"amazing", r"love", r"appreciate", r"fantastic", r"awesome"],
                "response": "Thank you so much! I'm glad I could help. Is there anything else you'd like to know?",
                "requires_hr_api": False
            }
        }
    
    def classify_intent(self, user_input: str) -> dict:
        """
        Classify user input into intent categories
        
        Args:
            user_input: The user's spoken or typed input
            
        Returns:
            dict: Intent classification result
        """
        import re
        
        user_input_lower = user_input.lower().strip()
        
        # Check for exact keyword matches first (highest priority)
        for intent_name, intent_data in self.intents.items():
            for keyword in intent_data["keywords"]:
                if keyword in user_input_lower:
                    logger.info(f"Intent classified as '{intent_name}' via keyword: '{keyword}'")
                    return {
                        "intent": intent_name,
                        "confidence": 0.9,
                        "requires_hr_api": intent_data["requires_hr_api"],
                        "response": intent_data["response"],
                        "matched_keyword": keyword
                    }
        
        # Check for pattern matches (medium priority)
        for intent_name, intent_data in self.intents.items():
            for pattern in intent_data["patterns"]:
                if re.search(pattern, user_input_lower):
                    logger.info(f"Intent classified as '{intent_name}' via pattern: '{pattern}'")
                    return {
                        "intent": intent_name,
                        "confidence": 0.8,
                        "requires_hr_api": intent_data["requires_hr_api"],
                        "response": intent_data["response"],
                        "matched_pattern": pattern
                    }
        
        # Check for HR-related content (lower priority but still HR query)
        hr_indicators = ["hr", "human resources", "employee", "work", "company", "job", "workplace"]
        if any(indicator in user_input_lower for indicator in hr_indicators):
            logger.info(f"Intent classified as 'hr_query' via HR indicators")
            return {
                "intent": "hr_query",
                "confidence": 0.6,
                "requires_hr_api": True,
                "response": None,
                "matched_indicators": [ind for ind in hr_indicators if ind in user_input_lower]
            }
        
        # Default to HR query if no specific intent found
        logger.info(f"Intent classified as 'hr_query' (default)")
        return {
            "intent": "hr_query",
            "confidence": 0.5,
            "requires_hr_api": True,
            "response": None,
            "reason": "default_classification"
        }

# Global intent classifier instance
intent_classifier = IntentClassifier()

# Intermediate Messaging System
class IntermediateMessaging:
    """Manages intermediate messages for long-running operations"""
    
    def __init__(self):
        self.intermediate_messages = {
            "hr_query": [
                "Let me look that up for you...",
                "Checking our HR system...",
                "Searching for the latest information...",
                "Gathering the details you need...",
                "Almost there, just a moment...",
                "Retrieving your information...",
                "Looking through our policies...",
                "Getting the most current details..."
            ],
            "daily_briefing": [
                "Preparing your daily briefing...",
                "Gathering today's updates...",
                "Collecting your personalized information...",
                "Almost ready with your briefing...",
                "Putting together your daily summary...",
                "Compiling the latest updates..."
            ],
            "complaint": [
                "I understand your concern. Let me help...",
                "Looking into this issue for you...",
                "Checking our support resources...",
                "Finding the best way to assist you...",
                "Gathering information to help resolve this..."
            ],
            "general": [
                "Working on that for you...",
                "Let me get that information...",
                "Just a moment while I check...",
                "Processing your request...",
                "Looking into this..."
            ]
        }
        
        self.message_index = 0
        self.last_message_time = 0
        self.message_interval = 3.0  # Send intermediate message every 3 seconds
    
    def get_intermediate_message(self, intent_type: str = "general") -> str:
        """Get the next intermediate message for the given intent type"""
        messages = self.intermediate_messages.get(intent_type, self.intermediate_messages["general"])
        
        # Cycle through messages
        message = messages[self.message_index % len(messages)]
        self.message_index += 1
        
        return message
    
    def should_send_intermediate_message(self) -> bool:
        """Check if enough time has passed to send an intermediate message"""
        import time
        current_time = time.time()
        
        if current_time - self.last_message_time >= self.message_interval:
            self.last_message_time = current_time
            return True
        
        return False
    
    def reset_timer(self):
        """Reset the message timer"""
        import time
        self.last_message_time = time.time()
        self.message_index = 0

# Global intermediate messaging instance
intermediate_messaging = IntermediateMessaging()

# Global user configuration storage
_current_user_config = {
    "user_id": DEFAULT_USER_ID,
    "chatlog_id": DEFAULT_CHATLOG_ID,
    "agent_id": DEFAULT_AGENT_ID,
    "user_email": "",
    "user_name": "Mobile User"
}

def get_user_config(room_name: str = None, participant_identity: str = None):
    """
    Get dynamic user configuration based on environment variables, frontend data, or room context.
    
    Priority:
    1. Frontend-provided configuration (from data channel)
    2. Environment variables (HR_USER_ID, HR_CHATLOG_ID, HR_AGENT_ID)
    3. Room-based lookup (if room_name provided)
    4. Identity-based lookup (if participant_identity provided)
    5. Default fallback values
    
    Args:
        room_name: LiveKit room name (can be used for user identification)
        participant_identity: Participant identity (can be used for user identification)
    
    Returns:
        dict: Configuration with user_id, chatlog_id, agent_id
    """
    import os
    
    # Use frontend-provided configuration if available
    if _current_user_config["user_id"] != DEFAULT_USER_ID:
        logger.info(f"Using frontend-provided user config: {_current_user_config}")
        return _current_user_config.copy()
    
    # Try to get from environment variables
    user_id = os.getenv("HR_USER_ID", DEFAULT_USER_ID)
    chatlog_id = int(os.getenv("HR_CHATLOG_ID", DEFAULT_CHATLOG_ID))
    agent_id = int(os.getenv("HR_AGENT_ID", DEFAULT_AGENT_ID))
    
    # Room-based user lookup (if room_name is provided)
    if room_name and room_name != "Tester-room1":  # Skip default room
        room_user_id = lookup_user_by_room(room_name)
        if room_user_id:
            user_id = room_user_id
            logger.info(f"User ID resolved from room '{room_name}': {user_id}")
    
    # Identity-based user lookup (if participant_identity is provided)
    if participant_identity and participant_identity != "Mobile-hr-worker":  # Skip default identity
        identity_user_id = lookup_user_by_identity(participant_identity)
        if identity_user_id:
            user_id = identity_user_id
            logger.info(f"User ID resolved from identity '{participant_identity}': {user_id}")
    
    config = {
        "user_id": user_id,
        "chatlog_id": chatlog_id,
        "agent_id": agent_id,
        "user_email": "",
        "user_name": "Mobile User"
    }
    
    logger.info(f"User config resolved: user_id={user_id}, chatlog_id={chatlog_id}, agent_id={agent_id}")
    return config

def update_user_config_from_frontend(config_data: dict):
    """
    Update user configuration from frontend data channel message.
    
    Args:
        config_data: Dictionary containing user configuration from frontend
    """
    global _current_user_config
    
    try:
        _current_user_config.update({
            "user_id": config_data.get("user_id", DEFAULT_USER_ID),
            "chatlog_id": int(config_data.get("chatlog_id", DEFAULT_CHATLOG_ID)),
            "agent_id": int(config_data.get("agent_id", DEFAULT_AGENT_ID)),
            "user_email": config_data.get("user_email", ""),
            "user_name": config_data.get("user_name", "Mobile User")
        })
        
        logger.info(f"✅ User configuration updated from frontend: {_current_user_config}")
        
    except (ValueError, TypeError) as e:
        logger.error(f"❌ Error updating user config from frontend: {e}")
        # Truncate long config data in logs to avoid scanner errors
        config_str = str(config_data)
        if len(config_str) > 500:
            logger.error(f"❌ Invalid config data: {config_str[:500]}... (truncated, {len(config_str)} total)")
        else:
            logger.error(f"❌ Invalid config data: {config_str}")

def lookup_user_by_room(room_name: str) -> str:
    """
    Look up user ID based on room name.
    This can be customized based on your room naming convention.
    
    Examples:
    - Room: "user-12345" -> User ID: "12345"
    - Room: "employee-john-doe" -> User ID: lookup in database
    - Room: "hr-session-abc123" -> User ID: extract from session ID
    
    Args:
        room_name: The LiveKit room name
        
    Returns:
        str: User ID if found, None otherwise
    """
    # Example implementations:
    
    # Option 1: Extract user ID from room name pattern
    if room_name.startswith("user-"):
        user_id = room_name.replace("user-", "")
        logger.info(f"Extracted user ID from room name: {user_id}")
        return user_id
    
    # Option 2: Look up in a mapping (you could load this from a file or database)
    room_user_mapping = {
        "john-doe-room": "user-john-doe-123",
        "jane-smith-room": "user-jane-smith-456",
        "hr-demo-room": "demo-user-789"
    }
    
    if room_name in room_user_mapping:
        user_id = room_user_mapping[room_name]
        logger.info(f"Found user ID in room mapping: {user_id}")
        return user_id
    
    # Option 3: Database lookup (implement if you have a user database)
    # user_id = database.lookup_user_by_room(room_name)
    
    logger.info(f"No user ID found for room: {room_name}")
    return None

def lookup_user_by_identity(participant_identity: str) -> str:
    """
    Look up user ID based on participant identity.
    This can be customized based on your identity naming convention.
    
    Examples:
    - Identity: "user-12345" -> User ID: "12345"
    - Identity: "employee-john-doe" -> User ID: lookup in database
    - Identity: "john.doe@company.com" -> User ID: lookup by email
    
    Args:
        participant_identity: The participant identity
        
    Returns:
        str: User ID if found, None otherwise
    """
    # Example implementations:
    
    # Option 1: Extract user ID from identity pattern
    if participant_identity.startswith("user-"):
        user_id = participant_identity.replace("user-", "")
        logger.info(f"Extracted user ID from identity: {user_id}")
        return user_id
    
    # Option 2: Email-based lookup
    if "@" in participant_identity:
        # Extract email and look up user ID
        email = participant_identity
        # user_id = database.lookup_user_by_email(email)
        logger.info(f"Email-based lookup for: {email}")
        # return user_id
    
    # Option 3: Look up in a mapping
    identity_user_mapping = {
        "john.doe": "user-john-doe-123",
        "jane.smith": "user-jane-smith-456",
        "hr-demo": "demo-user-789"
    }
    
    if participant_identity in identity_user_mapping:
        user_id = identity_user_mapping[participant_identity]
        logger.info(f"Found user ID in identity mapping: {user_id}")
        return user_id
    
    # Option 4: Database lookup (implement if you have a user database)
    # user_id = database.lookup_user_by_identity(participant_identity)
    
    logger.info(f"No user ID found for identity: {participant_identity}")
    return None

async def send_text_to_frontend(session: AgentSession, message_type: str, content: str, metadata: dict = None):
    """Send structured text data to the frontend via LiveKit data channel
    
    Automatically chunks large content to avoid buffer overflow errors.
    """
    try:
        import json
        
        # Check if session and room are properly available
        if not session or not hasattr(session, 'room') or not session.room:
            logger.debug(f"Session or room not available for sending {message_type} to frontend")
            return
            
        if not hasattr(session.room, 'local_participant') or not session.room.local_participant:
            logger.debug(f"Local participant not available for sending {message_type} to frontend")
            return
            
        # Check if there are any participants in the room (users connected)
        if not session.room.remote_participants:
            logger.debug(f"No remote participants connected for sending {message_type} to frontend")
            return
        
        # Maximum size for data channel messages (conservative limit to avoid scanner errors)
        # LiveKit typically supports up to 64KB, but we use 32KB to be safe
        MAX_MESSAGE_SIZE = 32 * 1024  # 32KB in bytes
        MAX_CONTENT_SIZE = 28 * 1024  # Leave room for JSON overhead
        
        # If content is too large, chunk it
        if len(content.encode('utf-8')) > MAX_CONTENT_SIZE:
            logger.info(f"Content too large ({len(content)} bytes), chunking into smaller messages")
            
            # Split content into chunks
            chunk_size = MAX_CONTENT_SIZE
            chunks = []
            content_bytes = content.encode('utf-8')
            
            for i in range(0, len(content_bytes), chunk_size):
                chunk_text = content_bytes[i:i+chunk_size].decode('utf-8', errors='ignore')
                chunks.append(chunk_text)
            
            # Send each chunk as a separate message
            total_chunks = len(chunks)
            for idx, chunk in enumerate(chunks):
                chunk_metadata = (metadata or {}).copy()
                chunk_metadata.update({
                    "is_chunked": True,
                    "chunk_index": idx,
                    "total_chunks": total_chunks,
                    "original_size": len(content)
                })
                
                data = {
                    "type": message_type,
                    "content": chunk,
                    "timestamp": datetime.now().isoformat(),
                    "metadata": chunk_metadata
                }
                
                json_data = json.dumps(data)
                json_size = len(json_data.encode('utf-8'))
                
                # Safety check: if JSON is still too large, truncate content further
                if json_size > MAX_MESSAGE_SIZE:
                    # Calculate how much to reduce content
                    overhead = json_size - len(chunk.encode('utf-8'))
                    max_content = MAX_MESSAGE_SIZE - overhead - 100  # Safety margin
                    
                    if max_content > 0:
                        chunk = chunk[:max_content]
                        data["content"] = chunk
                        json_data = json.dumps(data)
                    else:
                        logger.error(f"Message too large even after truncation, skipping chunk {idx}")
                        continue
                
                await session.room.local_participant.publish_data(
                    data=json_data.encode('utf-8'),
                    topic="chat"
                )
                
                # Small delay between chunks to avoid overwhelming the channel
                if idx < total_chunks - 1:
                    await asyncio.sleep(0.05)
            
            logger.info(f"Sent {message_type} to frontend in {total_chunks} chunks (total: {len(content)} bytes)")
        else:
            # Normal size message - send as-is
            data = {
                "type": message_type,
                "content": content,
                "timestamp": datetime.now().isoformat(),
                "metadata": metadata or {}
            }
            
            json_data = json.dumps(data)
            json_size = len(json_data.encode('utf-8'))
            
            # Final safety check
            if json_size > MAX_MESSAGE_SIZE:
                logger.warning(f"JSON message size ({json_size} bytes) exceeds limit, truncating content")
                # Truncate content to fit
                overhead = json_size - len(content.encode('utf-8'))
                max_content = MAX_MESSAGE_SIZE - overhead - 100
                
                if max_content > 0:
                    data["content"] = content[:max_content]
                    data["metadata"] = (metadata or {}).copy()
                    data["metadata"]["truncated"] = True
                    data["metadata"]["original_size"] = len(content)
                    json_data = json.dumps(data)
                else:
                    logger.error(f"Message too large even after truncation, skipping")
                    return
            
            await session.room.local_participant.publish_data(
                data=json_data.encode('utf-8'),
                topic="chat"
            )
            
            # Truncate log message to prevent very long log lines
            log_content = content[:200] + "..." if len(content) > 200 else content
            logger.info(f"Sent {message_type} to frontend: {log_content}")
        
    except Exception as e:
        logger.error(f"Error sending text to frontend: {e}")

async def send_intermediate_message(session: AgentSession, intent_type: str = "general"):
    """Send an intermediate message to keep user engaged during long operations"""
    try:
        message = intermediate_messaging.get_intermediate_message(intent_type)
        
        await send_text_to_frontend(
            session=session,
            message_type="intermediate_message",
            content=message,
            metadata={
                "intent_type": intent_type,
                "message_index": intermediate_messaging.message_index - 1,
                "is_intermediate": True
            }
        )
        
        logger.info(f"Sent intermediate message: {message}")
        
    except Exception as e:
        logger.error(f"Error sending intermediate message: {e}")

async def monitor_long_operation(session: AgentSession, intent_type: str, operation_name: str):
    """Monitor a long-running operation and send intermediate messages"""
    import asyncio
    
    try:
        # Reset the intermediate messaging timer
        intermediate_messaging.reset_timer()
        
        # Start monitoring task
        async def monitor():
            while True:
                await asyncio.sleep(1)  # Check every second
                
                if intermediate_messaging.should_send_intermediate_message():
                    await send_intermediate_message(session, intent_type)
        
        # Start monitoring in background
        monitor_task = asyncio.create_task(monitor())
        
        logger.info(f"Started monitoring for {operation_name} with intent type: {intent_type}")
        
        return monitor_task
        
    except Exception as e:
        logger.error(f"Error starting operation monitoring: {e}")
        return None


# ============================================================================
# ERROR MONITORING & NOTIFICATION SYSTEM
# ============================================================================

class ErrorSeverity(Enum):
    CRITICAL = "CRITICAL"  # System down, data loss
    HIGH = "HIGH"          # Major functionality broken
    MEDIUM = "MEDIUM"      # Degraded performance
    LOW = "LOW"            # Minor issues

class NotificationChannel(ABC):
    """Base class for notification channels"""
    
    @abstractmethod
    async def send(self, error_record: Dict):
        pass

class EmailNotification(NotificationChannel):
    """Email notification channel"""
    
    def __init__(self, smtp_server: str, smtp_port: int, 
                 sender_email: str, sender_password: str,
                 recipient_emails: List[str]):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.sender_email = sender_email
        self.sender_password = sender_password
        self.recipient_emails = recipient_emails
    
    async def send(self, error_record: Dict):
        """Send email notification"""
        try:
            # In production, use async SMTP library like aiosmtplib
            logger.info(f"📧 Email notification would be sent: {error_record['error_type']} - {error_record['severity']}")
            logger.info(f"   To: {', '.join(self.recipient_emails)}")
            logger.info(f"   Subject: 🚨 HR Worker Alert: {error_record['error_type']} - {error_record['severity']}")
        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")


class ErrorMonitor:
    """Centralized error monitoring and notification system"""
    
    def __init__(self):
        self.error_counts: Dict[str, int] = {}
        self.error_history: List[Dict] = []
        self.alert_thresholds = {
            ErrorSeverity.CRITICAL: 1,   # Email sent immediately on 1st occurrence
            ErrorSeverity.HIGH: 3,        # Email sent after 3 occurrences
            ErrorSeverity.MEDIUM: 5,      # Email sent after 5 occurrences
            ErrorSeverity.LOW: 10         # Email sent after 10 occurrences
        }
        self.notification_channels: List[NotificationChannel] = []
    
    async def log_error(
        self,
        error_type: str,
        message: str,
        severity: ErrorSeverity,
        context: Optional[Dict] = None,
        exception: Optional[Exception] = None
    ):
        """Log error and trigger notifications if needed"""
        error_key = f"{error_type}:{severity.value}"
        self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1
        
        error_record = {
            "timestamp": datetime.now().isoformat(),
            "error_type": error_type,
            "message": message,
            "severity": severity.value,
            "context": context or {},
            "exception": str(exception) if exception else None,
            "count": self.error_counts[error_key]
        }
        
        self.error_history.append(error_record)
        
        # Keep only last 1000 errors
        if len(self.error_history) > 1000:
            self.error_history = self.error_history[-1000:]
        
        # Log the error
        logger.error(f"[{severity.value}] {error_type}: {message}", exc_info=exception)
        
        # Check if we should send notification
        threshold = self.alert_thresholds.get(severity, 10)
        if self.error_counts[error_key] >= threshold:
            await self.send_notification(error_record)
    
    async def send_notification(self, error_record: Dict):
        """Send notification to configured channels"""
        for channel in self.notification_channels:
            try:
                await channel.send(error_record)
            except Exception as e:
                logger.error(f"Failed to send notification via {channel}: {e}")

# Global error monitor instance
error_monitor = ErrorMonitor()

def setup_notifications():
    """Setup notification channels from environment variables (Email only)"""
    # Email notifications only
    if os.getenv("ALERT_EMAIL_FROM") and os.getenv("ALERT_EMAIL_TO"):
        error_monitor.notification_channels.append(
            EmailNotification(
                smtp_server=os.getenv("SMTP_SERVER", "smtp.gmail.com"),
                smtp_port=int(os.getenv("SMTP_PORT", "587")),
                sender_email=os.getenv("ALERT_EMAIL_FROM"),
                sender_password=os.getenv("ALERT_EMAIL_PASSWORD", ""),
                recipient_emails=os.getenv("ALERT_EMAIL_TO", "").split(",")
            )
        )
        logger.info("✅ Email notifications configured")
    else:
        logger.warning("⚠️ Email notifications not configured. Set ALERT_EMAIL_FROM and ALERT_EMAIL_TO environment variables to enable.")

# Initialize notifications
setup_notifications()

# ============================================================================
# DATABASE CONNECTION POOLING
# ============================================================================

async def get_db_pool():
    """Get or create database connection pool"""
    global _db_pool
    if _db_pool is None:
        try:
            _db_pool = await asyncpg.create_pool(
                **DB_CONFIG,
                min_size=5,        # Minimum connections
                max_size=20,       # Maximum connections
                max_queries=50000,  # Max queries per connection
                max_inactive_connection_lifetime=300,  # 5 minutes
                command_timeout=60  # Query timeout
            )
            logger.info("✅ Database connection pool created")
        except Exception as e:
            await error_monitor.log_error(
                error_type="DB_POOL_CREATE_FAILED",
                message="Failed to create database connection pool",
                severity=ErrorSeverity.CRITICAL,
                exception=e
            )
            raise
    return _db_pool

async def get_db_connection():
    """Get connection from pool (or create new if pool not available)
    
    Returns:
        asyncpg.Connection: Database connection (use as async context manager)
    """
    try:
        pool = await get_db_pool()
        return pool.acquire()
    except Exception as e:
        logger.warning(f"Connection pool not available, creating direct connection: {e}")
        # Fallback to direct connection if pool fails
        # Note: Direct connection should be used with async context manager or manually closed
        conn = await asyncpg.connect(**DB_CONFIG)
        return conn

async def ensure_briefing_table_exists():
    """Ensure the briefing_cache table exists in the database (cached)"""
    global _table_exists_cache
    if _table_exists_cache:
        return
    
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS briefing_cache (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(255) NOT NULL,
                    briefing_content TEXT NOT NULL,
                    cache_type VARCHAR(20) NOT NULL DEFAULT 'general',  -- 'morning', 'evening', or 'general'
                    cache_date DATE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, cache_date, cache_type)
                );
                CREATE INDEX IF NOT EXISTS idx_briefing_cache_user_date ON briefing_cache(user_id, cache_date);
                CREATE INDEX IF NOT EXISTS idx_briefing_cache_user_date_type ON briefing_cache(user_id, cache_date, cache_type);
                CREATE INDEX IF NOT EXISTS idx_briefing_cache_date_type ON briefing_cache(cache_date, cache_type);
                CREATE INDEX IF NOT EXISTS idx_briefing_cache_updated_at ON briefing_cache(updated_at);
            """)
        _table_exists_cache = True
        logger.info("✅ Briefing cache table ensured to exist")
    except Exception as e:
        await error_monitor.log_error(
            error_type="TABLE_CREATION_FAILED",
            message="Failed to ensure briefing_cache table exists",
            severity=ErrorSeverity.HIGH,
            exception=e
        )
        logger.error(f"❌ Error ensuring briefing table exists: {e}")

async def save_briefing_to_db(user_id: str, briefing_content: str, cache_type: str = 'general'):
    """
    Save or update briefing in database for a user.
    
    Args:
        user_id: The user ID
        briefing_content: The briefing content
        cache_type: 'morning', 'evening', or 'general'
    """
    await ensure_briefing_table_exists()
    pool = await get_db_pool()
    try:
        async with pool.acquire() as conn:
            today = datetime.now().date()
            
            # Use INSERT ... ON CONFLICT to update if record exists
            await conn.execute("""
                INSERT INTO briefing_cache (user_id, briefing_content, cache_type, cache_date, updated_at)
                VALUES ($1, $2, $3, $4, CURRENT_TIMESTAMP)
                ON CONFLICT (user_id, cache_date, cache_type)
                DO UPDATE SET
                    briefing_content = EXCLUDED.briefing_content,
                    updated_at = CURRENT_TIMESTAMP
            """, user_id, briefing_content, cache_type, today)
            
        logger.info(f"✅ Briefing saved to database for user {user_id} (type: {cache_type})")
    except Exception as e:
        await error_monitor.log_error(
            error_type="DATABASE_SAVE_FAILED",
            message=f"Failed to save briefing for user {user_id}",
            severity=ErrorSeverity.HIGH,
            context={"user_id": user_id, "cache_type": cache_type},
            exception=e
        )
        raise

async def user_has_briefing_in_db(user_id: str) -> bool:
    """
    Check if a user has any briefing record in the database for today.
    
    Args:
        user_id: The user ID
    
    Returns:
        True if user has a briefing record, False otherwise
    """
    await ensure_briefing_table_exists()
    pool = await get_db_pool()
    try:
        async with pool.acquire() as conn:
            today = datetime.now().date()
            result = await conn.fetchval("""
                SELECT COUNT(*) 
                FROM briefing_cache 
                WHERE user_id = $1 AND cache_date = $2
            """, user_id, today)
            return result > 0 if result else False
    except Exception as e:
        await error_monitor.log_error(
            error_type="DATABASE_CHECK_FAILED",
            message=f"Failed to check if user has briefing: {user_id}",
            severity=ErrorSeverity.MEDIUM,
            context={"user_id": user_id},
            exception=e
        )
        return False

async def load_briefing_from_db(user_id: str, cache_type: str = None) -> str:
    """
    Load briefing from database for a user.
    
    Args:
        user_id: The user ID
        cache_type: Optional filter by cache type ('morning', 'evening', or None for any)
    
    Returns:
        Briefing content if found, None otherwise
    """
    await ensure_briefing_table_exists()
    pool = await get_db_pool()
    try:
        async with pool.acquire() as conn:
            today = datetime.now().date()
            
            if cache_type:
                result = await conn.fetchrow("""
                    SELECT briefing_content, updated_at 
                    FROM briefing_cache 
                    WHERE user_id = $1 AND cache_date = $2 AND cache_type = $3
                    ORDER BY updated_at DESC
                    LIMIT 1
                """, user_id, today, cache_type)
            else:
                # Get the most recent briefing for today (prefer evening, then morning, then general)
                result = await conn.fetchrow("""
                    SELECT briefing_content, updated_at 
                    FROM briefing_cache 
                    WHERE user_id = $1 AND cache_date = $2
                    ORDER BY 
                        CASE cache_type 
                            WHEN 'evening' THEN 1
                            WHEN 'morning' THEN 2
                            ELSE 3
                        END,
                        updated_at DESC
                    LIMIT 1
                """, user_id, today)
            
            if result:
                logger.info(f"📋 Loaded briefing from database for user {user_id}")
                return result['briefing_content']
            else:
                logger.debug(f"No briefing found in database for user {user_id} on {today}")
                return None
    except Exception as e:
        await error_monitor.log_error(
            error_type="DATABASE_LOAD_FAILED",
            message=f"Failed to load briefing from database for user {user_id}",
            severity=ErrorSeverity.MEDIUM,
            context={"user_id": user_id, "cache_type": cache_type},
            exception=e
        )
        return None

async def get_all_active_users():
    """Get all active users from the database"""
    pool = await get_db_pool()
    try:
        async with pool.acquire() as conn:
            # Get all users from the users table
            # Adjust this query based on your actual users table structure
            users = await conn.fetch("""
                SELECT DISTINCT user_id 
                FROM users 
                WHERE user_id IS NOT NULL
            """)
            user_ids = [row['user_id'] for row in users]
            logger.info(f"Found {len(user_ids)} active users in database")
            return user_ids
    except Exception as e:
        await error_monitor.log_error(
            error_type="DATABASE_FETCH_USERS_FAILED",
            message="Failed to fetch active users from database",
            severity=ErrorSeverity.HIGH,
            exception=e
        )
        return []

async def fetch_and_cache_briefing_for_user(user_id: str, cache_type: str = 'general'):
    """
    Fetch briefing from HR API and cache it in database for a specific user.
    
    Args:
        user_id: The user ID
        cache_type: 'morning', 'evening', or 'general'
    """
    try:
        logger.info(f"🔄 Fetching briefing for user {user_id} (type: {cache_type})")
        
        # Create a temporary Assistant instance to use its methods
        # We'll need to get user config for this user
        assistant = Assistant()
        
        # Get user configuration - we'll need to fetch chatlog_id and agent_id from DB
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            user_config_query = await conn.fetchrow("""
                SELECT user_id, tenant_id 
                FROM users 
                WHERE user_id = $1
            """, user_id)
            
            if not user_config_query:
                logger.warning(f"User {user_id} not found in database")
                return
            
            # Use default chatlog_id and agent_id (you may want to store these per user)
            user_config = {
                "user_id": user_id,
                "chatlog_id": DEFAULT_CHATLOG_ID,
                "agent_id": DEFAULT_AGENT_ID,
                "tenant_id": user_config_query['tenant_id']
            }
        
        # Generate JWT token
        jwt_token = await assistant._generate_jwt_token(user_id)
        headers = {
            "Authorization": f"Bearer {jwt_token}"
        }
        
        # Call HR API for briefing
        url = f"{HR_API_BASE_URL}{HR_API_ENDPOINT}"
        params = {
            "query": "System trigger: daily briefing",
            "user_id": user_id,
            "chatlog_id": user_config["chatlog_id"],
            "agent_id": user_config["agent_id"],
            "mobile_request": True
        }
        
        timeout = httpx.Timeout(30.0, connect=10.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url, params=params, headers=headers)
            
            if response.status_code != 200:
                await error_monitor.log_error(
                    error_type="HR_API_ERROR",
                    message=f"HR API returned error status {response.status_code} for user {user_id}",
                    severity=ErrorSeverity.HIGH,
                    context={
                        "user_id": user_id,
                        "status_code": response.status_code,
                        "response_text": response.text[:200] if hasattr(response, 'text') else None
                    }
                )
                response.raise_for_status()
            
            data = response.json()
            briefing_response = data.get("response", "No daily briefing available at this time")
            
            # Save to database
            await save_briefing_to_db(user_id, briefing_response, cache_type)
            
            # Also update in-memory cache
            _briefing_cache[user_id] = {
                'briefing': briefing_response,
                'timestamp': datetime.now()
            }
            
            logger.info(f"✅ Briefing fetched and cached for user {user_id} (type: {cache_type})")
            
    except httpx.TimeoutException as e:
        await error_monitor.log_error(
            error_type="HR_API_TIMEOUT",
            message=f"HR API request timed out for user {user_id}",
            severity=ErrorSeverity.MEDIUM,
            context={"user_id": user_id, "cache_type": cache_type},
            exception=e
        )
        raise
    except httpx.RequestError as e:
        await error_monitor.log_error(
            error_type="HR_API_REQUEST_FAILED",
            message=f"HR API request failed for user {user_id}",
            severity=ErrorSeverity.HIGH,
            context={"user_id": user_id, "cache_type": cache_type},
            exception=e
        )
        raise
    except Exception as e:
        await error_monitor.log_error(
            error_type="BRIEFING_FETCH_FAILED",
            message=f"Error fetching briefing for user {user_id}",
            severity=ErrorSeverity.HIGH,
            context={"user_id": user_id, "cache_type": cache_type},
            exception=e
        )
        raise

async def scheduled_briefing_task(cache_type: str):
    """
    Scheduled task to fetch and cache briefings for all active users.
    
    Args:
        cache_type: 'morning' (5 AM) or 'evening' (5 PM)
    """
    logger.info(f"⏰ Starting scheduled briefing task ({cache_type})")
    task_start_time = datetime.now()
    success_count = 0
    failure_count = 0
    
    try:
        # Get all active users
        user_ids = await get_all_active_users()
        
        if not user_ids:
            await error_monitor.log_error(
                error_type="SCHEDULED_TASK_NO_USERS",
                message="No active users found for briefing generation",
                severity=ErrorSeverity.LOW,
                context={"cache_type": cache_type}
            )
            return
        
        # Adaptive batch size based on user count
        if len(user_ids) > 100:
            batch_size = 20
            delay = 1
        elif len(user_ids) > 50:
            batch_size = 15
            delay = 1.5
        else:
            batch_size = 10
            delay = 2
        
        # Use semaphore to limit concurrent API calls
        semaphore = asyncio.Semaphore(20)  # Max 20 concurrent
        
        async def fetch_with_limit(user_id):
            async with semaphore:
                try:
                    await fetch_and_cache_briefing_for_user(user_id, cache_type)
                    return True
                except Exception:
                    return False
        
        # Process in batches
        for i in range(0, len(user_ids), batch_size):
            batch = user_ids[i:i + batch_size]
            tasks = [fetch_with_limit(user_id) for user_id in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Count successes and failures
            for result in results:
                if result is True:
                    success_count += 1
                else:
                    failure_count += 1
            
            # Small delay between batches
            await asyncio.sleep(delay)
        
        # Log summary
        if failure_count > 0:
            await error_monitor.log_error(
                error_type="SCHEDULED_TASK_PARTIAL_FAILURE",
                message=f"Scheduled task completed with {failure_count} failures out of {len(user_ids)} users",
                severity=ErrorSeverity.MEDIUM if failure_count < len(user_ids) * 0.1 else ErrorSeverity.HIGH,
                context={
                    "cache_type": cache_type,
                    "total_users": len(user_ids),
                    "success_count": success_count,
                    "failure_count": failure_count
                }
            )
        
        elapsed = (datetime.now() - task_start_time).total_seconds()
        logger.info(f"✅ Scheduled briefing task completed ({cache_type}) for {len(user_ids)} users in {elapsed:.2f}s (Success: {success_count}, Failed: {failure_count})")
        
    except Exception as e:
        await error_monitor.log_error(
            error_type="SCHEDULED_TASK_CRITICAL_FAILURE",
            message=f"Scheduled briefing task failed completely for {cache_type}",
            severity=ErrorSeverity.CRITICAL,
            context={"cache_type": cache_type},
            exception=e
        )
        raise

def start_scheduled_briefing_tasks():
    """Start the scheduled briefing tasks for 5 AM and 5 PM"""
    if scheduler.running:
        logger.info("Scheduler already running, skipping startup")
        return
    
    # Schedule morning briefing at 5:00 AM
    scheduler.add_job(
        scheduled_briefing_task,
        CronTrigger(hour=5, minute=0),
        args=['morning'],
        id='morning_briefing',
        name='Morning Briefing (5 AM)',
        replace_existing=True
    )
    
    # Schedule evening briefing at 5:00 PM
    scheduler.add_job(
        scheduled_briefing_task,
        CronTrigger(hour=17, minute=0),
        args=['evening'],
        id='evening_briefing',
        name='Evening Briefing (5 PM)',
        replace_existing=True
    )
    
    scheduler.start()
    logger.info("✅ Scheduled briefing tasks started (5 AM and 5 PM)")


# Daily Briefing Cache Functions
async def load_briefing_cache_async():
    """Load briefing cache - database first, then in-memory, then file backup (async)"""
    current_user_id = get_user_config().get('user_id', 'default')
    
    # Check database first (most reliable)
    db_briefing = await load_briefing_from_db(current_user_id)
    if db_briefing:
        # Update in-memory cache for faster future access
        _briefing_cache[current_user_id] = {
            'briefing': db_briefing,
            'timestamp': datetime.now()
        }
        logger.info(f"📋 Loaded briefing from database for user {current_user_id}")
        return db_briefing
    
    # If no briefing in database, check in-memory/file cache as fallback
    # Note: First-time users will have briefing fetched and created in get_daily_briefing()
    return load_briefing_cache()

def load_briefing_cache():
    """Load briefing cache - in-memory first, then file backup"""
    current_user_id = get_user_config().get('user_id', 'default')
    
    # Check in-memory cache first (fastest)
    if current_user_id in _briefing_cache:
        cache_data = _briefing_cache[current_user_id]
        logger.debug(f"In-memory cache hit for user_id: {current_user_id} at time: {cache_data['timestamp']}")
        cache_time = cache_data['timestamp']
        
        if datetime.now() - cache_time < timedelta(minutes=BRIEFING_CACHE_DURATION):
            logger.info(f"📋 Loaded valid in-memory briefing cache for user {current_user_id} from {cache_time}")
            return cache_data['briefing']
        else:
            logger.info("📋 In-memory briefing cache expired, will fetch fresh data")
            # Remove expired cache
            del _briefing_cache[current_user_id]
    else:
        logger.debug("In-memory cache miss for user_id: %s", current_user_id)
    
    # Fallback to file cache
    try:
        with open(BRIEFING_CACHE_FILE, 'r') as f:
            cache_data = json.load(f)
        logger.debug(f"File cache loaded for user_id: {cache_data.get('user_id', 'unknown')} at time: {cache_data.get('timestamp', 'unknown')}")
            
        cached_user_id = cache_data.get('user_id', 'unknown')
        
        # Check if cache belongs to current user
        if current_user_id != cached_user_id:
            logger.info(f"📋 File cache belongs to different user ({cached_user_id}), not using for current user ({current_user_id})")
            return None
            
        # Check if cache is still valid
        cache_time = datetime.fromisoformat(cache_data['timestamp'])
        if datetime.now() - cache_time < timedelta(minutes=BRIEFING_CACHE_DURATION):
            logger.info(f"📋 Loaded valid file briefing cache for user {current_user_id} from {cache_time}")
            # Load into in-memory cache for faster future access
            _briefing_cache[current_user_id] = {
                'briefing': cache_data['briefing'],
                'timestamp': cache_time
            }
            return cache_data['briefing']
        else:
            logger.info("📋 File briefing cache expired, will fetch fresh data")
            return None
    except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
        logger.debug(f"No valid file briefing cache found: {e}")
        return None
    except Exception as e:
        logger.warning("Failed to load file briefing cache: {}", str(e))


async def save_briefing_cache_async(briefing_content: str, cache_type: str = 'general'):
    """Save briefing content to database, in-memory, and file cache (async)"""
    current_user_id = get_user_config().get('user_id', 'default')
    now = datetime.now()
    
    # Save to database (most reliable)
    await save_briefing_to_db(current_user_id, briefing_content, cache_type)
    
    # Save to in-memory cache (fastest access)
    _briefing_cache[current_user_id] = {
        'briefing': briefing_content,
        'timestamp': now
    }
    logger.debug(f"Saving to in-memory cache for user_id: {current_user_id} at time: {now}")
    
    # Also save to file cache (persistence across restarts)
    try:
        cache_data = {
            'briefing': briefing_content,
            'timestamp': now.isoformat(),
            'user_id': current_user_id
        }
        
        with open(BRIEFING_CACHE_FILE, 'w') as f:
            logger.debug(f"Writing file cache for user_id: {current_user_id} at time: {now}")
            json.dump(cache_data, f, indent=2)
            
        logger.info("📋 Briefing cache saved to file successfully")
    except Exception as e:
        logger.warning(f"Failed to save briefing cache to file (in-memory cache still works): {e}")

def save_briefing_cache(briefing_content: str):
    """Save briefing content to both in-memory and file cache (sync version for backward compatibility)"""
    current_user_id = get_user_config().get('user_id', 'default')
    now = datetime.now()
    
    # Save to in-memory cache (fastest access)
    _briefing_cache[current_user_id] = {
        'briefing': briefing_content,
        'timestamp': now
    }
    logger.debug(f"Saving to in-memory cache for user_id: {current_user_id} at time: {now}")
    
    # Also save to file cache (persistence across restarts)
    try:
        cache_data = {
            'briefing': briefing_content,
            'timestamp': now.isoformat(),
            'user_id': current_user_id
        }
        
        with open(BRIEFING_CACHE_FILE, 'w') as f:
            logger.debug(f"Writing file cache for user_id: {current_user_id} at time: {now}")
            json.dump(cache_data, f, indent=2)
            
        logger.info("📋 Briefing cache saved to file successfully")
    except Exception as e:
        logger.warning(f"Failed to save briefing cache to file (in-memory cache still works): {e}")
    
    # Also save to database asynchronously (non-blocking)
    # Note: This requires an active event loop. If called from sync context without loop,
    # the task will be created but may not execute. Consider using async version instead.
    try:
        try:
            loop = asyncio.get_running_loop()
            # We're in an async context with a running loop
            asyncio.create_task(save_briefing_cache_async(briefing_content, 'general'))
        except RuntimeError:
            # No running event loop - try to get/create one
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(save_briefing_cache_async(briefing_content, 'general'))
                else:
                    # Not running, but exists - schedule it
                    asyncio.run_coroutine_threadsafe(
                        save_briefing_cache_async(briefing_content, 'general'),
                        loop
                    )
            except RuntimeError:
                # No event loop available at all, skip async save
                logger.debug("No event loop available for async database save, skipping")
    except Exception as e:
        logger.warning(f"Failed to save briefing to database (non-blocking): {e}")


async def get_cached_briefing_async():
    """Get cached briefing if available and valid (async, checks database first)"""
    cached_briefing = await load_briefing_cache_async()
    if cached_briefing:
        logger.info("🚀 Using cached briefing for instant response")
        return cached_briefing
    return None

def get_cached_briefing():
    """Get cached briefing if available and valid (sync version, checks in-memory/file cache)"""
    cached_briefing = load_briefing_cache()
    if cached_briefing:
        logger.info("🚀 Using cached briefing for instant response")
        return cached_briefing
    return None


async def send_automatic_greeting(session: AgentSession, assistant: 'Assistant'):
    """Send automatic greeting when connection is established"""
    try:
        import asyncio
        
        # Wait longer for the connection and TTS to fully establish
        await asyncio.sleep(2.5)
        
        # TTS will be initialized automatically when we first speak
        # No need to pre-warm with a spoken phrase
        logger.info("TTS will initialize on first speech")
        
        # Get user configuration for personalized greeting
        user_config = get_user_config()
        user_name = user_config.get("user_name", "there")
        
        # Create simple, focused greeting messages (briefing will come after)
        greeting_options = [
            f"Hello! I'm your HR assistant.",
            f"Hi! Welcome to your HR assistant.",
            f"Good day! I'm your HR assistant.",
            f"Hello! Your HR assistant is ready.",
            f"Hi there! I'm your HR assistant."
        ]
        
        # Select a greeting (you could randomize this or use time-based selection)
        import random
        greeting = random.choice(greeting_options)
        
        logger.info(f"🤖 Sending automatic greeting: {greeting}")
        
        # Send greeting to frontend
        await send_text_to_frontend(
            session=session,
            message_type="automatic_greeting",
            content=greeting,
            metadata={
                "source": "agent",
                "greeting_type": "connection_established",
                "user_name": user_name,
                "timestamp": datetime.now().isoformat()
            }
        )
        
        # Actually speak the greeting using the session's say method with better error handling
        try:
            # Minimal pause for TTS initialization
            await asyncio.sleep(0.1)
            await session.say(greeting)
            logger.info("✅ Automatic greeting spoken successfully")
        except Exception as e:
            logger.warning(f"Could not speak automatic greeting: {e}")
            # Try a simpler fallback greeting
            try:
                await asyncio.sleep(0.1)
                await session.say(f"Hello! Your HR assistant is ready to help.")
                logger.info("✅ Fallback greeting spoken successfully")
            except Exception as fallback_e:
                logger.error(f"Could not speak fallback greeting: {fallback_e}")
            logger.info("✅ Automatic greeting sent to frontend (not spoken)")
        
        logger.info("✅ Automatic greeting sent successfully")
        
    except Exception as e:
        logger.error(f"❌ Error sending automatic greeting: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")


class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions="""You are an HR assistant voice AI that helps employees with HR-related questions.
            
            AUTOMATIC GREETING: When a user first connects, you MUST:
            1. First call send_connection_greeting() to welcome them proactively with a warm greeting
            2. Then immediately call get_daily_briefing() to get their briefing
            3. Then speak the briefing naturally: "Here's your daily briefing: [briefing content]. How can I help you today?"
            4. Do this as ONE continuous flow - greeting, then briefing, all in sequence
            
            SMART CONVERSATION FLOW: You now have intelligent intent classification and conversation memory for optimal user experience.
            
            PRIMARY RULE: ALWAYS call smart_conversation_handler(user_input) for EVERY user interaction. This function will:
            1. Classify the user's intent (greeting, HR query, complaint, etc.)
            2. Determine if HR API call is needed or direct response is sufficient
            3. Route to appropriate function automatically
            4. Remember conversation context for follow-up questions
            
            CRITICAL: After calling ANY function tool, you MUST speak the response to the user. Function tools return information, but you need to present it conversationally. Never just return function results silently - always speak them naturally.
            
            CONVERSATION FLOW:
            1. User connects → You call send_connection_greeting() (automatic welcome)
            2. User speaks → You call smart_conversation_handler(user_input)
            3. Function classifies intent and determines response strategy
            4. For greetings/farewells/help → Direct response (fast)
            5. For HR queries/complaints → HR API call (comprehensive)
            6. ALWAYS speak the response back to the user - present function results naturally and conversationally
            
            CONTEXT AWARENESS:
            - The system remembers recent conversation topics
            - For follow-up questions like "What about sick leave?" it refers to previous context
            - Conversation memory helps provide more personalized responses
            
            DAILY BRIEFING PROTOCOL: When a user first connects, you should:
            1. First call send_connection_greeting() to greet them warmly
            2. Then immediately call get_daily_briefing() to retrieve their daily briefing information
            3. After getting the briefing, speak it naturally: "Here's your daily briefing: [provide the briefing content in a clear, organized way]. How can I help you today?"
            4. When presenting the briefing, make it engaging and easy to understand - don't just read it robotically
            5. IMPORTANT: Do NOT say "let me get your daily briefing" - just get it and present it directly
            
            IMPORTANT: 
            - Call send_connection_greeting() when user first connects (proactive greeting)
            - Use smart_conversation_handler() for all user interactions
            - When you see "System trigger: daily briefing", call get_daily_briefing() directly
            - Always speak naturally and conversationally
            - The system will automatically optimize response speed and accuracy
            
            RESPONSE HANDLING:
            - When query_hr_system() returns a response, ALWAYS SPEAK it to the user in a helpful, conversational way
            - When smart_conversation_handler() returns a response, ALWAYS SPEAK it to the user
            - When get_daily_briefing() returns content, ALWAYS SPEAK it to the user naturally
            - NEVER silently return function results - you must SPEAK everything you learn from function calls
            - If the HR API provides information, share it confidently and completely by SPEAKING it
            - If the response seems incomplete or unclear, ask follow-up questions to help the user
            - Never say "I cannot provide" unless you truly have no information - always try to be helpful
            - For company policies, workflows, and HR information, share whatever information the HR system provides by SPEAKING it
            - Be proactive in helping users understand HR processes and policies
            - Remember: Your responses are automatically converted to speech via TTS, so generate natural spoken text
            
            CRITICAL SPEECH FLOW REQUIREMENTS:
            - ALWAYS generate responses as SINGLE CONTINUOUS statements - never break responses into separate sentences with pauses
            - When speaking, combine all related thoughts into ONE flowing response without stopping between sentences
            - For example, instead of saying "Hello mobile user." [pause] "How can I help you today?" [pause] "Let me get your daily briefing."
            - Say: "Hello mobile user! How can I help you today? Let me get your daily briefing."
            - Generate responses that flow naturally from start to finish without artificial breaks
            - The TTS will handle natural pauses automatically - you don't need to create separate statements
            - Think of your responses as a continuous stream of speech, not separate statements""",
        )
        
        # Initialize conversation memory
        self.conversation_memory = []
        self.current_context = None

    def add_to_memory(self, user_input: str, intent: str, response: str = None):
        """Add interaction to conversation memory"""
        memory_entry = {
            "timestamp": datetime.now().isoformat(),
            "user_input": user_input,
            "intent": intent,
            "response": response
        }
        self.conversation_memory.append(memory_entry)
        
        # Update to keep last 10 interactions
        if len(self.conversation_memory) > 10:
            self.conversation_memory = self.conversation_memory[-10:]
        
        logger.info(f"Added to conversation memory: {intent} - {user_input[:50]}...")
    
    def get_conversation_context(self) -> str:
        """Get recent conversation context for better responses"""
        if not self.conversation_memory:
            return "This is the start of our conversation."
        
        recent_interactions = self.conversation_memory[-3:]  # Last 3 interactions
        context = "Recent conversation context:\n"
        for entry in recent_interactions:
            context += f"- User asked about: {entry['intent']} ({entry['user_input'][:50]}...)\n"
        
        return context
    
    def classify_and_respond(self, user_input: str) -> dict:
        """Classify user intent and determine response strategy"""
        # Classify the intent
        intent_result = intent_classifier.classify_intent(user_input)
        
        # Add to conversation memory
        self.add_to_memory(user_input, intent_result["intent"])
        
        # Update current context
        self.current_context = intent_result["intent"]
        
        logger.info(f"Intent classification result: {intent_result}")
        return intent_result

    # Function to fetch user details from the database
    async def fetch_user_details_from_db(self, user_id: str) -> dict:
        """Fetch tenant_id using user_id from the database."""
        pool = await get_db_pool()
        try:
            async with pool.acquire() as conn:
                query = "SELECT tenant_id FROM users WHERE user_id = $1"
                result = await conn.fetchrow(query, user_id)
                logger.debug(f"Database query result: {result}")

                if result:
                    return {
                        "user_id": user_id,
                        "tenant_id": result["tenant_id"]
                    }
                else:
                    await error_monitor.log_error(
                        error_type="TENANT_NOT_FOUND",
                        message=f"No tenant found for user_id: {user_id}",
                        severity=ErrorSeverity.MEDIUM,
                        context={"user_id": user_id}
                    )
                    raise ValueError("Tenant not found")
        except Exception as e:
            await error_monitor.log_error(
                error_type="FETCH_USER_DETAILS_FAILED",
                message=f"Failed to fetch user details for user_id: {user_id}",
                severity=ErrorSeverity.HIGH,
                context={"user_id": user_id},
                exception=e
            )
            raise

    # Update _generate_jwt_token to use this function
    async def _generate_jwt_token(self, user_id: str) -> str:
        """Generate JWT token for HR Worker API authentication."""
        try:
            user_details = await self.fetch_user_details_from_db(user_id)
            final_user_id = user_details["user_id"]
            final_tenant_id = user_details["tenant_id"]

            # Create payload with issued at and expiration time
            now = datetime.now(timezone.utc)
            issued_at = int(now.timestamp())
            expiration_time = now + timedelta(minutes=30)
            expires_at = int(expiration_time.timestamp())

            payload = {
                "user_id": final_user_id,
                "tenant_id": final_tenant_id,
                "iat": issued_at,
                "exp": expires_at
            }

            # Get JWT secret from environment variable, fallback to default for development
            jwt_secret = os.getenv("JWT_SECRET", "missionmind-dev")
            jwt_algorithm = os.getenv("JWT_ALGORITHM", "HS256")

            token = jwt.encode(
                payload,
                jwt_secret,
                algorithm=jwt_algorithm
            )

            # Log the generated token with limited visibility for debugging (SECURITY: never log full token)
            logger.info(f"Generated JWT token (partial): {token[:10]}...{token[-10:]}")
            logger.info(f"Generated JWT token for user: {final_user_id} with expiry at {expires_at}")
            return token
        except Exception as e:
            logger.error(f"Error generating JWT token: {e}")
            # Re-raise to let caller handle it
            raise

    # all functions annotated with @function_tool will be passed to the LLM when this
    # agent is active
    @function_tool
    async def get_daily_briefing(self):
        """Get the daily briefing information for the user. This includes important updates, announcements, and reminders for the day.

        This tool should be called automatically when a user first connects to provide them with their daily briefing.
        You can also call this manually when users ask for their daily briefing.
        """

        logger.info("=== get_daily_briefing() function called ===")
        
        # Get user configuration
        user_config = get_user_config()
        user_id = user_config["user_id"]
        
        # Check database cache first (most reliable)
        db_briefing = await load_briefing_from_db(user_id)
        if db_briefing:
            logger.info(f"✅ Returning existing briefing from database for user {user_id}")
            # Update in-memory cache for faster future access
            _briefing_cache[user_id] = {
                'briefing': db_briefing,
                'timestamp': datetime.now()
            }
            return db_briefing
        
        # No briefing found in database - this is a first-time user or briefing not yet generated
        logger.info(f"📝 No briefing found in database for user {user_id} - fetching and creating record...")
        
        # Fallback to in-memory/file cache while we fetch (for faster initial response)
        cached_briefing = get_cached_briefing()
        if cached_briefing:
            logger.info("🚀 Using in-memory/file cache while fetching fresh briefing...")
            # Still fetch in background to update database
            asyncio.create_task(fetch_and_cache_briefing_for_user(user_id, 'general'))
            return cached_briefing
        
        logger.info("Getting daily briefing from HR system (no cache found)")

        # Start intermediate messaging monitoring
        monitor_task = None
        try:
            session = getattr(self, '_session', None)
            if session and hasattr(session, 'room') and session.room:
                # Start monitoring for intermediate messages
                monitor_task = await monitor_long_operation(session, "daily_briefing", "daily briefing retrieval")
                
                # Send initial loading message
                await send_text_to_frontend(
                    session=session,
                    message_type="loading",
                    content="Preparing your daily HR briefing...",
                    metadata={"source": "hr_api", "query": "System trigger: daily briefing", "status": "loading"}
                )
        except Exception as e:
            logger.error(f"Error setting up intermediate messaging: {e}")

        try:
            # Get dynamic user configuration
            user_config = get_user_config()
            
            # Ensure user_id is obtained from user configuration
            user_id = user_config["user_id"]

            # Add JWT token when calling HR API
            jwt_token = await self._generate_jwt_token(user_id)
            headers = {
                "Authorization": f"Bearer {jwt_token}"
            }

            # Call the HR API for daily briefing with dynamic user and chatlog IDs
            url = f"{HR_API_BASE_URL}{HR_API_ENDPOINT}"
            logger.info(f"HR API URL: {url}")
            
            params = {
                "query": "System trigger: daily briefing",
                "user_id": user_config["user_id"],
                "chatlog_id": user_config["chatlog_id"],
                "agent_id": user_config["agent_id"],
                "mobile_request": True
            }
            logger.info(f"HR API params: {params}")
            
            logger.info("Making HTTP request to HR API...")
            # Use a longer timeout for daily briefing as it may require more processing
            timeout = httpx.Timeout(30.0, connect=10.0)  # 30s total, 10s for connection
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(url, params=params, headers=headers)
                logger.info(f"HR API response status: {response.status_code}")
                response.raise_for_status()
                
                data = response.json()
                # Truncate long response data in logs to avoid scanner errors
                data_str = str(data)
                if len(data_str) > 500:
                    logger.info(f"HR API response data: {data_str[:500]}... (truncated, {len(data_str)} total)")
                else:
                    logger.info(f"HR API response data: {data_str}")
                briefing_response = data.get("response", "No daily briefing available at this time")
                
                logger.info(f"Daily briefing received: {briefing_response[:100]}...")
                logger.info("=== get_daily_briefing() function completed successfully ===")
                
                # Stop intermediate messaging monitoring
                if monitor_task:
                    monitor_task.cancel()
                    logger.info("Stopped intermediate messaging monitoring")
                
                # Send daily briefing to frontend
                try:
                    session = getattr(self, '_session', None)
                    if session and hasattr(session, 'room') and session.room:
                        await send_text_to_frontend(
                            session=session,
                            message_type="daily_briefing",
                            content=briefing_response,
                            metadata={"source": "hr_api", "query": "System trigger: daily briefing"}
                        )
                    else:
                        logger.warning("Session or room not available for sending daily briefing to frontend")
                except Exception as e:
                    logger.error(f"Error sending daily briefing to frontend: {e}")
                
                # Save to cache for future instant responses (database, in-memory, and file)
                await save_briefing_cache_async(briefing_response, 'general')
                
                return briefing_response
            
        except httpx.HTTPStatusError as e:
            # Truncate long error responses to avoid scanner errors
            error_text = e.response.text[:500] + "..." if len(e.response.text) > 500 else e.response.text
            logger.error(f"HTTP error getting daily briefing: {e.response.status_code} - {error_text}")
            if monitor_task:
                monitor_task.cancel()
            return "I'm sorry, I couldn't retrieve your daily briefing at this time. Please try again later or contact HR directly."
        except httpx.RequestError as e:
            logger.error(f"Request error getting daily briefing: {e}")
            import traceback
            logger.error(f"Full error details: {traceback.format_exc()}")
            if monitor_task:
                monitor_task.cancel()
            # Provide more specific error message based on error type
            if isinstance(e, httpx.TimeoutException):
                return "I'm sorry, the HR system is taking longer than expected to prepare your daily briefing. Please try again in a moment."
            return "I'm sorry, I'm having trouble connecting to the HR system for your daily briefing. Please try again later."
        except Exception as e:
            logger.error(f"Unexpected error getting daily briefing: {e}")
            if monitor_task:
                monitor_task.cancel()
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return "I'm sorry, I encountered an error while retrieving your daily briefing. Please try again or contact HR directly."

    async def get_daily_briefing_with_speech(self):
        """Get daily briefing and automatically speak it to the user"""
        try:
            logger.info("=== get_daily_briefing_with_speech() called ===")
            
            # Wait a moment after greeting before starting briefing
            await asyncio.sleep(1.0)
            
            # Check cache first for instant response
            cached_briefing = get_cached_briefing()
            session = getattr(self, '_session', None)
            
            if cached_briefing and session:
                # Instant response with cached briefing
                logger.info("🚀 Speaking cached briefing instantly")
                try:
                    await session.say(f"Here's your daily briefing: {cached_briefing}. How can I help you today?")
                    logger.info("✅ Cached daily briefing spoken successfully")
                except Exception as e:
                    logger.error(f"Error speaking cached briefing: {e}")
                return
            
            # No cache available, fetch fresh briefing
            # Get the briefing content with timeout
            try:
                briefing_content = await asyncio.wait_for(self.get_daily_briefing(), timeout=20.0)
                logger.info("✅ Daily briefing retrieved successfully")
                
                # Speak the briefing to the user
                if session and briefing_content:
                    try:
                        logger.info("Speaking daily briefing to user")
                        await session.say(f"Here's your daily briefing: {briefing_content}. How can I help you today?")
                        logger.info("Daily briefing spoken successfully")
                    except Exception as e:
                        logger.error(f"Error speaking daily briefing: {e}")
            except asyncio.TimeoutError:
                logger.warning("Daily briefing request timed out, using fallback")
                if session:
                    try:
                        await session.say("I'm having trouble connecting to the HR system right now. Your daily briefing will be available shortly. How can I help you today?")
                    except Exception as e:
                        logger.error(f"Error speaking fallback message: {e}")
            except Exception as e:
                logger.error(f"Error fetching daily briefing: {e}")
                if session:
                    try:
                        await session.say("I'm having trouble retrieving your daily briefing right now. How can I help you today?")
                    except Exception as e:
                        logger.error(f"Error speaking error message: {e}")
                
        except Exception as e:
            logger.error(f"Error in get_daily_briefing_with_speech: {e}")
            import traceback
            # Truncate long tracebacks to avoid scanner errors
            tb_str = traceback.format_exc()
            if len(tb_str) > 500:
                logger.error(f"Traceback: {tb_str[:500]}... (truncated)")
            else:
                logger.error(f"Traceback: {tb_str}")
            # Fallback: speak a simple message
            try:
                session = getattr(self, '_session', None)
                if session:
                    await session.say("I'm preparing your daily briefing. Please give me a moment.")
            except Exception as fallback_error:
                logger.error(f"Fallback speech error: {fallback_error}")
                # Don't raise - just log and continue

    @function_tool
    async def query_hr_system(self, query: str):
        """Use this tool to query the HR system for information about company policies, benefits, leave requests, payroll, and other HR matters.

        This tool connects to the HR API to get accurate, up-to-date information from the HR system.

        Args:
            query: The HR-related question or request from the user
        """

        logger.info(f"Querying HR system: {query}")

        # Start intermediate messaging monitoring
        monitor_task = None
        try:
            session = getattr(self, '_session', None)
            if session and hasattr(session, 'room') and session.room:
                # Determine intent type for appropriate intermediate messages
                intent_result = self.classify_and_respond(query)
                intent_type = intent_result["intent"]
                
                # Start monitoring for intermediate messages
                monitor_task = await monitor_long_operation(session, intent_type, f"HR query: {query[:50]}")
                
                # Send initial loading message
                await send_text_to_frontend(
                    session=session,
                    message_type="loading",
                    content="Let me check that information for you...",
                    metadata={"source": "hr_api", "query": query, "status": "loading"}
                )
        except Exception as e:
            logger.error(f"Error setting up intermediate messaging: {e}")

        try:
            # Get dynamic user configuration
            user_config = get_user_config()
            
            # Ensure user_id is obtained from user configuration
            user_id = user_config["user_id"]

            # Generate JWT token
            token = await self._generate_jwt_token(user_id)

            headers = {
                "Authorization": f"Bearer {token}"
            }

            # Define the URL for the API request
            url = f"{HR_API_BASE_URL}{HR_API_ENDPOINT}"
            params = {
                "query": query,
                "user_id": user_config["user_id"],
                "chatlog_id": user_config["chatlog_id"],
                "agent_id": user_config["agent_id"],
                "mobile_request": True
            }

            logger.info(f"Making request to HR API: {url} with params: {params}")  # Log the request details

            # Use a longer timeout for HR queries as they may require more processing
            timeout = httpx.Timeout(30.0, connect=10.0)  # 30s total, 10s for connection
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(url, params=params, headers=headers)
                response.raise_for_status()
                
                logger.info(f"Full HTTP Response: status={response.status_code}, body={response.text[:500]}...")  # Log more of the response

                data = response.json()
                hr_response = data.get("response", "")
                
                # Validate the response
                if not hr_response or hr_response.strip() == "":
                    # Truncate long data in logs to avoid scanner errors
                    data_str = str(data)
                    if len(data_str) > 500:
                        logger.warning(f"HR API returned empty response. Full data: {data_str[:500]}... (truncated, {len(data_str)} total)")
                    else:
                        logger.warning(f"HR API returned empty response. Full data: {data_str}")
                    if monitor_task:
                        monitor_task.cancel()
                    return "I'm sorry, I didn't receive a response from the HR system for that question. Could you please rephrase your question or try asking about a specific topic?"
                
                # Check for common error indicators in the response
                hr_response_lower = hr_response.lower()
                error_indicators = [
                    "cannot provide",
                    "cannot help",
                    "unable to",
                    "error",
                    "problem",
                    "sorry, i don't",
                    "i don't have access",
                    "not available"
                ]
                
                if any(indicator in hr_response_lower for indicator in error_indicators) and len(hr_response) < 100:
                    logger.warning(f"HR API response appears to be an error or unhelpful: {hr_response}")
                    # Still return it, but log it for debugging
                
                logger.info(f"HR API response received: {hr_response[:200]}...")
                
                # Stop intermediate messaging monitoring
                if monitor_task:
                    monitor_task.cancel()
                    logger.info("Stopped intermediate messaging monitoring")
                
                return hr_response
            
        except httpx.HTTPStatusError as e:
            # Truncate long error responses to avoid scanner errors
            error_text = e.response.text[:500] + "..." if len(e.response.text) > 500 else e.response.text
            logger.error(f"HTTP error querying HR system: {e.response.status_code} - {error_text}")
            if monitor_task:
                monitor_task.cancel()
            return f"I'm sorry, I encountered an error while looking up that information. Please try again or contact HR directly."
        except httpx.RequestError as e:
            logger.error(f"Request error querying HR system: {e}")
            import traceback
            logger.error(f"Full error details: {traceback.format_exc()}")
            if monitor_task:
                monitor_task.cancel()
            # Provide more specific error message based on error type
            if isinstance(e, httpx.TimeoutException):
                return "I'm sorry, the HR system is taking longer than expected to respond. Please try again in a moment."
            return f"I'm sorry, I'm having trouble connecting to the HR system. Please try again later."
        except Exception as e:
            logger.error(f"Unexpected error querying HR system: {e}")
            if monitor_task:
                monitor_task.cancel()
            return f"I'm sorry, I encountered an error while looking up that information. Please try again or contact HR directly."

    @function_tool
    async def send_connection_greeting(self):
        """
        Send a personalized greeting when the user first connects.
        This function should be called automatically when the connection is established.
        """
        logger.info("🤖 Sending connection greeting...")
        
        try:
            # Get user configuration for personalized greeting
            user_config = get_user_config()
            user_name = user_config.get("user_name", "there")
            
            # Create personalized greeting messages
            greeting_options = [
                f"Hello! I'm your HR assistant. How can I help you today?",
                f"Hi! Welcome to your HR assistant. What can I do for you?",
                f"Good day! I'm here to help with any HR questions you might have.",
                f"Hello! Your HR assistant is ready to assist you. How may I help?",
                f"Hi there! I can help you with company policies, benefits, leave requests, and more. What would you like to know?"
            ]
            
            # Select a greeting (you could randomize this or use time-based selection)
            import random
            greeting = random.choice(greeting_options)
            
            logger.info(f"🤖 Connection greeting: {greeting}")
            
            # Send greeting to frontend
            session = getattr(self, '_session', None)
            if session and hasattr(session, 'room') and session.room:
                await send_text_to_frontend(
                    session=session,
                    message_type="automatic_greeting",
                    content=greeting,
                    metadata={
                        "source": "agent",
                        "greeting_type": "connection_established",
                        "user_name": user_name,
                        "timestamp": datetime.now().isoformat()
                    }
                )
                
                # Also speak the greeting directly
                try:
                    await session.say(greeting)
                    logger.info("✅ Connection greeting spoken successfully")
                except Exception as e:
                    logger.error(f"❌ Error speaking connection greeting: {e}")
            
            return greeting
            
        except Exception as e:
            logger.error(f"❌ Error sending connection greeting: {e}")
            return "Hello! I'm your HR assistant. How can I help you today?"

    @function_tool
    async def smart_conversation_handler(self, user_input: str):
        """
        Intelligently handle user input based on intent classification.
        This function determines whether to respond directly or call HR API.
        
        Args:
            user_input: The user's spoken or typed input
        """
        logger.info(f"Smart conversation handler called with: {user_input}")
        
        # Classify the intent
        intent_result = self.classify_and_respond(user_input)
        
        # If it doesn't require HR API, return the direct response
        if not intent_result["requires_hr_api"]:
            logger.info(f"Direct response for intent '{intent_result['intent']}': {intent_result['response']}")
            return intent_result["response"]
        
        # If it requires HR API, determine which function to call
        if intent_result["intent"] == "daily_briefing":
            logger.info("Calling get_daily_briefing for daily briefing request")
            return await self.get_daily_briefing()
        else:
            # For HR queries, complaints, etc.
            logger.info(f"Calling query_hr_system for intent '{intent_result['intent']}'")
            return await self.query_hr_system(user_input)


async def process_audio_with_noise_cancellation(audio_data):
    """Apply noise cancellation to audio data"""
    try:
        # Perform noise reduction
        reduced_noise_audio = nr.reduce_noise(y=audio_data, sr=16000)
        return reduced_noise_audio
    except Exception as e:
        logger.warning(f"Error in noise cancellation, using original audio: {e}")
        # Return original audio if noise cancellation fails
        return audio_data


def prewarm(proc: JobProcess):
    """Optimized prewarm function with faster VAD loading and TTS preparation"""
    logger.info("🔥 Prewarming VAD model...")
    start_time = time.time()
    
    # Use standard VAD loading
    proc.userdata["vad"] = silero.VAD.load()
    
    elapsed = time.time() - start_time
    logger.info(f"✅ VAD prewarm completed in {elapsed:.2f}s")
    
    # ✅ Pre-warm TTS for better audio quality using OpenAI SDK
    logger.info("🔥 Prewarming TTS for better audio quality...")
    try:
        client.audio.speech.create(
            model="tts-1-hd",
            voice="nova",
            input="Testing TTS warmup."
        )
        proc.userdata["tts_warmed"] = True
        logger.info("✅ TTS prewarm completed successfully")
    except Exception as e:
        logger.warning(f"TTS prewarm failed (will initialize later): {e}")
        proc.userdata["tts_warmed"] = False

    # Mark models as initialized
    if not proc.userdata.get("models_initialized"):
        proc.userdata["models_initialized"] = True


async def entrypoint(ctx: JobContext):
    # Logging setup
    # Add any other context you want in all log entries here
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    logger.info("=== Starting HR Voice Assistant (Optimized) ===")
    logger.info(f"Room: {ctx.room.name}")
    logger.info("🚀 Startup optimizations enabled for faster initialization")
    
    # Start scheduled briefing tasks (5 AM and 5 PM)
    # This will only start once, even if multiple entrypoints are called
    try:
        start_scheduled_briefing_tasks()
    except Exception as e:
        logger.warning(f"Could not start scheduled briefing tasks: {e}")
    
    # Get user configuration based on room context
    user_config = get_user_config(room_name=ctx.room.name)
    logger.info(f"Initial user config: {user_config}")
    
    # Check if briefing exists for this user, if not create one (first-time user)
    try:
        user_id = user_config.get("user_id")
        if user_id:
            # Check if user has any briefing record in database for today
            has_briefing = await user_has_briefing_in_db(user_id)
            if not has_briefing:
                # First-time user - no briefing found in table, fetch and create record
                logger.info(f"👤 First-time user detected ({user_id}) - no briefing record in database, fetching and creating...")
                # Fetch in background to create the record (will be available when user requests briefing)
                asyncio.create_task(fetch_and_cache_briefing_for_user(user_id, 'general'))
            else:
                # Existing user - briefing record exists in table, will be retrieved from there
                logger.info(f"✅ Existing user ({user_id}) - briefing record found in database table")
    except Exception as e:
        logger.warning(f"Could not check briefing for user: {e}")

    # Set up a complete voice AI pipeline with optimized OpenAI models
    logger.info("🚀 Setting up AgentSession with optimized OpenAI models...")
    start_time = time.time()
    
    try:
        # Initialize models with optimized settings for faster startup
        # Use LiveKit's OpenAI plugins (not the OpenAI SDK client directly)
        session = AgentSession(
            stt=livekit_openai.STT(model="whisper-1", language="en"),
            llm=livekit_openai.LLM(model="gpt-4o-mini"),
            tts=livekit_openai.TTS(model="tts-1-hd", voice="nova"),
            vad=ctx.proc.userdata["vad"],
        )
        
        elapsed = time.time() - start_time
        logger.info(f"✅ AgentSession created successfully in {elapsed:.2f}s")
    except Exception as e:
        logger.error(f"Failed to create AgentSession: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise  # Re-raise to let LiveKit handle the error

    # Resilient error handling during session start
    try:
        # Define the assistant variable earlier before its use
        assistant = Assistant()
        assistant._session = session  # Pass session to assistant for frontend communication

        # Start the session with optimized settings for faster initialization
        logger.info("🚀 Starting AgentSession with optimized settings...")
        start_time = time.time()

        await session.start(
            agent=assistant,
            room=ctx.room,
        )

        elapsed = time.time() - start_time
        logger.info(f"✅ AgentSession started successfully in {elapsed:.2f}s")
        logger.info("✅ TTS configured: tts-1-hd with voice 'nova'")
        logger.info("✅ AgentSession will automatically speak all LLM text responses")
    except Exception as e:
        logger.error(f"Failed to start session: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise  # Re-raise to let LiveKit handle the error properly

    # Handle false positive interruptions
    @session.on("agent_false_interruption")
    def _on_agent_false_interruption(ev):
        try:
            logger.info("Detected false positive interruption, resuming")
            session.generate_reply(instructions=ev.extra_instructions or None)
        except Exception as e:
            logger.error(f"Error handling false interruption: {e}")
            # Continue running - don't let interruption handling failures stop the agent
    
    # Send user speech to frontend as text
    async def process_audio(raw_audio, ev):
        try:
            processed_audio = await process_audio_with_noise_cancellation(raw_audio)
            stt_result = await session.stt.recognize(processed_audio)
            await send_text_to_frontend(
                session=session,
                message_type="user_speech",
                content=stt_result,
                metadata={"source": "user_speech", "timestamp": ev.timestamp}
            )
        except Exception as e:
            logger.error(f"Error in process_audio: {e}")
            # Continue running - don't let audio processing failures stop the agent

    @session.on("user_speech_committed")
    def _on_user_speech_committed(ev):
        # Truncate long text in logs to avoid scanner errors
        text_preview = ev.text[:200] + "..." if len(ev.text) > 200 else ev.text
        logger.info(f"User speech committed: {text_preview}")
        try:
            if hasattr(session, 'room') and session.room:
                raw_audio = ev.audio
                asyncio.create_task(process_audio(raw_audio, ev))
            else:
                logger.warning("Session room not available for sending user speech to frontend")
        except Exception as e:
            logger.error(f"Error during audio processing: {e}")

    # Send agent responses to frontend as text (exact match with voice)
    @session.on("agent_speech_committed")
    def _on_agent_speech_committed(ev):
        logger.info(f"🔊 Agent speech committed (spoken to user): {ev.text[:100]}...")
        try:
            if hasattr(session, 'room') and session.room:
                asyncio.create_task(send_text_to_frontend(
                    session=session,
                    message_type="agent_response",
                    content=ev.text,  # This is the exact text that was spoken
                    metadata={"source": "agent_speech", "timestamp": ev.timestamp}
                ))
            else:
                logger.warning("Session room not available for sending agent response to frontend")
        except Exception as e:
            logger.error(f"Error sending agent response to frontend: {e}")

    # Send agent speech start notification (optional - for UI indicators)
    @session.on("agent_speech_started")
    def _on_agent_speech_started(ev):
        logger.info("🔊 Agent started speaking - TTS is working!")
        # Note: We don't send generic text here since we'll send the exact text via agent_speech_committed

    # Send live transcripts as the agent speaks (real-time)
    @session.on("agent_speech_partial")
    def _on_agent_speech_partial(ev):
        # Truncate long text in logs to avoid scanner errors
        text_preview = ev.text[:200] + "..." if len(ev.text) > 200 else ev.text
        logger.info(f"Agent speech partial: {text_preview}")
        try:
            if hasattr(session, 'room') and session.room:
                asyncio.create_task(send_text_to_frontend(
                    session=session,
                    message_type="live_transcript",
                    content=ev.text,
                    metadata={"source": "agent_speech_partial", "timestamp": ev.timestamp, "is_partial": True}
                ))
            else:
                logger.warning("Session room not available for sending live transcript to frontend")
        except Exception as e:
            logger.error(f"Error sending live transcript to frontend: {e}")

    # Send user speech partial transcripts (real-time)
    @session.on("user_speech_partial")
    def _on_user_speech_partial(ev):
        # Truncate long text in logs to avoid scanner errors
        text_preview = ev.text[:200] + "..." if len(ev.text) > 200 else ev.text
        logger.info(f"User speech partial: {text_preview}")
        try:
            if hasattr(session, 'room') and session.room:
                asyncio.create_task(send_text_to_frontend(
                    session=session,
                    message_type="user_live_transcript",
                    content=ev.text,
                    metadata={"source": "user_speech_partial", "timestamp": ev.timestamp, "is_partial": True}
                ))
            else:
                logger.warning("Session room not available for sending user live transcript to frontend")
        except Exception as e:
            logger.error(f"Error sending user live transcript to frontend: {e}")

    # Handle data channel messages from frontend
    @session.on("data_received")
    def _on_data_received(ev):
        try:
            # Truncate log message to prevent very long log lines
            data_preview = ev.data[:100] + b"..." if len(ev.data) > 100 else ev.data
            logger.info(f"Data received from frontend: {data_preview}...")
            
            import json
            # Safety check: limit incoming data size to prevent scanner errors
            MAX_INCOMING_SIZE = 64 * 1024  # 64KB
            if len(ev.data) > MAX_INCOMING_SIZE:
                logger.error(f"Received data too large ({len(ev.data)} bytes), maximum is {MAX_INCOMING_SIZE} bytes")
                return
            
            data = json.loads(ev.data.decode('utf-8'))
            
            if data.get("type") == "user_configuration":
                logger.info("📥 Received user configuration from frontend")
                try:
                    update_user_config_from_frontend(data)
                    
                    # Send confirmation back to frontend
                    asyncio.create_task(send_text_to_frontend(
                        session=session,
                        message_type="user_config_confirmation",
                        content=f"User configuration received: {data.get('user_name', 'Unknown User')}",
                        metadata={"source": "agent", "config_received": True}
                    ))
                except Exception as e:
                    logger.error(f"Error processing user configuration: {e}")
            else:
                logger.info(f"📥 Received other data message: {data.get('type', 'unknown')}")
                
        except json.JSONDecodeError as e:
            logger.error(f"❌ Error parsing data message: {e}")
        except Exception as e:
            logger.error(f"❌ Error handling data message: {e}")
            # Continue running - don't let data channel errors stop the agent

    # Join the room and connect to the user
    logger.info("🔗 Connecting to room...")
    try:
        await ctx.connect()
        logger.info("✅ Connected to room successfully")
        logger.info(f"✅ Room connection established: {ctx.room.name}")
        logger.info(f"✅ Room participants: {len(ctx.room.remote_participants)} remote participant(s)")
    except Exception as e:
        logger.error(f"❌ Failed to connect to room: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise
    
    # Send startup completion message to frontend
    try:
        await send_text_to_frontend(
            session=session,
            message_type="startup_complete",
            content="HR Assistant is ready! Startup completed successfully.",
            metadata={
                "source": "agent",
                "startup_time": elapsed,
                "optimized": True,
                "timestamp": datetime.now().isoformat()
            }
        )
    except Exception as e:
        logger.warning(f"Could not send startup completion message: {e}")
    
    # Send automatic greeting after successful connection
    try:
        await send_automatic_greeting(session, assistant)
    except Exception as e:
        logger.error(f"Error sending automatic greeting: {e}")
        # Continue running - don't let greeting failures stop the agent
    
    # Trigger the daily briefing in background (non-blocking) with automatic speech
    logger.info("Session started, triggering daily briefing in background")
    try:
        # Run daily briefing in background without blocking
        asyncio.create_task(assistant.get_daily_briefing_with_speech())
        logger.info("Daily briefing started in background")
    except Exception as e:
        logger.error(f"Error starting daily briefing: {e}")
        logger.error(f"Error type: {type(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
    
    # Keep agent alive and responsive
    logger.info("🔄 Agent configured to stay active - no idle timeout")
    
    # Keep the agent running by waiting for room events
    try:
        # Wait for room to be disconnected or other events
        connection_check_count = 0
        while True:
            await asyncio.sleep(1)
            connection_check_count += 1
            
            # Log connection health every 30 seconds
            if connection_check_count % 30 == 0:
                if hasattr(session, 'room') and session.room:
                    logger.info(f"✅ Connection health check: Room '{session.room.name}' is active")
                else:
                    logger.warning("⚠️ Connection health check: Session room not available")
            
            # Check if session has room attribute and if it's connected
            if hasattr(session, 'room') and session.room and hasattr(session.room, 'is_connected'):
                if not session.room.is_connected:
                    logger.warning("⚠️ Room disconnected, agent session ending")
                    break
            else:
                # If no room attribute, just keep running
                logger.debug("Session room not available, continuing...")
    except asyncio.CancelledError:
        logger.info("Agent session cancelled (normal shutdown)")
        raise
    except Exception as e:
        logger.error(f"❌ Error in main loop: {e}")
        import traceback
        # Truncate long tracebacks to avoid scanner errors
        tb_str = traceback.format_exc()
        if len(tb_str) > 1000:
            logger.error(f"Traceback: {tb_str[:1000]}... (truncated)")
        else:
            logger.error(f"Traceback: {tb_str}")
        # Continue running instead of raising - agent should stay alive
        logger.info("🔄 Continuing agent operation despite error...")
        # Wait a bit before continuing to avoid tight error loops
        await asyncio.sleep(1)


# Health check app for deployment
health_app = FastAPI()

@health_app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "HR Voice Assistant",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }

@health_app.get("/")
async def root():
    return {"message": "HR Voice Assistant is running"}

async def monitor_db_pool_health():
    """Monitor database connection pool health"""
    try:
        pool = await get_db_pool()
        
        # Get pool statistics
        pool_stats = {
            "size": pool.get_size(),
            "idle": pool.get_idle_size(),
            "min_size": pool.get_min_size(),
            "max_size": pool.get_max_size()
        }
        
        # Check for issues
        if pool_stats["idle"] == 0 and pool_stats["size"] == pool_stats["max_size"]:
            await error_monitor.log_error(
                error_type="DB_POOL_EXHAUSTED",
                message="Database connection pool exhausted",
                severity=ErrorSeverity.HIGH,
                context=pool_stats
            )
        
        if pool_stats["size"] < pool_stats["min_size"]:
            await error_monitor.log_error(
                error_type="DB_POOL_BELOW_MIN",
                message="Database connection pool below minimum size",
                severity=ErrorSeverity.MEDIUM,
                context=pool_stats
            )
        
        # Health check
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
            
    except Exception as e:
        await error_monitor.log_error(
            error_type="DB_POOL_HEALTH_CHECK_FAILED",
            message="Database connection pool health check failed",
            severity=ErrorSeverity.CRITICAL,
            exception=e
        )

def start_health_server():
    """Start the health check server in a separate thread"""
    uvicorn.run(health_app, host="0.0.0.0", port=8080, log_level="info")

if __name__ == "__main__":
    # Ensure briefing table exists on startup
    try:
        asyncio.run(ensure_briefing_table_exists())
    except Exception as e:
        logger.warning(f"Could not ensure briefing table exists on startup: {e}")
    
    # Start health server in background
    import threading
    health_thread = threading.Thread(target=start_health_server, daemon=True)
    health_thread.start()
    
    # Start the main agent
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, prewarm_fnc=prewarm))