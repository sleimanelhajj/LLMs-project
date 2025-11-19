"""
PDF Analysis Agent

Handles runtime PDF upload and analysis using temporary RAG.
This is a custom tool that extracts text from PDFs and answers questions using vector search.
"""

import os
import asyncio
from typing import List, Dict, Any, Optional
from pathlib import Path
import PyPDF2
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_huggingface import HuggingFaceEmbeddings  # Updated import
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

from agents.base_agent import BaseAgent
from models.schemas import QueryRequest, AgentResponse
from config import DEFAULT_LLM_MODEL, LLM_TEMPERATURE, LLM_MAX_RETRIES, EMBEDDING_MODEL


class PDFAnalysisAgent(BaseAgent):
    """
    Agent for analyzing uploaded PDF documents using RAG.
    Creates temporary vector stores for each PDF session.
    """
    
    def __init__(self, google_api_key: str, upload_dir: str = "data/uploads"):
        super().__init__(
            name="PDFAnalysisAgent",
            description="Analyzes PDF documents and answers questions about their content using RAG"
        )
        self.google_api_key = google_api_key
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        
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
        
        # Store active PDF sessions (session_id -> vector_store)
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        
        # Text splitter for chunking
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
        )
    
    def can_handle(self, query: str) -> bool:
        """Check if query is PDF-related."""
        keywords = [
            "pdf", "document", "file", "upload", "analyze",
            "invoice", "contract", "report", "document"
        ]
        return any(keyword in query.lower() for keyword in keywords)
    
    async def upload_pdf(self, file_path: str, session_id: str) -> Dict[str, Any]:
        """
        Upload and process a PDF file.
        
        Args:
            file_path: Path to the PDF file
            session_id: Unique session identifier
            
        Returns:
            Dict with status and metadata
        """
        try:
            print(f"[PDFAgent] Processing PDF: {file_path}")
            
            # Extract text from PDF
            text_content = self._extract_text_from_pdf(file_path)
            
            if not text_content.strip():
                return {
                    "success": False,
                    "error": "Could not extract text from PDF. File may be empty or image-based."
                }
            
            # Create chunks
            chunks = self._create_chunks(text_content)
            
            print(f"[PDFAgent] Created {len(chunks)} chunks")
            
            # Create temporary vector store
            vector_store = await self._create_vector_store(chunks)
            
            # Store session data
            self.active_sessions[session_id] = {
                "file_path": file_path,
                "file_name": Path(file_path).name,
                "vector_store": vector_store,
                "chunk_count": len(chunks),
                "text_length": len(text_content)
            }
            
            print(f"[PDFAgent] PDF processed successfully for session {session_id}")
            
            return {
                "success": True,
                "file_name": Path(file_path).name,
                "chunks": len(chunks),
                "text_length": len(text_content),
                "message": f"Successfully processed {Path(file_path).name}. You can now ask questions about it."
            }
            
        except Exception as e:
            print(f"[PDFAgent] Error processing PDF: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e)
            }
    
    def _extract_text_from_pdf(self, file_path: str) -> str:
        """Extract text content from PDF file."""
        text = ""
        
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                print(f"[PDFAgent] PDF has {len(pdf_reader.pages)} pages")
                
                for page_num, page in enumerate(pdf_reader.pages):
                    page_text = page.extract_text()
                    if page_text:
                        text += f"\n--- Page {page_num + 1} ---\n"
                        text += page_text
        
        except Exception as e:
            print(f"[PDFAgent] Error extracting text: {e}")
            raise
        
        return text
    
    def _create_chunks(self, text: str) -> List[Document]:
        """Split text into chunks for vector store."""
        # Split text into chunks
        text_chunks = self.text_splitter.split_text(text)
        
        # Create Document objects
        documents = [
            Document(page_content=chunk, metadata={"chunk_id": i})
            for i, chunk in enumerate(text_chunks)
        ]
        
        return documents
    
    async def _create_vector_store(self, documents: List[Document]) -> FAISS:
        """Create FAISS vector store from documents."""
        try:
            # Create embeddings for all documents
            vector_store = FAISS.from_documents(
                documents=documents,
                embedding=self.embeddings
            )
            
            return vector_store
            
        except Exception as e:
            print(f"[PDFAgent] Error creating vector store: {e}")
            raise
    
    async def process_query(self, request: QueryRequest) -> AgentResponse:
        """Process a query about an uploaded PDF."""
        try:
            session_id = request.session_id or "default"
            query = request.query
            
            # Check if PDF is uploaded for this session
            if session_id not in self.active_sessions:
                return AgentResponse(
                    agent_name=self.name,
                    response="No PDF has been uploaded yet. Please upload a PDF file first using the upload_pdf method.",
                    success=False,
                    error="No active PDF session"
                )
            
            session_data = self.active_sessions[session_id]
            vector_store = session_data["vector_store"]
            
            print(f"[PDFAgent] Querying PDF: {session_data['file_name']}")
            
            # Search for relevant chunks
            relevant_docs = vector_store.similarity_search(query, k=5)
            
            if not relevant_docs:
                return AgentResponse(
                    agent_name=self.name,
                    response="I couldn't find relevant information in the PDF to answer your question.",
                    success=True
                )
            
            # Generate response using LLM
            response_text = await self._generate_answer(query, relevant_docs, session_data)
            
            return AgentResponse(
                agent_name=self.name,
                response=response_text,
                data={
                    "file_name": session_data["file_name"],
                    "retrieved_chunks": len(relevant_docs),
                    "chunks": [doc.page_content[:200] + "..." for doc in relevant_docs]
                },
                success=True
            )
            
        except Exception as e:
            print(f"[PDFAgent] Error processing query: {e}")
            import traceback
            traceback.print_exc()
            return AgentResponse(
                agent_name=self.name,
                response="I encountered an error while analyzing the PDF.",
                success=False,
                error=str(e)
            )
    
    async def _generate_answer(self, query: str, documents: List[Document], session_data: Dict) -> str:
        """Generate answer using LLM based on retrieved chunks."""
        
        # Format context from documents
        context = "\n\n".join([
            f"[Chunk {i+1}]\n{doc.page_content}"
            for i, doc in enumerate(documents)
        ])
        
        system_prompt = f"""You are a helpful assistant analyzing a PDF document.

Document: {session_data['file_name']}

Your task:
1. Answer the user's question based ONLY on the provided context
2. If the answer is not in the context, say so clearly
3. Cite specific information from the document
4. Be concise but thorough
5. If relevant, mention page numbers or sections

Context from document:
{context}"""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=query)
        ]
        
        response = await self.llm.ainvoke(messages)
        return response.content.strip()
    
    def clear_session(self, session_id: str) -> bool:
        """Clear a PDF session and free up memory."""
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
            print(f"[PDFAgent] Cleared session {session_id}")
            return True
        return False
    
    def get_active_sessions(self) -> List[Dict[str, Any]]:
        """Get list of active PDF sessions."""
        return [
            {
                "session_id": sid,
                "file_name": data["file_name"],
                "chunks": data["chunk_count"]
            }
            for sid, data in self.active_sessions.items()
        ]


