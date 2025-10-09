import logging
import asyncio
import time
from datetime import datetime

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
from livekit.plugins import openai, silero
import httpx
from fastapi import FastAPI
import uvicorn

# HR API Configuration
HR_API_BASE_URL = "https://dev-hrworkerapi.missionmind.ai/api/kafka"
HR_API_ENDPOINT = "/getBotResponse"

# Dynamic user configuration - can be overridden by environment variables
DEFAULT_USER_ID = "79f2b410-bbbe-43b9-a77f-38a6213ce13d"  # Fallback user
DEFAULT_CHATLOG_ID = 7747  # Fallback chatlog
DEFAULT_AGENT_ID = 6  # Fallback agent

logger = logging.getLogger("agent")

load_dotenv(".env.local")

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
                "keywords": ["policy", "benefits", "leave", "vacation", "sick", "payroll", "salary", "insurance", "retirement"],
                "patterns": [r"policy", r"benefits", r"leave", r"vacation", r"sick", r"payroll", r"salary", r"insurance", r"retirement"],
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
        logger.error(f"❌ Invalid config data: {config_data}")

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
    """Send structured text data to the frontend via LiveKit data channel"""
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
        
        data = {
            "type": message_type,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        
        # Send as data message to all participants
        await session.room.local_participant.publish_data(
            data=json.dumps(data).encode('utf-8'),
            topic="chat"
        )
        
        logger.info(f"Sent {message_type} to frontend: {content[:100]}...")
        
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

async def send_automatic_greeting(session: AgentSession, assistant: 'Assistant'):
    """Send automatic greeting when connection is established"""
    try:
        import asyncio
        
        # Wait a moment for the connection to fully establish
        await asyncio.sleep(1)
        
        # Get user configuration for personalized greeting
        user_config = get_user_config()
        user_name = user_config.get("user_name", "there")
        
        # Create personalized greeting messages
        greeting_options = [
            f"Hello {user_name}! I'm your HR assistant. How can I help you today?",
            f"Hi {user_name}! Welcome to your HR assistant. What can I do for you?",
            f"Good day {user_name}! I'm here to help with any HR questions you might have.",
            f"Hello {user_name}! Your HR assistant is ready to assist you. How may I help?",
            f"Hi there {user_name}! I can help you with company policies, benefits, leave requests, and more. What would you like to know?"
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
        
        # Note: The greeting will be spoken by the LLM when it processes the user input
        # We don't need to call assistant.say() here as it's not available in this context
        
        logger.info("✅ Automatic greeting sent successfully")
        
    except Exception as e:
        logger.error(f"❌ Error sending automatic greeting: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")


class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions="""You are an HR assistant voice AI that helps employees with HR-related questions.
            
            AUTOMATIC GREETING: When a user first connects, you should immediately call send_connection_greeting() to welcome them proactively. This creates a welcoming experience before they even speak.
            
            SMART CONVERSATION FLOW: You now have intelligent intent classification and conversation memory for optimal user experience.
            
            PRIMARY RULE: ALWAYS call smart_conversation_handler(user_input) for EVERY user interaction. This function will:
            1. Classify the user's intent (greeting, HR query, complaint, etc.)
            2. Determine if HR API call is needed or direct response is sufficient
            3. Route to appropriate function automatically
            4. Remember conversation context for follow-up questions
            
            CONVERSATION FLOW:
            1. User connects → You call send_connection_greeting() (automatic welcome)
            2. User speaks → You call smart_conversation_handler(user_input)
            3. Function classifies intent and determines response strategy
            4. For greetings/farewells/help → Direct response (fast)
            5. For HR queries/complaints → HR API call (comprehensive)
            6. Response is spoken back to user
            
            CONTEXT AWARENESS:
            - The system remembers recent conversation topics
            - For follow-up questions like "What about sick leave?" it refers to previous context
            - Conversation memory helps provide more personalized responses
            
            DAILY BRIEFING PROTOCOL: When you receive the message "System trigger: daily briefing", you must:
            1. Immediately call get_daily_briefing() to retrieve their daily briefing information
            2. Then greet them with: "Hello! I'm your HR assistant. Here's your daily briefing: [provide the briefing content]. How can I help you today? You can ask me about company policies, benefits, leave requests, or any other HR-related questions."
            
            IMPORTANT: 
            - Call send_connection_greeting() when user first connects (proactive greeting)
            - Use smart_conversation_handler() for all user interactions
            - When you see "System trigger: daily briefing", call get_daily_briefing() directly
            - Always speak naturally and conversationally
            - The system will automatically optimize response speed and accuracy""",
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
        
        # Keep only last 10 interactions to manage memory size
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

    # all functions annotated with @function_tool will be passed to the LLM when this
    # agent is active
    @function_tool
    async def get_daily_briefing(self):
        """Get the daily briefing information for the user. This includes important updates, announcements, and reminders for the day.

        This tool should be called automatically when a user first connects to provide them with their daily briefing.
        """

        logger.info("=== get_daily_briefing() function called ===")
        logger.info("Getting daily briefing from HR system")

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
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, params=params)
                logger.info(f"HR API response status: {response.status_code}")
                response.raise_for_status()
                
                data = response.json()
                logger.info(f"HR API response data: {data}")
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
                
                return briefing_response
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error getting daily briefing: {e.response.status_code} - {e.response.text}")
            if monitor_task:
                monitor_task.cancel()
            return "I'm sorry, I couldn't retrieve your daily briefing at this time. Please try again later or contact HR directly."
        except httpx.RequestError as e:
            logger.error(f"Request error getting daily briefing: {e}")
            if monitor_task:
                monitor_task.cancel()
            return "I'm sorry, I'm having trouble connecting to the HR system for your daily briefing. Please try again later."
        except Exception as e:
            logger.error(f"Unexpected error getting daily briefing: {e}")
            if monitor_task:
                monitor_task.cancel()
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return "I'm sorry, I encountered an error while retrieving your daily briefing. Please try again or contact HR directly."

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
            
            # Call the HR API directly with dynamic user and chatlog IDs
            url = f"{HR_API_BASE_URL}{HR_API_ENDPOINT}"
            
            params = {
                "query": query,
                "user_id": user_config["user_id"],
                "chatlog_id": user_config["chatlog_id"],
                "agent_id": user_config["agent_id"],
                "mobile_request": True
            }
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                
                data = response.json()
                hr_response = data.get("response", "No response received from HR system")
                
                logger.info(f"HR API response received: {hr_response[:100]}...")
                
                # Stop intermediate messaging monitoring
                if monitor_task:
                    monitor_task.cancel()
                    logger.info("Stopped intermediate messaging monitoring")
                
                return hr_response
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error querying HR system: {e.response.status_code} - {e.response.text}")
            if monitor_task:
                monitor_task.cancel()
            return f"I'm sorry, I encountered an error while looking up that information. Please try again or contact HR directly."
        except httpx.RequestError as e:
            logger.error(f"Request error querying HR system: {e}")
            if monitor_task:
                monitor_task.cancel()
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
                f"Hello {user_name}! I'm your HR assistant. How can I help you today?",
                f"Hi {user_name}! Welcome to your HR assistant. What can I do for you?",
                f"Good day {user_name}! I'm here to help with any HR questions you might have.",
                f"Hello {user_name}! Your HR assistant is ready to assist you. How may I help?",
                f"Hi there {user_name}! I can help you with company policies, benefits, leave requests, and more. What would you like to know?"
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


def prewarm(proc: JobProcess):
    """Optimized prewarm function with faster VAD loading"""
    logger.info("🔥 Prewarming VAD model...")
    start_time = time.time()
    
    # Use standard VAD loading
    proc.userdata["vad"] = silero.VAD.load()
    
    elapsed = time.time() - start_time
    logger.info(f"✅ VAD prewarm completed in {elapsed:.2f}s")


async def entrypoint(ctx: JobContext):
    # Logging setup
    # Add any other context you want in all log entries here
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    logger.info("=== Starting HR Voice Assistant (Optimized) ===")
    logger.info(f"Room: {ctx.room.name}")
    logger.info("🚀 Startup optimizations enabled for faster initialization")
    
    # Get user configuration based on room context
    user_config = get_user_config(room_name=ctx.room.name)
    logger.info(f"Initial user config: {user_config}")

    # Set up a complete voice AI pipeline with optimized OpenAI models
    logger.info("🚀 Setting up AgentSession with optimized OpenAI models...")
    start_time = time.time()
    
    # Initialize models with optimized settings for faster startup
    session = AgentSession(
        # Speech-to-Text with optimized settings
        stt=openai.STT(
            model="whisper-1",
            # Use faster processing mode
            language="en"  # Specify language for faster processing
        ),
        # LLM with optimized settings
        llm=openai.LLM(
            model="gpt-4o-mini"
        ),
        # Text-to-Speech with optimized settings
        tts=openai.TTS(
            model="tts-1",
            voice="alloy"
        ),
        # VAD for voice activity detection (preloaded in prewarm)
        vad=ctx.proc.userdata["vad"],
    )
    
    elapsed = time.time() - start_time
    logger.info(f"✅ AgentSession created successfully in {elapsed:.2f}s")

    # sometimes background noise could interrupt the agent session, these are considered false positive interruptions
    # when it's detected, you may resume the agent's speech
    @session.on("agent_false_interruption")
    def _on_agent_false_interruption(ev):
        logger.info("false positive interruption, resuming")
        session.generate_reply(instructions=ev.extra_instructions or None)
    
    # Send user speech to frontend as text
    @session.on("user_speech_committed")
    def _on_user_speech_committed(ev):
        logger.info(f"User speech committed: {ev.text}")
        try:
            if hasattr(session, 'room') and session.room:
                asyncio.create_task(send_text_to_frontend(
                    session=session,
                    message_type="user_speech",
                    content=ev.text,
                    metadata={"source": "user_speech", "timestamp": ev.timestamp}
                ))
            else:
                logger.warning("Session room not available for sending user speech to frontend")
        except Exception as e:
            logger.error(f"Error sending user speech to frontend: {e}")

    # Send agent responses to frontend as text (exact match with voice)
    @session.on("agent_speech_committed")
    def _on_agent_speech_committed(ev):
        logger.info(f"Agent speech committed: {ev.text}")
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
        logger.info("Agent started speaking")
        # Note: We don't send generic text here since we'll send the exact text via agent_speech_committed

    # Send live transcripts as the agent speaks (real-time)
    @session.on("agent_speech_partial")
    def _on_agent_speech_partial(ev):
        logger.info(f"Agent speech partial: {ev.text}")
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
        logger.info(f"User speech partial: {ev.text}")
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
        logger.info(f"Data received from frontend: {ev.data[:100]}...")
        try:
            import json
            data = json.loads(ev.data.decode('utf-8'))
            
            if data.get("type") == "user_configuration":
                logger.info("📥 Received user configuration from frontend")
                update_user_config_from_frontend(data)
                
                # Send confirmation back to frontend
                asyncio.create_task(send_text_to_frontend(
                    session=session,
                    message_type="user_config_confirmation",
                    content=f"User configuration received: {data.get('user_name', 'Unknown User')}",
                    metadata={"source": "agent", "config_received": True}
                ))
            else:
                logger.info(f"📥 Received other data message: {data.get('type', 'unknown')}")
                
        except json.JSONDecodeError as e:
            logger.error(f"❌ Error parsing data message: {e}")
        except Exception as e:
            logger.error(f"❌ Error handling data message: {e}")

    # Start the session with optimized settings for faster initialization
    logger.info("🚀 Starting AgentSession with optimized settings...")
    start_time = time.time()
    
    assistant = Assistant()
    assistant._session = session  # Pass session to assistant for frontend communication
    
    await session.start(
        agent=assistant,
        room=ctx.room,
    )
    
    elapsed = time.time() - start_time
    logger.info(f"✅ AgentSession started successfully in {elapsed:.2f}s")

    # Join the room and connect to the user
    logger.info("🔗 Connecting to room...")
    await ctx.connect()
    logger.info("✅ Connected to room successfully")
    
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
    await send_automatic_greeting(session, assistant)
    
    # Trigger the daily briefing by calling the assistant method (with timeout)
    logger.info("Session started, triggering daily briefing")
    try:
        # Call the daily briefing method on the assistant with timeout
        await asyncio.wait_for(assistant.get_daily_briefing(), timeout=15.0)
        logger.info("Daily briefing completed successfully")
    except asyncio.TimeoutError:
        logger.warning("Daily briefing timed out after 15 seconds - continuing without it")
    except Exception as e:
        logger.error(f"Error in daily briefing: {e}")
        logger.error(f"Error type: {type(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
    
    # Keep agent alive and responsive
    logger.info("🔄 Agent configured to stay active - no idle timeout")
    
    # Keep the agent running by waiting for room events
    try:
        # Wait for room to be disconnected or other events
        while True:
            await asyncio.sleep(1)
            if not session.room or not session.room.is_connected:
                logger.info("Room disconnected, agent session ending")
                break
    except Exception as e:
        logger.error(f"Session ended with error: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")


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

def start_health_server():
    """Start the health check server in a separate thread"""
    uvicorn.run(health_app, host="0.0.0.0", port=8080, log_level="info")

if __name__ == "__main__":
    # Start health server in background
    import threading
    health_thread = threading.Thread(target=start_health_server, daemon=True)
    health_thread.start()
    
    # Start the main agent
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, prewarm_fnc=prewarm))