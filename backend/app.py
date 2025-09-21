"""
ChatGPT Clone Backend - Phase 2: PDF Upload & Query
FastAPI application with OpenAI streaming integration and PDF processing
"""

import os
import json
import tempfile
from typing import AsyncGenerator, Dict, Any
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import openai
from dotenv import load_dotenv
import PyPDF2
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.schema import Document

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

# Initialize embeddings
embeddings = OpenAIEmbeddings(openai_api_key=os.getenv("OPENAI_API_KEY"))

# Global vector store for PDF content
pdf_vector_store: Dict[str, FAISS] = {}

# Text splitter for chunking PDF content
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    length_function=len,
)

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

class PDFUploadResponse(BaseModel):
    status: str
    message: str
    filename: str
    pages: int
    chunks: int

class PDFQueryRequest(BaseModel):
    question: str
    filename: str

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

# PDF upload endpoint
@app.post("/api/upload-pdf", response_model=PDFUploadResponse)
async def upload_pdf(file: UploadFile = File(...)):
    """Upload and process PDF file"""
    
    # Check if API key is set
    if not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(
            status_code=500,
            detail="OpenAI API key not configured. Please set OPENAI_API_KEY environment variable."
        )
    
    # Validate file type
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are allowed"
        )
    
    try:
        # Read PDF content
        pdf_content = await file.read()
        
        # Extract text from PDF
        pdf_text = ""
        pages = 0
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            tmp_file.write(pdf_content)
            tmp_file.flush()
            
            with open(tmp_file.name, 'rb') as pdf_file:
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                pages = len(pdf_reader.pages)
                
                for page in pdf_reader.pages:
                    pdf_text += page.extract_text() + "\n"
        
        # Clean up temporary file
        os.unlink(tmp_file.name)
        
        if not pdf_text.strip():
            raise HTTPException(
                status_code=400,
                detail="No text content found in PDF"
            )
        
        # Split text into chunks
        texts = text_splitter.split_text(pdf_text)
        documents = [Document(page_content=text) for text in texts]
        
        # Create vector store
        vector_store = FAISS.from_documents(documents, embeddings)
        
        # Store vector store with filename as key
        pdf_vector_store[file.filename] = vector_store
        
        return PDFUploadResponse(
            status="success",
            message=f"PDF processed successfully",
            filename=file.filename,
            pages=pages,
            chunks=len(texts)
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing PDF: {str(e)}"
        )

# PDF query endpoint with streaming
@app.post("/api/query-pdf")
async def query_pdf_stream(request: PDFQueryRequest):
    """Query PDF content with streaming response"""
    
    # Check if API key is set
    if not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(
            status_code=500,
            detail="OpenAI API key not configured. Please set OPENAI_API_KEY environment variable."
        )
    
    # Check if PDF is uploaded
    if request.filename not in pdf_vector_store:
        raise HTTPException(
            status_code=404,
            detail=f"PDF '{request.filename}' not found. Please upload it first."
        )
    
    try:
        # Get vector store for this PDF
        vector_store = pdf_vector_store[request.filename]
        
        # Search for relevant chunks
        docs = vector_store.similarity_search(request.question, k=3)
        
        # Prepare context from relevant chunks
        context = "\n\n".join([doc.page_content for doc in docs])
        
        # Create streaming response
        def generate_response() -> AsyncGenerator[str, None]:
            try:
                # Check if we have relevant context
                if not context.strip():
                    # No relevant content found, use ChatGPT directly
                    messages = [
                        {
                            "role": "user",
                            "content": f"Question: {request.question}\n\nNote: This question is not related to any uploaded PDF document."
                        }
                    ]
                    
                    stream = openai_client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=messages,
                        stream=True,
                        temperature=0.7,
                        max_tokens=1000
                    )
                    
                    # Send note that this is from ChatGPT
                    yield f"data: {json.dumps({'content': '[Note: This answer is from ChatGPT, not from your PDF]\n\n', 'done': False})}\n\n"
                    
                    for chunk in stream:
                        if chunk.choices[0].delta.content is not None:
                            content = chunk.choices[0].delta.content
                            yield f"data: {json.dumps({'content': content, 'done': False})}\n\n"
                    
                    yield f"data: {json.dumps({'content': '', 'done': True})}\n\n"
                    
                else:
                    # We have relevant context, try PDF first, then fallback if needed
                    messages = [
                        {
                            "role": "system",
                            "content": "You are a helpful assistant that answers questions based on the provided context from a PDF document. If the context doesn't contain enough information to answer the question, respond with exactly: 'PDF_INSUFFICIENT_INFO' and then provide what information you can from the PDF."
                        },
                        {
                            "role": "user",
                            "content": f"Context from PDF:\n{context}\n\nQuestion: {request.question}"
                        }
                    ]
                    
                    # First attempt with PDF context
                    response = openai_client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=messages,
                        temperature=0.7,
                        max_tokens=1000
                    )
                    
                    pdf_response = response.choices[0].message.content
                    
                    # Check if PDF response indicates insufficient info
                    if "PDF_INSUFFICIENT_INFO" in pdf_response:
                        # Clean up the response
                        clean_response = pdf_response.replace("PDF_INSUFFICIENT_INFO", "").strip()
                        
                        # Send PDF response first
                        if clean_response:
                            yield f"data: {json.dumps({'content': clean_response, 'done': False})}\n\n"
                        
                        # Add note about fallback
                        yield f"data: {json.dumps({'content': '\n\n[Note: The PDF doesn\'t contain sufficient information. Here\'s additional information from ChatGPT:]\n\n', 'done': False})}\n\n"
                        
                        # Fallback to ChatGPT with general knowledge
                        fallback_messages = [
                            {
                                "role": "user",
                                "content": f"Question: {request.question}\n\nNote: This question is not related to any uploaded PDF document."
                            }
                        ]
                        
                        stream = openai_client.chat.completions.create(
                            model="gpt-3.5-turbo",
                            messages=fallback_messages,
                            stream=True,
                            temperature=0.7,
                            max_tokens=1000
                        )
                        
                        for chunk in stream:
                            if chunk.choices[0].delta.content is not None:
                                content = chunk.choices[0].delta.content
                                yield f"data: {json.dumps({'content': content, 'done': False})}\n\n"
                        
                        yield f"data: {json.dumps({'content': '', 'done': True})}\n\n"
                    else:
                        # PDF had sufficient information, stream the response
                        yield f"data: {json.dumps({'content': pdf_response, 'done': True})}\n\n"
                
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
            "upload_pdf": "/api/upload-pdf",
            "query_pdf": "/api/query-pdf",
            "health": "/api/health",
            "debug": "/api/debug"
        }
    }

# Run the app
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
