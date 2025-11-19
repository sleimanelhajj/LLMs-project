"""
Orchestrator Agent

Main coordinator that routes user queries to specialized agents using LLM-based intent detection.
"""

from typing import List, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage

from agents.base_agent import BaseAgent
from agents.catalog_agent import CatalogAgent
from agents.delivery_agent import DeliveryAgent
from agents.company_info_agent import CompanyInfoAgent
from agents.policy_agent import PolicyAgent
from agents.pdf_agent import PDFAnalysisAgent
from agents.invoice_generator_agent import InvoiceGeneratorAgent
from models.schemas import QueryRequest, AgentResponse
from utils.vector_db_manager import initialize_policy_vector_db
from config import (
    DEFAULT_LLM_MODEL,
    LLM_TEMPERATURE,
    LLM_MAX_RETRIES,
    CATALOG_DB_PATH,
    GOOGLE_API_KEY,
)
import traceback


class OrchestratorAgent(BaseAgent):
    def __init__(
        self,
        google_api_key: str,
        catalog_db_path: str,
    ):
        super().__init__(
            name="OrchestratorAgent",
            description="Routes queries to appropriate specialized agents"
        )
        
        # Initialize LLM for routing decisions
        self.llm = ChatGoogleGenerativeAI(
            model=DEFAULT_LLM_MODEL,
            temperature=LLM_TEMPERATURE,
            google_api_key=google_api_key,
            max_retries=LLM_MAX_RETRIES,
        )

        # initialize policy vector database
        print("Initializing policy vector database...")
        policy_vector_db = initialize_policy_vector_db()

        # Initialize all specialized agents
        self.agents: List[BaseAgent] = [
            CatalogAgent(db_path=catalog_db_path, google_api_key=google_api_key),
            DeliveryAgent(config_path="data/delivery_rules.yaml"),
            CompanyInfoAgent(config_path="data/company_info.yaml"),
            PolicyAgent(
                vector_db_manager=policy_vector_db, google_api_key=google_api_key
            ),
            PDFAnalysisAgent(google_api_key=google_api_key),
            InvoiceGeneratorAgent(
                google_api_key=google_api_key, db_path=catalog_db_path
            ),
        ]

        # Create agent descriptions for LLM
        self.agent_descriptions = self._build_agent_descriptions()
    
    def can_handle(self, query: str) -> bool:
        """Orchestrator handles all queries by routing to appropriate agents."""
        return True  # Orchestrator can handle everything

    def _build_agent_descriptions(self) -> str:
        """Build descriptions of available agents for LLM routing."""
        descriptions = []
        for agent in self.agents:
            descriptions.append(f"- {agent.name}: {agent.description}")
        return "\n".join(descriptions)

    def _is_general_conversation(self, query: str) -> bool:
        """Check if query is general conversation (greetings, chitchat)."""
        general_keywords = [
            "hello",
            "hi",
            "hey",
            "good morning",
            "good afternoon",
            "good evening",
            "how are you",
            "what's up",
            "thanks",
            "thank you",
            "bye",
            "goodbye",
            "nice",
            "great",
            "awesome",
            "cool",
            "recommend",
            "suggest",
            "advice",
            "what do you think",
            "opinion",
            "best",
            "better",
        ]
        query_lower = query.lower()
        return any(keyword in query_lower for keyword in general_keywords)

    async def route_query(self, query: str) -> Optional[BaseAgent]:
        """
        Use LLM to determine which agent should handle the query.
        Returns None for general conversation (handled by orchestrator).
        """

        # Check if it's general conversation first
        if self._is_general_conversation(query):
            return None  # Will be handled by orchestrator itself

        system_prompt = f"""You are a query router for a warehouse management chatbot system.

Available agents:
{self.agent_descriptions}

Your task: Analyze the user's query and determine which agent should handle it.

Rules:
1. **CatalogAgent**: Product searches, inventory, prices, SKUs, "what products", "show me", "find", specific product inquiries
2. **DeliveryAgent**: Shipping, delivery times, costs, "delivery", "shipping", "send", "how long", "when will it arrive"
3. **CompanyInfoAgent**: Contact info, locations, hours, "where are you", "contact", "hours", "address"
4. **PolicyAgent**: Returns, warranties, terms & conditions, "policy", "return", "warranty", "refund"
5. **PDFAnalysisAgent**: Questions about uploaded PDF documents, "pdf", "document", "uploaded file"
6. **InvoiceGeneratorAgent**: Invoice generation requests, "generate invoice", "create invoice", "make an invoice", "need invoice"

Important:
- For greetings/chitchat, respond with "GENERAL"
- For recommendation requests without specific context, respond with "GENERAL"
- For product-specific questions (cables, ropes, bags), choose CatalogAgent
- For invoice requests, choose InvoiceGeneratorAgent

Respond with ONLY the agent name or "GENERAL", nothing else."""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Query: {query}"),
        ]

        try:
            response = await self.llm.ainvoke(messages)
            agent_name = response.content.strip()

            # Check for general conversation
            if "general" in agent_name.lower():
                return None

            # Find matching agent
            for agent in self.agents:
                if agent.name.lower() in agent_name.lower():
                    print(f"[Orchestrator] Routing to: {agent.name}")
                    return agent

            # If still no match, return None for general handling
            return None

        except Exception as e:
            print(f"[Orchestrator] Routing error: {e}")
            return None  # Handle as general conversation on error

    async def _handle_general_conversation(self, query: str) -> str:
        """Handle general conversation using LLM."""

        system_prompt = """You are a friendly warehouse assistant chatbot. 

Your personality:
- Professional but warm
- Helpful and knowledgeable
- Brief and to the point

Context: You work for Warehouse Supply Co., which sells industrial supplies like ropes, wire, bags, and accessories.

Your capabilities:
- Answer product questions
- Provide delivery information
- Share company details
- Explain policies
- Analyze uploaded PDFs
- Generate invoices

Guidelines:
- For greetings: Be warm and invite them to ask about products/services
- For thanks: Be gracious and ask if they need anything else
- For recommendations: Ask clarifying questions about their needs
- For advice: Guide them based on their use case
- Keep responses concise (2-3 sentences max)"""

        messages = [SystemMessage(content=system_prompt), HumanMessage(content=query)]

        response = await self.llm.ainvoke(messages)
        return response.content.strip()

    async def process_query(self, request: QueryRequest) -> AgentResponse:
        """
        Process query by routing to appropriate agent.
        """
        try:
            # Check if we're in the middle of an invoice conversation
            metadata = request.metadata or {}
            invoice_state = metadata.get("invoice_state", {})

            # If there's an active invoice state and it's not "start", route to InvoiceGeneratorAgent
            if invoice_state and invoice_state.get("step") != "start":
                print(
                    f"[Orchestrator] Continuing invoice conversation (step: {invoice_state.get('step')})"
                )
                # Find InvoiceGeneratorAgent
                for agent in self.agents:
                    if agent.name == "InvoiceGeneratorAgent":
                        return await agent.process_query(request)

            # Route to appropriate agent
            agent = await self.route_query(request.query)

            # Handle general conversation by orchestrator
            if not agent:
                print("[Orchestrator] Handling as general conversation")
                response_text = await self._handle_general_conversation(request.query)
                return AgentResponse(
                    agent_name="WarehouseAssistant",
                    response=response_text,
                    success=True,
                )

            # Let the agent handle the query
            response = await agent.process_query(request)

            return response

        except Exception as e:
            print(f"[Orchestrator] Error: {e}")

            traceback.print_exc()

            return AgentResponse(
                agent_name=self.name,
                response="I encountered an error processing your request. Please try again.",
                success=False,
                error=str(e),
            )
