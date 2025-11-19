import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Keys - Essential
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")  # Required for LLM

# Validate required keys
if not GOOGLE_API_KEY:
    print("⚠️  WARNING: GOOGLE_API_KEY not found in environment variables")
    print("Please add GOOGLE_API_KEY=your_key_here to your .env file")

# Database Configuration
DATABASE_DIR = "data"
CATALOG_DB_PATH = os.path.join(DATABASE_DIR, "catalog.db")
VECTOR_DB_PATH = os.path.join(DATABASE_DIR, "vector_db")

# MCP Server Configuration
MCP_HOST = "127.0.0.1"
MCP_PORT = 8899

# A2A Server Configuration
A2A_HOST = "localhost"
A2A_PORT = 8001

# FastAPI Configuration
API_HOST = "0.0.0.0"
API_PORT = 8000

# Vector Database Configuration
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
CHUNK_SIZE = 700
CHUNK_OVERLAP = 300
RETRIEVAL_K = 5
MIN_SCORE = 0.2

# LLM Configuration - Standardized across all agents
DEFAULT_LLM_MODEL = "gemini-2.0-flash"  # Stable version
LLM_TEMPERATURE = 0.1  # Low temperature for consistent responses
LLM_MAX_RETRIES = 2  # Reduce retries to fail faster

# File Paths
TEMPLATES_DIR = "templates"
DATA_DIR = "data"
INVOICES_DIR = os.path.join(DATA_DIR, "invoices")
UPLOADS_DIR = os.path.join(DATA_DIR, "uploads")

# Agent-specific paths
COMPANY_INFO_PATH = os.path.join(DATA_DIR, "company_info.yaml")
DELIVERY_INFO_PATH = os.path.join(DATA_DIR, "delivery_rules.yaml")
POLICY_VECTOR_DB_PATH = os.path.join(DATA_DIR, "vector_dbs", "policy_vectordb")

# Ensure directories exist
os.makedirs(DATABASE_DIR, exist_ok=True)
os.makedirs(INVOICES_DIR, exist_ok=True)
os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(TEMPLATES_DIR, exist_ok=True)
os.makedirs(os.path.join(DATA_DIR, "vector_dbs"), exist_ok=True)
