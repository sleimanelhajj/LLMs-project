# Installation and Setup Guide
## Employee Assistant Chatbot System

This guide provides step-by-step instructions to set up and run the Employee Assistant Chatbot system.

---

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Installation Steps](#installation-steps)
3. [Configuration](#configuration)
4. [Database Initialization](#database-initialization)
5. [Running the Application](#running-the-application)
6. [Accessing the Application](#accessing-the-application)
7. [Troubleshooting](#troubleshooting)

---

## Prerequisites

Before starting, ensure you have the following installed:

- **Python 3.10 or higher** (recommended: Python 3.11+)
- **pip** (Python package manager)
- **Git** (for cloning the repository)
- **Google API Key** (for Gemini 2.0 Flash LLM)

### Verify Python Installation
```bash
python --version
# Should output: Python 3.10.x or higher
```

---

## Installation Steps

### Step 1: Clone or Download the Project

If using Git:
```bash
git clone <repository-url>
cd "LLMs project"
```

Or download and extract the project folder, then navigate to it:
```bash
cd "C:\Users\Sleiman\LLMs project"
```

### Step 2: Create a Virtual Environment (Recommended)

Creating a virtual environment isolates project dependencies:

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows PowerShell:
.\venv\Scripts\Activate.ps1

# On Windows Command Prompt:
.\venv\Scripts\activate.bat

# On macOS/Linux:
source venv/bin/activate
```

### Step 3: Install Required Dependencies

Install all required Python packages:

```bash
pip install -r requirements.txt
```

This will install:
- **LangChain & LangGraph**: Agent framework
- **FastAPI & Uvicorn**: Web server
- **Google Generative AI**: LLM provider (Gemini)
- **FAISS**: Vector database for RAG
- **Sentence Transformers**: Embeddings
- **PyPDF**: PDF processing
- **ReportLab**: Invoice generation
- **And other dependencies...**

Installation may take 5-10 minutes depending on your internet connection.

---

## Configuration

### Step 1: Create Environment File

Create a `.env` file in the project root directory:

```bash
# On Windows PowerShell:
New-Item .env -ItemType File

# On macOS/Linux:
touch .env
```

### Step 2: Add Your API Key

Open the `.env` file in any text editor and add your Google API key:

```env
GOOGLE_API_KEY=your_google_api_key_here
```

**How to Get a Google API Key:**

1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Sign in with your Google account
3. Click "Create API Key"
4. Copy the generated key
5. Paste it in your `.env` file

**Important:** Keep your API key private and never commit it to version control!

### Step 3: Verify Configuration

The system will automatically load the API key from the `.env` file. You can verify by checking:

```python
# The config.py file will show a warning if the key is missing
python -c "import config; print('API Key loaded!' if config.GOOGLE_API_KEY else 'API Key missing!')"
```

---

## Database Initialization

The system uses multiple databases:

1. **SQLite Database** (`catalog.db`) - Product catalog, customers, and orders
2. **FAISS Vector Database** - Company documents for RAG (Retrieval-Augmented Generation)

### Initialize All Databases

Run the single initialization script that sets up everything:

```bash
python scripts/init_databases.py
```

This script will:
- Create the product catalog database with sample products
- Create customer and order tracking tables
- Initialize the vector database for company documents
- Set up all necessary directories
- Verify the setup

### Expected Output

You should see output like:
```
================================================================================
EMPLOYEE ASSISTANT CHATBOT - COMPLETE DATABASE INITIALIZATION
================================================================================

Creating directory structure...
✓ Created directory: data
✓ Created directory: data/invoices
✓ Created directory: data/documents
✓ Created directory: data/vector_dbs
...

Creating catalog database...
✓ Catalog database created at: data/catalog.db
✓ Inserted 43 products

Creating orders database...
✓ Created customers table with 5 customers
✓ Created orders table with 12 orders
...

Initializing vector database for company documents...
✓ Vector database initialized successfully

Verifying setup...
✓ Products table exists
✓ Found 43 products in database
...

================================================================================
INITIALIZATION COMPLETED SUCCESSFULLY!
================================================================================
```

### Verify Database Setup

After initialization, verify the databases exist:

```bash
# Check if databases were created
dir data\catalog.db
dir data\vector_dbs\
```

You should see:
- `data/catalog.db` - SQLite database file
- `data/vector_dbs/company/` - Vector database files
- `data/documents/` - Company PDF documents

---

## Running the Application

### Method 1: Run Simple API (Recommended)

The simple API runs a single-agent system with all tools:

```bash
python simple_api.py
```

You should see output like:
```
Starting Employee Assistant...
Initializing RAG vector database...
RAG initialized!
Agent ready!
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

### Method 2: Run with Auto-Reload (Development)

For development with automatic reloading on code changes:

```bash
uvicorn simple_api:app --host 0.0.0.0 --port 8000 --reload
```

### Expected Startup Process

1. **Agent Initialization** (~5-10 seconds)
   - Loads LLM model
   - Initializes all tools
   - Sets up RAG vector database

2. **Server Start**
   - FastAPI server starts on port 8000
   - Frontend is served from the root URL

---

## Accessing the Application

### Web Interface

Once the server is running, open your web browser and navigate to:

```
http://localhost:8000
```

You should see the **Warehouse Assistant** chat interface.

### API Documentation

FastAPI automatically generates interactive API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Health Check

Verify the system is running correctly:

```
http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "agent_loaded": true,
  "active_sessions": 0,
  "tools": [
    "search_products",
    "get_product_by_sku",
    "list_categories",
    "track_order",
    "get_order_history",
    "check_inventory",
    "get_inventory_summary",
    "get_sales_summary",
    "search_company_documents",
    "generate_invoice"
  ]
}
```

---

## Testing the System

### Sample Queries to Try

1. **Product Catalog**:
   - "Show me rope products"
   - "What is SKU PP-ROPE-12MM?"
   - "List all product categories"

2. **Inventory Management**:
   - "Check inventory for SKU PP-ROPE-12MM"
   - "Show low stock items"
   - "Get inventory summary"

3. **Order Tracking**:
   - "Track order for john.smith@email.com"
   - "Show order history for customer@example.com"

4. **Company Information** (RAG-based):
   - "What is the return policy?"
   - "What are the business hours?"
   - "Tell me about shipping policies"

5. **Sales Reports**:
   - "Get sales summary"
   - "Show top selling products"

6. **Invoice Generation**:
   - "Generate invoice for John Doe at john@example.com with items PP-ROPE-12MM:10"

---

## Project Structure

```
LLMs project/
├── simple_api.py              # Main FastAPI application
├── simple_agent.py            # Agent configuration
├── config.py                  # Configuration and settings
├── requirements.txt           # Python dependencies
├── .env                       # Environment variables (API keys)
│
├── data/                      # Data storage
│   ├── catalog.db            # Product catalog (SQLite)
│   ├── vector_dbs/           # Vector databases (FAISS)
│   ├── documents/            # Company documents (PDFs)
│   ├── invoices/             # Generated invoices
│   └── reports/              # Generated reports
│
├── tools/                     # Agent tools
│   ├── catalog_tools.py      # Product search tools
│   ├── order_tools.py        # Order tracking tools
│   ├── inventory_tools.py    # Inventory management
│   ├── sales_tools.py        # Sales reporting
│   ├── company_tools.py      # RAG-based company info
│   ├── invoice_tools.py      # Invoice generation
│   └── utils/                # Utility functions
│       ├── db_utils.py       # Database utilities
│       ├── rag_utils.py      # RAG/Vector DB utilities
│       ├── html_utils.py     # HTML formatting
│       └── vector_db_manager.py
│
├── scripts/                   # Initialization scripts
│   ├── init_databases.py     # Initialize all databases
│   ├── init_catalog_db.py    # Initialize product catalog
│   └── init_policy_db.py     # Initialize vector database
│
└── frontend/                  # Web interface
    └── simple_index.html     # Chat UI
```

---

## Troubleshooting

### Issue: "GOOGLE_API_KEY not found"

**Solution**: 
1. Ensure `.env` file exists in the project root
2. Check that `GOOGLE_API_KEY=your_key_here` is in the file
3. Restart the application after adding the key

### Issue: "Module not found" errors

**Solution**:
```bash
# Reinstall dependencies
pip install --upgrade -r requirements.txt
```

### Issue: Database not found

**Solution**:
```bash
# Reinitialize databases
python scripts/init_databases.py
```

### Issue: Port 8000 already in use

**Solution**:
```bash
# Use a different port
uvicorn simple_api:app --host 0.0.0.0 --port 8080
# Then access at http://localhost:8080
```

### Issue: Vector database initialization fails

**Solution**:
1. Ensure company documents exist in `data/documents/`
2. Delete old vector database: `rm -rf data/vector_dbs/company/`
3. Restart the application (it will recreate automatically)

### Issue: Slow response times

**Possible Causes**:
- First request is always slower (model loading)
- Vector database search can be slow on first run
- Network latency with Google API

**Solution**:
- Wait for warm-up (first 1-2 queries)
- Ensure stable internet connection
- Consider reducing `RETRIEVAL_K` in `config.py`

---

## System Requirements

### Minimum Requirements:
- **CPU**: Dual-core processor
- **RAM**: 4GB
- **Storage**: 1GB free space
- **Internet**: Stable connection for API calls

### Recommended Requirements:
- **CPU**: Quad-core processor or better
- **RAM**: 8GB or more
- **Storage**: 2GB free space
- **Internet**: High-speed connection

---

## Additional Configuration (Optional)

### Customize LLM Settings

Edit `config.py` to adjust LLM behavior:

```python
# LLM Configuration
DEFAULT_LLM_MODEL = "gemini-2.0-flash"  # Model version
LLM_TEMPERATURE = 0.1                    # Response creativity (0.0-1.0)
LLM_MAX_RETRIES = 2                      # Retry attempts on failure
```

### Customize RAG Settings

Edit `config.py` to adjust retrieval settings:

```python
# Vector Database Configuration
EMBEDDING_MODEL = "all-MiniLM-L6-v2"    # Embedding model
CHUNK_SIZE = 700                         # Document chunk size
CHUNK_OVERLAP = 300                      # Overlap between chunks
RETRIEVAL_K = 5                          # Number of results to retrieve
MIN_SCORE = 0.2                          # Minimum similarity score
```

---

## Security Considerations

1. **Never commit `.env` file** to version control
2. **Keep API keys private** and secure
3. **Use HTTPS** in production deployments
4. **Implement authentication** for production use
5. **Regular backups** of databases

---

## Support and Documentation

- **Project Documentation**: See `README.md`
- **API Documentation**: http://localhost:8000/docs (when running)
- **LangChain Docs**: https://python.langchain.com/
- **FastAPI Docs**: https://fastapi.tiangolo.com/

---

## Quick Start Summary

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Create .env file and add API key
echo "GOOGLE_API_KEY=your_key_here" > .env

# 3. Initialize databases
python scripts/init_databases.py

# 4. Run the application
python simple_api.py

# 5. Open browser
# Navigate to http://localhost:8000
```

---

**Congratulations! Your Employee Assistant Chatbot is now ready to use!**
