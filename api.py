"""
FastAPI Backend for Warehouse Chatbot

REST API endpoints for frontend integration.
"""

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import os
import uuid
from pathlib import Path
import tempfile
import shutil

from agents.orchestrator_agent import OrchestratorAgent
from agents.invoice_generator_agent import InvoiceGeneratorAgent
from models.schemas import QueryRequest, AgentResponse
from config import (
    GOOGLE_API_KEY,
    CATALOG_DB_PATH
)


# Request/Response Models
class ChatRequest(BaseModel):
    """Chat message request."""
    message: str = Field(..., description="User's message")
    session_id: Optional[str] = Field(None, description="Session ID for conversation history")


class ChatResponse(BaseModel):
    """Chat message response."""
    response: str = Field(..., description="Chatbot's response")
    agent_name: str = Field(..., description="Which agent handled the query")
    session_id: str = Field(..., description="Session ID for tracking conversation")
    success: bool = Field(..., description="Whether the query was successful")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional response metadata")


class InvoiceRequest(BaseModel):
    """Invoice generation request."""
    customer_name: str = Field(..., description="Customer name")
    customer_address: str = Field(..., description="Customer address (can be multi-line)")
    items: List[Dict[str, Any]] = Field(..., description="List of items with sku and quantity")


class InvoiceResponse(BaseModel):
    """Invoice generation response."""
    success: bool
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    pdf_path: Optional[str] = None
    subtotal: Optional[float] = None
    discount: Optional[float] = None
    tax: Optional[float] = None
    total: Optional[float] = None
    errors: Optional[List[str]] = None


# Initialize FastAPI app
app = FastAPI(
    title="Warehouse Chatbot API",
    description="Multi-agent chatbot system for warehouse operations",
    version="1.0.0"
)

# Configure CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global state
orchestrator: Optional[OrchestratorAgent] = None
invoice_generator: Optional[InvoiceGeneratorAgent] = None
conversation_history: Dict[str, List[Dict[str, str]]] = {}  # session_id -> messages
pdf_sessions: Dict[str, str] = {}  # session_id -> pdf_path


@app.on_event("startup")
async def startup_event():
    """Initialize agents on startup."""
    global orchestrator, invoice_generator
    
    print("🚀 Initializing Warehouse Chatbot API...")
    
    if not GOOGLE_API_KEY:
        raise RuntimeError("GOOGLE_API_KEY not found in environment")
    
    # Initialize orchestrator (policy vector DB is initialized internally)
    orchestrator = OrchestratorAgent(
        google_api_key=GOOGLE_API_KEY,
        catalog_db_path=CATALOG_DB_PATH
    )
    
    # Initialize invoice generator
    invoice_generator = InvoiceGeneratorAgent(
        google_api_key=GOOGLE_API_KEY,
        db_path=CATALOG_DB_PATH
    )
    
    print("✅ Agents initialized successfully!")


