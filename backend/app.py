"""
ChatGPT Clone Backend - Phase 1: Simple Chat
FastAPI application with OpenAI streaming integration
"""

import os
import json
from typing import AsyncGenerator
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import openai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(title="ChatGPT Clone API", version="1.0.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://*.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize OpenAI client
openai_client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Pydantic models
class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    messages: list[ChatMessage] = []

class HealthResponse(BaseModel):
    status: str
    message: str

# Health check endpoint
@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="ok",
        message="ChatGPT Clone API is running"
    )

# Debug endpoint to check environment variables
@app.get("/api/debug")
async def debug():
    """Debug endpoint to check environment variables"""
    api_key_status = "SET" if os.getenv("OPENAI_API_KEY") else "NOT SET"
    return {
        "status": "debug",
        "openai_api_key": api_key_status,
        "environment": "development" if os.getenv("ENVIRONMENT") != "production" else "production"
    }

# Main chat endpoint with streaming
@app.post("/api/chat")
async def chat_stream(request: ChatRequest):
    """Streaming chat endpoint"""
    
    # Check if API key is set
    if not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(
            status_code=500,
            detail="OpenAI API key not configured. Please set OPENAI_API_KEY environment variable."
        )
    
    try:
        # Prepare messages for OpenAI
        messages = []
        
        # Add conversation history
        for msg in request.messages:
            messages.append({
                "role": msg.role,
                "content": msg.content
            })
        
        # Add current user message
        messages.append({
            "role": "user",
            "content": request.message
        })
        
        # Create streaming response from OpenAI
        def generate_response() -> AsyncGenerator[str, None]:
            try:
                stream = openai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=messages,
                    stream=True,
                    temperature=0.7,
                    max_tokens=1000
                )
                
                for chunk in stream:
                    if chunk.choices[0].delta.content is not None:
                        content = chunk.choices[0].delta.content
                        # Send as Server-Sent Events format
                        yield f"data: {json.dumps({'content': content, 'done': False})}\n\n"
                
                # Send completion signal
                yield f"data: {json.dumps({'content': '', 'done': True})}\n\n"
                
            except Exception as e:
                error_msg = f"Error in OpenAI API: {str(e)}"
                yield f"data: {json.dumps({'error': error_msg, 'done': True})}\n\n"
        
        return StreamingResponse(
            generate_response(),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/plain; charset=utf-8"
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "ChatGPT Clone API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "chat": "/api/chat",
            "health": "/api/health",
            "debug": "/api/debug"
        }
    }

# Run the app
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
