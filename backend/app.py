"""
ChatGPT Clone Backend - Phase 2: PDF Upload & Query
FastAPI application with OpenAI streaming integration and PDF processing
"""

import os
import json
import tempfile
import pickle
from datetime import datetime
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

# Storage configuration
STORAGE_DIR = "/tmp" if os.getenv("VERCEL") else "./storage"
os.makedirs(STORAGE_DIR, exist_ok=True)

# Global storage for medical documents (now using file storage)
medical_vector_store: Dict[str, FAISS] = {}
medical_documents: Dict[str, Dict[str, Any]] = {}

# Medical categories
MEDICAL_CATEGORIES = [
    "Clinical Diagnosis",
    "Clinical Treatment", 
    "Clinical Signs and Symptoms",
    "Research",
    "Therapeutics",
    "Physiology",
    "Genetic",
    "Others"
]

# Text splitter for chunking PDF content
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    length_function=len,
)

# Helper functions for file storage
def save_vector_store(filename: str, vector_store: FAISS):
    """Save vector store to file"""
    file_path = os.path.join(STORAGE_DIR, f"{filename}_vector.pkl")
    # Save FAISS index and vectors separately to avoid thread lock issues
    index_data = {
        'index': vector_store.index,
        'docstore': vector_store.docstore,
        'index_to_docstore_id': vector_store.index_to_docstore_id
    }
    with open(file_path, 'wb') as f:
        pickle.dump(index_data, f)

def load_vector_store(filename: str) -> FAISS:
    """Load vector store from file"""
    file_path = os.path.join(STORAGE_DIR, f"{filename}_vector.pkl")
    with open(file_path, 'rb') as f:
        index_data = pickle.load(f)
    
    # Reconstruct FAISS vector store properly
    vector_store = FAISS(
        embedding_function=embeddings,
        index=index_data['index'],
        docstore=index_data['docstore'],
        index_to_docstore_id=index_data['index_to_docstore_id']
    )
    
    return vector_store

def save_document_info(filename: str, doc_info: Dict[str, Any]):
    """Save document info to file"""
    file_path = os.path.join(STORAGE_DIR, f"{filename}_info.json")
    with open(file_path, 'w') as f:
        json.dump(doc_info, f)

def load_document_info(filename: str) -> Dict[str, Any]:
    """Load document info from file"""
    file_path = os.path.join(STORAGE_DIR, f"{filename}_info.json")
    with open(file_path, 'r') as f:
        return json.load(f)

def document_exists(filename: str) -> bool:
    """Check if document files exist"""
    vector_path = os.path.join(STORAGE_DIR, f"{filename}_vector.pkl")
    info_path = os.path.join(STORAGE_DIR, f"{filename}_info.json")
    return os.path.exists(vector_path) and os.path.exists(info_path)

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

class MedicalUploadResponse(BaseModel):
    status: str
    message: str
    filename: str
    pages: int
    chunks: int
    category: str = ""

class MedicalQueryRequest(BaseModel):
    question: str
    filename: str

class MedicalExportRequest(BaseModel):
    filename: str
    title: str
    journal_source: str

class MedicalImportRequest(BaseModel):
    filename: str
    title: str
    journal_source: str
    conversation_history: list

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
                    max_tokens=1000,
                    timeout=30  # 30 second timeout
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
        docs = vector_store.similarity_search(request.question, k=5)
        
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

