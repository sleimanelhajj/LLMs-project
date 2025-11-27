"""
Orchestrator Agent

Main coordinator that routes user queries to specialized agents using LLM-based intent detection.
"""

from typing import List, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage

from agents.base_agent import BaseAgent
from agents.catalog_agent import CatalogAgent
from agents.company_agent import CompanyAgent
from agents.invoice_generator_agent import InvoiceGeneratorAgent
from agents.order_tracking_agent import OrderTrackingAgent
from agents.report_agent import ReportAgent
from models.schemas import QueryRequest, AgentResponse
from config import DEFAULT_LLM_MODEL, LLM_TEMPERATURE, LLM_MAX_RETRIES
import traceback


class OrchestratorAgent(BaseAgent):
    def __init__(self, google_api_key: str, catalog_db_path: str):
        super().__init__(
            name="OrchestratorAgent",
            description="Routes queries to appropriate specialized agents",
        )

        self.llm = ChatGoogleGenerativeAI(
            model=DEFAULT_LLM_MODEL,
            temperature=LLM_TEMPERATURE,
            google_api_key=google_api_key,
            max_retries=LLM_MAX_RETRIES,
        )

        self.agents: List[BaseAgent] = [
            CatalogAgent(db_path=catalog_db_path, google_api_key=google_api_key),
            CompanyAgent(google_api_key=google_api_key, documents_dir="data/documents"),
            InvoiceGeneratorAgent(google_api_key=google_api_key, db_path=catalog_db_path),
            OrderTrackingAgent(),
            ReportAgent(),
        ]

        self.agent_descriptions = self._build_agent_descriptions()

    def can_handle(self, query: str) -> bool:
        return True

    def _build_agent_descriptions(self) -> str:
        descriptions = []
        for agent in self.agents:
            descriptions.append(f"- {agent.name}: {agent.description}")
        return "\n".join(descriptions)

    def _is_general_conversation(self, query: str) -> bool:
        """Check if query is purely social/greeting - NOT product questions."""
        general_keywords = [
            "hello", "hi", "hey", "good morning", "good afternoon", "good evening",
            "how are you", "what's up", "thanks", "thank you", "bye", "goodbye",
            "nice to meet", "great talking",
        ]
        query_lower = query.lower()
        
        # If query mentions products, it's NOT general conversation
        product_keywords = [
            "rope", "wire", "bag", "cable", "nylon", "polypropylene", "canvas",
            "product", "buy", "purchase", "recommend", "better", "best", "which one",
            "strength", "heavy", "blocks", "attach", "price", "stock", "inventory"
        ]
        if any(keyword in query_lower for keyword in product_keywords):
            return False
        
        # If query is about orders, it's NOT general conversation
        order_keywords = [
            "order", "track", "tracking", "delivery", "shipped", "shipping",
            "where is my", "order history", "my orders", "status"
        ]
        if any(keyword in query_lower for keyword in order_keywords):
            return False
        
        # If query is about reports, it's NOT general conversation
        report_keywords = [
            "report", "sales", "revenue", "inventory", "stock level", "analytics",
            "low stock", "best seller", "top product",
            # Time periods often used in report follow-ups
            "7 days", "30 days", "90 days", "all time", "last week", "last month"
        ]
        if any(keyword in query_lower for keyword in report_keywords):
            return False
        
        return any(keyword in query_lower for keyword in general_keywords)

    async def route_query(self, query: str, last_agent: str = None) -> Optional[BaseAgent]:
        if self._is_general_conversation(query):
            return None

        system_prompt = f"""You are a query router for a warehouse management chatbot system.

Available agents:
{self.agent_descriptions}

Your task: Analyze the user's query and determine which agent should handle it.

Rules:
1. **CatalogAgent**: Product searches, inventory, prices, SKUs, product recommendations, product comparisons, "which one is better", "recommend", "best for", strength/weight/material questions about products, anything about ropes/wires/bags/cables
2. **CompanyAgent**: Company info, contact details, locations, hours, delivery/shipping options, costs, policies, returns, warranties, refunds
3. **InvoiceGeneratorAgent**: Invoice generation requests, "generate invoice", "create invoice", "make an invoice", "need invoice"
4. **OrderTrackingAgent**: Order tracking, order status, "where is my order", "track order", "order history", "my orders", delivery status, tracking number queries
5. **ReportAgent**: Sales reports, revenue analytics, inventory reports, stock levels, low stock alerts, best sellers, top products, business analytics

Important:
- For simple greetings only (hi, hello, how are you), respond with "GENERAL"
- For ANY question about products, materials, recommendations, or comparisons → CatalogAgent
- If user mentions rope, nylon, polypropylene, wire, bag, blocks, heavy, strength → CatalogAgent
- For company/delivery options/policy questions → CompanyAgent
- For invoice requests → InvoiceGeneratorAgent
- For order tracking, order status, "where is my order", order history → OrderTrackingAgent
- For sales reports, inventory reports, analytics, stock levels → ReportAgent
- IMPORTANT: If the query is a short response like a time period ("7 days", "30 days", "all time", "last month") or a confirmation ("yes", "no", "okay"), AND there was a previous agent, route to that same agent.

Previous agent (if any): {last_agent if last_agent else "None"}

Respond with ONLY the agent name or "GENERAL", nothing else."""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Query: {query}"),
        ]

        try:
            response = await self.llm.ainvoke(messages)
            agent_name = response.content.strip()

            if "general" in agent_name.lower():
                return None

            for agent in self.agents:
                if agent.name.lower() in agent_name.lower():
                    print(f"[Orchestrator] Routing to: {agent.name}")
                    return agent

            return None

        except Exception as e:
            print(f"[Orchestrator] Routing error: {e}")
            return None

    async def _handle_general_conversation(self, query: str) -> str:
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
        """Process query by routing to appropriate agent with detailed thinking logs."""
        try:
            thinking_log = []  # Collect routing decisions for transparency
            
            metadata = request.metadata or {}
            invoice_state = metadata.get("invoice_state", {})

            # Check for active invoice conversation
            if invoice_state and invoice_state.get("step") != "start":
                step = invoice_state.get('step')
                thinking_log.append(f"🔄 Detected active invoice conversation at step: {step}")
                thinking_log.append(f"✓ Routing to: InvoiceGeneratorAgent (invoice flow)")
                print(f"[Orchestrator] Continuing invoice conversation (step: {step})")
                
                for agent in self.agents:
                    if agent.name == "InvoiceGeneratorAgent":
                        response = await agent.process_query(request)
                        # Add thinking log to response metadata
                        if response.data:
                            response.data["thinking"] = thinking_log
                        else:
                            response.data = {"thinking": thinking_log}
                        return response

            # Route query to appropriate agent
            thinking_log.append(f"📝 Analyzing query: '{request.query}'")
            
            # Get last agent from metadata for context-aware routing
            last_agent = metadata.get("last_agent", None)
            if last_agent:
                thinking_log.append(f"📎 Previous agent context: {last_agent}")
            
            agent = await self.route_query(request.query, last_agent)

            # Handle general conversation
            if not agent:
                thinking_log.append("💭 Detected: General conversation / greeting")
                thinking_log.append("✓ Routing to: WarehouseAssistant (general handler)")
                print("[Orchestrator] Handling as general conversation")
                
                response_text = await self._handle_general_conversation(request.query)
                return AgentResponse(
                    agent_name="WarehouseAssistant",
                    response=response_text,
                    success=True,
                    data={"thinking": thinking_log}
                )

            # Route to specialized agent
            thinking_log.append(f"🎯 Selected agent: {agent.name}")
            thinking_log.append(f"📋 Agent capability: {agent.description}")
            thinking_log.append(f"✓ Routing to: {agent.name}")
            
            response = await agent.process_query(request)
            
            # Add thinking log and last_agent to response metadata
            if response.data:
                response.data["thinking"] = thinking_log
                response.data["last_agent"] = agent.name
            else:
                response.data = {"thinking": thinking_log, "last_agent": agent.name}
            
            return response

        except Exception as e:
            thinking_log.append(f"❌ Error during routing: {str(e)}")
            print(f"[Orchestrator] Error: {e}")
            traceback.print_exc()
            
            return AgentResponse(
                agent_name=self.name,
                response="I encountered an error processing your request. Please try again.",
                success=False,
                error=str(e),
                data={"thinking": thinking_log}
            )