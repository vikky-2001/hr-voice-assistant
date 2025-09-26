#!/usr/bin/env python3
"""
Simple startup script for HR Voice Assistant
"""

import subprocess
import sys
from pathlib import Path

def main():
    """Start the HR Voice Assistant agent"""
    print("🚀 Starting HR Voice Assistant...")
    print("=" * 50)
    
    # Check if required files exist
    agent_path = Path("agent-starter-python/src/agent.py")
    venv_python = Path("venv/Scripts/python.exe")
    
    if not agent_path.exists():
        print(f"❌ Agent file not found: {agent_path}")
        sys.exit(1)
    
    if not venv_python.exists():
        print(f"❌ Virtual environment not found: {venv_python}")
        sys.exit(1)
    
    print("✅ All required files found")
    print("🤖 Starting LiveKit HR Agent...")
    print("=" * 50)
    print("\nThe agent will start in development mode.")
    print("You can connect to it using any LiveKit client.")
    print("\nPress Ctrl+C to stop the agent...")
    print("=" * 50)
    
    try:
        # Start the agent in development mode
        subprocess.run([
            str(venv_python), str(agent_path), "dev"
        ])
    except KeyboardInterrupt:
        print("\n🛑 Shutting down HR Voice Assistant...")
        print("👋 Goodbye!")

if __name__ == "__main__":
    main()