# Medical document upload endpoint
@app.post("/api/upload-medical", response_model=MedicalUploadResponse)
async def upload_medical_document(file: UploadFile = File(...)):
    """Upload and process medical document"""
    
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
        
        # Categorize immediately during upload (skip on Vercel for performance)
        if os.getenv("VERCEL"):
            category = "Medical Document"  # Default category on Vercel
        else:
            # Local development - categorize with AI
            first_chunk = texts[0][:400] if texts else ""
            category_prompt = f"""Categorize this medical document: {first_chunk}
Categories: {', '.join(MEDICAL_CATEGORIES)}
Answer:"""
            
            category_response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": category_prompt}],
                temperature=0.7,
                max_tokens=20
            )
            
            category = category_response.choices[0].message.content.strip()
            if category not in MEDICAL_CATEGORIES:
                category = "Others"
        
        # Store vector store and document info to files
        save_vector_store(file.filename, vector_store)
        doc_info = {
            "filename": file.filename,
            "pages": pages,
            "chunks": len(texts),
            "category": category,  # Set immediately
            "full_text": pdf_text,  # Store full text for Vercel simple search
            "conversation_history": []
        }
        save_document_info(file.filename, doc_info)
        
        return MedicalUploadResponse(
            status="success",
            message=f"Medical document processed successfully",
            filename=file.filename,
            pages=pages,
            chunks=len(texts),
            category=category
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing medical document: {str(e)}"
        )