@app.get("/")
async def root():
    """API root endpoint."""
    return {
        "message": "Warehouse Chatbot API",
        "version": "1.0.0",
        "endpoints": {
            "chat": "/api/chat",
            "invoice": "/api/invoice",
            "upload_pdf": "/api/upload-pdf",
            "download_invoice": "/api/invoice/{invoice_number}",
            "health": "/health"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "orchestrator_ready": orchestrator is not None,
        "invoice_generator_ready": invoice_generator is not None
    }


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Main chat endpoint.
    
    Handles general queries, product search, company info, policies, etc.
    """
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    
    try:
        # Generate or use existing session ID
        session_id = request.session_id or str(uuid.uuid4())
        
        # Get conversation history for context
        if session_id not in conversation_history:
            conversation_history[session_id] = []
        
        history = conversation_history[session_id]
        
        # Extract invoice state from last message if it exists
        invoice_state = None
        if history:
            for msg in reversed(history):
                if msg.get("role") == "assistant" and msg.get("invoice_state"):
                    invoice_state = msg["invoice_state"]
                    break
        
        # Process query
        metadata = {"history": history[-5:]}  # Last 5 messages for context
        if invoice_state:
            metadata["invoice_state"] = invoice_state
        
        query_request = QueryRequest(
            query=request.message,
            metadata=metadata
        )
        
        response: AgentResponse = await orchestrator.process_query(query_request)
        
        # Extract invoice state from response data if present
        response_invoice_state = None
        if hasattr(response, 'data') and response.data:
            response_invoice_state = response.data.get('invoice_state')
        
        # Update conversation history
        history.append({"role": "user", "content": request.message})
        history.append({
            "role": "assistant",
            "content": response.response,
            "invoice_state": response_invoice_state
        })
        
        # Keep only last 20 messages
        if len(history) > 20:
            conversation_history[session_id] = history[-20:]
        
        return ChatResponse(
            response=response.response,
            agent_name=response.agent_name,
            session_id=session_id,
            success=response.success,
            metadata=response.data if hasattr(response, 'data') and response.data else None
        )
        
    except Exception as e:
        print(f"Error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/upload-pdf")
async def upload_pdf(
    file: UploadFile = File(...),
    session_id: Optional[str] = None
):
    """
    Upload PDF for analysis.
    
    The PDF is associated with a session and can be queried via the chat endpoint.
    """
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    
    try:
        # Validate file type
        if not file.filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are supported")
        
        # Generate session ID
        session_id = session_id or str(uuid.uuid4())
        
        # Save PDF temporarily
        temp_dir = Path(tempfile.gettempdir()) / "chatbot_pdfs"
        temp_dir.mkdir(exist_ok=True)
        
        pdf_path = temp_dir / f"{session_id}_{file.filename}"
        
        with open(pdf_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Upload to PDF agent
        result = await orchestrator.pdf_agent.upload_pdf(str(pdf_path))
        
        if result["success"]:
            pdf_sessions[session_id] = str(pdf_path)
            
            return {
                "success": True,
                "session_id": session_id,
                "filename": file.filename,
                "message": "PDF uploaded successfully. You can now ask questions about it.",
                "pages": result.get("pages", 0)
            }
        else:
            raise HTTPException(status_code=400, detail=result.get("error", "PDF upload failed"))
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error uploading PDF: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/invoice", response_model=InvoiceResponse)
async def generate_invoice(request: InvoiceRequest):
    """
    Generate invoice PDF.
    
    Returns invoice details and path to download PDF.
    """
    if not invoice_generator:
        raise HTTPException(status_code=503, detail="Invoice generator not initialized")
    
    try:
        result = await invoice_generator.generate_invoice(
            customer_name=request.customer_name,
            customer_address=request.customer_address,
            items=request.items
        )
        
        if result["success"]:
            return InvoiceResponse(
                success=True,
                invoice_number=result["invoice_number"],
                invoice_date=result["invoice_date"],
                pdf_path=result["pdf_path"],
                subtotal=result["subtotal"],
                discount=result["discount"],
                tax=result["tax"],
                total=result["total"]
            )
        else:
            return InvoiceResponse(
                success=False,
                errors=result["errors"]
            )
            
    except Exception as e:
        print(f"Error generating invoice: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/invoice/{invoice_number}")
async def download_invoice(invoice_number: str):
    """
    Download generated invoice PDF.
    """
    try:
        # Find invoice file
        invoice_dir = Path("data/invoices")
        pdf_path = invoice_dir / f"{invoice_number}.pdf"
        
        if not pdf_path.exists():
            raise HTTPException(status_code=404, detail="Invoice not found")
        
        return FileResponse(
            path=str(pdf_path),
            media_type="application/pdf",
            filename=f"{invoice_number}.pdf"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error downloading invoice: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/session/{session_id}")
async def clear_session(session_id: str):
    """
    Clear conversation history and uploaded PDFs for a session.
    """
    try:
        # Clear conversation history
        if session_id in conversation_history:
            del conversation_history[session_id]
        
        # Clear PDF session
        if session_id in pdf_sessions:
            pdf_path = pdf_sessions[session_id]
            if os.path.exists(pdf_path):
                os.remove(pdf_path)
            del pdf_sessions[session_id]
        
        return {"success": True, "message": "Session cleared"}
        
    except Exception as e:
        print(f"Error clearing session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/products")
async def get_products(category: Optional[str] = None):
    """
    Get product catalog.
    
    Optional category filter.
    """
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    
    try:
        import sqlite3
        
        conn = sqlite3.connect(CATALOG_DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if category:
            cursor.execute("SELECT * FROM products WHERE category = ?", (category,))
        else:
            cursor.execute("SELECT * FROM products")
        
        products = []
        for row in cursor.fetchall():
            products.append(dict(row))
        
        conn.close()
        
        return {"success": True, "products": products}
        
    except Exception as e:
        print(f"Error fetching products: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    
    print("=" * 80)
    print("🚀 Starting Warehouse Chatbot API")
    print("=" * 80)
    print("\nAPI Documentation: http://localhost:8000/docs")
    print("Alternative Docs: http://localhost:8000/redoc")
    print("\n" + "=" * 80)
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
