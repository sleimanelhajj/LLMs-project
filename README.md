# Employee Assistant Chatbot

A sophisticated multi-agent AI system built for warehouse employees to manage business operations through a conversational interface.

## System Architecture

### Core Components:
1. **Multi-Agent System** - Main orchestrator with specialized sub-agents
2. **LangGraph Agent** - Specialized invoice processing
3. **MCP Server** - Model Context Protocol for tool hosting
4. **FastAPI Backend** - Web API and A2A communication
5. **Vector Database** - RAG for document analysis
6. **SQLite Database** - Product catalog management

### Agents:
- **CatalogAgent**: Product database queries (SQL)
- **DeliveryAgent**: Delivery options (YAML)
- **CompanyInfoAgent**: Company information (YAML)
- **PolicyAgent**: Company policies (Vector DB/RAG)
- **PDF_Agent**: Runtime PDF analysis (Vector DB/RAG)
- **LangGraphAgent**: Invoice generation via A2A protocol

## Features

- **Multi-Modal Data Access**: SQL, YAML, and RAG-based queries
- **Runtime PDF Processing**: Upload and analyze documents
- **Invoice Generation**: Complete order processing system
- **A2A Communication**: Agent-to-Agent protocol
- **Monitoring**: LangSmith integration

## Setup

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Environment Variables**:
   Create a `.env` file with your API keys:
   ```
   OPENAI_API_KEY=your_openai_key
   LANGCHAIN_API_KEY=your_langsmith_key
   LANGCHAIN_TRACING_V2=true
   LANGCHAIN_PROJECT=employee-assistant
   ```

3. **Initialize Databases**:
   ```bash
   python scripts/init_databases.py
   ```

4. **Start Services**:
   ```bash
   # Terminal 1: MCP Server
   python mcp_server.py
   
   # Terminal 2: LangGraph Agent Server
   python agents/langgraph_agent_server.py
   
   # Terminal 3: FastAPI Backend
   python api/main.py
   ```

## Project Structure

```
├── agents/                 # Multi-agent system
├── api/                    # FastAPI backend
├── data/                   # Databases and configurations
├── mcp/                    # MCP server implementation
├── models/                 # Data models and schemas
├── services/               # Core business logic
├── scripts/                # Utility scripts
├── templates/              # HTML templates
└── tests/                  # Test cases
```

## Usage

The system provides a conversational interface for:
- Product inquiries and inventory management
- Company information and policies
- Delivery planning and logistics
- Document analysis and processing
- Invoice generation and processing

## Monitoring

- **LangSmith**: Workflow tracing and debugging
- **Logs**: Structured logging for all components
- **Metrics**: Performance monitoring and analytics
