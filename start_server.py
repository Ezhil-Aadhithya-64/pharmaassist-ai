#!/usr/bin/env python
"""
Quick start script for PharmaAssist AI backend.
Usage: python start_server.py
"""
import sys
import os

def check_setup():
    """Check if basic setup is complete."""
    print("Checking setup...")
    
    # Check if .env exists
    if not os.path.exists(".env"):
        print("❌ .env file not found!")
        print("Please create .env file. See SETUP_GUIDE.md for instructions.")
        return False
    
    # Check if GROQ_API_KEY is set
    from backend.core import config
    if not config.GROQ_API_KEY or config.GROQ_API_KEY == "your_groq_api_key_here":
        print("❌ GROQ_API_KEY not configured!")
        print("\nPlease update .env file with your Groq API key:")
        print("1. Get key from: https://console.groq.com")
        print("2. Update .env: GROQ_API_KEY=gsk_your_actual_key")
        print("\nSee SETUP_GUIDE.md for detailed instructions.")
        return False
    
    print("✅ Setup looks good!")
    return True

def start_server():
    """Start the FastAPI server."""
    if not check_setup():
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("Starting PharmaAssist AI Backend Server")
    print("=" * 60)
    print("\nServer will be available at:")
    print("  - API: http://localhost:8000")
    print("  - Docs: http://localhost:8000/docs")
    print("  - Health: http://localhost:8000/health")
    print("\nPress Ctrl+C to stop the server")
    print("=" * 60 + "\n")
    
    import uvicorn
    uvicorn.run(
        "backend.api.routes:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

if __name__ == "__main__":
    start_server()
