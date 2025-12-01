"""
Simple FastAPI server for the Employee Assistant Agent.

This is a streamlined version using a single ReAct agent with multiple tools.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional, List
import uvicorn
import os

from simple_agent import create_employee_assistant
from utils.rag_utils import initialize_company_vector_db

# =============================================================================
# FastAPI App
# =============================================================================

app = FastAPI(
    title="Employee Assistant API",
    description="Simple AI assistant for warehouse employees",
    version="2.0.0",
)

# CORS - Allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Create the agent once at startup
agent = None

# Session history storage (in-memory for simplicity)
sessions = {}


@app.on_event("startup")
async def startup():
    """Initialize the agent and RAG vector database on startup."""
    global agent
    print("🚀 Starting Employee Assistant...")
    
    # Initialize RAG vector database for company documents
    print("📚 Initializing RAG vector database...")
    initialize_company_vector_db()
    print("✅ RAG initialized!")
    
    # Create the agent
    agent = create_employee_assistant()
    print("✅ Agent ready!")


# =============================================================================
# Request/Response Models
# =============================================================================


class Message(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    history: Optional[List[Message]] = None


class ChatResponse(BaseModel):
    response: str
    success: bool
    agent_name: Optional[str] = "EmployeeAssistant"
    metadata: Optional[dict] = None


# =============================================================================
# Endpoints
# =============================================================================


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the frontend."""
    frontend_path = os.path.join(
        os.path.dirname(__file__), "frontend", "simple_index.html"
    )
    if os.path.exists(frontend_path):
        with open(frontend_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Employee Assistant API Running</h1><p>Frontend not found.</p>"


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat with the employee assistant.
    Maintains conversation history per session.
    """
    global agent, sessions

    if not agent:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    try:
        # Get or create session history
        session_id = request.session_id or "default"
        if session_id not in sessions:
            sessions[session_id] = []

        # Build context from recent history
        context = ""
        for msg in sessions[session_id][-6:]:  # Last 6 messages (3 exchanges)
            role = "User" if msg["role"] == "user" else "Assistant"
            context += f"{role}: {msg['content']}\n"
        
        # Combine context with current message
        if context:
            full_input = f"Previous conversation:\n{context}\nCurrent question: {request.message}"
        else:
            full_input = request.message

        # Invoke the agent (AgentExecutor uses "input" key)
        result = agent.invoke({"input": full_input})

        # Extract response from result
        response_text = result.get("output", "I couldn't process your request. Please try again.")

        # Save to session history
        sessions[session_id].append({"role": "user", "content": request.message})
        sessions[session_id].append({"role": "assistant", "content": response_text})

        # Keep session history manageable
        if len(sessions[session_id]) > 20:
            sessions[session_id] = sessions[session_id][-20:]

        return ChatResponse(
            response=response_text,
            success=True,
            agent_name="EmployeeAssistant",
            metadata={"session_id": session_id},
        )

    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
        return ChatResponse(response=f"An error occurred: {str(e)}", success=False)


# Legacy endpoint for compatibility
@app.post("/chat", response_model=ChatResponse)
async def chat_legacy(request: ChatRequest):
    """Legacy chat endpoint for compatibility."""
    return await chat(request)


@app.get("/health")
async def health():
    """Detailed health check."""
    return {
        "status": "healthy",
        "agent_loaded": agent is not None,
        "active_sessions": len(sessions),
        "tools": [
            "search_products",
            "get_product_by_sku",
            "list_categories",
            "track_order",
            "get_order_history",
            "check_inventory",
            "get_inventory_summary",
            "get_sales_summary",
            "search_company_documents",  # RAG-based company info
            "generate_invoice",
        ],
    }


@app.delete("/sessions/{session_id}")
async def clear_session(session_id: str):
    """Clear a session's history."""
    if session_id in sessions:
        del sessions[session_id]
        return {"success": True, "message": f"Session {session_id} cleared"}
    return {"success": False, "message": "Session not found"}


# =============================================================================
# Run Server
# =============================================================================

if __name__ == "__main__":
    uvicorn.run("simple_api:app", host="0.0.0.0", port=8000, reload=True)
