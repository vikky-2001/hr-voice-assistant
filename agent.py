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
from livekit.plugins import openai, silero
import httpx
from fastapi import FastAPI
import uvicorn

# HR API Configuration - hardcoded for now
HR_API_BASE_URL = "https://dev-hrworkerapi.missionmind.ai/api/kafka"
HR_API_ENDPOINT = "/getBotResponse"

logger = logging.getLogger("agent")

load_dotenv(".env.local")


class Assistant(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions="""You are an HR assistant voice AI that helps employees with HR-related questions.
            You can answer questions about company policies, benefits, leave requests, payroll, and other HR matters.
            When users ask HR questions, use the query_hr_system function to get accurate, up-to-date information from the HR system.
            Your responses should be helpful, professional, and concise. Speak naturally and conversationally.
            If you don't have specific information, let the user know you're looking it up for them.""",
        )

    # all functions annotated with @function_tool will be passed to the LLM when this
    # agent is active
    @function_tool
    async def query_hr_system(self, query: str):
        """Use this tool to query the HR system for information about company policies, benefits, leave requests, payroll, and other HR matters.

        This tool connects to the HR API to get accurate, up-to-date information from the HR system.

        Args:
            query: The HR-related question or request from the user
        """

        logger.info(f"Querying HR system: {query}")

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

    # Set up a complete voice AI pipeline with OpenAI STT, LLM, and TTS
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

    # sometimes background noise could interrupt the agent session, these are considered false positive interruptions
    # when it's detected, you may resume the agent's speech
    @session.on("agent_false_interruption")
    def _on_agent_false_interruption(ev):
        logger.info("false positive interruption, resuming")
        session.generate_reply(instructions=ev.extra_instructions or None)

    # Start the session, which initializes the voice pipeline and warms up the models
    await session.start(
        agent=Assistant(),
        room=ctx.room,
        # Simplified setup without noise cancellation for testing
    )

    # Join the room and connect to the user
    await ctx.connect()
    
    # Send a welcome message when the session starts
    welcome_message = "Hello! I'm your HR assistant. How can I help you today? You can ask me about company policies, benefits, leave requests, or any other HR-related questions."
    logger.info("Sending welcome message to user")
    await session.say(welcome_message, allow_interruptions=True)


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