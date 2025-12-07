"""
Utility modules for the Employee Assistant Agent.

Contains:
- db_utils: Database connection helpers
- rag_utils: RAG/Vector database functionality
- catalog_tools: Product catalog tools
- order_tools: Order tracking tools
- inventory_tools: Inventory management tools
- sales_tools: Sales reporting tools
- company_tools: Company info (RAG-based) tools
- invoice_tools: Invoice generation tools
"""

from tools.utils.db_utils import get_db_connection
from tools.utils.rag_utils import initialize_company_vector_db, search_company_vector_db
from tools.catalog_tools import search_products, get_product_by_sku, list_categories
from tools.order_tools import track_order, get_order_history
from tools.inventory_tools import check_inventory, get_inventory_summary
from tools.sales_tools import get_sales_summary
from tools.company_tools import search_company_documents
from tools.invoice_tools import generate_invoice
from tools.external_api_tools import (
    convert_currency,
    get_currency_rates,
    check_delivery_delays,
    calculate_business_days,
)

__all__ = [
    # Database
    "get_db_connection",
    # RAG
    "initialize_company_vector_db",
    "search_company_vector_db",
    # Tools
    "search_products",
    "get_product_by_sku",
    "list_categories",
    "track_order",
    "get_order_history",
    "check_inventory",
    "get_inventory_summary",
    "get_sales_summary",
    "search_company_documents",
    "generate_invoice",
    # External APIs
    "convert_currency",
    "get_currency_rates",
    "check_delivery_delays",
    "calculate_business_days",
]
