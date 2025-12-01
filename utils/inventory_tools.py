"""
Inventory Tools

Tools for checking inventory levels and getting inventory summaries.
"""

from typing import Optional
from langchain_core.tools import tool
from utils.db_utils import get_db_connection


@tool
def check_inventory(category: Optional[str] = None, low_stock_only: bool = False) -> str:
    """
    Check inventory levels across products.
    
    Args:
        category: Optional category filter
        low_stock_only: If True, only show items with less than 100 units
    
    Returns:
        Inventory summary with stock levels
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        query = """
            SELECT sku, name, category, quantity_on_hand, unit_price,
                   (quantity_on_hand * unit_price) as stock_value
            FROM products
        """
        params = []
        conditions = []
        
        if category:
            conditions.append("LOWER(category) = LOWER(?)")
            params.append(category)
        
        if low_stock_only:
            conditions.append("quantity_on_hand < 100")
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += " ORDER BY quantity_on_hand ASC LIMIT 15"
        
        cursor.execute(query, params)
        products = cursor.fetchall()
        
        if not products:
            return "No products found matching criteria"
        
        result = "**Inventory Status**\n\n"
        if low_stock_only:
            result += "⚠️ *Low Stock Items (< 100 units)*\n\n"
        
        total_value = 0
        for p in products:
            status = "🔴 CRITICAL" if p['quantity_on_hand'] < 50 else "🟡 LOW" if p['quantity_on_hand'] < 100 else "🟢 OK"
            result += f"**{p['name']}** ({p['sku']})\n"
            result += f"  Stock: {p['quantity_on_hand']} units {status}\n"
            result += f"  Value: ${p['stock_value']:,.2f}\n\n"
            total_value += p['stock_value']
        
        result += f"---\n**Total Value Shown:** ${total_value:,.2f}"
        
        return result
        
    finally:
        conn.close()


@tool  
def get_inventory_summary() -> str:
    """
    Get a high-level summary of inventory by category.
    
    Returns:
        Summary table with total products, units, and value by category
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT 
                category,
                COUNT(*) as product_count,
                SUM(quantity_on_hand) as total_units,
                SUM(quantity_on_hand * unit_price) as total_value
            FROM products
            GROUP BY category
            ORDER BY total_value DESC
        """)
        
        categories = cursor.fetchall()
        
        result = "**📊 Inventory Summary by Category**\n\n"
        result += "| Category | Products | Units | Value |\n"
        result += "|----------|----------|-------|-------|\n"
        
        grand_total_units = 0
        grand_total_value = 0
        
        for cat in categories:
            result += f"| {cat['category']} | {cat['product_count']} | {cat['total_units']:,} | ${cat['total_value']:,.2f} |\n"
            grand_total_units += cat['total_units']
            grand_total_value += cat['total_value']
        
        result += f"| **TOTAL** | **{sum(c['product_count'] for c in categories)}** | **{grand_total_units:,}** | **${grand_total_value:,.2f}** |"
        
        return result
        
    finally:
        conn.close()
