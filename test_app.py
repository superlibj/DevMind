#!/usr/bin/env python3
"""
Simple test script to run the AI Agent web interface.
"""
import os
import sys

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set environment variables
os.environ["PYTHONPATH"] = os.path.dirname(os.path.abspath(__file__))

from fastapi import FastAPI
from fastapi.responses import JSONResponse
import uvicorn

# Create a simple test app
app = FastAPI(
    title="AI Code Development Agent",
    description="AI-powered development assistant (Test Mode)",
    version="1.0.0",
)

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "AI Code Development Agent",
        "version": "1.0.0",
        "status": "running",
        "mode": "test"
    }

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": "2024-04-18T00:00:00Z"
    }

@app.post("/api/v1/chat")
async def chat(request: dict):
    """Simple chat endpoint."""
    message = request.get("message", "")
    return {
        "response": f"Hello! You said: {message}. This is a test response from the AI agent.",
        "session_id": "test_session_123"
    }

if __name__ == "__main__":
    print("Starting AI Code Development Agent in test mode...")
    print("Available endpoints:")
    print("  - GET  /          : Root information")
    print("  - GET  /health    : Health check")
    print("  - POST /api/v1/chat : Simple chat test")
    print()

    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
        log_level="info"
    )