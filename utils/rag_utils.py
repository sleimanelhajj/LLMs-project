"""
RAG / Vector Database utilities for company documents.

Handles PDF loading, chunking, embedding, and similarity search.
"""

import os
from typing import Optional, List, Dict, Any
from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

from config import (
    EMBEDDING_MODEL, CHUNK_SIZE, CHUNK_OVERLAP, 
    RETRIEVAL_K, MIN_SCORE, DATA_DIR
)


# Global vector store for company documents
_company_vector_store: Optional[FAISS] = None
_embeddings: Optional[HuggingFaceEmbeddings] = None

# Paths for company documents and vector store
COMPANY_DOCS_DIR = os.path.join(DATA_DIR, "documents")
COMPANY_VECTOR_DB_PATH = os.path.join(DATA_DIR, "vector_dbs", "company_vectordb")


def _get_embeddings() -> HuggingFaceEmbeddings:
    """Get or create the embeddings model (singleton pattern)."""
    global _embeddings
    if _embeddings is None:
        print(f"[RAG] Initializing embeddings model: {EMBEDDING_MODEL}")
        _embeddings = HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )
    return _embeddings


def _load_and_chunk_pdf(file_path: str) -> List[Document]:
    """Load a PDF and split it into chunks."""
    try:
        loader = PyPDFLoader(file_path)
        documents = loader.load()
        print(f"[RAG] Loaded {len(documents)} pages from {file_path}")
        
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            length_function=len,
            separators=["\n\n", "\n", " ", ""],
        )
        
        chunks = text_splitter.split_documents(documents)
        print(f"[RAG] Created {len(chunks)} chunks")
        return chunks
    except Exception as e:
        print(f"[RAG] Error loading PDF {file_path}: {e}")
        return []


def initialize_company_vector_db() -> Optional[FAISS]:
    """Initialize or load the company documents vector database."""
    global _company_vector_store
    
    embeddings = _get_embeddings()
    
    # Try to load existing vector store
    if os.path.exists(COMPANY_VECTOR_DB_PATH):
        try:
            print(f"[RAG] Loading existing vector store from {COMPANY_VECTOR_DB_PATH}")
            _company_vector_store = FAISS.load_local(
                COMPANY_VECTOR_DB_PATH,
                embeddings,
                allow_dangerous_deserialization=True
            )
            print("[RAG] Vector store loaded successfully")
            return _company_vector_store
        except Exception as e:
            print(f"[RAG] Error loading vector store: {e}")
    
    # Build new vector store from documents
    if not os.path.exists(COMPANY_DOCS_DIR):
        print(f"[RAG] Documents directory not found: {COMPANY_DOCS_DIR}")
        return None
    
    # Find PDF files
    pdf_files = list(Path(COMPANY_DOCS_DIR).glob("*.pdf"))
    if not pdf_files:
        print(f"[RAG] No PDF files found in {COMPANY_DOCS_DIR}")
        return None
    
    print(f"[RAG] Found {len(pdf_files)} PDF file(s)")
    
    # Load and chunk all documents
    all_chunks = []
    for pdf_file in pdf_files:
        chunks = _load_and_chunk_pdf(str(pdf_file))
        all_chunks.extend(chunks)
    
    if not all_chunks:
        print("[RAG] No chunks created from documents")
        return None
    
    # Create vector store
    print(f"[RAG] Creating vector store with {len(all_chunks)} chunks...")
    _company_vector_store = FAISS.from_documents(
        documents=all_chunks,
        embedding=embeddings
    )
    
    # Save for future use
    os.makedirs(os.path.dirname(COMPANY_VECTOR_DB_PATH), exist_ok=True)
    _company_vector_store.save_local(COMPANY_VECTOR_DB_PATH)
    print(f"[RAG] Vector store saved to {COMPANY_VECTOR_DB_PATH}")
    
    return _company_vector_store


def search_company_vector_db(query: str, k: int = RETRIEVAL_K) -> List[Dict[str, Any]]:
    """
    Search the company documents vector database.
    
    Args:
        query: The search query
        k: Number of results to return
        
    Returns:
        List of relevant document chunks with scores
    """
    global _company_vector_store
    
    if _company_vector_store is None:
        _company_vector_store = initialize_company_vector_db()
    
    if _company_vector_store is None:
        return []
    
    try:
        results = _company_vector_store.similarity_search_with_score(query, k=k)
        
        filtered_results = []
        for doc, score in results:
            # Convert distance to similarity (FAISS returns L2 distance)
            similarity = 1 / (1 + score)
            
            if similarity >= MIN_SCORE:
                filtered_results.append({
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "score": round(similarity, 3),
                })
        
        return filtered_results
    except Exception as e:
        print(f"[RAG] Error during search: {e}")
        return []
