"""
Simple agent using LangGraph create_react_agent functionality (ReAct pattern).

Has access to all the tools defined in the utils/ directory.
"""

from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent
from config import GOOGLE_API_KEY, LLM_TEMPERATURE
from tools import (
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
    convert_currency,
    get_currency_rates,
    check_delivery_delays,
    calculate_business_days,
)


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
        convert_currency,
        get_currency_rates,
        check_delivery_delays,
        calculate_business_days,
    ]

    model = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",  
        google_api_key=GOOGLE_API_KEY,
        temperature=LLM_TEMPERATURE,
        top_p=0.95,
    )

    system_prompt = """You are a helpful Employee Assistant for a warehouse supply company.

CRITICAL RULES:
1. For ANY question about products, orders, inventory, sales, or company info → CALL THE APPROPRIATE TOOL IMMEDIATELY
2. Do NOT answer from memory - ALWAYS use tools for data
3. When a tool returns HTML output, return it EXACTLY as-is without modification
4. Only give a greeting if the user ONLY says hello/hi with no other request

TOOL MAPPING:
- Products/items/rope/wire/etc → search_products or get_product_by_sku
- Categories → list_categories  
- Orders/tracking → track_order or get_order_history
- Inventory/stock → check_inventory or get_inventory_summary
- Sales/revenue → get_sales_summary
- Policies/hours/contact → search_company_documents
- Invoice → generate_invoice
- Currency → convert_currency or get_currency_rates
- Holidays/delays → check_delivery_delays or calculate_business_days

TOOL OUTPUT FORMAT:
Tools return HTML with <table>, <strong>, <br> tags. Return this HTML EXACTLY as received.

DEFAULT PARAMETERS:
- Sales period: "30days" (unless specified: "7days", "90days", "all")
- Invoice currency: "USD" (unless specified: EUR, GBP, etc.)
- Country code: "US" (unless specified)

Be concise. Focus on the current user message only, ignore previous greetings."""

    agent = create_react_agent(
        model=model,
        tools=tools,
        prompt=system_prompt,
    )

    return agent