import logging
import asyncio
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

# HR API Configuration - hardcoded for now
HR_API_BASE_URL = "https://dev-hrworkerapi.missionmind.ai/api/kafka"
HR_API_ENDPOINT = "/getBotResponse"

logger = logging.getLogger("agent")

load_dotenv(".env.local")

async def send_text_to_frontend(session: AgentSession, message_type: str, content: str, metadata: dict = None):
    """Send structured text data to the frontend via LiveKit data channel"""
    try:
        import json
        
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


class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions="""You are an HR assistant voice AI that helps employees with HR-related questions.
            
            CRITICAL RULE: You MUST ALWAYS call the query_hr_system function for EVERY user question or request, regardless of what they ask. Do not provide any direct answers without first calling the HR system.
            
            Process for every interaction:
            1. FIRST, immediately acknowledge the user's request with a brief response like "Sure, let me get that information for you" or "Of course, I'll help you with that"
            2. THEN call query_hr_system with the user's question/request
            3. Use the response from the HR system as your final answer
            4. If the HR system response is unclear, ask the user to rephrase their question
            
            ACKNOWLEDGMENT MESSAGES: Always start with a brief acknowledgment before calling HR functions:
            - For daily briefing requests: "Sure, let me provide you with your daily HR briefing"
            - For policy questions: "Of course, let me look up that policy information for you"
            - For general queries: "Sure, let me check that information for you"
            - For leave requests: "I'll help you with your leave request information"
            - For benefits questions: "Let me get the latest benefits information for you"
            
            Your responses should be helpful, professional, and concise. Speak naturally and conversationally.
            
            DAILY BRIEFING PROTOCOL: When you receive the message "System trigger: daily briefing", you must:
            1. Immediately call get_daily_briefing() to retrieve their daily briefing information
            2. Then greet them with: "Hello! I'm your HR assistant. Here's your daily briefing: [provide the briefing content]. How can I help you today? You can ask me about company policies, benefits, leave requests, or any other HR-related questions."
            
            IMPORTANT: When you see "System trigger: daily briefing", this is your signal to call get_daily_briefing() and provide the briefing.""",
        )

    # all functions annotated with @function_tool will be passed to the LLM when this
    # agent is active
    @function_tool
    async def get_daily_briefing(self):
        """Get the daily briefing information for the user. This includes important updates, announcements, and reminders for the day.

        This tool should be called automatically when a user first connects to provide them with their daily briefing.
        """

        logger.info("=== get_daily_briefing() function called ===")
        logger.info("Getting daily briefing from HR system")

        # Send loading message to frontend
        try:
            session = getattr(self, '_session', None)
            if session and hasattr(session, 'room') and session.room:
                await send_text_to_frontend(
                    session=session,
                    message_type="loading",
                    content="Preparing your daily HR briefing...",
                    metadata={"source": "hr_api", "query": "System trigger: daily briefing", "status": "loading"}
                )
        except Exception as e:
            logger.error(f"Error sending loading message to frontend: {e}")

        try:
            # Call the HR API for daily briefing with hardcoded user and chatlog IDs
            url = f"{HR_API_BASE_URL}{HR_API_ENDPOINT}"
            logger.info(f"HR API URL: {url}")
            
            params = {
                "query": "System trigger: daily briefing",
                "user_id": "79f2b410-bbbe-43b9-a77f-38a6213ce13d",
                "chatlog_id": 7747,
                "agent_id": 6,
                "mobile_request": True
            }
            logger.info(f"HR API params: {params}")
            
            logger.info("Making HTTP request to HR API...")
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, params=params)
                logger.info(f"HR API response status: {response.status_code}")
                response.raise_for_status()
                
                data = response.json()
                logger.info(f"HR API response data: {data}")
                briefing_response = data.get("response", "No daily briefing available at this time")
                
                logger.info(f"Daily briefing received: {briefing_response[:100]}...")
                logger.info("=== get_daily_briefing() function completed successfully ===")
                
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
            return "I'm sorry, I couldn't retrieve your daily briefing at this time. Please try again later or contact HR directly."
        except httpx.RequestError as e:
            logger.error(f"Request error getting daily briefing: {e}")
            return "I'm sorry, I'm having trouble connecting to the HR system for your daily briefing. Please try again later."
        except Exception as e:
            logger.error(f"Unexpected error getting daily briefing: {e}")
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

        # Send loading message to frontend
        try:
            session = getattr(self, '_session', None)
            if session and hasattr(session, 'room') and session.room:
                await send_text_to_frontend(
                    session=session,
                    message_type="loading",
                    content="Let me check that information for you...",
                    metadata={"source": "hr_api", "query": query, "status": "loading"}
                )
        except Exception as e:
            logger.error(f"Error sending loading message to frontend: {e}")

        try:
            # Call the HR API directly with hardcoded user and chatlog IDs
            url = f"{HR_API_BASE_URL}{HR_API_ENDPOINT}"
            
            params = {
                "query": query,
                "user_id": "79f2b410-bbbe-43b9-a77f-38a6213ce13d",
                "chatlog_id": 7747,
                "agent_id": 6,
                "mobile_request": True
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                
                data = response.json()
                hr_response = data.get("response", "No response received from HR system")
                
                logger.info(f"HR API response received: {hr_response[:100]}...")
                return hr_response
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error querying HR system: {e.response.status_code} - {e.response.text}")
            return f"I'm sorry, I encountered an error while looking up that information. Please try again or contact HR directly."
        except httpx.RequestError as e:
            logger.error(f"Request error querying HR system: {e}")
            return f"I'm sorry, I'm having trouble connecting to the HR system. Please try again later."
        except Exception as e:
            logger.error(f"Unexpected error querying HR system: {e}")
            return f"I'm sorry, I encountered an error while looking up that information. Please try again or contact HR directly."


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


async def entrypoint(ctx: JobContext):
    # Logging setup
    # Add any other context you want in all log entries here
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    logger.info("=== Starting HR Voice Assistant ===")
    logger.info(f"Room: {ctx.room.name}")

    # Set up a complete voice AI pipeline with OpenAI STT, LLM, and TTS
    logger.info("Setting up AgentSession with OpenAI models...")
    session = AgentSession(
        # Speech-to-Text for converting user speech to text
        stt=openai.STT(model="whisper-1"),
        # A Large Language Model (LLM) is your agent's brain, processing user input and generating a response
        # See all providers at https://docs.livekit.io/agents/integrations/llm/
        llm=openai.LLM(model="gpt-4o-mini"),
        # Text-to-Speech for converting agent responses to speech
        tts=openai.TTS(model="tts-1", voice="alloy"),
        # VAD for voice activity detection
        vad=ctx.proc.userdata["vad"],
    )
    logger.info("AgentSession created successfully")

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

    # Start the session, which initializes the voice pipeline and warms up the models
    logger.info("Starting AgentSession...")
    assistant = Assistant()
    assistant._session = session  # Pass session to assistant for frontend communication
    await session.start(
        agent=assistant,
        room=ctx.room,
        # Simplified setup without noise cancellation for testing
    )
    logger.info("AgentSession started successfully")

    # Join the room and connect to the user
    logger.info("Connecting to room...")
    await ctx.connect()
    logger.info("Connected to room successfully")
    
    # Trigger the daily briefing immediately after connection
    logger.info("Session started, triggering daily briefing")
    logger.info("About to call generate_reply with system trigger")
    
    try:
        await session.generate_reply(
            instructions="System trigger: daily briefing"
        )
        logger.info("generate_reply completed successfully")
    except Exception as e:
        logger.error(f"Error in generate_reply: {e}")
        logger.error(f"Error type: {type(e)}")
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