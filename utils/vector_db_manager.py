"""
Vector Database Manager for RAG Implementation

Handles document loading, chunking, embedding, and retrieval using FAISS.
"""

import os
from typing import List, Dict, Any, Optional
from pathlib import Path

from langchain_community.document_loaders import (
    TextLoader,
    PyPDFLoader,
    DirectoryLoader
)
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

from config import (
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    EMBEDDING_MODEL,
    VECTOR_DB_PATH,
    RETRIEVAL_K,
    MIN_SCORE
)


class VectorDBManager:
    """Manages vector database operations for RAG."""
    
    def __init__(
        self,
        db_path: str = VECTOR_DB_PATH,
        embedding_model: str = EMBEDDING_MODEL
    ):
        self.db_path = db_path
        self.embedding_model = embedding_model
        
        # Initialize embeddings
        print(f"🔧 Initializing embeddings model: {embedding_model}")
        self.embeddings = HuggingFaceEmbeddings(
            model_name=embedding_model,
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )
        
        # Load or initialize vector store
        self.vector_store = self._load_or_create_vector_store()
    
    def _load_or_create_vector_store(self) -> Optional[FAISS]:
        """Load existing vector store or return None if doesn't exist."""
        if os.path.exists(self.db_path):
            try:
                print(f"📂 Loading existing vector database from {self.db_path}")
                return FAISS.load_local(
                    self.db_path,
                    self.embeddings,
                    allow_dangerous_deserialization=True
                )
            except Exception as e:
                print(f"⚠️  Error loading vector store: {e}")
                return None
        return None
    
    def create_vector_store_from_documents(
        self,
        documents: List[Document]
    ) -> FAISS:
        """Create vector store from documents."""
        print(f"🔨 Creating vector store with {len(documents)} documents")
        
        vector_store = FAISS.from_documents(
            documents=documents,
            embedding=self.embeddings
        )
        
        # Save to disk
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        vector_store.save_local(self.db_path)
        print(f"💾 Vector store saved to {self.db_path}")
        
        return vector_store
    
    def load_and_chunk_documents(
        self,
        file_paths: List[str],
        chunk_size: int = CHUNK_SIZE,
        chunk_overlap: int = CHUNK_OVERLAP
    ) -> List[Document]:
        """Load documents and split into chunks."""
        print(f"📄 Loading {len(file_paths)} document(s)")
        
        all_documents = []
        
        for file_path in file_paths:
            if not os.path.exists(file_path):
                print(f"⚠️  File not found: {file_path}")
                continue
            
            # Determine loader based on file extension
            ext = Path(file_path).suffix.lower()
            
            try:
                if ext == '.pdf':
                    loader = PyPDFLoader(file_path)
                elif ext in ['.txt', '.md']:
                    loader = TextLoader(file_path, encoding='utf-8')
                else:
                    print(f"⚠️  Unsupported file type: {ext}")
                    continue
                
                documents = loader.load()
                print(f"  ✅ Loaded {len(documents)} page(s) from {Path(file_path).name}")
                all_documents.extend(documents)
                
            except Exception as e:
                print(f"  ❌ Error loading {file_path}: {e}")
        
        # Split documents into chunks
        if not all_documents:
            print("⚠️  No documents loaded")
            return []
        
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
        
        chunks = text_splitter.split_documents(all_documents)
        print(f"✂️  Split into {len(chunks)} chunks")
        
        return chunks
    
    def add_documents_to_store(self, documents: List[Document]):
        """Add new documents to existing vector store."""
        if self.vector_store is None:
            print("Creating new vector store")
            self.vector_store = self.create_vector_store_from_documents(documents)
        else:
            print(f"Adding {len(documents)} documents to existing store")
            self.vector_store.add_documents(documents)
            self.vector_store.save_local(self.db_path)
            print("💾 Vector store updated")
    
    def similarity_search(
        self,
        query: str,
        k: int = RETRIEVAL_K,
        min_score: float = MIN_SCORE
    ) -> List[Dict[str, Any]]:
        """
        Perform similarity search with score threshold.
        
        Returns:
            List of dicts with 'content', 'metadata', and 'score'
        """
        if self.vector_store is None:
            print("⚠️  Vector store not initialized")
            return []
        
        try:
            # Get documents with scores
            results = self.vector_store.similarity_search_with_score(query, k=k)
            
            # Filter by score and format
            filtered_results = []
            for doc, score in results:
                # FAISS returns distance, lower is better
                # Convert to similarity score (1 - normalized_distance)
                similarity = 1 / (1 + score)
                
                if similarity >= min_score:
                    filtered_results.append({
                        'content': doc.page_content,
                        'metadata': doc.metadata,
                        'score': round(similarity, 3)
                    })
            
            print(f"🔍 Found {len(filtered_results)} relevant chunks (min_score={min_score})")
            return filtered_results
            
        except Exception as e:
            print(f"❌ Error during search: {e}")
            return []
    
    def delete_vector_store(self):
        """Delete the vector store from disk."""
        if os.path.exists(self.db_path):
            import shutil
            shutil.rmtree(self.db_path)
            print(f"🗑️  Deleted vector store at {self.db_path}")
            self.vector_store = None


def initialize_policy_vector_db(policy_docs_dir: str = "data/documents") -> VectorDBManager:
    """Initialize vector database with policy documents."""
    
    print("🚀 Initializing Policy Vector Database")
    print(f"   Documents directory: {policy_docs_dir}")
    
    manager = VectorDBManager()
    
    # Check if vector store already exists
    if manager.vector_store is not None:
        print("✅ Policy vector database already initialized")
        return manager
    
    # Find all policy documents
    policy_files = []
    if os.path.exists(policy_docs_dir):
        for file in os.listdir(policy_docs_dir):
            if file.endswith(('.txt', '.pdf', '.md')):
                policy_files.append(os.path.join(policy_docs_dir, file))
    
    if not policy_files:
        print(f"⚠️  No policy documents found in {policy_docs_dir}")
        print("Please add policy documents (.txt, .pdf, .md) to the documents directory")
        return manager
    
    print(f"📚 Found {len(policy_files)} policy document(s)")
    
    # Load and process documents
    chunks = manager.load_and_chunk_documents(policy_files)
    
    if chunks:
        # Create vector store and update manager's vector_store reference
        manager.vector_store = manager.create_vector_store_from_documents(chunks)
        print("✅ Policy vector database initialized successfully")
    else:
        print("❌ Failed to create vector database - no chunks generated")
    
    return manager


if __name__ == "__main__":
    """Test vector database initialization."""
    print("=" * 80)
    print("VECTOR DATABASE MANAGER TEST")
    print("=" * 80 + "\n")
    
    # Initialize
    manager = initialize_policy_vector_db()
    
    # Test search
    if manager.vector_store:
        test_queries = [
            "What is the return policy?",
            "How long does shipping take?",
            "What are the bulk discounts?",
        ]
        
        print("\n" + "=" * 80)
        print("TESTING SEARCH FUNCTIONALITY")
        print("=" * 80 + "\n")
        
        for query in test_queries:
            print(f"\n🔍 Query: {query}")
            results = manager.similarity_search(query, k=3)
            
            for i, result in enumerate(results, 1):
                print(f"\n  Result {i} (score: {result['score']}):")
                print(f"  {result['content'][:200]}...")
            print("-" * 80)
        
        print("\n✅ All tests completed")
    else:
        print("\n⚠️  Vector store not available for testing")