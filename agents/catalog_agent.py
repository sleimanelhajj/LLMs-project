import sqlite3
import json
from typing import List, Dict, Any
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage

from agents.base_agent import BaseAgent
from models.schemas import QueryRequest, AgentResponse, ProductModel
from config import DEFAULT_LLM_MODEL, LLM_MAX_RETRIES


class CatalogAgent(BaseAgent):
    def __init__(self, db_path: str, google_api_key: str):
        super().__init__(
            name="CatalogAgent",
            description="Searches product catalog, checks inventory, provides prices and product details",
        )

        self.db_path = db_path

        self.llm = ChatGoogleGenerativeAI(
            model=DEFAULT_LLM_MODEL,
            temperature=0.3,
            google_api_key=google_api_key,
            max_retries=LLM_MAX_RETRIES,
        )

        self.catalog_summary = self._get_catalog_summary()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _get_catalog_summary(self) -> str:
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT category, COUNT(*) as count FROM products GROUP BY category")
            rows = cursor.fetchall()
            conn.close()

            summary = "Available product categories:\n"
            for row in rows:
                summary += f"- {row['category']}: {row['count']} products\n"
            return summary
        except Exception as e:
            print(f"[CatalogAgent] Summary Error: {e}")
            return "Product categories: Ropes, Wire, Bags, Accessories"

    def _execute_sql(self, query: str, params: tuple = ()) -> List[ProductModel]:
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()

            products = []
            for row in rows:
                row_dict = {
                    "id": row["id"],
                    "sku": row["sku"],
                    "name": row["name"],
                    "category": row["category"],
                    "unit_price": row["unit_price"],
                    "unit_of_measure": row["unit_of_measure"],
                    "quantity_on_hand": row["quantity_on_hand"],
                    "description": row["description"],
                    "specifications": row["specifications"],
                }
                products.append(ProductModel(**row_dict))
            return products
        except Exception as e:
            print(f"[CatalogAgent] SQL Error: {e}")
            return []

    def can_handle(self, query: str) -> bool:
        keywords = [
            "product",
            "price",
            "inventory",
            "stock",
            "sku",
            "catalog",
            "rope",
            "bag",
            "wire",
            "cost",
            "available",
            "buy",
            "purchase",
        ]
        return any(keyword in query.lower() for keyword in keywords)

    async def process_query(self, request: QueryRequest) -> AgentResponse:
        try:
            query = request.query

            search_strategy = await self._analyze_query_intent(query)

            print(f"[CatalogAgent] Search strategy: {search_strategy}")

            products = self._execute_search(search_strategy)

            if products:
                response = await self._generate_response(query, products, search_strategy)
            else:
                response = (
                    "I couldn't find any products matching your query. "
                    "Try asking about:\n"
                    "• Ropes (nylon, polypropylene)\n"
                    "• Wire and cables\n"
                    "• Storage bags\n"
                    "• Accessories (hooks, clips, thimbles)"
                )

            return AgentResponse(
                agent_name=self.name,
                response=response,
                data={"products": [p.model_dump() for p in products]},
                success=True,
            )

        except Exception as e:
            print(f"[CatalogAgent] Error: {e}")
            import traceback

            traceback.print_exc()
            return AgentResponse(
                agent_name=self.name,
                response="I encountered an error while searching the product catalog.",
                success=False,
                error=str(e),
            )

    async def _analyze_query_intent(self, query: str) -> Dict[str, Any]:
        system_prompt = """You are a product search analyzer. Analyze the user's query and determine what they're looking for.

Available product information:
- Categories: Ropes, Wire, Bags, Accessories
- Attributes: name, category, price, stock level, description, specifications
- Materials: nylon, polypropylene, steel

Your task: Determine the search strategy as JSON:
{
    "intent": "category_search" | "material_search" | "specific_product" | "price_query" | "inventory_check" | "show_all",
    "keywords": ["list", "of", "search", "terms"],
    "filters": {
        "category": "category name or null",
        "material": "material or null",
        "min_price": number or null,
        "max_price": number or null
    },
    "context": "brief explanation of what user wants"
}

IMPORTANT: Only use "show_all" if the user EXPLICITLY asks to see ALL products (e.g., "show me all products", "list everything", "what's your entire catalog").

For specific or vague requests, use category_search or material_search.

Examples:
Query: "What products do you have?" 
{"intent": "category_search", "keywords": ["products"], "filters": {}, "context": "Vague query - ask for clarification or show popular items"}

Query: "Do you have rope in stock?"
{"intent": "category_search", "keywords": ["rope"], "filters": {"category": "Ropes"}, "context": "User wants to see rope products"}

Query: "Show me nylon products"
{"intent": "material_search", "keywords": ["nylon"], "filters": {"material": "nylon"}, "context": "User wants nylon products"}

Query: "List all products" or "Show me your entire catalog"
{"intent": "show_all", "keywords": [], "filters": {}, "context": "User explicitly wants all products"}

Query: "Which rope would you recommend?"
{"intent": "category_search", "keywords": ["rope", "recommend"], "filters": {"category": "Ropes"}, "context": "User wants rope recommendations"}

Respond ONLY with valid JSON, no other text."""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Analyze this query: {query}"),
        ]

        response = await self.llm.ainvoke(messages)

        try:
            strategy = json.loads(response.content.strip())
            return strategy
        except json.JSONDecodeError:
            return {
                "intent": "category_search",
                "keywords": [],
                "filters": {},
                "context": "Fallback search",
            }

    def _execute_search(self, strategy: Dict[str, Any]) -> List[ProductModel]:
        filters = strategy.get("filters", {})
        keywords = strategy.get("keywords", [])

        sql = "SELECT * FROM products"
        conditions = []
        params = []

        if filters.get("category"):
            conditions.append("category = ?")
            params.append(filters["category"])

        if filters.get("material"):
            material = filters["material"]
            conditions.append("(name LIKE ? OR description LIKE ? OR specifications LIKE ?)")
            params.extend([f"%{material}%"] * 3)

        if keywords and not filters.get("category") and not filters.get("material"):
            keyword_conditions = []
            for keyword in keywords:
                keyword_conditions.append("(name LIKE ? OR category LIKE ? OR description LIKE ?)")
                params.extend([f"%{keyword}%"] * 3)
            if keyword_conditions:
                conditions.append(f"({' OR '.join(keyword_conditions)})")

        if filters.get("min_price"):
            conditions.append("unit_price >= ?")
            params.append(filters["min_price"])

        if filters.get("max_price"):
            conditions.append("unit_price <= ?")
            params.append(filters["max_price"])

        if conditions:
            sql += " WHERE " + " AND ".join(conditions)

        sql += " ORDER BY category, name"

        print(f"[CatalogAgent] Executing SQL: {sql}")
        print(f"[CatalogAgent] Params: {params}")

        return self._execute_sql(sql, tuple(params))

    async def _generate_response(
        self, query: str, products: List[ProductModel], strategy: Dict[str, Any]
    ) -> str:
        product_data = self._format_products_for_llm(products)

        system_prompt = """You are a helpful warehouse assistant. Present product information clearly and naturally.

Guidelines:
1. Answer the user's specific question
2. Group products by category when showing multiple items
3. Include: product name, SKU, price per unit, and stock level
4. Be conversational but professional
5. Use bullet points for lists
6. Don't add information not in the product data

Context: {context}

Product Data:
{product_data}"""

        messages = [
            SystemMessage(
                content=system_prompt.format(
                    context=strategy.get("context", "Product search"), product_data=product_data
                )
            ),
            HumanMessage(content=query),
        ]

        response = await self.llm.ainvoke(messages)
        return response.content.strip()

    def _format_products_for_llm(self, products: List[ProductModel]) -> str:
        if not products:
            return "No products found."

        formatted = []
        for p in products:
            formatted.append(
                f"{p.name} ({p.sku})\n"
                f"Category: {p.category}\n"
                f"Price: ${p.unit_price:.2f}/{p.unit_of_measure}\n"
                f"Stock: {p.quantity_on_hand} {p.unit_of_measure}s\n"
                f"Description: {p.description or 'N/A'}"
            )

        return "\n\n".join(formatted)