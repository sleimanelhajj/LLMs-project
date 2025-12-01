"""
Simple Employee Assistant Agent using LangChain's create_agent (ReAct pattern).

This single agent has access to all tools and can reason about which ones to use.
No need for multiple agents or an orchestrator - the LLM handles tool selection.

Tools are organized in separate utility files for maintainability:
- utils/catalog_tools.py - Product catalog search and details
- utils/order_tools.py - Order tracking and history
- utils/inventory_tools.py - Inventory management
- utils/sales_tools.py - Sales reports
- utils/company_tools.py - Company info (RAG-based)
- utils/invoice_tools.py - Invoice generation
"""

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import create_agent

from config import GOOGLE_API_KEY

# Import all tools from utility modules
from utils.catalog_tools import search_products, get_product_by_sku, list_categories
from utils.order_tools import track_order, get_order_history
from utils.inventory_tools import check_inventory, get_inventory_summary
from utils.sales_tools import get_sales_summary
from utils.company_tools import search_company_documents
from utils.invoice_tools import generate_invoice

# Re-export RAG initialization for the API


def create_employee_assistant():
    tools = [
        search_products,
        get_product_by_sku,
        list_categories,
        track_order,
        get_order_history,
        check_inventory,
        get_inventory_summary,
        get_sales_summary,
        search_company_documents,
        generate_invoice,
    ]

    model = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        google_api_key=GOOGLE_API_KEY,
        temperature=0.1,
    )

    # System prompt with ReAct format
    system_prompt = """You are a helpful Employee Assistant for a warehouse supply company.

You help employees with:
1. **Product Catalog** - Search products, check details, browse categories
2. **Order Tracking** - Track orders by ID, tracking number, or customer email
3. **Inventory** - Check stock levels, view low stock alerts, get inventory summaries
4. **Sales Reports** - View sales summaries and top products/customers
5. **Company Info** - Answer questions about policies, contact info, hours (uses RAG search)
6. **Invoice Generation** - Create invoices for customer orders

Guidelines:
- Be concise and helpful
- Use the appropriate tool for each request
- If you need more information, ask the user
- Format responses clearly with markdown
- For product searches, show relevant details
- For orders, always include the status and tracking info
- For invoices, you need customer name, email, and items with quantities

Available product categories: Ropes, Wire, Bags, Safety, Hardware, Packaging

Invoice format: Items should be specified as "SKU:quantity" (e.g., "PP-ROPE-12MM:10,HW-SHACKLE-10:5")

You have access to the following tools:

{tools}

Begin!

Question: {input}
Thought:{agent_scratchpad}"""

    # system_prompt is your long string (without the ReAct formatting section)
    agent = create_agent(
        model=model,
        tools=tools,
        system_prompt=system_prompt,
    )

    return agent
