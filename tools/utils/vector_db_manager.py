import os
from typing import List, Optional
from pathlib import Path

from langchain_community.document_loaders import TextLoader, PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

from config import (
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    EMBEDDING_MODEL,
    VECTOR_DB_PATH,
)


class VectorDBManager:
    def __init__(
        self, db_path: str = VECTOR_DB_PATH, embedding_model: str = EMBEDDING_MODEL
    ):
        self.db_path = db_path
        self.embedding_model = embedding_model

        print(f"Initializing embeddings model: {embedding_model}")
        self.embeddings = HuggingFaceEmbeddings(
            model_name=embedding_model,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )

        self.vector_store = self._load_or_create_vector_store()

    def _load_or_create_vector_store(self) -> Optional[FAISS]:
        if os.path.exists(self.db_path):
            try:
                print(f"Loading existing vector database from {self.db_path}")
                return FAISS.load_local(
                    self.db_path, self.embeddings, allow_dangerous_deserialization=True
                )
            except Exception as e:
                print(f"Error loading vector store: {e}")
                return None
        return None

    def create_vector_store_from_documents(self, documents: List[Document]) -> FAISS:
        vector_store = FAISS.from_documents(
            documents=documents, embedding=self.embeddings
        )
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        vector_store.save_local(self.db_path)
        return vector_store

    def load_and_chunk_documents(
        self,
        file_paths: List[str],
        chunk_size: int = CHUNK_SIZE,
        chunk_overlap: int = CHUNK_OVERLAP,
    ) -> List[Document]:
        all_documents = []
        for file_path in file_paths:
            if not os.path.exists(file_path):
                print(f"File not found: {file_path}")
                continue

            extension = Path(file_path).suffix.lower()

            # support for loading multipme file types
            try:
                if extension == ".pdf":
                    loader = PyPDFLoader(file_path)
                elif extension in [".txt", ".md"]:
                    loader = TextLoader(file_path, encoding="utf-8")
                else:
                    print(f"Unsupported file type: {extension} for file {file_path}")
                    continue

                documents = loader.load()
                print("loaded the document successfully")
                all_documents.extend(documents)

            except Exception as e:
                print(f"Error loading {file_path}: {e}")

        if not all_documents:
            print("No documents loaded")
            return []

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", " ", ""],
        )

        chunks = text_splitter.split_documents(all_documents)
        return chunks
