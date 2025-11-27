"""
Company Agent

Unified agent that handles company information, delivery options, and policies
using RAG from a company PDF document.

Tools:
1. search_company_info - RAG search through company document
2. get_structured_data - Get structured data (delivery options, locations, etc.)
"""

import os
from typing import List, Dict, Any, Optional
from pathlib import Path
import PyPDF2

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

from agents.base_agent import BaseAgent
from models.schemas import QueryRequest, AgentResponse
from config import DEFAULT_LLM_MODEL, LLM_TEMPERATURE, LLM_MAX_RETRIES, EMBEDDING_MODEL


class CompanyAgent(BaseAgent):
    """
    Unified agent for company-related queries including:
    - Company information (contact, hours, locations)
    - Delivery options and shipping policies
    - Return policies, warranties, terms & conditions
    
    Uses RAG from a company PDF document stored in data/documents/
    """
    
    def __init__(
        self, 
        google_api_key: str, 
        documents_dir: str = "data/documents",
        vector_db_path: str = "data/vector_dbs/company"
    ):
        super().__init__(
            name="CompanyAgent",
            description="Answers questions about company info, delivery options, and policies using company documents"
        )
        
        self.google_api_key = google_api_key
        self.documents_dir = Path(documents_dir)
        self.vector_db_path = Path(vector_db_path)
        self.documents_dir.mkdir(parents=True, exist_ok=True)
        self.vector_db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize LLM
        self.llm = ChatGoogleGenerativeAI(
            model=DEFAULT_LLM_MODEL,
            temperature=LLM_TEMPERATURE,
            google_api_key=google_api_key,
            max_retries=LLM_MAX_RETRIES,
        )
        
        # Initialize embeddings
        self.embeddings = HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL,
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )
        
        # Text splitter for chunking
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=800,
            chunk_overlap=150,
            length_function=len,
        )
        
        # Vector store for company documents
        self.vector_store: Optional[FAISS] = None
        
        # Initialize vector store from documents
        self._initialize_vector_store()
        
        # System prompt for Q&A
        self.system_prompt = self._create_system_prompt()
    
    def _create_system_prompt(self) -> str:
        return """You are a helpful Company Assistant for Warehouse Supply Co.

You answer questions about:
- **Company Information**: Contact details, locations, business hours, services
- **Delivery & Shipping**: Shipping options, costs, delivery times, tracking
- **Policies**: Return policies, warranties, terms & conditions, refunds

**Instructions:**
1. Use ONLY the information provided in the context
2. If the context doesn't contain the answer, say "I don't have that specific information. Please contact our customer service."
3. Be clear, concise, and professional
4. For pricing/delivery questions, provide specific numbers when available
5. For contact info, provide complete details (phone, email, address)
6. Suggest follow-up actions when appropriate

**Response Style:**
- Start with a direct answer
- Provide relevant details
- Keep responses conversational but professional"""

    def can_handle(self, query: str) -> bool:
        """Check if query is company/delivery/policy related."""
        keywords = [
            # Company info
            "company", "contact", "phone", "email", "address", "location",
            "hours", "open", "close", "where", "office", "warehouse", "about",
            # Delivery
            "delivery", "shipping", "ship", "send", "deliver", "eta", "arrival",
            "express", "overnight", "pickup", "tracking", "how long", "how fast",
            # Policy
            "policy", "return", "refund", "warranty", "terms", "conditions",
            "exchange", "cancel", "cancellation",
        ]
        return any(keyword in query.lower() for keyword in keywords)
    
    def _initialize_vector_store(self) -> None:
        """Initialize or load the vector store from company documents."""
        
        # Try to load existing vector store
        if self.vector_db_path.exists():
            try:
                print(f"[CompanyAgent] Loading existing vector store from {self.vector_db_path}")
                self.vector_store = FAISS.load_local(
                    str(self.vector_db_path),
                    self.embeddings,
                    allow_dangerous_deserialization=True
                )
                print("[CompanyAgent] Vector store loaded successfully")
                return
            except Exception as e:
                print(f"[CompanyAgent] Error loading vector store: {e}")
        
        # Create new vector store from documents
        self._build_vector_store()
    
    def _build_vector_store(self) -> None:
        """Build vector store from PDF documents in the documents directory."""
        
        if not self.documents_dir.exists():
            print(f"[CompanyAgent] Documents directory not found: {self.documents_dir}")
            return
        
        # Find all PDF files
        pdf_files = list(self.documents_dir.glob("*.pdf"))
        
        if not pdf_files:
            print(f"[CompanyAgent] No PDF files found in {self.documents_dir}")
            print("[CompanyAgent] Please add company.pdf or other documents to data/documents/")
            return
        
        print(f"[CompanyAgent] Found {len(pdf_files)} PDF file(s)")
        
        all_chunks = []
        
        for pdf_path in pdf_files:
            try:
                print(f"[CompanyAgent] Processing: {pdf_path.name}")
                text_content = self._extract_text_from_pdf(str(pdf_path))
                
                if text_content.strip():
                    # Create document with metadata
                    doc = Document(
                        page_content=text_content,
                        metadata={"source": pdf_path.name}
                    )
                    
                    # Split into chunks
                    chunks = self.text_splitter.split_documents([doc])
                    all_chunks.extend(chunks)
                    print(f"[CompanyAgent] Created {len(chunks)} chunks from {pdf_path.name}")
                    
            except Exception as e:
                print(f"[CompanyAgent] Error processing {pdf_path.name}: {e}")
        
        if all_chunks:
            # Create vector store
            print(f"[CompanyAgent] Creating vector store with {len(all_chunks)} total chunks")
            self.vector_store = FAISS.from_documents(all_chunks, self.embeddings)
            
            # Save vector store
            self.vector_store.save_local(str(self.vector_db_path))
            print(f"[CompanyAgent] Vector store saved to {self.vector_db_path}")
        else:
            print("[CompanyAgent] No content extracted from documents")
    
    def _extract_text_from_pdf(self, file_path: str) -> str:
        """Extract text content from PDF file."""
        text = ""
        
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                for page_num, page in enumerate(pdf_reader.pages):
                    page_text = page.extract_text()
                    if page_text:
                        text += f"\n--- Page {page_num + 1} ---\n"
                        text += page_text
        
        except Exception as e:
            print(f"[CompanyAgent] Error extracting text from {file_path}: {e}")
            raise
        
        return text
    
    # ==================== TOOL 1: search_company_info ====================
    async def search_company_info(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """
        Tool 1: Search company documents using RAG.
        
        Args:
            query: The search query
            k: Number of results to return
            
        Returns:
            List of relevant document chunks with scores
        """
        if self.vector_store is None:
            return []
        
        try:
            results = self.vector_store.similarity_search_with_score(query, k=k)
            
            formatted_results = []
            for doc, score in results:
                # Convert distance to similarity score (convert numpy.float32 to Python float)
                similarity = float(1 / (1 + score))
                
                formatted_results.append({
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "score": round(similarity, 3)
                })
            
            return formatted_results
            
        except Exception as e:
            print(f"[CompanyAgent] Search error: {e}")
            return []
    
    # ==================== TOOL 2: get_structured_data ====================
    async def get_structured_data(self, data_type: str) -> Dict[str, Any]:
        """
        Tool 2: Get structured information extracted from context.
        
        Args:
            data_type: Type of data to retrieve:
                - "delivery_options": Shipping methods and costs
                - "locations": Store/warehouse locations
                - "contact": Contact information
                - "hours": Business hours
                - "policies_summary": Quick policy summary
        
        Returns:
            Structured data dictionary
        """
        if self.vector_store is None:
            return {"error": "No company documents loaded"}
        
        # Search for relevant content based on data type
        search_queries = {
            "delivery_options": "shipping delivery options costs express overnight standard",
            "locations": "location address warehouse office branch",
            "contact": "contact phone email customer service support",
            "hours": "business hours open close operating schedule",
            "policies_summary": "return policy warranty refund exchange terms"
        }
        
        query = search_queries.get(data_type, data_type)
        results = await self.search_company_info(query, k=3)
        
        if not results:
            return {"error": f"No information found for {data_type}"}
        
        # Use LLM to extract structured data
        context = "\n\n".join([r["content"] for r in results])
        
        extraction_prompt = f"""Based on the following context, extract structured information about "{data_type}".

Context:
{context}

Return the information in a clear, organized format. If specific details are not available, indicate "Not specified".
Focus only on {data_type} information."""

        try:
            messages = [
                SystemMessage(content="You extract and organize information from documents. Be concise and accurate."),
                HumanMessage(content=extraction_prompt)
            ]
            
            response = await self.llm.ainvoke(messages)
            
            return {
                "data_type": data_type,
                "content": response.content.strip(),
                "sources": [r["metadata"] for r in results]
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    # ==================== Main Query Processing ====================
    async def process_query(self, request: QueryRequest) -> AgentResponse:
        """Process query using RAG on company documents."""
        
        try:
            query = request.query
            
            # Check if vector store is available
            if self.vector_store is None:
                return AgentResponse(
                    agent_name=self.name,
                    response="I'm sorry, but the company information database is not currently available. "
                             "Please ensure company documents are placed in data/documents/ and restart the application. "
                             "You can also contact customer service directly at support@warehousesupply.com",
                    success=False,
                    error="Vector store not initialized - no documents found"
                )
            
            # Tool 1: Search for relevant information
            print(f"[CompanyAgent] Searching for: {query}")
            retrieved_chunks = await self.search_company_info(query, k=5)
            
            if not retrieved_chunks:
                return AgentResponse(
                    agent_name=self.name,
                    response="I couldn't find specific information about that in our company documents. "
                             "Please contact customer service at support@warehousesupply.com or call (555) 123-4567.",
                    success=True,
                    data={"retrieved_chunks": 0}
                )
            
            # Format context from retrieved chunks
            context = self._format_context(retrieved_chunks)
            
            # Get conversation history if available
            history = request.metadata.get("history", []) if request.metadata else []
            
            # Generate answer using LLM
            response_text = await self._generate_answer(query, context, history)
            
            return AgentResponse(
                agent_name=self.name,
                response=response_text,
                success=True,
                data={
                    "retrieved_chunks": len(retrieved_chunks),
                    "relevance_scores": [float(chunk["score"]) for chunk in retrieved_chunks],
                    "sources": [chunk["metadata"] for chunk in retrieved_chunks],
                    "tools_used": ["search_company_info"]
                }
            )
            
        except Exception as e:
            print(f"[CompanyAgent] Error: {e}")
            import traceback
            traceback.print_exc()
            
            return AgentResponse(
                agent_name=self.name,
                response="I encountered an error while looking up company information. Please try again or contact customer service.",
                success=False,
                error=str(e)
            )
    
    def _format_context(self, chunks: List[Dict[str, Any]]) -> str:
        """Format retrieved chunks into context for LLM."""
        context_parts = []
        
        for i, chunk in enumerate(chunks, 1):
            score = chunk["score"]
            content = chunk["content"].strip()
            source = chunk["metadata"].get("source", "Unknown")
            
            context_parts.append(f"[Source: {source} | Relevance: {score:.2f}]\n{content}")
        
        return "\n\n---\n\n".join(context_parts)
    
    async def _generate_answer(
        self, 
        query: str, 
        context: str, 
        history: List[Dict[str, str]] = None
    ) -> str:
        """Generate answer using LLM with context."""
        
        # Build conversation history context
        history_context = ""
        if history:
            history_parts = []
            for msg in history[-3:]:  # Last 3 messages
                role = msg.get("role", "user")
                content = msg.get("content", "")
                history_parts.append(f"{role.capitalize()}: {content}")
            history_context = "\n".join(history_parts)
        
        user_prompt = f"""Context from company documents:
{context}

{"Previous conversation:" + chr(10) + history_context + chr(10) if history_context else ""}
User Question: {query}

Please provide a helpful answer based on the context above."""

        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        try:
            response = await self.llm.ainvoke(messages)
            return response.content.strip()
        except Exception as e:
            print(f"[CompanyAgent] LLM error: {e}")
            return "I encountered an error generating a response. Please try again."
    
    def rebuild_vector_store(self) -> bool:
        """Force rebuild of vector store from documents."""
        try:
            # Delete existing vector store
            if self.vector_db_path.exists():
                import shutil
                shutil.rmtree(self.vector_db_path)
            
            # Rebuild
            self._build_vector_store()
            return self.vector_store is not None
            
        except Exception as e:
            print(f"[CompanyAgent] Error rebuilding vector store: {e}")
            return False