# Medical document query endpoint with streaming
@app.post("/api/query-medical")
async def query_medical_document_stream(request: MedicalQueryRequest):
    """Query medical document content with streaming response"""
    
    # Check if API key is set
    if not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(
            status_code=500,
            detail="OpenAI API key not configured. Please set OPENAI_API_KEY environment variable."
        )
    
    # Check if document is uploaded
    if not document_exists(request.filename):
        raise HTTPException(
            status_code=404,
            detail=f"Medical document '{request.filename}' not found. Please upload it first."
        )
    
    try:
        # Load vector store and document info from files
        vector_store = load_vector_store(request.filename)
        doc_info = load_document_info(request.filename)
        
        # Search for relevant chunks (skip vector search on Vercel)
        if os.getenv("VERCEL"):
            # Simple text search for Vercel
            pdf_text = doc_info.get("full_text", "")
            # Use first 1000 characters as context
            context = pdf_text[:1000] if pdf_text else "No content available"
        else:
            # Local: Full vector search
            docs = vector_store.similarity_search(request.question, k=5)
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
                            "content": f"Question: {request.question}\n\nNote: This question is not related to any uploaded medical document."
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
                    yield f"data: {json.dumps({'content': '[Note: This answer is from ChatGPT, not from your medical document]\n\n', 'done': False})}\n\n"
                    
                    for chunk in stream:
                        if chunk.choices[0].delta.content is not None:
                            content = chunk.choices[0].delta.content
                            yield f"data: {json.dumps({'content': content, 'done': False})}\n\n"
                    
                    yield f"data: {json.dumps({'content': '', 'done': True})}\n\n"
                    
                else:
                    # We have relevant context, implement medical logic
                    # Category already set during upload
                    
                    # Skip quality assessment on Vercel for performance
                    if os.getenv("VERCEL"):
                        quality_score = 0.7  # Default to "good" on Vercel
                    else:
                        # Local development - assess quality
                        quality_prompt = f"""Rate the semantic similarity between the document content and the user's question on a scale of 0.0 to 1.0.

Document content: {context}
User question: {request.question}

Respond with only a number between 0.0 and 1.0."""
                        
                        quality_response = openai_client.chat.completions.create(
                            model="gpt-3.5-turbo",
                            messages=[{"role": "user", "content": quality_prompt}],
                            temperature=0.1,
                            max_tokens=10
                        )
                        
                        try:
                            quality_score = float(quality_response.choices[0].message.content.strip())
                        except:
                            quality_score = 0.5  # Default to average
                    
                    # Determine response strategy based on quality
                    if quality_score >= 0.7:  # Good
                        # Use PDF content only
                        messages = [
                            {
                                "role": "system",
                                "content": "You are a medical assistant. Answer based on the provided medical document content. Include appropriate medical disclaimers."
                            }
                        ]
                        
                        # Add conversation history (last 5 exchanges)
                        recent_history = doc_info["conversation_history"][-5:] if doc_info["conversation_history"] else []
                        for conv in recent_history:
                            messages.append({"role": "user", "content": conv["question"]})
                            if "response" in conv:
                                messages.append({"role": "assistant", "content": conv["response"]})
                        
                        # Add current question with context
                        messages.append({
                            "role": "user",
                            "content": f"Medical document content:\n{context}\n\nQuestion: {request.question}\n\nNote: This analysis is based on the uploaded medical document and should not replace professional medical advice."
                        })
                        
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
                                yield f"data: {json.dumps({'content': content, 'done': False})}\n\n"
                        
                        yield f"data: {json.dumps({'content': '', 'done': True})}\n\n"
                        
                    elif quality_score >= 0.4:  # Average
                        # Combine PDF and ChatGPT
                        messages = [
                            {
                                "role": "system",
                                "content": "You are a medical assistant. Answer based on the provided medical document content. If the document doesn't have sufficient information, respond with exactly: 'MEDICAL_INSUFFICIENT_INFO' and then provide what information you can from the document."
                            }
                        ]
                        
                        # Add conversation history (last 5 exchanges)
                        recent_history = doc_info["conversation_history"][-5:] if doc_info["conversation_history"] else []
                        for conv in recent_history:
                            messages.append({"role": "user", "content": conv["question"]})
                            if "response" in conv:
                                messages.append({"role": "assistant", "content": conv["response"]})
                        
                        # Add current question with context
                        messages.append({
                            "role": "user",
                            "content": f"Medical document content:\n{context}\n\nQuestion: {request.question}"
                        })
                        
                        response = openai_client.chat.completions.create(
                            model="gpt-3.5-turbo",
                            messages=messages,
                            temperature=0.7,
                            max_tokens=1000
                        )
                        
                        medical_response = response.choices[0].message.content
                        
                        if "MEDICAL_INSUFFICIENT_INFO" in medical_response:
                            clean_response = medical_response.replace("MEDICAL_INSUFFICIENT_INFO", "").strip()
                            
                            if clean_response:
                                yield f"data: {json.dumps({'content': clean_response, 'done': False})}\n\n"
                            
                            yield f"data: {json.dumps({'content': '\n\n[Additional information from ChatGPT:]\n\n', 'done': False})}\n\n"
                            
                            fallback_messages = [
                                {
                                    "role": "user",
                                    "content": f"Question: {request.question}\n\nNote: This is general medical information and should not replace professional medical advice."
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
                            yield f"data: {json.dumps({'content': medical_response, 'done': True})}\n\n"
                    
                    else:  # Poor (quality_score < 0.4)
                        # Use ChatGPT only
                        messages = [
                            {
                                "role": "system",
                                "content": "You are a medical assistant providing general medical information. This should not replace professional medical advice."
                            }
                        ]
                        
                        # Add conversation history (last 5 exchanges)
                        recent_history = doc_info["conversation_history"][-5:] if doc_info["conversation_history"] else []
                        for conv in recent_history:
                            messages.append({"role": "user", "content": conv["question"]})
                            if "response" in conv:
                                messages.append({"role": "assistant", "content": conv["response"]})
                        
                        # Add current question
                        messages.append({
                            "role": "user",
                            "content": f"Question: {request.question}\n\nNote: This is general medical information and should not replace professional medical advice."
                        })
                        
                        yield f"data: {json.dumps({'content': '[Note: This answer is from ChatGPT, not from your medical document]\n\n', 'done': False})}\n\n"
                        
                        stream = openai_client.chat.completions.create(
                            model="gpt-3.5-turbo",
                            messages=messages,
                            stream=True,
                            temperature=0.7,
                            max_tokens=1000
                        )
                        
                        # Collect response for storage (skip on Vercel for performance)
                        full_response = ""
                        if not os.getenv("VERCEL"):
                            for chunk in stream:
                                if chunk.choices[0].delta.content is not None:
                                    content = chunk.choices[0].delta.content
                                    full_response += content
                                    yield f"data: {json.dumps({'content': content, 'done': False})}\n\n"
                        else:
                            # Vercel: just stream without collecting
                            for chunk in stream:
                                if chunk.choices[0].delta.content is not None:
                                    content = chunk.choices[0].delta.content
                                    yield f"data: {json.dumps({'content': content, 'done': False})}\n\n"
                        
                        yield f"data: {json.dumps({'content': '', 'done': True})}\n\n"
                        
                        # Store conversation (local only)
                        if not os.getenv("VERCEL"):
                            # Limit response to 100 words
                            response_words = full_response.split()[:100]
                            limited_response = " ".join(response_words)
                            
                            doc_info["conversation_history"].append({
                                "question": request.question,
                                "response": limited_response,
                                "quality_score": quality_score if 'quality_score' in locals() else 0.0,
                                "timestamp": str(datetime.now())
                            })
                            
                            # Save updated document info back to file
                            save_document_info(request.filename, doc_info)
                
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

# Medical document export endpoint
@app.post("/api/export-medical")
async def export_medical_document(request: MedicalExportRequest):
    """Export medical document conversation as JSON"""
    
    # Check if API key is set
    if not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(
            status_code=500,
            detail="OpenAI API key not configured. Please set OPENAI_API_KEY environment variable."
        )
    
    # Check if document exists
    if not document_exists(request.filename):
        raise HTTPException(
            status_code=404,
            detail=f"Medical document '{request.filename}' not found."
        )
    
    try:
        doc_info = load_document_info(request.filename)
        
        # Generate summary using ChatGPT
        conversation_text = "\n".join([
            f"Q: {conv['question']}" for conv in doc_info["conversation_history"]
        ])
        
        summary_prompt = f"""Summarize the following medical document conversation in 2-3 sentences:

Document: {request.filename}
Category: {doc_info['category']}
Conversations:
{conversation_text}

Provide a concise summary of the discussion."""
        
        summary_response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": summary_prompt}],
            temperature=0.7,
            max_tokens=200
        )
        
        conversation_summary = summary_response.choices[0].message.content
        
        # Create export JSON
        export_data = {
            "document": {
                "filename": request.filename,
                "category": doc_info["category"],
                "title": request.title,
                "journal_source": request.journal_source,
                "upload_date": doc_info.get("upload_date", ""),
                "pages": doc_info["pages"],
                "chunks": doc_info["chunks"]
            },
            "conversation_summary": conversation_summary,
            "conversation": doc_info["conversation_history"],
            "metadata": {
                "export_date": str(datetime.now()),
                "total_questions": len(doc_info["conversation_history"])
            }
        }
        
        return export_data
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error exporting medical document: {str(e)}"
        )

