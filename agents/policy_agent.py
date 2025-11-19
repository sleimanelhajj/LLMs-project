import os
from typing import List, Dict, Any
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate

from agents.base_agent import BaseAgent
from models.schemas import QueryRequest, AgentResponse
from utils.vector_db_manager import VectorDBManager
from config import DEFAULT_LLM_MODEL, LLM_TEMPERATURE, GOOGLE_API_KEY


class PolicyAgent(BaseAgent):
    def __init__(
        self,
        vector_db_manager: VectorDBManager,
        google_api_key: str = GOOGLE_API_KEY,
    ):
        super().__init__(
            name="PolicyAgent",
            description="Answers company policy questions using RAG on policy documents",
        )

        self.vector_db = vector_db_manager

        if not google_api_key:
            raise ValueError("Google API key required for PolicyAgent")

        self.llm = ChatGoogleGenerativeAI(
            model=DEFAULT_LLM_MODEL,
            temperature=LLM_TEMPERATURE,
            google_api_key=google_api_key,
        )

        # System prompt for policy Q&A
        self.system_prompt = self._create_system_prompt()

    def _create_system_prompt(self) -> str:
        return """You are a Policy Assistant for Warehouse Solutions Inc.

Your role is to answer questions about company policies accurately based on the provided context.

**Instructions:**
1. Use ONLY the information provided in the context
2. If the context doesn't contain the answer, say "I don't have information about that in our policies"
3. Be clear, concise, and helpful
4. Quote specific policy sections when relevant
5. If multiple policies apply, mention all relevant ones
6. Do not make up information or policies

**Response Format:**
- Start with a direct answer
- Provide relevant policy details
- Include section references if applicable
- Suggest follow-up actions if needed (e.g., "Contact customer service for...")

Be professional and customer-service oriented."""

    def can_handle(self, query: str) -> bool:
        """Check if query is policy-related."""
        policy_keywords = [
            "policy",
            "return",
            "refund",
            "warranty",
            "shipping",
            "payment",
            "tax",
            "discount",
            "account",
            "privacy",
            "complaint",
            "dispute",
            "terms",
            "conditions",
        ]
        return any(keyword in query.lower() for keyword in policy_keywords)

    async def process_query(self, request: QueryRequest) -> AgentResponse:
        """Process policy query using RAG."""
        try:
            query = request.query

            # Get conversation history from metadata
            history = request.metadata.get("history", []) if request.metadata else []

            # Check if vector store is available
            if self.vector_db.vector_store is None:
                return AgentResponse(
                    agent_name=self.name,
                    response="I'm sorry, but the policy database is not currently available. Please contact customer service directly.",
                    success=False,
                    error="Vector store not initialized",
                )

            # Retrieve relevant policy sections
            print(f"Searching policies for: {query}")
            retrieved_chunks = self.vector_db.similarity_search(query, k=5)

            if not retrieved_chunks:
                return AgentResponse(
                    agent_name=self.name,
                    response="I couldn't find specific information about that in our policy documents. Please contact customer service at support@warehousesolutions.com for clarification.",
                    success=True,
                    data={"retrieved_chunks": 0},
                )

            # format context from retrieved chunks
            context = self._format_context(retrieved_chunks)

            # Generate answer using LLM with conversation history
            response_text = await self._generate_answer(query, context, history)

            return AgentResponse(
                agent_name=self.name,
                response=response_text,
                success=True,
                data={
                    "retrieved_chunks": len(retrieved_chunks),
                    "relevance_scores": [
                        float(chunk["score"]) for chunk in retrieved_chunks
                    ],  
                    "sources": [chunk["metadata"] for chunk in retrieved_chunks],
                },
            )

        except Exception as e:
            return AgentResponse(
                agent_name=self.name,
                response="I encountered an error while looking up policy information. Please try again or contact customer service.",
                success=False,
                error=str(e),
            )

    def _format_context(self, chunks: List[Dict[str, Any]]) -> str:
        """Format retrieved chunks into context for LLM."""
        context_parts = []

        for i, chunk in enumerate(chunks, 1):
            score = chunk["score"]
            content = chunk["content"].strip()

            context_parts.append(f"[Source {i} - Relevance: {score:.2f}]\n{content}\n")

        return "\n---\n".join(context_parts)

    async def _generate_answer(
        self, query: str, context: str, history: List[Dict[str, str]] = None
    ) -> str:
        # Build conversation history context
        history_text = ""
        if history and len(history) > 0:
            history_text = "\n\nCONVERSATION HISTORY:\n"
            for msg in history[-4:]:  # Last 4 messages (2 exchanges)
                role = "User" if msg.get("role") == "user" else "Assistant"
                content = msg.get("content", "")
                history_text += f"{role}: {content}\n"

        prompt = f"""Based on the following policy information and conversation history, answer the user's question.

POLICY CONTEXT:
{context}
{history_text}

USER QUESTION: {query}

Please provide a clear, helpful answer. If the question is a follow-up or clarification based on the conversation history, use that context to provide a more relevant answer. If the question is general (like "what does refund mean?"), provide a helpful general explanation."""

        messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=prompt),
        ]

        response = await self.llm.ainvoke(messages)
        return response.content


