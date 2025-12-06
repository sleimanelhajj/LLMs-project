from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, List
import uvicorn
import os
from langchain_core.messages import HumanMessage, AIMessage
from agent import create_employee_assistant
from tools import initialize_company_vector_db


app = FastAPI(
    title="Employee Assistant API",
    description="Simple AI assistant for warehouse employees",
    version="2.0.0",
)
frontend_dir = os.path.join(os.path.dirname(__file__), "frontend")
app.mount("/static", StaticFiles(directory=frontend_dir), name="static")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


# Create the agent once at startupp
agent = None

# Session history storage (in-memory for simplicity)
# Each session: list of {"role": "user"|"assistant", "content": str}
sessions = {}


@app.on_event("startup")
async def startup():
    """Initialize the agent and RAG vector database on startup."""
    global agent
    print("Starting Employee Assistant...")

    # Initialize RAG vector database for company documents
    print("Initializing RAG vector database...")
    initialize_company_vector_db()
    print("RAG initialized!")

    # Create the agent
    agent = create_employee_assistant()
    print("Agent ready!")


# models


class Message(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    history: Optional[List[Message]] = None  # kept for compatibility, currently unused


class ChatResponse(BaseModel):
    response: str
    success: bool
    agent_name: Optional[str] = "EmployeeAssistant"
    metadata: Optional[dict] = None


# endpoints


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the frontend."""
    frontend_path = os.path.join(os.path.dirname(__file__), "frontend", "index.html")
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

        # Keep only recent history to avoid context length issues
        # Keep last 6 messages (3 exchanges) from history
        recent_history = sessions[session_id][-6:] if len(sessions[session_id]) > 6 else sessions[session_id]
        
        # Build LangChain messages from session history
        lc_messages = []
        for msg in recent_history:
            if msg["role"] == "user":
                lc_messages.append(HumanMessage(content=msg["content"]))
            else:
                lc_messages.append(AIMessage(content=msg["content"]))

        # Add the current user message
        lc_messages.append(HumanMessage(content=request.message))
        
        print(f"[API] Context size: {len(lc_messages)} messages")

        # Invoke the agent graph
        # Use "messages" key (required by create_agent agents)
        result = await agent.ainvoke({"messages": lc_messages})

        # The agent returns state with a "messages" list
        result_messages = result["messages"]
        last_msg = result_messages[-1]
        
        # Extract response text - handle both string and list content
        if isinstance(last_msg.content, str):
            response_text = last_msg.content
        elif isinstance(last_msg.content, list):
            # Extract text from content blocks
            response_text = "".join(
                block.get("text", "") if isinstance(block, dict) else str(block)
                for block in last_msg.content
            )
        else:
            response_text = str(last_msg.content)
        
        # Ensure response is not empty
        response_text = response_text.strip()
        if not response_text:
            print(f"WARNING: Empty response detected. Last message: {last_msg}")
            print(f"Last message type: {type(last_msg)}, content: {last_msg.content}")
            print(f"Response metadata: {getattr(last_msg, 'response_metadata', {})}")
            
            # Check if there are tool messages with content we can use
            tool_responses = []
            for msg in result_messages:
                if hasattr(msg, '__class__') and msg.__class__.__name__ == 'ToolMessage':
                    if hasattr(msg, 'content') and msg.content:
                        tool_responses.append(str(msg.content))
            
            if tool_responses:
                # Use the tool response directly
                response_text = tool_responses[-1]
                print(f"[API] Using tool response as fallback: {response_text[:100]}...")
            else:
                # Generic fallback
                response_text = "I apologize, but I encountered an issue generating a response. This may be due to context length. Please try starting a new conversation."

        # Extract tool usage information from the messages
        tools_used = []
        for msg in result_messages:
            # Check if message has tool calls
            if (
                hasattr(msg, "additional_kwargs")
                and "tool_calls" in msg.additional_kwargs
            ):
                for tool_call in msg.additional_kwargs["tool_calls"]:
                    if "function" in tool_call and "name" in tool_call["function"]:
                        tool_name = tool_call["function"]["name"]
                        if tool_name not in tools_used:
                            tools_used.append(tool_name)
            # Also check for ToolMessage (response from tools)
            elif hasattr(msg, "name") and msg.name and msg.name not in tools_used:
                tools_used.append(msg.name)

        # Debug logging
        print(f"Tools used: {tools_used}")

        # Save to session history
        sessions[session_id].append({"role": "user", "content": request.message})
        sessions[session_id].append({"role": "assistant", "content": response_text})

        # Keep session history manageable - only keep last 10 messages (5 exchanges)
        if len(sessions[session_id]) > 10:
            sessions[session_id] = sessions[session_id][-10:]

        return ChatResponse(
            response=response_text,
            success=True,
            agent_name="EmployeeAssistant",
            metadata={"session_id": session_id, "tools_used": tools_used},
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


@app.post("/api/clear-session")
async def clear_session(session_id: str = "default"):
    """Clear conversation history for a session."""
    global sessions
    if session_id in sessions:
        sessions[session_id] = []
        return {"success": True, "message": f"Session {session_id} cleared"}
    return {"success": True, "message": "Session not found or already empty"}


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


if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