# Medical document import endpoint
@app.post("/api/import-medical")
async def import_medical_document(request: MedicalImportRequest):
    """Import medical document conversation from JSON"""
    
    # Check if API key is set
    if not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(
            status_code=500,
            detail="OpenAI API key not configured. Please set OPENAI_API_KEY environment variable."
        )
    
    try:
        # Validate the import data
        if not request.filename or not request.title:
            raise HTTPException(
                status_code=400,
                detail="Invalid import data: filename and title are required"
            )
        
        # Create a mock vector store (since we don't have the original PDF)
        # We'll use a simple text-based approach for imported documents
        mock_text = f"Imported medical document: {request.title}\nSource: {request.journal_source}\nFilename: {request.filename}"
        texts = text_splitter.split_text(mock_text)
        documents = [Document(page_content=text) for text in texts]
        
        # Create vector store
        vector_store = FAISS.from_documents(documents, embeddings)
        
        # Store vector store and document info to files
        save_vector_store(request.filename, vector_store)
        doc_info = {
            "filename": request.filename,
            "pages": 0,  # Unknown for imported documents
            "chunks": len(texts),
            "category": "Imported Document",
            "conversation_history": request.conversation_history,  # Fresh start - replace existing
            "imported": True,
            "title": request.title,
            "journal_source": request.journal_source
        }
        save_document_info(request.filename, doc_info)
        
        return {
            "status": "success",
            "message": f"Medical document '{request.filename}' imported successfully",
            "filename": request.filename,
            "title": request.title,
            "journal_source": request.journal_source,
            "conversation_count": len(request.conversation_history)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error importing medical document: {str(e)}"
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
            "upload_medical": "/api/upload-medical",
            "query_medical": "/api/query-medical",
            "export_medical": "/api/export-medical",
            "import_medical": "/api/import-medical",
            "health": "/api/health",
            "debug": "/api/debug"
        }
    }

# Run the app
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