# Test function
async def test_pdf_agent():
    """Test the PDF Analysis Agent."""
    import os
    from config import GOOGLE_API_KEY
    
    if not GOOGLE_API_KEY:
        print("❌ GOOGLE_API_KEY not found")
        return
    
    print("=" * 80)
    print("PDF ANALYSIS AGENT TEST")
    print("=" * 80 + "\n")
    
    agent = PDFAnalysisAgent(google_api_key=GOOGLE_API_KEY)
    
    # Test with invoice
    test_pdf_path = "data/test_documents/sample_invoice.pdf"
    
    if not os.path.exists(test_pdf_path):
        print(f"⚠️  Test PDF not found at: {test_pdf_path}")
        print("Run: python scripts/create_sample_pdfs.py")
        return
    
    # Upload PDF
    print("📄 Uploading invoice PDF...")
    upload_result = await agent.upload_pdf(test_pdf_path, session_id="test_session")
    
    if upload_result["success"]:
        print(f"✅ {upload_result['message']}")
        print(f"   Chunks: {upload_result['chunks']}")
        print(f"   Text length: {upload_result['text_length']} characters\n")
    else:
        print(f"❌ Upload failed: {upload_result['error']}")
        return
    
    # Test queries
    test_queries = [
        "What is this document about?",
        "What is the total amount?",
        "Who is the customer?",
        "What items are listed in the invoice?",
        "What are the payment terms?",
    ]
    
    print("=" * 80)
    print("TESTING QUERIES")
    print("=" * 80 + "\n")
    
    for i, query in enumerate(test_queries, 1):
        print(f"[{i}/{len(test_queries)}] 👤 USER: {query}")
        
        request = QueryRequest(query=query, session_id="test_session")
        response = await agent.process_query(request)
        
        print(f"🤖 {response.agent_name}:")
        print(response.response)
        
        if response.data:
            print(f"\n   📊 Retrieved {response.data.get('retrieved_chunks', 0)} chunks")
        
        print("\n" + "-" * 80 + "\n")
        await asyncio.sleep(2)  # Rate limit
    
    # Clear session
    agent.clear_session("test_session")
    print("✅ Session cleared")
    
    print("=" * 80)
    print("✅ TEST COMPLETED")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_pdf_agent())