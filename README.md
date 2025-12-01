# Employee Assistant Chatbot

A sophisticated multi-agent AI system built for warehouse employees to manage business operations through a conversational interface.

## System Architecture

### Core Components:
1. **Multi-Agent System** - Main orchestrator with specialized sub-agents
2. **FastAPI Backend** - Web API
3. **Vector Database** - RAG for company document analysis
4. **SQLite Database** - Product catalog management

### Agents:
- **CatalogAgent**: Product database queries (SQL)
- **CompanyAgent**: Company information (Vector DB/RAG from company PDF)
- **OrderTrackingAgent**: Order status and tracking
- **ReportAgent**: Business reports and analytics
- **InvoiceGeneratorAgent**: Invoice generation (PDF)

## Features

- **Multi-Modal Data Access**: SQL, YAML, and RAG-based queries
- **Invoice Generation**: Complete order processing system
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
   # Terminal 1: LangGraph Agent Server
   python agents/langgraph_agent_server.py
   
   # Terminal 2: FastAPI Backend
   python api.py
   ```

## Project Structure

```
├── agents/                 # Multi-agent system
├── data/                   # Databases and configurations
├── frontend/               # Web frontend
├── models/                 # Data models and schemas
├── scripts/                # Utility scripts
├── utils/                  # Utility functions
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
